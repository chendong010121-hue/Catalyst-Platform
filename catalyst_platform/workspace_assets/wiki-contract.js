// One reading contract for both Wiki entries.
//
// The workbench page and the standalone /wiki page read the same store, so they must agree on
// four things that used to be written twice: what an address means, which page an address names,
// which version the reader thinks it is on, and what a refusal says. Each is a pure function
// here, so a difference between the two entries is a bug in one of them, not a design choice.
(function (global) {
  'use strict';

  var ROUTES = ['home', 'work', 'agents', 'wiki', 'enterprise', 'runs', 'reviews', 'settings', 'experiments'];

  // Fields a page's `fields` may carry that describe the store rather than the business object.
  // The reader keeps them, but shows them after the business text, under "技术信息".
  var TECHNICAL = ['type', 'title', 'canonical_key', 'canonical_id', 'version_id', 'authority_class',
    'owner_acceptance_basis', 'acceptance_basis_receipt', 'acceptance_basis_issuer',
    'generated_from', 'freshness', 'evidence_count', 'mention_count', 'member_count',
    'duty_count', 'event_count', 'condition_count',
    'confirmed_by_absence', 'aliases', 'scope_id', 'source_id', 'revision'];

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function parameters(query) {
    var params = {};
    if (!query) return params;
    new URLSearchParams(query).forEach(function (value, key) { params[key] = value; });
    return params;
  }

  // `#wiki?scope=…&page=…&anchor=…&version=…` — the route is the part before `?`, and an
  // unknown route is reported as such instead of being rewritten into `home` behind the caller.
  function parseHash(hash) {
    var raw = String(hash == null ? '' : hash).replace(/^#/, '');
    var at = raw.indexOf('?');
    var name = (at < 0 ? raw : raw.slice(0, at)).trim();
    var params = parameters(at < 0 ? '' : raw.slice(at + 1));
    var known = !name || ROUTES.indexOf(name) >= 0;
    return { raw: raw, name: name, route: known ? (name || 'home') : 'home', known: known, params: params };
  }

  function buildHash(route, params) {
    var query = new URLSearchParams();
    Object.keys(params || {}).forEach(function (key) {
      var value = params[key];
      if (value !== null && value !== undefined && value !== '') query.set(key, String(value));
    });
    var search = query.toString();
    return '#' + route + (search ? '?' + search : '');
  }

  function readerUrl(params) {
    var query = new URLSearchParams();
    ['scope', 'page', 'anchor', 'version', 'ev', 'back'].forEach(function (key) {
      var value = (params || {})[key];
      if (value !== null && value !== undefined && value !== '') query.set(key, String(value));
    });
    var search = query.toString();
    return '/wiki' + (search ? '?' + search : '');
  }

  // A page the address names is either that page or explicitly missing. Falling back to the
  // overview here is what made a typed address silently show a different document.
  function resolvePage(model, wanted) {
    var pages = (model && model.pages) || [];
    if (!wanted) {
      var fallback = pages.find(function (page) { return page.kind === 'overview'; }) || pages[0] || null;
      return { page: fallback, missing: null };
    }
    var found = pages.find(function (page) { return page.path === wanted; }) || null;
    return { page: found, missing: found ? null : wanted };
  }

  // The API only ever returns the store's active version. An address that names an older one is
  // a claim this reader cannot keep, so it says so instead of rendering today's version under
  // yesterday's address.
  function versionState(requested, model) {
    var current = (model && model.meta && model.meta.active_version_id) || null;
    if (!requested) return { state: 'unspecified', requested: null, current: current };
    return { state: requested === current ? 'same' : 'changed', requested: requested, current: current };
  }

  var ERRORS = {
    scope_unknown: '这个知识范围没有在本工作区声明。',
    scope_has_no_store: '这个知识范围在本工作区还没有存储；声明不会创建存储。',
    scope_invalid: '这个知识范围的标识不合法。',
    page_not_found: '这个知识范围里没有这个页面。',
    version_changed: '地址指向的版本已经不是当前的 active 版本，页面内容可能已经变化。',
    wiki_unavailable: '本机 Wiki 暂时读不到；页面不会用替代数据填补。'
  };

  function errorText(code, fallback) {
    if (ERRORS[code]) return ERRORS[code];
    if (fallback) return String(fallback) + '（' + code + '）';
    return '读取失败：' + (code || '未记录原因') + '。';
  }

  function scrollToAnchor(container, id) {
    if (!container || !id) return false;
    var target = container.querySelector('#' + (global.CSS && CSS.escape ? CSS.escape(id) : id));
    if (!target) return false;
    target.scrollIntoView({ block: 'start', behavior: 'smooth' });
    return true;
  }

  // Business fields first, store fields after. Nothing is dropped: the technical block is kept
  // verbatim under a disclosure, so a reader who needs the key or the version can still get it.
  function splitFields(fields) {
    var business = [];
    var technical = [];
    Object.keys(fields || {}).forEach(function (key) {
      var value = fields[key];
      var row = { key: key, value: value };
      if (TECHNICAL.indexOf(key) >= 0) technical.push(row); else business.push(row);
    });
    return { business: business, technical: technical };
  }

  // What a reviewer can do today is part of the card: it never promises a decision the page
  // cannot record, and it says which one is still missing instead of drawing an empty button.
  var REVIEW_SENTENCE = '核对依据行所在的来源，看原句是否真的支持这条主张；这一条还没有逐条意见入口，页面不代替你记下判断。';

  // Five questions in the order a reviewer asks them. The answers are the row's own; nothing
  // here recomputes a qualification or turns a derived record into a read original.
  function objectPanel(view) {
    if (!view) return '';
    var roles = (view.roles || []).map(function (role) {
      // A condition reaches a holder through a duty or an event; the card says which one,
      // so the reader can follow the same hop the projection took.
      var via = role.via ? '（经 ' + role.via + '）' : '';
      return role.label + via + '：'
        + (role.resolved ? role.title : role.key + '（这一版没有对应页面）');
    }).join('；') || '没有记录持有者或适用对象（未挂到对象）';
    var attachedLine = view.unattached && view.unattached_reason
      ? '挂靠：未挂到对象（' + view.unattached_reason + '）' : '';
    var citations = (view.citations || []).map(function (row) {
      return '<li>' + esc(row.line) + '</li>';
    }).join('') || '<li>这一条没有记录引用，页面不代它补一条。</li>';
    // What the row itself recorded as still open; a row that recorded nothing says so instead
    // of the card turning silence into a question.
    var unsettled = view.unsettled
      ? '尚未确认（' + (view.unsettled_source === 'observed_absence' ? '原文' : '记录') + '）：' + view.unsettled
      : '尚未确认：没有记录未确认项';
    var advanced = JSON.stringify(view.advanced || {}, null, 1);
    return '<section class="wk-obj-card">'
      + '<h3>' + esc(view.kind_label) + ' · ' + esc(view.title) + '</h3>'
      + '<dl class="wk-obj-facts">'
      + '<dt>对象是什么</dt><dd>' + esc(view.kind_label) + '；' + esc(roles) + '</dd>'
      + (attachedLine ? '<dt>挂在哪</dt><dd>' + esc(attachedLine) + '</dd>' : '')
      + '<dt>系统主张什么</dt><dd>' + esc(view.statement || '（这句话为空）') + '</dd>'
      + '<dt>依据是哪一行</dt><dd><ul class="wk-obj-cites">' + citations + '</ul></dd>'
      + '<dt>为什么待审</dt><dd>' + esc(view.qualification_label) + ' · 依据：' + esc(view.basis_label)
      + '（' + esc(view.basis || '未记录') + '）· 校验：' + esc(view.verification_label)
      + (view.scope_state ? ' · 范围状态：' + esc(view.scope_state) : '') + '</dd>'
      + '<dt>尚未确认什么</dt><dd>' + esc(unsettled) + '</dd>'
      + '<dt>可以做什么审阅</dt><dd>' + esc(REVIEW_SENTENCE) + '</dd>'
      + '</dl>'
      + '<details class="wk-tech"><summary>高级信息（条目、候选、版本、引用原始字段）</summary>'
      + '<pre class="mono">' + esc(advanced) + '</pre></details>'
      + '</section>';
  }

  function objectChips(objects) {
    if (!objects || !objects.length) return '';
    var chips = objects.map(function (view, index) {
      return '<button class="wk-object" type="button" data-object="' + index + '" aria-pressed="false">'
        + esc(view.kind_label) + ' · ' + esc(view.title)
        + '<span class="wk-obj-state">' + esc(view.qualification_label) + '</span></button>';
    }).join('');
    return '<div class="wk-objects"><p class="wk-tagline">本页挂着 ' + objects.length
      + ' 个业务对象：点开读它是什么、谁持有、依据在哪一行、为什么待审。</p>'
      + '<div class="wk-object-list">' + chips + '</div>'
      + '<div class="wk-object-detail" hidden></div></div>';
  }

  // Both entries wire the same handler, so a chip opens the same card in either reader.
  function bindObjects(host, objects) {
    if (!host || !objects || !objects.length) return;
    var detail = host.querySelector('.wk-object-detail');
    if (!detail) return;
    host.querySelectorAll('[data-object]').forEach(function (button) {
      button.addEventListener('click', function () {
        var view = objects[Number(button.getAttribute('data-object'))];
        if (!view) return;
        detail.innerHTML = objectPanel(view);
        detail.hidden = false;
        host.querySelectorAll('[data-object]').forEach(function (other) {
          other.setAttribute('aria-pressed', other === button ? 'true' : 'false');
        });
      });
    });
  }

  // ------------------------------------------------------------------ shared blocks
  //
  // Both reading entries render these blocks; neither keeps its own copy. A block is a pure
  // function of the model, the page and (for evidence) the row the reader picked, so a
  // difference between the two entries is a bug in one of them.
  function fieldsHtml(page) {
    var split = splitFields((page && page.fields) || {});
    function cell(row) {
      var value = row.value;
      if (value === null || value === undefined || value === '') return '';
      return '<span class="wk-kv">' + esc(row.key) + ' <b>'
        + esc(Array.isArray(value) ? value.join('、') : value) + '</b></span>';
    }
    var business = split.business.map(cell).join('');
    var technical = split.technical.map(cell).join('');
    return (business ? '<p class="wk-facts">' + business + '</p>' : '')
      + (technical
        ? '<details class="wk-tech"><summary>技术信息（键、版本、准入、派生）</summary>'
          + '<p class="wk-facts">' + technical + '</p></details>'
        : '');
  }

  function tocHtml(page) {
    var toc = (page && page.toc) || [];
    if (!toc.length) return '<p class="wk-note">这一页没有二级标题。</p>';
    return '<div class="wk-tocline"><span class="wk-toc-cap">本页</span>'
      + toc.map(function (item) {
        return '<button class="wk-toc-link" type="button" data-wk-anchor="' + esc(item.id) + '">'
          + esc(item.text) + '</button>';
      }).join('') + '</div>';
  }

  // One page list for both entries: same grouping, same order, same search, same current mark.
  function navHtml(model, options) {
    var opts = options || {};
    var pages = (model && model.pages) || [];
    var current = opts.current || null;
    var needle = String(opts.query || '').trim().toLowerCase();
    var groups = {};
    var seen = [];
    pages.forEach(function (page) {
      if (needle) {
        var hay = [page.title, page.path, page.text,
          (page.fields && (page.fields.canonical_key || page.fields.canonical_id)) || '']
          .join(' ').toLowerCase();
        if (hay.indexOf(needle) < 0) return;
      }
      if (!groups[page.kind]) { groups[page.kind] = []; seen.push(page.kind); }
      groups[page.kind].push(page);
    });
    var declared = ((model && model.meta && model.meta.kind_order) || [])
      .filter(function (kind) { return groups[kind]; });
    var order = declared.concat(seen.filter(function (kind) { return declared.indexOf(kind) < 0; }));
    var html = order.map(function (kind) {
      var rows = groups[kind].slice().sort(function (a, b) {
        return String(a.title || '').localeCompare(String(b.title || ''), 'zh');
      });
      var items = rows.map(function (page) {
        var flag = page.kind === 'entity' && !(page.evidence || []).length
          ? '<span class="wk-flag">·无逐行证据</span>' : '';
        return '<button class="wk-item" type="button" data-wk-open="' + esc(page.path)
          + '" aria-current="' + (page.path === current) + '">' + esc(page.title) + flag + '</button>';
      }).join('');
      return '<div class="wk-group"><h3><span>' + esc(rows[0].kind_label || kind) + '</span><span>'
        + rows.length + '</span></h3>' + items + '</div>';
    }).join('');
    return html || '<p class="wk-empty">没有匹配的页面。</p>';
  }

  function evidenceBadges(row) {
    var parts = [];
    if (row.verified) parts.push('<span class="wk-badge ok">行摘要一致</span>');
    else if (row.source_label === '缺失') parts.push('<span class="wk-badge bad">来源缺失</span>');
    else parts.push('<span class="wk-badge bad">行摘要不符</span>');
    if (row.derived) parts.push('<span class="wk-badge warn">派生提案</span>');
    if (!row.located_by_line) parts.push('<span class="wk-badge warn">非行定位</span>');
    return parts.join(' ');
  }

  // The drawer: the page's own evidence rows, each one the same button in both readers.
  function evidenceHtml(page, bank, current) {
    var rows = ((page && page.evidence) || []).map(function (id) { return (bank || {})[id]; })
      .filter(Boolean);
    if (!rows.length) return '';
    var ok = rows.filter(function (row) { return row.verified; }).length;
    var derived = rows.filter(function (row) { return row.derived; }).length;
    var items = rows.map(function (row) {
      return '<li><button class="wk-ev" type="button" data-ev="' + esc(row.id)
        + '" aria-current="' + (row.id === current) + '">'
        + '<span class="wk-src"><code>' + esc(row.source) + '</code><small>@ ' + esc(row.locator)
        + ' · ' + esc(row.status_text) + '</small></span>'
        + '<span>' + evidenceBadges(row) + '</span></button></li>';
    }).join('');
    return '<h2 id="wk-evidence-heading">证据</h2>'
      + '<p class="wk-tagline">' + rows.length + ' 行逐行证据 · 行摘要一致 ' + ok
      + ' · 来自派生提案 ' + derived + '。点一行看它引用的原文。</p>'
      + '<ul class="wk-evlist">' + items + '</ul>';
  }

  function evidenceDetail(row) {
    if (!row) return '';
    var shown = row.snippet == null ? null
      : (row.snippet.length > 600 ? row.snippet.slice(0, 600) + ' …（本行共 ' + row.snippet.length + ' 字符）' : row.snippet);
    var snippet = shown
      ? '<div class="wk-snippet"><mark>' + esc(shown) + '</mark></div>'
      : '<div class="wk-snippet empty">这一行读不到：来源不在记录位置，也没有可用的恢复副本。</div>';
    var chain = row.chain ? '<div class="wk-hop"><b>证据链第二跳</b>'
      + '<div>提案指向 <b>' + esc(row.chain.path || '（未记录）') + '</b>'
      + (row.chain.locator ? ' <span class="mono">' + esc(row.chain.locator) + '</span>' : '') + '</div>'
      + (row.chain.quote ? '<div>所引原文：<b>' + esc(row.chain.quote) + '</b></div>' : '')
      + '<div class="mono">这一跳落在文件内部定位上；能不能核对取决于这份文件能不能读。</div></div>' : '';
    return '<section class="wk-card active">'
      + '<h2 class="wk-eyebrow">证据 · ' + esc(row.source_label) + (row.derived ? ' · 派生提案' : '') + '</h2>'
      + '<dl class="wk-facts">'
      + '<dt>来源</dt><dd class="mono">' + esc(row.source) + '</dd>'
      + '<dt>定位</dt><dd class="mono">' + esc(row.locator) + '</dd>'
      + '<dt>行</dt><dd>' + esc(row.line == null ? '非行定位' : row.line) + '</dd>'
      + '<dt>类别</dt><dd>' + esc(row.evidence_class || '未记录') + '</dd>'
      + '<dt>新鲜度</dt><dd>' + esc(row.freshness || '未记录') + '</dd>'
      + '<dt>记录状态</dt><dd>' + esc(row.status_text) + '</dd>'
      + '<dt>span sha256</dt><dd class="mono">' + esc(row.span_sha256 ? String(row.span_sha256).slice(0, 16) + '…' : '未记录') + '</dd>'
      + '<dt>revision</dt><dd class="mono">' + esc(row.revision ? String(row.revision).slice(0, 16) + '…' : '未记录') + '</dd>'
      + '<dt>支撑 meaning</dt><dd class="mono">' + esc(row.meaning_id || '未匹配到 store 行') + '</dd>'
      + '</dl>' + snippet + '<div class="wk-hop">' + evidenceBadges(row) + '</div>' + chain
      + '<p class="wk-note">这里只证明「引用的那一行还在、字节与记录的摘要一致」；它不说明这句话对不对。</p>'
      + '</section>';
  }

  function backlinksHtml(page, byPath) {
    var rows = (page && page.backlinks) || [];
    if (!rows.length) return '';
    return '<div class="wk-backlinks-list">' + rows.map(function (path) {
      var target = byPath && byPath.get ? byPath.get(path) : null;
      return '<button class="wk-back" type="button" data-wk-open="' + esc(path) + '">'
        + esc(target ? target.title : path) + '</button>';
    }).join('') + '</div>';
  }

  var ADMISSION = {
    test_only: { verdict: '这个版本是测试准入（test_only），不是企业 Owner 批准。', bad: true },
    organization_owner: { verdict: '这个版本记录为组织 Owner 接受（organization_owner）。', bad: false }
  };

  // Who admitted what is on screen, and on what basis. The version page carries its own
  // fields; every other page reads the active version's authority from the model. A version
  // that saved no basis says so; the reader never fills one in.
  function admission(model, page) {
    var meta = (model && model.meta) || {};
    var fields = (page && page.fields) || {};
    var active = meta.authority || {};
    var activeBasis = active.acceptance_basis || {};
    var cls = fields.authority_class || active.authority_class || null;
    var state = fields.owner_acceptance_basis || active.acceptance_basis_state || null;
    if (!cls && !state) return '';
    var known = ADMISSION[cls];
    var verdict = known ? known.verdict : (cls ? '这个范围记录的作者类别是 ' + cls + '。' : '这个范围没有记录作者类别。');
    var basis = state === 'recorded'
      ? '业务批准依据：已记录（receipt ' + (fields.acceptance_basis_receipt || activeBasis.receipt_id || '未记录')
        + (fields.acceptance_basis_issuer || activeBasis.issuer_id ? '，issuer ' + (fields.acceptance_basis_issuer || activeBasis.issuer_id) : '')
        + '）。这是该版本的准入签发记录，不等于企业 Owner 批准。'
      : '业务批准依据：未记录业务批准依据，页面不补一条。';
    return '<div class="wk-banner admission' + (known && known.bad ? ' bad' : '') + '"><b>'
      + esc(verdict) + '</b> ' + esc(basis) + '</div>';
  }

  function versionNotice(model, requested) {
    var state = versionState(requested, model);
    if (state.state !== 'changed') return '';
    return '<div class="wk-banner bad"><b>版本已变化。</b>地址指向 <code>'
      + esc(String(state.requested).slice(0, 16)) + '…</code>，当前 active 是 <code>'
      + esc(String(state.current || '无').slice(0, 16)) + '…</code>。这个页面只读当前 active 版本，'
      + '不会用旧地址显示成旧版本。<button class="text-button" type="button" data-wk-reload>按当前版本重新载入</button></div>';
  }

  global.WikiContract = {
    ROUTES: ROUTES,
    TECHNICAL: TECHNICAL,
    parseHash: parseHash,
    buildHash: buildHash,
    readerUrl: readerUrl,
    resolvePage: resolvePage,
    versionState: versionState,
    errorText: errorText,
    scrollToAnchor: scrollToAnchor,
    splitFields: splitFields,
    objectChips: objectChips,
    objectPanel: objectPanel,
    bindObjects: bindObjects,
    fieldsHtml: fieldsHtml,
    tocHtml: tocHtml,
    navHtml: navHtml,
    evidenceBadges: evidenceBadges,
    evidenceHtml: evidenceHtml,
    evidenceDetail: evidenceDetail,
    backlinksHtml: backlinksHtml,
    admission: admission,
    versionNotice: versionNotice
  };
})(window);
