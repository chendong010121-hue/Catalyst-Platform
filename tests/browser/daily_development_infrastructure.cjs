// Offline UI proof, including a real process restart and Windows DPAPI fake Key.
const {chromium}=require('C:/Users/13752/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {spawn}=require('node:child_process'),fs=require('node:fs'),path=require('node:path');
const out=path.resolve(process.argv[2]),workspace=path.resolve(process.argv[3]),base='http://127.0.0.1:8814';
if(fs.existsSync(out)||fs.existsSync(workspace))throw Error('Fresh outputs required');fs.mkdirSync(out,{recursive:true});
const env={PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'};
for(const k of ['PATH','Path','SystemRoot','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'])if(process.env[k]!==undefined)env[k]=process.env[k];
const check=(v,m)=>{if(!v)throw Error(m)};let child,browser,stage=0,page;
async function stop(){if(child){const done=new Promise(r=>child.once('exit',r));child.kill();await done;child=null;}}
async function boot(){
 stage++;const folder=path.join(out,'boot-'+stage);fs.mkdirSync(folder);
 child=spawn('python',['-u','-m','tests.browser.project_fixture','--infrastructure','--daily-replies','--workspace',workspace,'--out',folder,'--port','8814'],{cwd:path.resolve(__dirname,'../..'),env,windowsHide:true});
 child.stdout.pipe(fs.createWriteStream(path.join(folder,'service.log')));child.stderr.pipe(fs.createWriteStream(path.join(folder,'service-error.log')));
 let ready=false;for(let i=0;i<100;i++){await new Promise(r=>setTimeout(r,100));try{ready=(await fetch(base+'/api/settings')).ok;if(ready)break}catch{}}check(ready,'Service unavailable');
}
(async()=>{try{
 await boot();browser=await chromium.launch({headless:true});page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 for(const [route,title] of [['home','你希望 AI 帮助完成什么？'],['agents','Agents'],['wiki','Wiki'],
   ['enterprise','Enterprise'],['reviews','Reviews'],['experiments','Development'],['runs','Observability']]){
   await page.goto(base+'/#'+route,{waitUntil:'networkidle'});
   await page.getByRole('heading',{name:title,exact:true}).first().waitFor();
 }
 await page.goto(base+'/?daily-settings='+Date.now()+'#settings',{waitUntil:'networkidle'});
 check(await page.locator('[name=max_requests],[name=max_output_tokens],[name=budget_cny],[name=consent],[name=allow_asset_read]').count()===0,'Daily settings expose old limits or grants');
 await page.locator('[name=api_key]').fill('OFFLINE-SYNTHETIC-PERSISTENCE-KEY');await page.locator('[name=remember_key]').check();
 const saved=page.waitForResponse(r=>r.url()===base+'/api/settings'&&r.request().method()==='POST');await page.locator('#daily-connection-form [type=submit]').click();check((await saved).ok(),'Connect refused');
 let state=await(await fetch(base+'/api/settings')).json();check(state.saved_credential_available&&state.connection_available&&state.connection_mode==='daily','Daily connection not saved');
 async function chat(message){await page.goto(base+'/?chat='+Date.now()+'#home',{waitUntil:'networkidle'});await page.locator('#message-input').fill(message);const pending=page.waitForResponse(r=>r.url()===base+'/api/ask'&&r.request().method()==='POST');await page.locator('#composer [type=submit]').click();const response=await pending;check(response.status()===202,'Chat not dispatched');const {run_id}=await response.json();let result;for(let i=0;i<100;i++){const r=await fetch(base+'/api/runs/'+run_id+'/result');if(r.ok){result=await r.json();break}await new Promise(r=>setTimeout(r,100))}check(result?.status==='success',JSON.stringify(result));return result;}
 const chats=[await chat('你好，请简短介绍自己。'),await chat('请用一句话说明如何开始日常工作。')];
 const beforeRestart=await(await fetch(base+'/api/settings')).json();
 await stop();await boot();await page.reload({waitUntil:'networkidle'});
 state=await(await fetch(base+'/api/settings')).json();check(state.saved_credential_available&&!state.configured,'GET restored a model task or lost saved Key');
 await page.goto(base+'/#home',{waitUntil:'networkidle'});
 await page.locator('.chat-turn').nth(1).waitFor();
 check((await page.locator('.chat-panel').innerText()).includes('你好，请简短介绍自己。'),'Prior question was lost on restart');
 await page.goto(base+'/#settings',{waitUntil:'networkidle'});check(await page.locator('[name=api_key]').inputValue()==='','Key was returned to browser');
 const resumed=await chat('继续我们的日常工作。');
 state=await(await fetch(base+'/api/settings')).json();check(state.configured&&state.connection_mode==='daily','User task failed lazy daily reconnect');
 await page.goto(base+'/#home',{waitUntil:'networkidle'});
 await page.locator('.chat-turn').nth(2).waitFor();
 await page.locator('[data-chat-run="'+resumed.run_id+'"]').click();
 await page.locator('[data-obs-run="'+resumed.run_id+'"][aria-expanded="true"]').waitFor();
 await page.goto(base+'/#home',{waitUntil:'networkidle'});
 await page.locator('#new-chat').click();
 await page.waitForFunction(()=>document.querySelector('#chat-thread-select')?.value!=='initial');
 check(await page.locator('.chat-panel > .chat-turn').count()===0,'New conversation inherited visible turns');
 const separate=await chat('请解释如何验证项目。');
 check(separate.chat.thread_id!=='initial'&&separate.chat.context_run_ids.length===0,'New conversation received previous context');
 await page.locator('#chat-thread-select').selectOption('initial');
 await page.locator('.chat-turn').nth(2).waitFor();
 check(await page.locator('.chat-panel .chat-turn').count()===3,'Could not reopen prior conversation');
 const continued=await chat('回到这条对话继续。');
 check(continued.chat.thread_id==='initial'&&continued.chat.context_run_ids.includes(resumed.run_id)
   &&!continued.chat.context_run_ids.includes(separate.run_id),'Reopened conversation used the wrong context');
 const dailyBeforeExperiment=await(await fetch(base+'/api/settings')).json();
 async function settingsAction(action,data={}){return page.evaluate(async({action,data})=>{const config=await(await fetch('/api/config')).json();const r=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json','X-Catalyst-CSRF':config.csrf_token},body:JSON.stringify({action,data})});const result=await r.json();if(!r.ok)throw Error(JSON.stringify(result));return result;},{action,data})}
 const reviewed=await settingsAction('qualification_check');check(reviewed.qualification_review,'Metadata check produced no review proposal');
 const metadataReview=await settingsAction('qualification_approve',{proposal_sha256:reviewed.qualification_review.proposal_sha256,confirmed:true});
 await page.goto(base+'/?development='+Date.now()+'#experiments',{waitUntil:'networkidle'});
 await page.locator('#development-request').fill('请为合成组织资料准备一次测试，输出上限 16384。');
 const drafted=page.waitForResponse(r=>r.url()===base+'/api/project-tests'&&r.request().method()==='POST');await page.locator('#development-prepare').click();const draftResponse=await drafted;check(draftResponse.status()===202,'Planning not dispatched by Monitor');const planRun=(await draftResponse.json()).run_id;
 let planResult;for(let i=0;i<100;i++){const r=await fetch(base+'/api/runs/'+planRun+'/result');if(r.ok){planResult=await r.json();break}await new Promise(r=>setTimeout(r,150))}
 check(planResult?.state==='TEST_CARD_PREPARED',JSON.stringify(planResult));
 let tests=await(await fetch(base+'/api/project-tests')).json();let card=tests.items[0];check(card.state==='PREPARED'&&card.model_requests===0&&card.prepared_by==='LLM','Plan executed Subject');
 check(card.card.max_output_tokens===16384&&tests.plans[0].model_requests===1,'Wrong AI proposal/allowance');
 await page.goto(base+'/?development='+Date.now()+'#experiments',{waitUntil:'networkidle'});await page.locator('[data-test-execute]').waitFor();await page.screenshot({path:path.join(out,'review-card.png'),fullPage:true});
 const started=page.waitForResponse(r=>r.url()===base+'/api/project-tests'&&r.request().method()==='POST');await page.locator('[data-test-execute]').click();const response=await started;check(response.status()===202,'Test not admitted');const {run_id}=await response.json();
 let result;for(let i=0;i<100;i++){const r=await fetch(base+'/api/runs/'+run_id+'/result');if(r.ok){result=await r.json();break}await new Promise(r=>setTimeout(r,150))}
 check(result?.status==='success',JSON.stringify(result));
 tests=await(await fetch(base+'/api/project-tests')).json();card=tests.items[0];check(card.model_requests===2&&card.state==='FINISHED','Wrong subject ledger');
 const calls=JSON.parse(fs.readFileSync(path.join(out,'boot-2/fake-calls.json')));check(calls.length===6&&calls.at(-1).max_tokens===16384,'Output limit did not reach actual request');
 check(!JSON.stringify(calls.at(-3)).includes('服务组负责登记'),'Planning read source content');
 check(!JSON.stringify(calls).includes('是否有来源支持职责归属'),'Review leaked to model');
 state=await(await fetch(base+'/api/settings')).json();check(state.configured&&state.connection_mode==='daily'&&state.saved_credential_available,'Experiment disturbed daily connection');check(state.budget.task_id===dailyBeforeExperiment.budget.task_id&&state.budget.attempts===dailyBeforeExperiment.budget.attempts&&state.budget.charged_cny===dailyBeforeExperiment.budget.charged_cny,'Experiment charged daily allowance');check(state.budget.max_requests===null&&state.budget.budget_cny===null,'Daily connection retained cumulative caps');
 check(errors.length===0,errors.join('\n'));await page.goto(base+'/?development='+Date.now()+'#experiments',{waitUntil:'networkidle'});await page.screenshot({path:path.join(out,'result.png'),fullPage:true});
 fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({kind:'FAKE_NOT_LIVE',real_api_calls:0,process_restart:true,chats,resumed,beforeRestart,dailyBeforeExperiment,metadataReview,planning:planResult,result,tests,settings:state,errors},null,2));console.log(path.basename(process.argv[1])==='test_infrastructure.cjs'?'TEST_INFRASTRUCTURE_BROWSER_PASS':'DAILY_DEVELOPMENT_INFRASTRUCTURE_BROWSER_PASS');
}catch(e){if(page){await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});fs.writeFileSync(path.join(out,'failure.json'),JSON.stringify({error:String(e),body:await page.locator('body').innerText()}));}throw e}
finally{if(browser)await browser.close();await stop();}})().catch(e=>{console.error(e);process.exitCode=1});
