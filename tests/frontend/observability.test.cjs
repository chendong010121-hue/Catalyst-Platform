// Deterministic presentation checks. Synthetic records only, no Provider/credentials.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../catalyst_platform/workspace_assets/app.js'),'utf8');
const moduleText=source.split('// OBSERVABILITY_MODULE_BEGIN')[1].split('// OBSERVABILITY_MODULE_END')[0].split('\n').slice(1).join('\n');
const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function setup(api=async()=>{throw Error('unexpected read')}){
 const S={runs:[],run:null,result:null,meta:{source_identity:{commit:'synthetic'}},workText:{},route:'home'};
 const context={S,escape,api,head:()=>'',note:()=>'',empty:(a,b)=>a+' '+b,statusText:v=>v,render:()=>{},Intl,Date,Map,Set,Number,JSON,Promise,matchMedia:()=>({matches:true})};
 vm.createContext(context);vm.runInContext(moduleText+';globalThis.O=Observability;',context);return {O:context.O,S};
}
function trace(overrides={}){return {run_id:'offline-run',status:'success',events:[
 {event_type:'request.started',sequence:0,timestamp:'2026-10-24T02:00:00Z'},
 {event_type:'span.started',sequence:1,span_id:'span',span_name:'llm.request',model_call_id:'m'},
 {event_type:'llm.request.started',sequence:2,model_call_id:'m',span_id:'span',model:'deepseek-flash',provider_id:'deepseek'},
 {event_type:'llm.response.received',sequence:3,model_call_id:'m',span_id:'span',input_tokens:100,output_tokens:20},
 {event_type:'span.ended',sequence:4,span_id:'span',status:'success',duration_ms:230},
 {event_type:'request.terminal',sequence:5,terminal_status:'success',duration_ms:250}],...overrides};}
function receipt(){return {mode:'LIVE_CHAT',external_calls:1,status:'success',budget:{charged_cny:'7.99'},model_receipt:{peak_rate_estimated_cny:'0.00036',usage:{prompt_tokens:100,completion_tokens:20}}};}
test('projects actual response and span duration, not cumulative task spending',()=>{const {O}=setup();const p=O.project(trace(),receipt());assert.equal(p.cost,0.00036);assert.equal(p.input,100);assert.equal(p.output,20);assert.equal(p.calls[0].ms,230);assert.equal(p.ms,250);});
test('missing usage remains unknown, not zero',()=>{const t=trace();delete t.events[3].input_tokens;const p=setup().O.project(t,receipt());assert.equal(p.calls[0].input,null);assert.equal(p.completeUsage,false);assert.equal(p.cost,null);});
test('malformed negative, string, fractional token values are not usage',()=>{for(const input of [-1,'100',1.5,Infinity]){const t=trace();t.events[3].input_tokens=input;assert.equal(setup().O.project(t).calls[0].input,null);}});
test('MOCK cannot produce a genuine cost receipt',()=>{const r=receipt();r.mode='MOCK';assert.equal(setup().O.project(trace(),r).cost,null);});
test('receipt token mismatch cannot qualify cost',()=>{const r=receipt();r.model_receipt.usage.prompt_tokens=999;assert.equal(setup().O.project(trace(),r).cost,null);});
test('scope cumulative-only amount is never used as run cost',()=>{const r=receipt();delete r.model_receipt;assert.equal(setup().O.project(trace(),r).cost,null);});
test('multi-call receipt is not attributed to the whole run',()=>{const t=trace();t.events.push({event_type:'llm.request.started',model_call_id:'m2'});assert.equal(setup().O.project(t,receipt()).cost,null);});
test('transport start without receipt does not invent sent or metered status',()=>{const t=trace({events:[{event_type:'llm.request.started',model_call_id:'m'}],status:'incomplete'});const p=setup().O.project(t);assert.equal(p.external,null);assert.equal(p.calls[0].status,'无完整响应');assert.match(setup().O.stages(p),/无完整终态/);});
test('denied tool does not create a tool execution',()=>{const p=setup().O.project(trace({events:[{event_type:'tool.execution.denied'}]}));const ui=setup().O.stages(p);assert.match(ui,/工具拒绝 1/);assert.doesNotMatch(ui,/工具执行/);});
test('local information stage has no fabricated LLM or tool phase',()=>{const p=setup().O.project(trace({events:[{event_type:'request.started'},{event_type:'request.terminal',terminal_status:'success'}]}),{mode:'LOCAL_INFO'});assert.doesNotMatch(setup().O.stages(p),/模型|工具/);});
test('bounded initial reads use only GET-shaped api calls and at most two concurrent reads',async()=>{let active=0,peak=0,calls=[];const {O,S}=setup(async(...args)=>{assert.equal(args.length,1);calls.push(args[0]);active++;peak=Math.max(active,peak);await new Promise(r=>setTimeout(r,1));active--;return args[0].endsWith('/result')?receipt():trace();});S.runs=Array.from({length:30},(_,i)=>({run_id:'r'+i,last_sequence:5,status:'success'}));await O.load();assert.equal(calls.length,24);assert.equal(peak,2);assert.match(O.page(),/已载入 12 条/);assert.match(O.page(),/再载入12条/);assert.ok(calls.every(p=>p.startsWith('/api/runs/')));});
test('a failed read stays visible and produces no demo fallback',async()=>{const {O,S}=setup(async()=>{throw Error('offline failure')});S.runs=[{run_id:'r0'}];await O.load();assert.match(O.page(),/部分运行读取失败/);assert.match(O.page(),/已载入 0 条/);});
test('raw events are escaped, initially collapsed, and uncollected context is explicit',()=>{const {O,S}=setup();S.run=trace();S.run.events.push({event_type:'span.started',span_id:'x',span_name:'<img src=x onerror=alert(1)>'});S.result=receipt();const ui=O.page();assert.ok(ui.includes('&lt;img'));assert.ok(!ui.includes('<img'));assert.ok(!ui.includes('<details open'));});
test('unknown model selection never changes active provider or submits work',()=>{assert.doesNotMatch(moduleText,/\/api\/(ask|settings|uploads|cancel)|localStorage|sessionStorage/);assert.doesNotMatch(moduleText,/\bfetch\(/);assert.ok(source.includes('Observability.stages'));});


test('missing and UNKNOWN-mode usage never appears as zero or paid consumption',async()=>{const {O,S}=setup(async p=>p.endsWith('/result')?null:trace());S.runs=[{run_id:'r',last_sequence:5,status:'success'}];await O.load();const ui=O.page();assert.match(ui,/已报告 Token<\/small><strong>未记录/);assert.doesNotMatch(ui,/class="obs-bar-col"/);});
test('charts and hierarchy preserve CSP without inline styles',()=>{const {O,S}=setup();S.run=trace();S.result=receipt();assert.doesNotMatch(O.page(),/ style=/);});
test('collapsed raw details do not construct raw JSON before expansion',()=>{const {O,S}=setup();S.run=trace();S.result=receipt();assert.doesNotMatch(O.page(),/class="raw-json"/);});
test('terminal result 404 can be reread on explicit refresh',async()=>{let ready=false;const {O,S}=setup(async p=>{if(p.endsWith('/result')){if(!ready){const e=Error('not committed');e.status=404;throw e;}return receipt();}return trace();});S.runs=[{run_id:'r',last_sequence:5,status:'success'}];await O.load();assert.match(O.page(),/UNKNOWN/);ready=true;await O.load();assert.match(O.page(),/LIVE_CHAT/);});
test('stale cache version is excluded and failed refresh does not retain old facts',async()=>{let failed=false;const {O,S}=setup(async p=>{if(failed)throw Error('read fail');return p.endsWith('/result')?receipt():trace();});S.runs=[{run_id:'r',last_sequence:5,status:'success'}];await O.load();assert.match(O.page(),/已载入 1 条/);S.runs[0].last_sequence=6;assert.match(O.page(),/已载入 0 条/);failed=true;await O.load();assert.match(O.page(),/已载入 0 条/);});
test('new selected result merges through the same presentation seam',async()=>{const {O,S}=setup();S.runs=[{run_id:'offline-run',last_sequence:5,status:'success'}];O.remember(trace(),receipt());assert.match(O.page(),/已载入 1 条/);assert.match(O.page(),/0.000360/);});
test('read queue bound also covers selected-run reads',async()=>{let active=0,max=0;const {O}=setup(async()=>{active++;max=Math.max(active,max);await new Promise(r=>setTimeout(r,2));active--;return {};});await Promise.all(Array.from({length:8},()=>O.read('/api/runs/a')));assert.equal(max,2);});
test('old selected GET cannot overwrite newer selection',async()=>{const {O,S}=setup();const requests=new Map();let rendered=0;const c={S,Observability:{...O,read:p=>new Promise(r=>requests.set(p,r))},stream:null,runReadGeneration:0,render:()=>rendered++,watchRun:()=>{throw Error('unexpected stream')},refresh:async()=>{}};vm.createContext(c);const fn=source.slice(source.indexOf('async function readRun('),source.indexOf('\nfunction watchRun('));vm.runInContext(fn,c);const a=c.readRun('A');const b=c.readRun('B');requests.get('/api/runs/B')({...trace(),run_id:'B'});await new Promise(setImmediate);requests.get('/api/runs/B/result')(receipt());await b;requests.get('/api/runs/A')({...trace(),run_id:'A'});await new Promise(setImmediate);requests.get('/api/runs/A/result')(receipt());await a;assert.equal(S.run.run_id,'B');assert.equal(rendered,1);});
test('stale SSE is ignored after selection changes',async()=>{let instance;class ES{constructor(){this.listeners={};instance=this;}addEventListener(t,f){this.listeners[t]=f;}close(){}}const S={run:{run_id:'A'},events:[],route:'runs'};let renders=0;const c={S,stream:null,EventSource:ES,render:()=>renders++,readRun:()=>{throw Error('old stream switched selection')},refresh:async()=>{},toast:()=>{}};vm.createContext(c);const fn=source.slice(source.indexOf('function watchRun('),source.indexOf('\nasync function submit('));vm.runInContext(fn,c);c.watchRun('A');S.run={run_id:'B'};await instance.listeners['run.event']({data:JSON.stringify({event_type:'request.terminal',run_id:'A',sequence:9})});assert.equal(S.events.length,0);assert.equal(renders,0);});

test('selected run detail appears between its row and the next run',()=>{
 const {O,S}=setup();const a=trace({run_id:'run-A'}),b=trace({run_id:'run-B'});
 S.runs=[{run_id:'run-A',last_sequence:5,status:'success'},{run_id:'run-B',last_sequence:5,status:'success'}];
 O.remember(a,receipt());O.remember(b,receipt());S.run=a;S.result=receipt();
 const html=O.page();assert.ok(html.indexOf('data-obs-run="run-A"')<html.indexOf('id="obs-detail"'));
 assert.ok(html.indexOf('id="obs-detail"')<html.indexOf('data-obs-run="run-B"'));
 assert.match(html,/class="obs-detail-row"/);assert.match(html,/aria-expanded="true"/);
 assert.equal((html.match(/id="obs-detail"/g)||[]).length,1);
});

test('inline running detail uses newly streamed selected events',()=>{
 const {O,S}=setup();const a=trace({run_id:'run-A',status:'running',events:[{event_type:'request.started',sequence:0}]});
 S.runs=[{run_id:'run-A',last_sequence:0,status:'running'}];O.remember(a,null);S.run=a;
 S.run.events.push({event_type:'span.started',sequence:1,span_id:'live',span_name:'STREAMED-LIVE-SPAN'});
 const html=O.page();assert.match(html,/STREAMED-LIVE-SPAN/);assert.match(html,/obs-run-row selected is-running/);
});

test('terminal evidence clears running emphasis even before the run summary refreshes',()=>{
 const {O}=setup();const p=O.project(trace({status:'running'}),receipt());
 assert.equal(p.status,'success');
});

test('detail prioritizes task context and keeps technical identity in a closed disclosure',()=>{
 const {O,S}=setup();S.run=trace();S.result=receipt();S.workText[S.run.run_id]='检查申请流程';
 const html=O.page();assert.match(html,/<h2[^>]*>检查申请流程<\/h2>/);
 assert.match(html,/<details class="disclosure obs-identity"[^>]*><summary>运行身份与数据边界<\/summary>/);
 assert.doesNotMatch(html,/<details class="disclosure obs-identity"[^>]*\bopen\b/);
 assert.doesNotMatch(html,/role="tablist"|role="tab"/);
 assert.match(html,/role="group" aria-label="运行详情视图"/);
 assert.match(html,/aria-pressed="true"/);
 assert.match(html,/业务语义：未评价/);
});

test('run records expose one whole-row interaction without duplicate close or arrow controls',()=>{
 const {O,S}=setup();S.run=trace();S.result=receipt();const html=O.page();
 assert.match(html,/data-obs-row="offline-run"/);
 assert.doesNotMatch(html,/id="obs-close"|obs-disclosure-arrow/);
 assert.match(html,/data-obs-run="offline-run"/);
});
