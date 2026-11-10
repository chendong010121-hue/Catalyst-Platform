const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../catalyst_platform/workspace_assets/app.js'),'utf8');
test('Development names the navigation and page while preserving existing bookmarks',()=>{
 assert.ok(source.includes("['experiments','Development']"));
 assert.ok(source.includes("head('Development',"));
 assert.ok(source.includes('前往 Development →'));
 assert.doesNotMatch(source,/测试与迭代/);
 assert.ok(source.includes("'/api/project-tests'"));
});
