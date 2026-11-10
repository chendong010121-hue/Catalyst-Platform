// The Wiki reading page. Read-only over /api/wiki/model; there is deliberately no sample data.
//
// The address is the reading state: scope, page, anchor and the version the reader believes it
// is on. Navigation goes through the same contract the workbench uses, so a link copied from
// here opens the same scope there instead of the daily one.
'use strict';

const $ = (id) => document.getElementById(id);
const esc = (value) => String(value == null ? '' : value).replace(/[&<>"']/g,
  (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const KIND_MEANING = { claim: '断言', relation: '关系', unknown: '缺失断言', condition: '条件',
  exception: '例外', entity: '实体', alias: '别名', concept: '概念', source: '来源' };
const meaningLine = (rows) => Object.entries(rows || {})
  .map(([kind, count]) => `${KIND_MEANING[kind] || kind} ${count}`).join(' · ');
const contract = window.WikiContract;

const state = { data: null, byPath: new Map(), page: null, ev: null, q: '', returnTo: null,
  scope: null, anchor: null, version: null, versionState: null };

async function get(path) {
  const response = await fetch(path, { headers: { Accept: 'application/json' } });
  let payload = null;
  try { payload = await response.json(); } catch { payload = null; }
  if (!response.ok) throw new Error((payload && payload.error && payload.error.code) || `HTTP_${response.status}`);
  if (!payload) throw new Error('JSON_INVALID');
  return payload;
}

function status(text, bad) {
  const box = $('wk-status');
  box.textContent = text;
  box.classList.toggle('bad', Boolean(bad));
  box.hidden = false;
  $('wk-layout').hidden = true;
}

// ------------------------------------------------------------------ navigation
// The page list, its grouping and its search are the contract's, so this entry and the
// workbench cannot drift apart on what a page is called or where it sits.
function renderNav() {
  $('wk-nav').innerHTML = contract.navHtml(state.data, { current: state.page, query: state.q });
}

// ------------------------------------------------------------------ page
// Business fields first; the store-side fields stay available under "技术信息", unchanged.
function chips(page) {
  return contract.fieldsHtml(page);
}

function evidenceSection(page) {
  return contract.evidenceHtml(page, state.data.evidence, state.ev);
}

function versionBanner() {
  return contract.versionNotice(state.data, state.version);
}

function renderPage() {
  const page = state.byPath.get(state.page);
  if (!page) return;
  const meta = state.data.meta;
  document.title = `Wiki · ${page.title}`;
  $('wk-crumb').innerHTML = `<span>${esc(page.kind_label)}</span><span>·</span><code>${esc(page.path)}</code>`;
  $('wk-title').textContent = page.title;
  $('wk-meta').innerHTML = chips(page);

  const banners = [versionBanner(), contract.admission(state.data, page)];
  if (!meta.sources.recorded) {
    banners.push('<div class="wk-banner"><b>这个工作区还没有登记来源。</b>页面由投影生成，因此只有概览、索引、缺口与操作记录；登记一份资料后这里才会出现实体与来源页。</div>');
  }
  if ((page.kind === 'overview' || page.kind === 'gaps') && meta.evidence.missing) {
    banners.push(`<div class="wk-banner"><b>${meta.evidence.missing} 行页面证据的来源不在记录位置。</b>页面能打开，不等于这份副本能自证：这些行指向的文件在配置的根目录下找不到，右栏「证据面」给出总数。</div>`);
  }
  $('wk-banner').innerHTML = banners.join('');
  $('wk-body').innerHTML = contract.objectChips(page.objects) + page.html + evidenceSection(page);
  contract.bindObjects($('wk-body'), page.objects);

  $('wk-toc').innerHTML = contract.tocHtml(page);

  const backlinks = page.backlinks || [];
  $('wk-backlinks-wrap').hidden = !backlinks.length;
  $('wk-backlinks').innerHTML = contract.backlinksHtml(page, state.byPath);
  const reload = $('wk-reload') || document.querySelector('[data-wk-reload]');
  if (reload) reload.onclick = () => { state.version = null; boot(); };
}

// ------------------------------------------------------------------ rail
function fact(label, value, mono) {
  return `<dt>${esc(label)}</dt><dd${mono ? ' class="mono"' : ''}>${esc(value)}</dd>`;
}

function renderHealth() {
  const meta = state.data.meta;
  const store = meta.store_index_sha256 ? `${meta.store_index_sha256.slice(0, 12)}…` : '无（空 store）';
  $('wk-health').innerHTML = [
    fact('store', store, true),
    fact('索引稳定', meta.index_stable ? '是（读前读后一致）' : '否（期间有提交）'),
    fact('verify', `${meta.verify.status} · 问题 ${meta.verify.problems}`),
    fact('产物 / 孤儿', `${meta.verify.artifact_count} / ${meta.verify.orphans}`),
    fact('active 版本', meta.active_version_id || '无', true),
    fact('概念集', meta.concept_version || '无'),
    fact('链接 / 死链 / 歧义', `${meta.links.links} / ${meta.links.unresolved} / ${meta.links.ambiguous}`),
    fact('来源 在场/登记', `${meta.sources.present} / ${meta.sources.recorded}`),
    fact('派生提案缺失', meta.sources.derived_missing),
  ].join('');
}

function renderSurface() {
  const meta = state.data.meta;
  const evidence = meta.evidence;
  $('wk-surface').innerHTML = [
    fact('全库证据行', evidence.rows),
    fact('页面逐行证据', evidence.on_pages),
    fact('其中核对通过', evidence.verified),
    fact('来自派生提案', evidence.derived),
    fact('无页面承载', evidence.off_pages),
    fact('已接受 meaning', meta.meanings_total),
  ].join('');
  const off = meaningLine(evidence.off_page_kinds);
  $('wk-surface-note').textContent = evidence.off_pages
    ? `没有独立页面的 ${evidence.off_pages} 行属于：${off}。它们在 store 里是被接受的，页面上看不到——这是下一层视图要补的。`
    : '没有无页面承载的证据行。';
  $('wk-surface-note').textContent += ` 已接受 meaning：${meaningLine(meta.meanings)}。`;
}

function renderEvidence() {
  const slot = $('wk-evidence');
  const row = state.ev ? state.data.evidence[state.ev] : null;
  if (!row) { slot.innerHTML = ''; return; }
  slot.innerHTML = contract.evidenceDetail(row)
    + '<button class="secondary wk-close" type="button" id="wk-close-ev">关闭（Esc）</button>';
  $('wk-close-ev').onclick = () => select(state.page, null);
}

// ------------------------------------------------------------------ routing
// The address carries the reading state; the version it names is checked against the store on
// every boot, so a stale link says so instead of rendering today's pages under it.
function urlFor({ page, ev, version }) {
  const query = new URLSearchParams();
  if (state.scope) query.set('scope', state.scope);
  if (page || state.page) query.set('page', page || state.page);
  if (state.anchor) query.set('anchor', state.anchor);
  if (version || state.data && state.data.meta.active_version_id) {
    query.set('version', version || state.data.meta.active_version_id);
  }
  if (ev || state.ev) query.set('ev', ev || state.ev);
  if (state.returnTo) query.set('back', state.returnTo);
  const search = query.toString();
  return `/wiki${search ? '?' + search : ''}`;
}

// The way back is a reading state of its own: it names whatever the reader is showing now —
// page and version included — so the workbench keeps the same version check the address had.
function renderBack() {
  const scope = state.data && state.data.meta.scope;
  if (!scope) return;
  const query = new URLSearchParams({ scope });
  if (state.page) query.set('page', state.page);
  const version = state.data.meta.active_version_id;
  if (version) query.set('version', version);
  const back = $('wk-back');
  // A caller that opened this page from a graph gets its own address back, scope and object
  // included; without one the way back is the reading list, as before.
  if (back) back.setAttribute('href', state.returnTo ? '/' + state.returnTo : `/#wiki?${query.toString()}`);
  const brand = document.querySelector('a.brand');
  if (brand) brand.setAttribute('href', `/#wiki?scope=${encodeURIComponent(scope)}`);
}

function sync(push) {
  if (push && state.data) history.replaceState(null, '', urlFor({}));
}

function select(page, ev, scroll) {
  if (page && state.byPath.has(page) && page !== state.page) {
    state.page = page;
    state.ev = null;
  }
  state.ev = ev || null;
  renderBack();
  renderNav();
  renderPage();
  renderEvidence();
  sync(true);
  if (scroll) $('wk-article').scrollIntoView({ block: 'start' });
}

function renderAll() {
  renderNav();
  renderPage();
  renderHealth();
  renderSurface();
  renderEvidence();
}

document.addEventListener('click', (event) => {
  const link = event.target.closest('[data-wk-open], [data-page]');
  if (link) {
    event.preventDefault();
    select(link.dataset.wkOpen || link.dataset.page, null, true);
    return;
  }
  const row = event.target.closest('[data-ev]');
  if (row) { event.preventDefault(); select(null, row.dataset.ev); return; }
  const reload = event.target.closest('[data-wk-reload]');
  if (reload) { event.preventDefault(); state.version = null; boot(); return; }
  const jump = event.target.closest('[data-wk-anchor], [data-anchor]');
  if (jump) {
    event.preventDefault();
    state.anchor = jump.dataset.wkAnchor || jump.dataset.anchor;
    contract.scrollToAnchor($('wk-body'), state.anchor) || contract.scrollToAnchor($('wk-article'), state.anchor);
    sync(true);
  }
});

$('wk-q').addEventListener('input', (event) => { state.q = event.target.value; renderNav(); });

document.addEventListener('keydown', (event) => {
  if (event.key === '/' && document.activeElement !== $('wk-q')) { event.preventDefault(); $('wk-q').focus(); }
  if (event.key === 'Escape' && state.ev) { select(null, null); }
});

async function boot() {
  const params = new URLSearchParams(location.search);
  state.scope = params.get('scope');
  state.version = params.get('version');
  state.anchor = params.get('anchor');
  const returnTo = params.get('back');
  state.returnTo = returnTo && /^#[A-Za-z0-9/?=&%_.:+-]*$/.test(returnTo) ? returnTo : null;
  let model;
  try {
    model = await get('/api/wiki/model' + (state.scope ? '?scope=' + encodeURIComponent(state.scope) : ''));
  } catch (error) {
    status(`读取本机 Wiki 失败：${contract.errorText(error.message)} 本页不展示替代数据；换一个范围或刷新可重试。`, true);
    return;
  }
  state.data = model;
  state.byPath = new Map(model.pages.map((page) => [page.path, page]));
  state.versionState = contract.versionState(state.version, model);
  const resolved = contract.resolvePage(model, params.get('page'));
  if (resolved.missing) {
    status(`这个范围里没有页面 ${resolved.missing}。地址不会被静默改写成别的文档；修改 page 参数，或从工作区重新进入。`, true);
    return;
  }
  state.page = resolved.page.path;
  state.ev = params.get('ev') && model.evidence[params.get('ev')] ? params.get('ev') : null;
  $('wk-scope').textContent = `${model.meta.scope} · 只读投影`;
  renderBack();
  $('wk-status').hidden = true;
  $('wk-layout').hidden = false;
  renderAll();
  sync(true);
}

boot();
