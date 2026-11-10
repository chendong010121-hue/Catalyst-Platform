const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../catalyst_platform/workspace_assets/app.js'),'utf8');
const block=source.split('// KNOWLEDGE_SURFACE_BEGIN')[1].split('// KNOWLEDGE_SURFACE_END')[0];
const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const badge=t=>`<span class="preview-label">${escape(t)}</span>`;
const empty=(t,d)=>`<div class="empty"><h2>${escape(t)}</h2><p>${escape(d)}</p></div>`;
function setup(){const ctx={escape,badge,empty,btoa,document:{querySelector:()=>null}};vm.createContext(ctx);vm.runInContext(block+'\n;globalThis.__toBase64=toBase64;',ctx);return ctx;}

test('a native document shows identity and freshness instead of pretending to have text',()=>{
 const html=setup().wikiSourceView({source_id:'source_a',source_format:'pdf',relative_path:'blueprint.pdf',authority:'NATIVE_SOURCE_IDENTITY_ONLY',source_revision:'r1',current_revision:'r1',fresh:true,status:'STAGED',content:null});
 assert.match(html,/PDF/);
 assert.match(html,/与登记一致/);
 assert.match(html,/原生文档暂不提供正文预览/);
 assert.match(html,/id="wiki-withdraw"/);
 assert.doesNotMatch(html,/document-text/);
});

test('a drifted native document is reported as changed, not as unreadable',()=>{
 const html=setup().wikiSourceView({source_id:'source_a',source_format:'docx',relative_path:'policy.docx',current_revision:'r2',source_revision:'r1',fresh:false,content:null});
 assert.match(html,/磁盘内容已变更/);
 assert.match(html,/DOCX/);
 assert.match(html,/原生文档暂不提供正文预览/);
});

test('a withdrawn source is labelled and cannot be withdrawn twice from the view',()=>{
 const html=setup().wikiSourceView({source_id:'source_a',source_format:'pdf',relative_path:'a.pdf',status:'WITHDRAWN',content:null});
 assert.match(html,/已撤销登记/);
 assert.doesNotMatch(html,/id="wiki-withdraw"/);
});

test('markdown text is escaped and keeps its original reading path',()=>{
 const html=setup().wikiSourceView({source_id:'source_b',source_format:'md',relative_path:'policy.md',authority:'SOURCE_DOCUMENT_NOT_ACCEPTED_ONTOLOGY',content:'# Policy\n<img onerror=evil()>'});
 assert.match(html,/document-text/);
 assert.match(html,/&lt;img/);
 assert.doesNotMatch(html,/<img/);
 assert.match(html,/Markdown 来源/);
});

test('registered bytes survive a base64 round trip without chunk corruption',()=>{
 const ctx=setup();
 const bytes=Uint8Array.from({length:70001},(_,i)=>i%251);
 const encoded=ctx.__toBase64(bytes);
 const decoded=Buffer.from(encoded,'base64');
 assert.equal(decoded.length,bytes.length);
 assert.deepEqual([...decoded.subarray(0,256)],[...bytes.subarray(0,256)]);
 assert.deepEqual([...decoded.subarray(-256)],[...bytes.subarray(-256)]);
});
