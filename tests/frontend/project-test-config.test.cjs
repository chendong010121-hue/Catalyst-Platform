const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../catalyst_platform/workspace_assets/app.js'),'utf8');
test('project tests let the user select bounded request limits while retaining defaults',()=>{
 assert.ok(source.includes('name="max_requests"'));
 assert.ok(source.includes('name="max_output_tokens"'));
 assert.ok(source.includes('max_requests:Number(data.get('));
 assert.ok(source.includes('max_output_tokens:Number(data.get('));
});

test('background render snapshots the actual draft before replacing its form',()=>{
 const vm=require('node:vm');
 const values={source_id:'candidate',objective:'unsent objective',max_depth:'2',max_requests:'5',max_output_tokens:'2048'};
 const form={querySelector:()=>({open:true})};
 const state={projectTestDraft:{objective:''}};
 const implementation=source.slice(source.indexOf('function rememberTestDraft('),source.indexOf('function preserveTestDraft('));
 const context={S:state,FormData:class {constructor(f){assert.equal(f,form)}get(k){return values[k]}},Number};
 vm.createContext(context);vm.runInContext(implementation,context);context.rememberTestDraft(form);
 assert.equal(state.projectTestDraft.objective,'unsent objective');
 assert.equal(state.projectTestDraft.max_requests,5);
 assert.equal(state.projectTestDraft.max_output_tokens,2048);
 assert.equal(state.projectTestDraft.advanced,true);
 assert.ok(source.includes('function render(){const restoreTest=preserveTestDraft();'));
});
