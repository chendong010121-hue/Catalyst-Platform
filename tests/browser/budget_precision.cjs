// Original settings page -> original settings API; fake Provider, no paid calls.
const {chromium}=require('C:/Users/13752/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path');
const output=path.resolve(process.argv[2]),workspace=path.resolve(process.argv[3]);
const product=path.resolve(__dirname,'../..'),base='http://127.0.0.1:8810';
if(fs.existsSync(output)||fs.existsSync(workspace))throw Error('Fresh test output/workspace required');
fs.mkdirSync(output,{recursive:true});
const env={PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'};
for(const k of ['Path','PATH','SystemRoot','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'])if(process.env[k]!==undefined)env[k]=process.env[k];
const check=(ok,message)=>{if(!ok)throw Error(message)};
let child,browser;
(async()=>{try{
 child=spawn('python',['-u','-m','tests.browser.project_fixture','--workspace',workspace,'--out',output,'--port','8810'],{cwd:product,env,windowsHide:true});
 child.stdout.pipe(fs.createWriteStream(path.join(output,'service.log')));
 child.stderr.pipe(fs.createWriteStream(path.join(output,'service-error.log')));
 let ready=false;
 for(let i=0;i<100;i++){await new Promise(r=>setTimeout(r,100));try{ready=(await fetch(base+'/api/settings')).ok;if(ready)break}catch{}}
 check(ready,'Fixture service unavailable');
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage();
 await page.goto(base+'/#settings',{waitUntil:'networkidle'});
 const amount=page.locator('#model-form [name=budget_cny]');
 await amount.fill('1.286144');
 const validity=await amount.evaluate(el=>({valid:el.checkValidity(),stepMismatch:el.validity.stepMismatch}));
 check(validity.valid&&!validity.stepMismatch,'Exact six-decimal budget rejected by the platform form');
 for(const bad of ['0','10.000001','1.2861445']){
   await amount.fill(bad);check(!(await amount.evaluate(el=>el.checkValidity())),'Out-of-range/precision budget accepted: '+bad);
 }
 await amount.fill('1.286144');
 await page.locator('[name=api_key]').fill('OFFLINE-BROWSER-FIXTURE-NOT-A-KEY');
 await page.locator('[name=max_requests]').fill('8');
 await page.locator('[name=max_output_tokens]').selectOption('4096');
 await page.locator('[name=allow_project_read]').check();
 await page.locator('[name=consent]').check();
 const posted=page.waitForResponse(r=>r.url()===base+'/api/settings'&&r.request().method()==='POST');
 await page.locator('#model-form [type=submit]').click();
 const response=await posted;check(response.ok(),'Original settings API rejected configuration');
 const sent=response.request().postDataJSON();delete sent.data.api_key;
 check(sent.data.budget_cny==='1.286144','UI changed the exact budget before sending');
 const saved=await(await fetch(base+'/api/settings')).json();
 check(saved.budget.budget_cny==='1.286144','Backend did not preserve exact budget');
 check(saved.budget.max_requests===8,'Request cap changed');
 check(saved.reserved_requests===0&&saved.budget.attempts===0,'Saving settings dispatched a model');
 check(saved.allow_project_read&&!saved.allow_asset_read,'Source permissions changed');
 fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify({verdict:'PASS',kind:'ORIGINAL_UI_FAKE_PROVIDER',validity,sent,saved,real_api_calls:0},null,2));
 console.log('PLATFORM_BUDGET_PRECISION_PASS');
}catch(error){fs.writeFileSync(path.join(output,'failure.json'),JSON.stringify({error:String(error)}));throw error}
finally{if(browser)await browser.close();if(child){const done=new Promise(r=>child.once('exit',r));child.kill();await done}}})().catch(e=>{console.error(e);process.exitCode=1});
