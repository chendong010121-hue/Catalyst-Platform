// Both reading entries draw the same blocks: these tests fail when one of them grows its own
// copy of the navigation, the field split, the evidence list, the backlinks or the admission.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.join(__dirname,'../../catalyst_platform/workspace_assets/');
const read=name=>fs.readFileSync(path.join(root,name),'utf8');
const contractSource=read('wiki-contract.js');
const workbench=read('app.js');
const standalone=read('wiki.js');

function contract(){
  const ctx={URLSearchParams};
  ctx.window=ctx;
  vm.createContext(ctx);
  vm.runInContext(contractSource,ctx);
  return ctx.WikiContract;
}

test('the contract exposes the blocks both entries render',()=>{
  const c=contract();
  ['fieldsHtml','tocHtml','navHtml','evidenceHtml','evidenceDetail','backlinksHtml','admission','versionNotice']
    .forEach(name=>assert.equal(typeof c[name],'function',name));
});

test('neither entry keeps its own copy of a shared block',()=>{
  for(const source of [workbench,standalone]){
    assert.doesNotMatch(source,/function evidenceBadges/);
    assert.doesNotMatch(source,/function matches\(/);
  }
  assert.match(workbench,/WikiContract\.admission\(/);
  assert.match(workbench,/WikiContract\.navHtml\(/);
  assert.match(workbench,/WikiContract\.tocHtml\(/);
  assert.match(workbench,/WikiContract\.evidenceHtml\(/);
  assert.match(workbench,/WikiContract\.backlinksHtml\(/);
  assert.match(standalone,/contract\.admission\(/);
  assert.match(standalone,/contract\.navHtml\(/);
  assert.match(standalone,/contract\.tocHtml\(/);
  assert.match(standalone,/contract\.evidenceHtml\(/);
  assert.match(standalone,/contract\.backlinksHtml\(/);
});

test('an object card says what the row recorded as unsettled, or that nothing was recorded',()=>{
  const c=contract();
  const base={kind_label:'职责',title:'负责分公司项目具体执行',roles:[],citations:[],qualification_label:'待审（pending）',
    basis:'duty_attached_to_another_unit',basis_label:'职责挂在另一个单位上',verification_label:'未确认（unconfirmed）'};
  assert.match(c.objectPanel(Object.assign({},base,{unsettled:'页面未写生效日期',unsettled_source:'observed_absence'})),
    /尚未确认（原文）：页面未写生效日期/);
  assert.match(c.objectPanel(base),/尚未确认：没有记录未确认项/);
  assert.doesNotMatch(c.objectPanel(base),/业务已确认|已获业务批准/);
});

test('an admission banner states the basis it has and fills in none when the version saved none',()=>{
  const c=contract();
  const page={fields:{authority_class:'test_only',owner_acceptance_basis:'missing'}};
  const missing=c.admission({meta:{}},page);
  assert.match(missing,/不是企业 Owner 批准/);
  assert.match(missing,/业务批准依据：未记录业务批准依据/);
  const recorded=c.admission({meta:{}},{fields:{authority_class:'test_only',owner_acceptance_basis:'recorded',
    acceptance_basis_receipt:'receipt_1',acceptance_basis_issuer:'test-owner'}});
  assert.match(recorded,/receipt_1/);
  assert.match(recorded,/不等于企业 Owner 批准/);
  assert.doesNotMatch(recorded,/业务已确认|已获批准/);
});
