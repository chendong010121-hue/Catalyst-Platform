// The business picture of one candidate: objects first, evidence only when asked.
//
// The provenance graph (schema v1) draws sources and every evidence node before the first
// item; read as a business picture it is unusable. This module draws what the candidate
// saved - entities, duties, events, conditions, relations - says how many of each exist,
// and lets a reader pick one object to see its one-hop neighbourhood. It never picks a
// center on its own, never turns a candidate edge into a confirmed hierarchy, and never
// labels a layout reading as a stated relation. Every count it prints comes from the
// server answer; nothing here is estimated.
(function (global) {
  'use strict';

  var KIND_LABEL = {
    entity: '实体', duty: '职责', event: '事件', condition: '条件', relation: '关系',
    claim: '主张', unknown: '未知', alias: '别名', exception: '例外', negative_claim: '否定主张',
    semantic_candidate: '条目'
  };
  var OBJECT_KINDS = ['entity', 'duty', 'event', 'condition'];
  var ORDER = ['entity', 'duty', 'event', 'condition', 'relation', 'claim', 'alias',
    'exception', 'negative_claim', 'unknown', 'semantic_candidate'];
  var QUALIFICATION = { pending: '待审', inferred: '推断读出', stated: '原句陈述', confirmed: '已确认' };
  var RELATION_SOURCE = { LAYOUT: '版式判读（未确认）', STATED: '原句陈述', NONE: '没有记录来源' };
  // A node box wide enough for a saved name; the full text is in the node's title.
  var NODE_WIDTH = 220, NODE_STEP = 245;

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function clip(text, limit) {
    var value = String(text == null ? '' : text);
    return value.length > limit ? value.slice(0, limit - 1) + '…' : value;
  }

  function byId(graph) {
    var map = {};
    (graph.nodes || []).forEach(function (node) { map[node.id] = node; });
    return map;
  }

  function nodeOfKind(node) {
    return KIND_LABEL[node.type] || node.type;
  }

  function stateText(node) {
    if (node.type === 'relation') return RELATION_SOURCE[node.relation_source] || '候选关系（未确认）';
    var qualification = node.qualification ? (QUALIFICATION[node.qualification] || node.qualification) : '未记录资格';
    return '候选 · ' + qualification;
  }

  function summaryLine(graph) {
    var totals = (graph.budget && graph.budget.by_type) || {};
    var objects = [];
    var others = [];
    ORDER.forEach(function (kind) {
      var row = totals[kind];
      if (!row || !row.total) return;
      var text = KIND_LABEL[kind] + ' ' + row.total;
      (OBJECT_KINDS.indexOf(kind) >= 0 ? objects : others).push(text);
    });
    var evidence = totals.evidence || { shown: 0, total: 0 };
    return '<p class="bg-summary">业务对象：' + esc(objects.join(' · '))
      + (others.length ? '；其余条目：' + esc(others.join(' · ')) : '') + '。'
      + '证据节点 ' + evidence.shown + ' / ' + evidence.total
      + (graph.evidence_expanded ? '（已展开）' : '（默认不画）') + '。</p>';
  }

  function explainLines(graph) {
    var explain = graph.explain || {};
    var rows = [];
    if (explain.focus) rows.push('<p class="bg-explain">' + esc(explain.focus) + '</p>');
    if (explain.truncation) rows.push('<p class="bg-explain bg-warn">' + esc(explain.truncation) + '</p>');
    rows.push('<p class="bg-explain">' + esc(explain.evidence || '') + '</p>');
    return rows.join('');
  }

  function listSection(graph) {
    var index = graph.index || [];
    var filterKinds = OBJECT_KINDS.concat(['unattached']);
    var chips = filterKinds.map(function (kind) {
      var label = kind === 'unattached' ? '未挂靠' : KIND_LABEL[kind];
      var count = kind === 'unattached'
        ? (graph.unattached || []).length
        : index.filter(function (row) { return row.kind === kind; }).length;
      return '<button class="bg-chip" type="button" data-bg-kind="' + kind + '" aria-pressed="false">'
        + esc(label) + ' <b>' + count + '</b></button>';
    }).join('');
    var rows = index.map(function (row) {
      var marks = [];
      if (row.unattached) marks.push('<span class="bg-badge warn">未挂靠</span>');
      if (row.qualification) marks.push('<span class="bg-badge">' + esc(QUALIFICATION[row.qualification] || row.qualification) + '</span>');
      // The name the store saved leads; the producer key stays beside it as advanced detail.
      // A row the store saved no name for shows its key rather than an invented label.
      var name = row.display_name || row.label || row.key || row.id;
      return '<button class="bg-row" type="button" data-bg-object="' + esc(row.id) + '" data-bg-row-kind="' + esc(row.kind) + '" data-bg-unattached="' + (row.unattached ? '1' : '0') + '">'
        + '<span class="bg-kind bg-' + esc(row.kind) + '">' + esc(KIND_LABEL[row.kind] || row.kind) + '</span>'
        + '<span class="bg-row-label" title="' + esc(name + (row.key && row.key !== name ? ' · ' + row.key : '')) + '">'
        + esc(clip(name, 64)) + '</span>'
        + '<span class="bg-row-key" title="' + esc(row.key || '') + '">' + esc(row.key || '') + '</span>' + marks.join('') + '</button>';
    }).join('');
    var unattached = graph.unattached || [];
    var missing = unattached.length ? '<details class="bg-missing" open><summary>未挂靠的条目 · '
      + unattached.length + '</summary><ul>' + unattached.map(function (row) {
        return '<li><code>' + esc(row.key || row.id) + '</code> · ' + esc(row.reason) + '</li>';
      }).join('') + '</ul></details>'
      : '<p class="bg-explain">没有未挂靠的职责、事件或条件。</p>';
    return '<div class="bg-list-wrap"><div class="bg-chips">' + chips + '</div>'
      + '<p class="bg-hint">选中一个对象，只画它和一跳邻居；没有选中时不指定中心。</p>'
      + '<div class="bg-rows" id="bg-rows">' + (rows || '<p class="bg-explain">本候选没有业务对象。</p>') + '</div>'
      + missing + '</div>';
  }

  function layout(graph) {
    var nodes = (graph.nodes || []).filter(function (node) { return node.type !== 'evidence' && node.type !== 'source_revision'; });
    var columns = [];
    ORDER.forEach(function (kind) {
      var column = nodes.filter(function (node) { return node.type === kind; });
      if (column.length) columns.push({ kind: kind, nodes: column });
    });
    var extra = nodes.filter(function (node) { return ORDER.indexOf(node.type) < 0; });
    if (extra.length) columns.push({ kind: 'semantic_candidate', nodes: extra });
    var points = {};
    columns.forEach(function (column, columnIndex) {
      column.nodes.forEach(function (node, rowIndex) {
        points[node.id] = { x: 30 + columnIndex * NODE_STEP, y: 26 + rowIndex * 84, kind: column.kind };
      });
    });
    var evidenceNodes = (graph.nodes || []).filter(function (node) { return node.type === 'evidence'; });
    evidenceNodes.forEach(function (node, index) {
      points[node.id] = { x: 30 + columns.length * NODE_STEP, y: 26 + index * 84, kind: 'evidence' };
    });
    return { columns: columns, points: points };
  }

  function svg(graph) {
    var placed = layout(graph);
    var points = placed.points;
    var width = Math.max(760, 30 + (placed.columns.length + (Object.keys(points).some(function (id) { return points[id].kind === 'evidence'; }) ? 1 : 0)) * NODE_STEP + 120);
    var height = Math.max(360, 40 + Math.max.apply(null, [1].concat(Object.keys(points).map(function (id) { return points[id].y; }))) + 120);
    var edges = (graph.edges || []).map(function (edge) {
      var from = points[edge.source], to = points[edge.target];
      if (!from || !to) return '';
      var x1 = from.x + NODE_WIDTH, y1 = from.y + 27, x2 = to.x, y2 = to.y + 27;
      var mid = (x1 + x2) / 2;
      var curve = 'M' + x1 + ' ' + y1 + ' C' + (x1 + 40) + ' ' + y1 + ' ' + (x2 - 40) + ' ' + y2 + ' ' + x2 + ' ' + y2;
      return '<path class="bg-edge ' + (from.kind === 'relation' || to.kind === 'relation' ? 'bg-edge-rel' : '')
        + '" marker-end="url(#bg-arrow)" d="' + curve + '"></path>'
        + '<text class="bg-edge-label" x="' + mid + '" y="' + ((y1 + y2) / 2 - 5) + '" text-anchor="middle">'
        + esc(edge.label || edge.type) + '</text>';
    }).join('');
    var nodes = Object.keys(points).map(function (id) {
      var node = (graph.nodes || []).find(function (row) { return row.id === id; }) || { id: id, type: 'unknown' };
      var point = points[id];
      var kind = node.type === 'evidence' ? 'evidence' : node.type;
      // A node is called the way the store named it: a saved name, a relation's predicate,
      // an evidence row's locator. The key is the fallback and the tooltip, not the label.
      var label = node.type === 'evidence' ? (node.locator || node.evidence_id)
        : (node.display_name || (node.type === 'relation' ? (node.predicate || '关系') : (node.label || node.key || node.id)));
      var sub = node.type === 'evidence' ? (node.relative_path || '来源记录')
        : (node.sub_label || stateText(node));
      var full = nodeOfKind(node) + ' · ' + label + (node.key && node.key !== label ? ' · ' + node.key : '');
      var layoutNote = node.relation_source === 'LAYOUT' ? ' bg-layout' : '';
      return '<g class="bg-node bg-' + esc(kind) + layoutNote + '" data-bg-node="' + esc(node.id) + '" role="button" tabindex="0" title="' + esc(full) + '" aria-label="' + esc(full) + '">'
        + '<rect x="' + point.x + '" y="' + point.y + '" width="' + NODE_WIDTH + '" height="54" rx="7"></rect>'
        + '<text class="bg-node-label" x="' + (point.x + NODE_WIDTH / 2) + '" y="' + (point.y + 22) + '" text-anchor="middle">'
        + esc(clip(label, 18)) + '</text>'
        + '<text class="bg-node-sub" x="' + (point.x + NODE_WIDTH / 2) + '" y="' + (point.y + 41) + '" text-anchor="middle">'
        + esc(clip(sub, 26)) + '</text></g>';
    }).join('');
    return '<div class="bg-canvas"><svg viewBox="0 0 ' + width + ' ' + height + '" width="' + width
      + '" height="' + height + '" role="img" aria-label="候选业务对象与一跳关联">'
      + '<defs><marker id="bg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
      + '<path d="M0 0 10 5 0 10z" fill="currentColor"></path></marker></defs>'
      + edges + nodes + '</svg></div>'
      + '<p class="bg-legend">全部节点都是候选，不是已确认知识。虚线框与虚线边表示版式判读，不是原句写明的组织隶属。</p>';
  }

  function entityCard(node) {
    var facts = [
      ['对象是什么', '实体' + (node.business_type ? ' · ' + node.business_type : '')],
      ['系统主张什么', node.label || '（这句话为空）'],
      ['依据是哪一行', '证据 ' + (node.evidence_ids || []).length + ' 条；展开依据可看记录到的位置'],
      ['为什么待审', '候选 · ' + (node.qualification ? (QUALIFICATION[node.qualification] || node.qualification) : '未记录资格')]
    ];
    return '<section class="wk-obj-card"><h3>实体 · ' + esc(node.display_name || node.label || node.key || node.id) + '</h3>'
      + '<dl class="wk-obj-facts">' + facts.map(function (row) {
        return '<dt>' + esc(row[0]) + '</dt><dd>' + esc(row[1]) + '</dd>';
      }).join('') + '</dl></section>';
  }

  function wikiHref(node, ctx) {
    var key = node.type === 'entity' ? node.key
      : node.type === 'duty' ? node.holder
        : node.type === 'event' ? (node.from || [])[0]
          : null;
    if (!key || !ctx || !ctx.pageFor) return '';
    var page = ctx.pageFor(key);
    if (!page) return '';
    var query = new URLSearchParams();
    if (ctx.scope) query.set('scope', ctx.scope);
    query.set('page', page);
    if (ctx.version) query.set('version', ctx.version);
    if (ctx.backHash) query.set('back', ctx.backHash);
    return '/wiki?' + query.toString();
  }

  function focusSection(graph, ctx) {
    var nodes = byId(graph);
    var focus = graph.focus && nodes[graph.focus.node_id];
    if (!focus) {
      return '<p class="bg-explain bg-warn">' + esc((graph.explain || {}).focus || '这个对象不在本候选。') + '</p>';
    }
    var card = focus.type === 'entity' ? entityCard(focus)
      : (focus.object ? (global.WikiContract ? global.WikiContract.objectPanel(focus.object) : '') : entityCard(focus));
    var href = wikiHref(focus, ctx);
    var name = focus.display_name || focus.label || focus.key || focus.id;
    return '<div class="bg-focus-head"><button class="secondary" type="button" data-bg-clear>← 回到对象列表</button>'
      + '<p class="bg-hint">正在看 <b>' + esc(nodeOfKind(focus)) + '</b> · ' + esc(name)
      + (focus.key && focus.key !== name ? '（<code>' + esc(focus.key) + '</code>）' : '')
      + ' 的一跳关联。候选内容只在这里读，不改身份、资格或准入。</p></div>'
      + svg(graph)
      + '<div class="bg-card-wrap">' + card
      + (href ? '<p class="bg-wiki-link"><a href="' + esc(href) + '">在 Wiki 读这个对象 ↗</a>'
        + '<small>打开完整阅读页；返回时回到这个候选、这个对象和这个版本。</small></p>'
        : '<p class="bg-explain">这个对象在已接受版本里没有对应页面；候选内容不会临时生成一页。</p>')
      + '</div>';
  }

  function panel(graph, ctx) {
    if (!graph) return '';
    var evidence = (graph.budget && graph.budget.by_type && graph.budget.by_type.evidence) || { shown: 0, total: 0 };
    var toggle = '<button class="secondary" type="button" data-bg-evidence="' + (graph.evidence_expanded ? '0' : '1') + '">'
      + (graph.evidence_expanded ? '收起依据' : '展开依据') + '（证据 ' + evidence.shown + ' / ' + evidence.total + '）</button>';
    var body = graph.focus && graph.focus.found ? focusSection(graph, ctx) : listSection(graph);
    return '<section class="bg-view" id="bg-root">' + summaryLine(graph) + explainLines(graph)
      + '<div class="bg-tools"><input id="bg-q" class="search" placeholder="搜索对象：名称、键、持有者…" aria-label="搜索业务对象">'
      + toggle + '</div>' + body + '</section>';
  }

  function bind(host, graph, ctx) {
    if (!host || !graph) return;
    var rows = Array.prototype.slice.call(host.querySelectorAll('[data-bg-object]'));
    var chips = Array.prototype.slice.call(host.querySelectorAll('[data-bg-kind]'));
    var active = null;
    function applyFilter() {
      var query = (host.querySelector('#bg-q') && host.querySelector('#bg-q').value || '').trim().toLowerCase();
      rows.forEach(function (row) {
        var text = (row.textContent || '').toLowerCase();
        var kindOk = !active || (active === 'unattached' ? row.dataset.bgUnattached === '1' : row.dataset.bgRowKind === active);
        row.hidden = !(kindOk && (!query || text.indexOf(query) >= 0));
      });
    }
    var search = host.querySelector('#bg-q');
    if (search) search.addEventListener('input', applyFilter);
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        active = active === chip.dataset.bgKind ? null : chip.dataset.bgKind;
        chips.forEach(function (other) { other.setAttribute('aria-pressed', other === chip && active ? 'true' : 'false'); });
        applyFilter();
      });
    });
    rows.forEach(function (row) {
      row.addEventListener('click', function () { ctx.focus(row.dataset.bgObject); });
    });
    var clear = host.querySelector('[data-bg-clear]');
    if (clear) clear.addEventListener('click', function () { ctx.clear(); });
    var toggle = host.querySelector('[data-bg-evidence]');
    if (toggle) toggle.addEventListener('click', function () { ctx.evidence(toggle.dataset.bgEvidence === '1'); });
    host.querySelectorAll('[data-bg-node]').forEach(function (node) {
      node.addEventListener('click', function () {
        if (node.dataset.bgNode === (graph.focus && graph.focus.node_id)) return;
        ctx.focus(node.dataset.bgNode);
      });
      node.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); node.click(); }
      });
    });
  }

  global.BusinessGraph = { panel: panel, bind: bind, KIND_LABEL: KIND_LABEL };
})(window);
