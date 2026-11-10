const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const src=fs.readFileSync(path.join(__dirname,'../../catalyst_platform/workspace_assets/app.js'),'utf8');
function setup(sources=[]){
 const context={S:{projectSources:sources,sending:false},escape:v=>String(v??'').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')};
 vm.createContext(context);
 vm.runInContext(src.slice(src.indexOf('function projectSelector()'),src.indexOf('\nfunction home()')),context);
 return context;
}
test('default Home has no optional project controls',()=>{
 assert.equal(setup().projectSelector(),'');
});
test('Host sources render only ID selection and bounded objective/depth',()=>{
 const html=setup([{source_id:'fixture-id',label:'<fixture>',object_type:'skill'}]).projectSelector();
 assert.match(html,/fixture-id/);assert.match(html,/&lt;fixture&gt;/);
 assert.match(html,/id="project-objective"/);assert.match(html,/id="project-depth"/);
 assert.doesNotMatch(html,/type="file"|name="path"|name="root"|D3/);
});
test('project submission uses monitor run readback with no browser path',async()=>{
 const calls=[];const elements={'#project-source':{value:'fixture-id'},'#project-objective':{value:'Inspect'},'#project-depth':{value:'1'}};
 const c={S:{sending:false,csrf:'fixture-csrf',workText:{}},$:s=>elements[s],render:()=>{},go:()=>{},toast:()=>{},refresh:async()=>{},readRun:async id=>calls.push(id),api:async(path,body)=>{calls.push({path,body});return {run_id:'run_fixture'}}};
 vm.createContext(c);vm.runInContext(src.slice(src.indexOf('async function submitProject()'),src.indexOf('\nasync function submit(text)')),c);
 await c.submitProject();assert.equal(calls[0].path,'/api/project-analysis');
 assert.deepEqual(JSON.parse(JSON.stringify(calls[0].body)),{source_id:'fixture-id',objective:'Inspect',max_depth:1});
 assert.equal(calls[1],'run_fixture');
});
test('result shows actual method and source manifest identities with unresolved status',()=>{
 const c={escape:v=>String(v??'')};vm.createContext(c);
 vm.runInContext(src.slice(src.indexOf('function projectReceipt('),src.indexOf('\nfunction work()')),c);
 assert.equal(c.projectReceipt({}), '');
 const html=c.projectReceipt({result:{output:{project_analysis:{method:{component_id:'project-understand',version:'0.1.0',package_sha256:'method-fixture-sha'},source_manifest_sha256:'source-fixture-sha',analysis:{achieved_depth:0,decision_readiness:'NEEDS_EVIDENCE'},semantic_quality:'NOT_EVALUATED'}}}});
 assert.match(html,/method-fixture-sha/);assert.match(html,/source-fixture-sha/);assert.match(html,/NEEDS_EVIDENCE/);
});
