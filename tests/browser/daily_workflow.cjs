// Uses the original offline service fixture; never touches a daily/live Key.
const {chromium}=require('C:/Users/13752/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {spawn}=require('node:child_process');const fs=require('node:fs'),path=require('node:path');
const output=path.resolve(process.argv[2]),workspace=path.resolve(process.argv[3]),product=path.resolve(__dirname,'../..');
if(fs.existsSync(output)||fs.existsSync(workspace))throw Error('Fresh output/workspace required');
fs.mkdirSync(output,{recursive:true});const base='http://127.0.0.1:8802';
const env={PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'};for(const k of ['Path','PATH','SystemRoot','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'])if(process.env[k]!==undefined)env[k]=process.env[k];
let child,browser;const errors=[];const check=(x,m)=>{if(!x)throw Error(m)};
(async()=>{try{
 child=spawn('python',['-u','-m','tests.browser.project_fixture','--workspace',workspace,'--out',output,'--port','8802'],{cwd:product,env,windowsHide:true});child.stdout.pipe(fs.createWriteStream(path.join(output,'service.log')));child.stderr.pipe(fs.createWriteStream(path.join(output,'service-error.log')));
 let meta;for(let i=0;i<100;i++){await new Promise(r=>setTimeout(r,150));try{const r=await fetch(base+'/api/workspace');if(r.ok){meta=await r.json();break}}catch{}}
 check(meta,'Fixture source identity required');
 browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1380,height:960}});page.on('pageerror',e=>errors.push(String(e)));
 const mutations=[];page.on('request',r=>{if(r.method()==='POST')mutations.push(r.url())});
 await page.goto(base+'/#home',{waitUntil:'networkidle'});
 const request='帮我为 Understand 准备回归测试方案';
 await page.locator('#message-input').fill(request);await page.locator('#composer [type=submit]').click();
 await page.locator('#development-request').waitFor();check(await page.locator('#development-request').inputValue()===request,'Home request preserved');
 check(mutations.length===0,'Routing must not upload, dispatch or call models');
 check(await page.locator('#project-test-form').count()===0,'Manual source form hidden');check(await page.locator('[data-offline-check]').count()===0,'Offline demonstrations hidden');
 await page.screenshot({path:path.join(output,'development.png'),fullPage:true});
 await page.goto(base+'/#settings',{waitUntil:'networkidle'});await page.locator('#daily-connection-form').waitFor();
 check(await page.locator('[name=allow_project_read],[name=budget_cny],[name=max_requests],[name=max_output_tokens],[name=consent]').count()===0,'Daily connection has no cumulative controls');
 await page.screenshot({path:path.join(output,'settings.png'),fullPage:true});
 const plans=await (await fetch(base+'/api/evaluation-workflows')).json();check(plans.items.length===0,'Handoff only, no prepared server workflow');
 const settings=await (await fetch(base+'/api/settings')).json();check(settings.key_status==='MISSING','No Key');check(errors.length===0,'No browser errors');
 fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify({verdict:'PASS_WITH_LIMITS',fixture:'ORIGINAL_FAKE_SERVICE_NO_LIVE',source:meta.source_identity,plans,settings,errors,real_api_calls:0},null,2));console.log('DAILY_WORKFLOW_BROWSER_PASS');
}catch(e){fs.writeFileSync(path.join(output,'failure.json'),JSON.stringify({error:String(e),errors}));throw e}finally{if(browser)await browser.close();if(child){const done=new Promise(r=>child.once('exit',r));child.kill();await done}}})().catch(e=>{console.error(e);process.exitCode=1});
