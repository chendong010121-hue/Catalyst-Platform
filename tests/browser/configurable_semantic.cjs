// Local browser + actual Monitor/Harness/Runtime, deterministic transport only.
const {chromium}=require('C:/Users/13752/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {spawn}=require('node:child_process'),fs=require('node:fs'),path=require('node:path');
const out=path.resolve(process.argv[2]),workspace=path.resolve(process.argv[3]),base='http://127.0.0.1:8812';
if(fs.existsSync(out)||fs.existsSync(workspace))throw Error('Fresh outputs required');fs.mkdirSync(out,{recursive:true});
const env={PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'};
for(const k of ['PATH','Path','SystemRoot','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'])if(process.env[k]!==undefined)env[k]=process.env[k];
let child,browser;const check=(v,m)=>{if(!v)throw Error(m)};
(async()=>{try{
 child=spawn('python',['-u','-m','tests.browser.project_fixture','--semantic','--workspace',workspace,'--out',out,'--port','8812'],{cwd:path.resolve(__dirname,'../..'),env,windowsHide:true});
 child.stdout.pipe(fs.createWriteStream(path.join(out,'service.log')));child.stderr.pipe(fs.createWriteStream(path.join(out,'service-error.log')));
 let ready=false;for(let i=0;i<100;i++){await new Promise(r=>setTimeout(r,100));try{ready=(await fetch(base+'/api/settings')).ok;if(ready)break}catch{}}check(ready,'Service unavailable');
 browser=await chromium.launch({headless:true});const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(base+'/#settings',{waitUntil:'networkidle'});
 await page.locator('[name=api_key]').fill('OFFLINE-BROWSER-ONLY-NOT-A-KEY');await page.locator('[name=max_requests]').fill('2');await page.locator('[name=budget_cny]').fill('1');
 await page.locator('[name=max_output_tokens]').selectOption('1024');await page.locator('[name=consent]').check();
 const saved=page.waitForResponse(r=>r.url()===base+'/api/settings'&&r.request().method()==='POST');await page.locator('#model-form [type=submit]').click();check((await saved).ok(),'Settings rejected');
 await page.goto(base+'/#experiments',{waitUntil:'networkidle'});
 const form=page.locator('#project-test-form');await form.locator('[name=source_id]').selectOption('synthetic-documents');
 await form.locator('[name=objective]').fill('理解组织职责，形成有来源的候选');await form.locator('summary').click();
 await form.locator('[name=max_requests]').fill('4');await form.locator('[name=max_output_tokens]').fill('1024');
 const prepared=page.waitForResponse(r=>r.url()===base+'/api/project-tests'&&r.request().method()==='POST');await form.locator('[type=submit]').click();check((await prepared).ok(),'Card rejected');
 let cards=await(await fetch(base+'/api/project-tests')).json();let card=cards.items[0];
 check(card.card.task_kind==='enterprise_semantics'&&card.card.max_requests===4&&card.card.max_output_tokens===1024,'Wrong bound profile');
 check(card.card.source_preflight.files[0].locators>0&&card.model_requests===0,'Prepare was not zero-model/readable');
 await page.screenshot({path:path.join(out,'review-card.png'),fullPage:true});
 const started=page.waitForResponse(r=>r.url()===base+'/api/project-tests'&&r.request().method()==='POST');await page.locator('[data-test-execute]').click();const response=await started;check(response.status()===202,'Monitor rejected');const {run_id}=await response.json();
 let result;for(let i=0;i<100;i++){const r=await fetch(base+'/api/runs/'+run_id+'/result');if(r.ok){result=await r.json();break}await new Promise(r=>setTimeout(r,150))}
 check(result?.status==='success',JSON.stringify(result));check(result.capture.boundary==='BEFORE_HARVEST'&&result.source_coverage.unread.length===0,'Wrong capture/coverage');
 cards=await(await fetch(base+'/api/project-tests')).json();card=cards.items[0];check(card.model_requests===2&&card.state==='FINISHED','Wrong settlement');
 const settings=await(await fetch(base+'/api/settings')).json();check(settings.budget.attempts===0,'Daily ledger consumed');
 const trace=await(await fetch(base+'/api/runs/'+run_id)).json();check(trace.events.some(e=>e.event_type==='tool.execution.started'&&e.capability_id==='understand'),'Missing Understand R4');
 check(!JSON.stringify(JSON.parse(fs.readFileSync(path.join(out,'fake-calls.json')))).includes('是否有来源支持职责归属'),'Review leaked to Subject');
 check(errors.length===0,errors.join('\n'));await page.goto(base+'/#experiments',{waitUntil:'networkidle'});await page.screenshot({path:path.join(out,'result.png'),fullPage:true});
 fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({verdict:'PASS_WITH_LIMITS',kind:'FAKE_NOT_LIVE',real_api_calls:0,result,card,trace,errors},null,2));console.log('CONFIGURABLE_SEMANTIC_BROWSER_PASS');
}finally{if(browser)await browser.close();if(child){const done=new Promise(r=>child.once('exit',r));child.kill();await done}}})().catch(e=>{console.error(e);process.exitCode=1});
