// Isolated browser qualification only. No real Provider, Key, or daily service.
const {chromium}=require('C:/Users/13752/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {spawn}=require('node:child_process');const fs=require('node:fs'),path=require('node:path');
const output=path.resolve(process.argv[2]),workspace=path.resolve(process.argv[3]),product=path.resolve(__dirname,'../..');
if(fs.existsSync(output)||fs.existsSync(workspace))throw Error('Fresh output/workspace required');
fs.mkdirSync(output,{recursive:true});const base='http://127.0.0.1:8802';
const env={PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'};for(const k of ['Path','PATH','SystemRoot','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'])if(process.env[k]!==undefined)env[k]=process.env[k];
const scoped=process.argv.includes('--owner-scope-fixture');
let child,browser;const errors=[];function check(x,m){if(!x)throw Error(m)}
(async()=>{try{
 child=spawn('python',['-u','-m','tests.browser.project_fixture','--workspace',workspace,'--out',output,'--port','8802',...(scoped?['--owner-scope-fixture']:[])],{cwd:product,env,windowsHide:true});
 child.stdout.pipe(fs.createWriteStream(path.join(output,'service.log')));child.stderr.pipe(fs.createWriteStream(path.join(output,'service-error.log')));
 let meta;for(let i=0;i<100;i++){await new Promise(r=>setTimeout(r,150));try{const r=await fetch(base+'/api/workspace');if(r.ok){meta=await r.json();break}}catch{}}
 check(meta,'Fixture unavailable');check(meta.source_identity.dirty===false,'Exact clean source required');
 browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1380,height:960}});
 page.on('pageerror',e=>errors.push(String(e)));await page.goto(base+'/#settings',{waitUntil:'networkidle'});
 await page.locator('#model-form').waitFor();await page.locator('[name=api_key]').fill('OFFLINE-BROWSER-FIXTURE-NOT-A-KEY');
 if(!scoped){await page.locator('[name=max_requests]').fill('6');await page.locator('[name=budget_cny]').fill('1');await page.locator('[name=max_output_tokens]').selectOption('1024');}else{check(await page.locator('[name=max_requests]').inputValue()==='4','Scope not fixed');check(await page.locator('[name=budget_cny]').inputValue()==='0.387072','Budget not fixed');}await page.locator('[name=consent]').check();
 const configured=page.waitForResponse(r=>r.url()===base+'/api/settings'&&r.request().method()==='POST');await page.locator('#model-form [type=submit]').click();check((await configured).ok(),'Configuration rejected');
 await page.goto(base+'/#home',{waitUntil:'networkidle'});if(!scoped)await page.locator('details.disclosure summary').filter({hasText:'理解已授权项目'}).click();
 if(!scoped)await page.locator('#project-objective').fill('Explain this Agent dependency');await page.locator('#project-depth').selectOption('2');
 await page.screenshot({path:path.join(output,'home.png'),fullPage:true});
 const started=page.waitForResponse(r=>r.url()===base+'/api/project-analysis'&&r.request().method()==='POST');await page.locator('#project-analysis [type=submit]').click();const reply=await started;check(reply.status()===202,'Task admission refused');const {run_id}=await reply.json();
 let result;for(let i=0;i<150;i++){const r=await fetch(base+'/api/runs/'+run_id+'/result');if(r.ok){result=await r.json();break}await new Promise(r=>setTimeout(r,100))}
 check(result?.state==='PROJECT_ANALYZED',JSON.stringify(result));const p=result.result.output.project_analysis;
 check(p.method.version==='0.1.0'&&p.semantic_quality==='NOT_EVALUATED','Incorrect qualification');check(p.tool_executions.project_expand_evidence===1,'No actual expansion');check(p.lifecycle.handle_released===true,'Runtime handle retained');
 await page.getByText('项目方法 project-understand @ 0.1.0',{exact:false}).waitFor();check((await page.locator('body').innerText()).includes(p.method.package_sha256),'Method identity not visible');await page.screenshot({path:path.join(output,'result.png'),fullPage:true});
 await page.goto(base+'/#runs',{waitUntil:'networkidle'});await page.screenshot({path:path.join(output,'runs.png'),fullPage:true});
 const trace=await(await fetch(base+'/api/runs/'+run_id)).json();check(trace.events.some(e=>e.event_type==='tool.execution.started'&&e.capability_id==='project_submit_analysis'),'No original R4');check(errors.length===0,'Browser errors');
 fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify({verdict:'PASS_WITH_LIMITS',fixture:'FAKE_TRANSPORT_NOT_LIVE',source:meta.source_identity,run_id,result,trace,errors,real_api_calls:0},null,2));
 console.log('PROJECT_BROWSER_PASS_WITH_LIMITS '+run_id);
 }catch(e){fs.writeFileSync(path.join(output,'failure.json'),JSON.stringify({error:String(e),errors}));throw e}finally{if(browser)await browser.close();if(child){const done=new Promise(r=>child.once('exit',r));child.kill();await done}}})().catch(e=>{console.error(e);process.exitCode=1});
