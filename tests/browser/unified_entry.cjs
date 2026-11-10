// Synthetic browser acceptance over the original product entry and transport seam.
// Never a production launcher, paid model test, optimizer or semantic evaluator.
const {chromium}=require('C:/Users/13752/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');const path=require('node:path');
const product=path.resolve(__dirname,'../..');
const output=path.resolve(process.argv[2]);const primary=path.resolve(process.argv[3]);
const probe=process.argv.includes('--allow-dirty-probe');
const base='http://127.0.0.1:8801';
const fixtureKey='OFFLINE-INTEGRATION-KEY-NOT-A-CREDENTIAL';
if(fs.existsSync(output)||fs.existsSync(primary))throw Error('Fresh evidence and primary workspace required');
fs.mkdirSync(output,{recursive:true});
const safeEnv={PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'};
for(const name of ['Path','PATH','SystemRoot','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'])
 if(process.env[name]!==undefined)safeEnv[name]=process.env[name];
let child,browser,page,phase='setup',view=0;const runs=[],errors=[],external=[],identities=[];
function assert(value,message){if(!value)throw Error(message)}
function readCalls(out){const file=path.join(out,'deterministic-calls.jsonl');return fs.existsSync(file)?fs.readFileSync(file,'utf8').trim().split(/\r?\n/).filter(Boolean).map(JSON.parse):[]}
async function api(url){const response=await fetch(base+url);return {status:response.status,body:await response.json()}}
async function start(workspace,out){
 fs.mkdirSync(out,{recursive:true});
 child=spawn('python',['-u','-m','tests.browser.workspace_fixture','--workspace',workspace,'--out',out,'--port','8801'],
  {cwd:product,env:safeEnv,windowsHide:true});
 child.stdout.pipe(fs.createWriteStream(path.join(out,'service.log')));child.stderr.pipe(fs.createWriteStream(path.join(out,'service-error.log')));
 let meta;
 for(let i=0;i<80;i++){await new Promise(r=>setTimeout(r,200));try{const reply=await api('/api/workspace');if(reply.status===200){meta=reply.body;break}}catch{}}
 assert(meta,'Fixture service unavailable');
 assert(meta.source_identity.source_root.replaceAll('\\','/').toLowerCase()===product.replaceAll('\\','/').toLowerCase(),'Wrong product root');
 assert(probe||meta.source_identity.dirty===false,'Final source not clean');identities.push(meta.source_identity);
 const ready=JSON.parse(fs.readFileSync(path.join(out,'ready.json'),'utf8'));
 assert(ready.ledger_source.replaceAll('\\','/').includes('/_vendor/dispatch_ledger_v1.py'),'Packaged ledger not used');
 await page.goto(base+'/?qa-home='+(++view)+'#home',{waitUntil:'networkidle'});await page.locator('#message-input').waitFor();
}
async function stop(){if(child){const ended=new Promise(r=>child.once('exit',r));child.kill();await ended;child=null}}
async function settings(tab='models'){
 // A full settings navigation closes previous SSE and waits for both startup
 // reads before filling. Filling the initial render races its async refresh.
 await page.goto(base+'/?qa-view='+(++view)+'#settings',{waitUntil:'networkidle'});
 await page.locator('[data-tab="'+tab+'"]').click();
 await page.locator(tab==='models'?'#model-form':'#profile-form').waitFor();
}
async function configure(asset=false,limit=2){
 await settings();
 await page.locator('[name=api_key]').fill(fixtureKey);
 await page.locator('[name=max_requests]').fill(String(limit));
 await page.locator('[name=budget_cny]').fill('1');
 await page.locator('[name=max_output_tokens]').selectOption('1024');
 await page.locator('[name=consent]').check();
 await page.locator('[name=allow_asset_read]').setChecked(asset);
 const response=page.waitForResponse(r=>r.url()===base+'/api/settings'&&r.request().method()==='POST');
 await page.locator('#model-form [type=submit]').click();const reply=await response;
 assert(reply.ok(),'Model fixture scope rejected: '+JSON.stringify(await reply.json()));
 const state=(await api('/api/settings')).body;assert(state.configured,'Scope not configured');
 await page.waitForFunction(()=>document.querySelector('[name=api_key]')?.value==='');
}
async function result(id){
 for(let i=0;i<120;i++){const reply=await api('/api/runs/'+id+'/result');if(reply.status===200)return reply.body;await new Promise(r=>setTimeout(r,150))}
 throw Error('Result unavailable: '+id)
}
async function submit(text,wait=true){
 await page.goto(base+'/?qa-home='+(++view)+'#home',{waitUntil:'networkidle'});await page.locator('#message-input').fill(text);
 const response=page.waitForResponse(r=>r.url()===base+'/api/ask'&&r.request().method()==='POST');
 await page.locator('#composer [type=submit]').click();const reply=await response;assert(reply.ok(),'Ask refused at HTTP boundary');
 const id=(await reply.json()).run_id;
 if(!wait)return id;
 const value=await result(id);runs.push(value);return value;
}
async function disconnect(){await settings();await page.locator('#disconnect-model').click();
 for(let i=0;i<30;i++){if((await api('/api/settings')).body.key_status==='MISSING')return;await new Promise(r=>setTimeout(r,100))}
 throw Error('Scope did not disconnect')}
async function verifyFence(out){const value=JSON.parse(fs.readFileSync(path.join(out,'fences.json'),'utf8'));
 assert(!value.external_attempts.length&&!value.forbidden_reads.length,'Fixture fence violation')}
(async()=>{
 try{
  browser=await chromium.launch({headless:true,args:['--disable-background-networking','--disable-sync']});
  page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{const url=route.request().url();if(url.startsWith(base+'/')||url.startsWith('data:'))await route.continue();else{external.push(url);await route.abort()}});
  phase='main';const mainOut=path.join(output,'main');await start(primary,mainOut);
  await settings('profile');await page.locator('[name=display_name]').fill('离线验收用户');
  await page.locator('[name=workspace_name]').fill('合成资料 · 集成验收');
  const profileSave=page.waitForResponse(r=>r.url()===base+'/api/settings'&&r.request().method()==='POST');
  await page.locator('#profile-form [type=submit]').click();assert((await profileSave).ok(),'Profile save failed');
  const local=await submit('你能做什么？');assert(local.mode==='LOCAL_INFO'&&!readCalls(mainOut).length,'Local info called a model');
  await configure(true,2);assert(!readCalls(mainOut).length,'Saving configuration dispatched');
  const used=await submit('请读取现有系统组件清单（离线合成验收）');
  assert(used.state==='CHAT_COMPLETED'&&used.asset_read_verified&&used.lifecycle.handle_released,'Original asset/Runtime/lifecycle chain incomplete');
  assert(readCalls(mainOut).length===2,'Tool pair did not use exactly two deterministic exchanges');
  await page.getByText('离线模型替身',{exact:false}).first().waitFor();
  await page.screenshot({path:path.join(output,'work.png'),fullPage:true});
  const capped=await submit('请求额度耗尽后不得再发出调用');assert(capped.state==='BLOCKED'&&readCalls(mainOut).length===2,'Request limit bypass');
  await disconnect();
  await page.goto(base+'/?qa-home='+(++view)+'#home',{waitUntil:'networkidle'});await page.locator('#load-example').click();
  const uploadAsk=page.waitForResponse(r=>r.url()===base+'/api/ask'&&r.request().method()==='POST');
  await page.locator('#composer [type=submit]').click();const uploadedId=(await(await uploadAsk).json()).run_id;
  const captured=await result(uploadedId);runs.push(captured);
  assert(captured.execution_entry==='HarnessSession.capture_execution'&&!captured.version_id,'MOCK document path or formal-write boundary changed');
  for(const route of ['wiki','enterprise','reviews','agents','runs']){
   await page.goto(base+'/#'+route);await page.locator('h1').first().waitFor();
   await page.waitForTimeout(300);await page.screenshot({path:path.join(output,route+'.png'),fullPage:true});
  }
  await page.setViewportSize({width:390,height:844});await page.goto(base+'/?qa-home='+(++view)+'#home',{waitUntil:'networkidle'});
  await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});await page.setViewportSize({width:1440,height:1000});
  await verifyFence(mainOut);await stop();
  phase='main-cold';const coldOut=path.join(output,'main-cold');await start(primary,coldOut);
  let state=(await api('/api/settings')).body;assert(state.key_status==='MISSING'&&!state.enabled,'Credential restored on cold start');
  assert(state.profile.display_name==='离线验收用户','Profile did not persist');
  assert((await result(used.run_id)).lifecycle.handle_released,'Evidence not cold-readable');
  assert(!readCalls(coldOut).length,'Cold start replayed a model call');await verifyFence(coldOut);await stop();
  phase='timeout';const failedRoot=path.join(output,'timeout-workspace'),failedOut=path.join(output,'timeout');
  await start(failedRoot,failedOut);await configure(false,2);
  const failed=await submit('OFFLINE_FIXTURE_TIMEOUT');assert(failed.state!=='CHAT_COMPLETED'&&readCalls(failedOut).length===1,'Timeout invalid');
  assert(!failed.lifecycle.handle_released,'Nonterminal failure released');
  await submit('不得重试未知请求');assert(readCalls(failedOut).length===1,'Uncertain request repeated');
  await disconnect();await verifyFence(failedOut);await stop();
  phase='timeout-cold';const failedCold=path.join(output,'timeout-cold');await start(failedRoot,failedCold);
  state=(await api('/api/settings')).body;assert(state.key_status==='MISSING','Unknown scope restored credential');
  const refusal=await page.evaluate(async key=>{const c=await(await fetch('/api/config')).json();const r=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json','X-Catalyst-CSRF':c.csrf_token},body:JSON.stringify({action:'model',data:{api_key:key,provider_id:'deepseek',model:'deepseek-flash',max_requests:2,budget_cny:'1',max_output_tokens:1024,consent:true,allow_asset_read:false}})});return {status:r.status,body:await r.json()}},fixtureKey);
  assert(refusal.status===400&&!readCalls(failedCold).length,'Cold unknown scope permitted new dispatch');
  await verifyFence(failedCold);await stop();
  phase='cancel';const cancelOut=path.join(output,'cancel');await start(path.join(output,'cancel-workspace'),cancelOut);await configure(false,2);
  const cancelId=await submit('OFFLINE_FIXTURE_SLOW',false);
  for(let i=0;i<50&&!readCalls(cancelOut).length;i++)await page.waitForTimeout(100);
  await page.locator('#cancel').click();const cancelled=await result(cancelId);runs.push(cancelled);
  assert(cancelled.state==='CANCELLED'&&readCalls(cancelOut).length===1,'Cancellation did not stop follow-up');
  await verifyFence(cancelOut);await disconnect();await stop();
  assert(!errors.length&&!external.length,'Browser errors/external requests: '+JSON.stringify({errors,external}));
  fs.writeFileSync(path.join(output,'BROWSER_RECEIPT.json'),JSON.stringify({verdict:probe?'PROBE_ONLY':'PASS_OFFLINE_BROWSER',
   identities,runs,errors,external,real_paid_api_calls:0,real_key_reads:0,
   model_results:'DETERMINISTIC_FIXTURES_NOT_SEMANTIC_QUALITY',preview_data:primary},null,2));
  console.log('UNIFIED_ENTRY_BROWSER_PASS');
 }catch(error){
  let body='';if(page){body=await page.locator('body').innerText().catch(()=> '');await page.screenshot({path:path.join(output,'failure.png'),fullPage:true}).catch(()=>{});}
  fs.writeFileSync(path.join(output,'FAILURE.json'),JSON.stringify({phase,error:error.message,body,errors,external,runs},null,2));throw error;
 }finally{await stop();if(browser)await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
