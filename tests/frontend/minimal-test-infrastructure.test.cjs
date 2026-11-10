const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../catalyst_platform/workspace_assets/app.js'),'utf8');
test('AI preparation uses explicit bounded draft action and never execution approval',()=>{
 const start=source.indexOf("const ai=$('#ai-test-draft')"),end=source.indexOf("document.querySelectorAll('[data-test-execute]')",start);
 const body=source.slice(start,end);assert.ok(body.includes("action:'draft'"));assert.ok(!body.includes("action:'execute'"));
 assert.ok(source.includes('S.planningAllowance?.budget_cny'));assert.ok(source.includes('输出上限 ${escape(c.max_output_tokens)}'));
});
test('saved credential is not copied into password input or client storage',()=>{
 assert.ok(source.includes("action:'credential_save'"));assert.ok(source.includes("action:'credential_forget'"));
 assert.ok(source.includes("?'model_saved':"));assert.ok(!source.includes('localStorage.setItem(\'api_key'));
 assert.ok(source.includes("if(action==='model_saved')delete payload.api_key"));
});
test('daily settings omit output sizing; prepared cards retain concrete limits',()=>{
 const settings=source.slice(source.indexOf('function settingsPage()'),source.indexOf('function bindSettings()'));
 assert.doesNotMatch(settings,/name="max_output_tokens"/);
 assert.ok(source.includes('输出上限 ${escape(c.max_output_tokens)}'));
});
