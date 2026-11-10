// Browser -> reviewed card -> ORIGINAL Monitor/Runtime/fake Provider/P0/Evaluation.
const {chromium}=require('C:/Users/13752/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {spawn}=require('node:child_process'),fs=require('node:fs'),path=require('node:path');
const out=path.resolve(process.argv[2]),workspace=path.resolve(process.argv[3]);
if(fs.existsSync(out)||fs.existsSync(workspace))throw Error('Fresh outputs required');
fs.mkdirSync(out,{recursive:true});const base='http://127.0.0.1:8811',product=path.resolve(__dirname,'../..');
const env={PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'};
for(const k of ['PATH','Path','SystemRoot','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'])if(process.env[k]!==undefined)env[k]=process.env[k];
const check=(v,m)=>{if(!v)throw Error(m)};let child,browser;
(async()=>{try{
 child=spawn('python',['-u','-m','tests.browser.project_fixture','--workspace',workspace,'--out',out,'--port','8811'],{cwd:product,env,windowsHide:true});
 child.stdout.pipe(fs.createWriteStream(path.join(out,'service.log')));child.stderr.pipe(fs.createWriteStream(path.join(out,'service-error.log')));
 let ready=false;for(let i=0;i<100;i++){await new Promise(r=>setTimeout(r,100));try{ready=(await fetch(base+'/api/settings')).ok;if(ready)break}catch{}}
 check(ready,'Service unavailable');browser=await chromium.launch({headless:true});const page=await browser.newPage();const errors=[];
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('pageerror',e=>fs.appendFileSync(path.join(out,'events.log'),'ERROR '+String(e)+'\n'));
 page.on('request',r=>{if(r.method()==='POST')fs.appendFileSync(path.join(out,'events.log'),'POST '+r.url()+'\n')});
 page.on('response',r=>{if(r.request().method()==='POST')fs.appendFileSync(path.join(out,'events.log'),'RESPONSE '+r.status()+' '+r.url()+'\n')});
 await page.goto(base+'/#settings',{waitUntil:'networkidle'});
 await page.locator('[name=api_key]').fill('OFFLINE-BROWSER-ONLY-NOT-A-KEY');
 await page.locator('[name=max_requests]').fill('2');await page.locator('[name=budget_cny]').fill('1');
 await page.locator('[name=max_output_tokens]').selectOption('1024');await page.locator('[name=consent]').check();
 const configured=page.waitForResponse(r=>r.url()===base+'/api/settings'&&r.request().method()==='POST');
 await page.locator('#model-form [type=submit]').click();check((await configured).ok(),'Connection rejected');
 const daily=await(await fetch(base+'/api/settings')).json();check(daily.budget.attempts===0,'Unexpected model dispatch');
 await page.goto(base+'/#experiments',{waitUntil:'networkidle'});
 await page.locator('#project-test-form [name=objective]').fill('Explain this Agent dependency');
 await page.locator('#project-test-form [name=max_depth]').selectOption('2');
 fs.writeFileSync(path.join(out,'form-before.json'),JSON.stringify(await page.locator('#project-test-form').evaluate(f=>({html:f.outerHTML,valid:f.checkValidity(),handler:String(f.onsubmit),values:[...new FormData(f).entries()]})),null,2));
 const prepared=page.waitForResponse(r=>r.url()===base+'/api/project-tests'&&r.request().method()==='POST');
 await page.screenshot({path:path.join(out,'before-prepare.png'),fullPage:true});
 await page.locator('#project-test-form [type=submit]').click({timeout:5000});
 fs.writeFileSync(path.join(out,'after-click.json'),JSON.stringify(await page.locator('#project-test-form').evaluate(f=>({valid:f.checkValidity(),values:[...new FormData(f).entries()]}))));
 const prepResponse=await prepared;check(prepResponse.ok(),'Prepare rejected: '+JSON.stringify(await prepResponse.json()));
 const confirm=page.locator('[data-test-execute]');await confirm.waitFor();check(await confirm.count()===1,'Not one card');
 let cards=await(await fetch(base+'/api/project-tests')).json();check(cards.items.length===1,'Missing frozen card');
 check(cards.items[0].state==='PREPARED'&&cards.items[0].model_requests===0,'Prepare executed models');
 check(cards.items[0].card.max_requests===8,'Automatic request cap wrong');
 const rejected=await page.evaluate(async row=>{
   const {csrf_token}=await(await fetch('/api/config')).json();const statuses=[];
   const body={action:'execute',test_id:row.test_id,card_sha256:row.card_sha256,confirmed:true};
   for(const [payload,csrf] of [[{...body,confirmed:false},csrf_token],[{...body,card_sha256:'0'.repeat(64)},csrf_token],[{...body,max_requests:99},csrf_token],[body,'wrong-csrf']]){
     const response=await fetch('/api/project-tests',{method:'POST',headers:{'Content-Type':'application/json','X-Catalyst-CSRF':csrf},body:JSON.stringify(payload)});statuses.push(response.status);
   }return statuses;
 },cards.items[0]);check(rejected.every(s=>s>=400),'Invalid scope/CSRF accepted');
 check(await page.locator('#project-test-form [name=budget_cny]').count()===0,'User must not type test limits');
 await page.screenshot({path:path.join(out,'review-card.png'),fullPage:true});
 const started=page.waitForResponse(r=>r.url()===base+'/api/project-tests'&&r.request().method()==='POST');
 await confirm.click();const response=await started;check(response.status()===202,'Original Monitor rejected');const {run_id}=await response.json();
 let result;for(let i=0;i<100;i++){const r=await fetch(base+'/api/runs/'+run_id+'/result');if(r.ok){result=await r.json();break}await new Promise(r=>setTimeout(r,150))}
 check(result?.status==='success',JSON.stringify(result));
 const after=await(await fetch(base+'/api/settings')).json();check(after.budget.task_id===daily.budget.task_id&&after.budget.attempts===0,'Daily scope consumed/replaced');
 cards=await(await fetch(base+'/api/project-tests')).json();const card=cards.items[0];
 check(card.state==='FINISHED'&&card.model_requests===4,'Wrong test settlement');
 check(card.card.method.version==='0.1.0'&&card.semantic_quality==='NOT_EVALUATED','False semantic promotion');
 check(card.mechanical_evaluation.dimensions.SOURCE_IDENTITY.status==='PASS','Missing original mechanical review');
 const trace=await(await fetch(base+'/api/runs/'+run_id)).json();
 check(trace.events.some(e=>e.event_type==='tool.execution.started'&&e.capability_id==='project_submit_analysis'),'Missing actual original R4 tool event');
 await page.goto(base+'/#experiments',{waitUntil:'networkidle'});await page.getByText('FINISHED',{exact:false}).first().waitFor();
 check(await page.locator('[data-test-execute]').count()===0,'Completed test can be rerun');
 await page.screenshot({path:path.join(out,'result.png'),fullPage:true});check(errors.length===0,errors.join('\n'));
 fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({verdict:'PASS_WITH_LIMITS',kind:'FAKE_NOT_LIVE',result,trace,card,daily_before:daily,daily_after:after,rejected,errors,real_api_calls:0},null,2));
 console.log('PROJECT_ACCEPTANCE_BROWSER_PASS');
}catch(e){fs.writeFileSync(path.join(out,'failure.json'),JSON.stringify({error:String(e)}));throw e}
finally{if(browser)await browser.close();if(child){const done=new Promise(r=>child.once('exit',r));child.kill();await done}}})().catch(e=>{console.error(e);process.exitCode=1});
