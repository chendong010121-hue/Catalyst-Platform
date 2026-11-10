const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const src=fs.readFileSync(path.join(__dirname,'../../catalyst_platform/workspace_assets/app.js'),'utf8');
function panel(review){
 const c={S:{capabilityReview:review},escape:v=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'),badge:v=>`[${v}]`,empty:(t,n)=>`<p>empty:${t}</p>`};
 vm.createContext(c);
 vm.runInContext(src.slice(src.indexOf('function capabilityReviewPanel(){'),src.indexOf('\nfunction projectTestPanel(')),c);
 return c.capabilityReviewPanel();
}
function pair(over={}){
 return {relation:'SIMILAR',action:'EVALUATE_IN_DEVELOPMENT',reason:'同职责、同形态与接口：竞争实现',requires_owner_confirmation:true,evaluation_questions:['右侧未覆盖「安装时复制脚本」，是否也会满足？'],input_digest:'d'.repeat(64),coverage:{matched:4,left_only:0,right_only:1},left:{id:'skill-porting',version:'2026.10.10.1',kind:'skill',responsibility_key:'port-external-package',statement:'a'},right:{id:'skill-porting-alt',version:'1.0.0',kind:'skill',responsibility_key:'port-external-package',statement:'b'},...over};
}
test('the panel states the comparison is not a verdict',()=>{
 const html=panel({items:[pair()],claims:[{},{}],source:'workspace',write_enabled:false,errors:[]});
 assert.match(html,/^<section class="section-card">/);
 assert.match(html,/能力入库比对/);
 assert.match(html,/不判定谁更好/);
 assert.match(html,/同职责竞争实现/);
 assert.match(html,/去 Development 对比评测/);
 assert.match(html,/建议的评测问题 · 不是结论/);
 assert.match(html,/只读，不写入 Wiki/);
});
test('each Reviews function sits in its own bordered card',()=>{
 const c={S:{reviews:[],maintenance:{items:[]}},escape:v=>String(v??''),head:()=>'',note:()=>'',empty:()=>'',badge:v=>v,capabilityReviewPanel:()=>'<section class="section-card">review</section>'};
 vm.createContext(c);
 vm.runInContext(src.slice(src.indexOf('function reviews(){'),src.indexOf('\nfunction capabilityReviewPanel(')),c);
 const html=c.reviews();
 assert.equal((html.match(/class="section-card"/g)||[]).length,3);
});
test('a competing pair offers navigation but no enabled replacement',()=>{
 const html=panel({items:[pair({action:'REPLACE',relation:'SAME'})],claims:[{}],source:'workspace',write_enabled:false,errors:[]});
 assert.match(html,/替换 · 需评测证据与 Owner 确认/);
 assert.match(html,/button class="secondary" disabled/);
 assert.doesNotMatch(html,/data-replace-capability/);
});
test('keep-both explains that wiki boundaries are not writable yet',()=>{
 const html=panel({items:[pair({action:'KEEP_BOTH',relation:'COMPLEMENTARY',evaluation_questions:[]})],claims:[{}],source:'examples',write_enabled:false,errors:[]});
 assert.match(html,/都保留 · 写入 Wiki 的适用边界尚未开放/);
 assert.match(html,/产品内置样例声明/);
});
test('claim content is escaped',()=>{
 const html=panel({items:[pair({left:{id:'<img src=x>',version:'1',kind:'skill',responsibility_key:'k',statement:'s'}})],claims:[{}],source:'workspace',write_enabled:false,errors:[]});
 assert.doesNotMatch(html,/<img src=x>/);
 assert.match(html,/&lt;img src=x&gt;/);
});
test('invalid claims are surfaced instead of hidden',()=>{
 const html=panel({items:[],claims:[],source:'workspace',write_enabled:false,errors:[{file:'broken.claim.json',violation:'claim:unbacked:what.obligations[0]'}]});
 assert.match(html,/broken\.claim\.json/);
 assert.match(html,/claim:unbacked/);
});
test('an empty library says where claims belong',()=>{
 const html=panel({items:[],claims:[],source:'workspace',write_enabled:false,errors:[]});
 assert.match(html,/empty:没有可比对的能力声明/);
});

test('a declared split needs no evaluation and says so',()=>{
 const html=panel({items:[pair({relation:'COMPLEMENTARY',action:'KEEP_BOTH',requires_owner_confirmation:false,reason:'两侧都在不适用范围里点名对方：这是分工，不是竞争',evaluation_questions:[]})],claims:[{},{}],source:'workspace',write_enabled:false,errors:[]});
 assert.match(html,/同职责不同分工/);
 assert.match(html,/这是分工，不是竞争/);
 assert.doesNotMatch(html,/去 Development 对比评测/);
 assert.match(html,/都保留 · 写入 Wiki 的适用边界尚未开放/);
});
