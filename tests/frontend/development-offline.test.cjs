const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../catalyst_platform/workspace_assets/app.js'),'utf8');
test('Development exposes explicitly synthetic offline checks',()=>{
 assert.match(source,/data-offline-check/);
 assert.match(source,/\/api\/development-offline/);
 assert.match(source,/不代表企业语义评价/);
});
