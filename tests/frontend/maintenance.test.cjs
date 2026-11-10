const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const src=fs.readFileSync(path.join(__dirname,'../../catalyst_platform/workspace_assets/app.js'),'utf8');
function setup(items=[]){
 const c={S:{reviews:[],maintenance:{items}},escape:v=>String(v??'').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'),head:()=>'',note:()=>'',empty:()=>'<p>no knowledge candidates</p>',badge:v=>v};vm.createContext(c);
 vm.runInContext(src.slice(src.indexOf('function reviews()'),src.indexOf('\nfunction render()')),c);return c;
}
test('Reviews separates maintenance from enterprise knowledge decisions',()=>{
 const html=setup().reviews();assert.match(html,/系统更新/);assert.match(html,/知识待审/);assert.match(html,/data-maintenance="prepare"/);assert.doesNotMatch(html,/自动批准|正式语义通过/);
});
test('validated tool card exposes escaped exact diff and explicit confirmation',()=>{
 const html=setup([{review_id:'review_abc',title:'<img evil>',status:'VALIDATED',approval_digest:'a'.repeat(64),candidate:{version:'2.0.0'},parent:null,evaluation:{passed:true,runtime_run_ids:['run_x']},diff:'<script>no</script>',can_accept:true}]).reviews();
 assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<img|<script>/);assert.match(html,/data-maintenance="approve"/);assert.match(html,/确认/);
});
test('pending and applied cards show restart and rollback instead of immediate activation',()=>{
 assert.match(setup([{review_id:'x',status:'PENDING_RESTART',candidate:{},evaluation:{},approval_digest:'a'}]).reviews(),/data-maintenance="restart"/);
 assert.match(setup([{review_id:'x',status:'APPLIED',candidate:{},evaluation:{},approval_digest:'a'}]).reviews(),/data-maintenance="rollback"/);
});
test('restart waits for new server CSRF even when persisted session identity is unchanged',async()=>{
 let configReads=0,refreshed=0;const c={S:{meta:{session_id:'old'},csrf:'old-csrf'},window:{confirm:()=>true},document:{querySelectorAll:()=>[]},toast:()=>{},render:()=>{},setTimeout:f=>{f()},refresh:async()=>{refreshed++},api:async(p)=>{
  if(p==='/api/maintenance')return {status:'RESTARTING'};
  if(p==='/api/config'){configReads++;return configReads===1?{session_id:'old',csrf_token:'old-csrf'}:{session_id:'old',csrf_token:'new-csrf'}}
  if(p==='/api/workspace')return {session_id:'old'};
  if(p==='/api/capabilities')return {items:[{id:'updated'}]};throw Error(p);
 }};vm.createContext(c);vm.runInContext(src.slice(src.indexOf('async function maintenanceAction('),src.indexOf('\nfunction bindMaintenance()')),c);
 await c.maintenanceAction('restart');assert.equal(configReads,2);assert.equal(c.S.csrf,'new-csrf');assert.equal(c.S.meta.session_id,'old');assert.equal(refreshed,1);
});
