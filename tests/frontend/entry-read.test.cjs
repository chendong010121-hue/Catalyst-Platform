const {test}=require('node:test');const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../../catalyst_platform/workspace_assets/app.js'),'utf8');
const fn=source.slice(source.indexOf('async function api('),source.indexOf('\nconst go='));
const busy=()=>({ok:false,status:409,json:async()=>({error:{code:'workspace_busy'}})});
function client(fetch){const context={fetch,S:{csrf:'synthetic-token'},setTimeout:fn=>fn(),Promise,Error,JSON};vm.createContext(context);vm.runInContext(fn,context);return context.api}
test('read-only transient workspace busy is bounded and recoverable',async()=>{
 let calls=0;const api=client(async(p,o)=>{assert.equal(o.method,'GET');calls++;return calls<3?busy():{ok:true,status:200,json:async()=>({ready:true})}});
 assert.equal((await api('/api/workspace')).ready,true);assert.equal(calls,3);
});
test('sustained workspace busy stops after four GET attempts',async()=>{
 let calls=0;const api=client(async()=>{calls++;return busy()});
 await assert.rejects(api('/api/assets'),e=>e.status===409&&e.message==='workspace_busy');assert.equal(calls,4);
});
test('POST actions are never implicitly retried even on workspace busy',async()=>{
 for(const path of ['/api/ask','/api/settings','/api/cancel','/api/maintenance']){
  let calls=0;const api=client(async(p,o)=>{calls++;assert.equal(o.method,'POST');return busy()});
  await assert.rejects(api(path,{action:'synthetic'}));assert.equal(calls,1);
 }
});
test('network failures and other HTTP errors do not receive retry',async()=>{
 for(const code of [404,500,409]){
  let calls=0;const api=client(async()=>{calls++;return {ok:false,status:code,json:async()=>({error:{code:'different_error'}})}});
  await assert.rejects(api('/api/workspace'));assert.equal(calls,1);
 }
 let calls=0;const api=client(async()=>{calls++;throw Error('synthetic network failure')});
 await assert.rejects(api('/api/workspace'));assert.equal(calls,1);
});
