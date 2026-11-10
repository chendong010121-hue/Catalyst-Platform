// UI-only acceptance over an already running original Workspace server.
// Synthetic workspace, GET-only traffic, no Provider/key/configuration action.
const {chromium}=require('C:/Users/13752/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const base=process.argv[2]||'http://127.0.0.1:8802';
const out=path.resolve(process.argv[3]);
if(fs.existsSync(out))throw Error('Fresh UI evidence directory required');
fs.mkdirSync(out,{recursive:true});
const assert=(ok,message)=>{if(!ok)throw Error(message)};
let browser,page;const errors=[],external=[],writes=[],checks=[];let phase='setup',sequence=0;
async function visit(route){await page.goto(base+'/?ui-check='+(++sequence)+'#'+route,{waitUntil:'networkidle'});await page.locator('h1').first().waitFor()}
async function screen(name){await page.screenshot({path:path.join(out,name+'.png'),fullPage:true})}
async function readable(){return page.evaluate(()=>{
 const lum=c=>{const n=c.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4});return n[0]*.2126+n[1]*.7152+n[2]*.0722};
 const result=[];
 for(const e of document.querySelectorAll('.intro,.page-description,.note,.footer-note,.work-text small,.obs-coverage,.obs-metrics small,.obs-table td small,.settings-form label')){
  if(!e.getClientRects().length)continue;
  const c=getComputedStyle(e);let p=e,bg;
  while(p){const b=getComputedStyle(p).backgroundColor;if(b!=='rgba(0, 0, 0, 0)'&&b!=='transparent'){bg=b;break}p=p.parentElement}
  const a=lum(c.color),b=lum(bg||'rgb(255,255,255)');result.push({size:parseFloat(c.fontSize),contrast:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)});
 }
 return {overflow:document.documentElement.scrollWidth>innerWidth,labels:result};
})}
(async()=>{try{
 browser=await chromium.launch({headless:true});page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async r=>{const q=r.request();if(!q.url().startsWith(base+'/')){external.push(q.url());await r.abort();return}if(q.method()!=='GET'){writes.push({method:q.method(),url:q.url()});await r.abort();return}await r.continue()});
 phase='routes';
 for(const route of ['home','agents','wiki','enterprise','runs','reviews','settings']){
  await visit(route);const result=await readable();assert(!result.overflow,route+' horizontal overflow');
  assert(result.labels.every(x=>x.size>=12&&x.contrast>=4.5),route+' unreadable secondary label: '+JSON.stringify(result.labels.filter(x=>x.size<12||x.contrast<4.5)));
  if(route!=='settings')assert(await page.locator('.nav-link[aria-current="page"]').count()===1,route+' current route missing');
  await screen('desktop-'+route);checks.push({route,viewport:'1440x1000',label_count:result.labels.length,min_contrast:Math.min(...result.labels.map(x=>x.contrast))});
 }
 phase='keyboard';await visit('wiki');await page.keyboard.press('Tab');assert(await page.locator('#skip-to-main').evaluate(e=>e===document.activeElement),'Skip not first keyboard target');await page.keyboard.press('Enter');assert(await page.locator('#main').evaluate(e=>e===document.activeElement),'Skip lost current route/main focus');assert(page.url().endsWith('#wiki'),'Skip changed route');
 await page.locator('.account-menu summary').focus();await page.keyboard.press('Enter');assert(await page.locator('.account-menu').evaluate(e=>e.open),'Keyboard account open failed');await page.keyboard.press('Escape');assert(!await page.locator('.account-menu').evaluate(e=>e.open),'Account Escape failed');
 await page.locator('.account-menu summary').click();await page.locator('h1').click();assert(!await page.locator('.account-menu').evaluate(e=>e.open),'Outside account dismissal failed');
 await page.locator('#about').click();assert(await page.locator('#info-dialog').evaluate(e=>e.open),'Native dialog open failed');await screen('dialog');await page.keyboard.press('Escape');assert(!await page.locator('#info-dialog').evaluate(e=>e.open),'Native dialog Escape failed');
 phase='wiki';assert(!await page.locator('#wiki-capabilities').evaluate(e=>e.open),'Wiki capabilities unexpectedly expanded');await page.locator('#wiki-capabilities summary').click();await page.locator('[data-asset]').first().click();await page.locator('.doc-body h2').waitFor();await screen('wiki-asset');
 phase='agent-local-interaction';await visit('agents');await page.locator('#message-input').fill('UI only local draft');await page.locator('#toggle-caps').click();await page.locator('[data-add]:not([disabled])').first().click();assert(await page.locator('[data-remove]').count()===1,'Capability preference missing');await page.locator('[data-remove]').click();assert(await page.locator('.user-message').count()===0,'Removing a preference submitted the draft');assert(await page.locator('#message-input').inputValue()==='UI only local draft','Preference removal lost input');
 phase='model-form';await visit('settings');assert(await page.locator('#model-form fieldset').count()===3,'Model groups missing');assert(await page.locator('[name=api_key]').getAttribute('type')==='password','Key input unmasked');assert(await page.locator('[name=consent]').evaluate(e=>e.required),'Consent requirement removed');assert(await page.locator('[name=max_requests]').getAttribute('max')==='20','Request cap changed');assert(await page.locator('[name=budget_cny]').getAttribute('max')==='10','Budget cap changed');assert(await page.locator('#model-form [type=submit]').isDisabled(),'Preview permits model scope submission');
 phase='responsive';for(const size of [{width:1024,height:900},{width:390,height:844},{width:320,height:740}]){
  await page.setViewportSize(size);for(const route of ['home','wiki','runs','settings']){await visit(route);const r=await readable();assert(!r.overflow,route+' overflow at '+size.width);assert(r.labels.every(x=>x.size>=12&&x.contrast>=4.5),route+' inaccessible labels at '+size.width);await screen(size.width+'-'+route);checks.push({route,viewport:size.width+'x'+size.height,label_count:r.labels.length});}
 }
 phase='preferences';await page.setViewportSize({width:1440,height:1000});await page.emulateMedia({reducedMotion:'reduce',contrast:'more'});await visit('home');await page.locator('#about').click();assert(await page.locator('#info-dialog').evaluate(e=>getComputedStyle(e).transform==='none'),'Reduced-motion dialog moves');await page.keyboard.press('Escape');await page.evaluate(()=>document.documentElement.style.fontSize='20px');assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),'Text scaling overflows');await screen('larger-text');
 await page.emulateMedia({reducedMotion:'no-preference',contrast:'no-preference'});await visit('home');await page.locator('.account-menu summary').click();await page.waitForTimeout(200);await screen('account-menu');
 const meta=await page.evaluate(async()=>await(await fetch('/api/workspace')).json());assert(meta.mode==='BLOCKED','UI qualification requires BLOCKED mode');assert(!errors.length&&!external.length&&!writes.length,JSON.stringify({errors,external,writes}));
 fs.writeFileSync(path.join(out,'RECEIPT.json'),JSON.stringify({verdict:'PASS_UI_ONLY',source_identity:meta.source_identity,mode:meta.mode,checks,errors,external,writes,real_api_calls:0,real_key_reads:0,limitations:['Chromium and emulated sizes; not real iOS/Safari or screen-reader certification','Synthetic UI evidence does not establish semantic or Provider quality']},null,2));console.log('UI_CRAFT_PASS');
}catch(e){if(page)await screen('failure').catch(()=>{});fs.writeFileSync(path.join(out,'FAILURE.json'),JSON.stringify({phase,error:e.message,errors,external,writes},null,2));throw e}finally{if(browser)await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
