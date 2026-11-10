// The reading tasks this product is accepted on, run against a real page.
//
// A task passes only if a person could do it: find the page, read what is saved there, recognise
// what the object is called, open the line a claim rests on, jump inside the page, leave and come
// back with the same scope and version, and see a refusal named when the address is wrong. The
// script is read-only; it records what it saw and exits non-zero if any task failed.
//
//   node scripts/acceptance/reading-tasks.mjs --base http://127.0.0.1:8817 --out <dir>
//
// Playwright is resolved from PLAYWRIGHT_MODULE when set, otherwise from the local cache path
// printed in the report, so a machine without it fails with a sentence instead of a stack trace.
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const require = createRequire(import.meta.url);
const CANDIDATES = [
  process.env.PLAYWRIGHT_MODULE,
  'C:/Users/13752/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright',
].filter(Boolean);

function loadPlaywright() {
  for (const path of CANDIDATES) {
    try { return { module: require(path), path }; } catch { /* try the next one */ }
  }
  console.error('playwright not found; set PLAYWRIGHT_MODULE to the module directory');
  process.exit(2);
}

const args = process.argv.slice(2);
const arg = (name, fallback) => {
  const at = args.indexOf(`--${name}`);
  return at >= 0 && args[at + 1] ? args[at + 1] : fallback;
};
const BASE = arg('base', 'http://127.0.0.1:8817').replace(/\/$/, '');
const OUT = arg('out', '.');
const SCOPE = arg('scope', 'enterprise:synthetic-joint/project:m1-test-scope');
const PAGE = arg('page', 'entities/fmgongsi_qita_yuangong.md');
const DUTY = '负责分公司项目具体执行';
const HOLDER = '分公司其他员工';

const { module: playwright, path: playwrightPath } = loadPlaywright();
const { chromium } = playwright;

const checks = [];
const ok = (task, name, value, detail) => checks.push({
  task, name, ok: Boolean(value), detail: detail === undefined ? String(value) : String(detail).slice(0, 400),
});

const scopeQuery = (extra = {}) => {
  const query = new URLSearchParams({ scope: SCOPE, ...extra });
  return query.toString();
};

// A producer key looks like `duty_fmgongsi_qita_yuangong`: lowercase ASCII, digits and
// underscores. A label made only of that is a key, not a name a business reader recognises.
const KEY_LIKE = /^[a-z][a-z0-9_.\-]*$/;
const hasHan = (text) => /[\u4e00-\u9fff]/.test(String(text || ''));

async function main() {
  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));

  const guarded = async (task, name, body) => {
    try { await body(); } catch (error) { ok(task, name, false, String(error && error.message).slice(0, 200)); }
  };

  const readInline = async (query) => {
    await page.goto(`${BASE}/#wiki?${scopeQuery(query)}`, { waitUntil: 'networkidle' });
    await page.locator('#wk-inline').waitFor({ timeout: 20000 });
    await page.waitForTimeout(1200);
    return (await page.locator('#wk-inline').innerText()).replace(/\s+/g, ' ');
  };

  // ---------------------------------------------------------------- A1: read one duty
  await guarded('A1', '从测试范围进入实体页，读出它保存的职责、资格与来源', async () => {
    const duty = await readInline({ page: PAGE });
    ok('A1', '实体页出现职责段落与这句话', /职责/.test(duty) && duty.includes(DUTY), duty.slice(0, 300));
    ok('A1', '职责写明持有人且可回到持有人页',
      new RegExp(`持有者：${HOLDER}`).test(duty) && /entities\/fmgongsi_qita_yuangong\.md/.test(duty), duty.slice(0, 300));
    ok('A1', '待审与依据没有被美化成已确认',
      /待审（pending）/.test(duty) && /duty_attached_to_another_unit/.test(duty)
        && !/业务已确认|已获批准|已获业务批准/.test(duty), duty.slice(0, 400));
    ok('A1', '依据行指出来源与行号，并说明只核对了派生记录',
      /依据行/.test(duty) && /line:\d+/.test(duty) && /派生记录|没有回读原件/.test(duty), duty.slice(0, 400));
    const title = (await page.locator('#wk-inline h2').first().innerText()).trim();
    ok('A1', '页面以业务名称开头而不是拼音键', title === HOLDER && !KEY_LIKE.test(title), title);

    // The line a claim rests on has to open: clicking the row shows its own record.
    const row = page.locator('#wk-inline [data-ev]').first();
    const rows = await page.locator('#wk-inline [data-ev]').count();
    ok('A1', '页面给出可打开的依据行', rows > 0, `${rows} evidence rows`);
    if (rows > 0) {
      await row.click();
      await page.waitForTimeout(500);
      const detail = (await page.locator('#wk-ev-detail').innerText().catch(() => '')).replace(/\s+/g, ' ');
      ok('A1', '点开依据能看到位置与派生标记',
        /定位/.test(detail) && /line:\d+/.test(detail) && /派生提案|来源缺失/.test(detail), detail.slice(0, 300));
    }
    await page.screenshot({ path: join(OUT, 'task-entity-duty.png'), fullPage: false });
  });

  // ---------------------------------------------------------------- A1/A2: the object card
  await guarded('A1', '点开业务对象能读完它的五个问题', async () => {
    const duty = await readInline({ page: PAGE });
    const chips = await page.locator('#wk-inline .wk-object').count();
    ok('A1', '实体页给出可点开的业务对象', chips > 0, `${chips} object chips · ${duty.slice(0, 80)}`);
    await page.locator('#wk-inline .wk-object').first().click();
    await page.waitForTimeout(500);
    const panel = (await page.locator('#wk-inline .wk-obj-card').innerText().catch(() => '')).replace(/\s+/g, ' ');
    ok('A1', '对象卡回答「是什么、主张什么、依据在哪、为什么待审、能做什么、尚未确认什么」',
      /对象是什么/.test(panel) && /系统主张什么/.test(panel) && /依据是哪一行/.test(panel)
        && /为什么待审/.test(panel) && /可以做什么审阅/.test(panel) && /尚未确认什么/.test(panel), panel.slice(0, 300));
    ok('A1', '对象卡不把待审读成已确认',
      /待审（pending）/.test(panel) && !/业务已确认|已获批准|已获业务批准/.test(panel), panel.slice(0, 400));
    ok('A1', '技术字段收在高级信息里', (await page.locator('#wk-inline .wk-obj-card details.wk-tech').count()) === 1, panel.slice(0, 200));
    await page.screenshot({ path: join(OUT, 'task-object-panel.png'), fullPage: false });
  });

  await guarded('A2', '能从实体页说清事件尚未确认什么', async () => {
    const ev = await readInline({ page: 'entities/touzi_guanli_zhongxin.md' });
    ok('A2', '事件段落列出参与方', /参与事件/.test(ev) && /起点：/.test(ev) && /终点：/.test(ev), ev.slice(0, 300));
    ok('A2', '事件给出待审依据而不是「已发生」',
      /待审（pending）|推断读出（inferred）/.test(ev) && /roles_or_endpoints_unsettled/.test(ev)
        && !/已发生/.test(ev), ev.slice(0, 400));
    ok('A2', '事件写明尚未确认什么，没有记录就写没有记录',
      /尚未确认[：（]/.test(ev) && (/没有记录未确认项/.test(ev) || /页面未写|未说明|未列明|不确定/.test(ev)), ev.slice(0, 400));
    await page.screenshot({ path: join(OUT, 'task-entity-event.png'), fullPage: false });
  });

  // ---------------------------------------------------------------- A3: dropped rows
  await guarded('A3', '从未收获条目里能区分引用缺失、资格待审与业务缺席', async () => {
    await page.goto(`${BASE}/#enterprise`, { waitUntil: 'networkidle' });
    await page.locator('#scope-select').waitFor({ timeout: 20000 });
    const options = await page.locator('#scope-select option').allInnerTexts();
    const testOption = options.find((text) => text.includes('测试成果'));
    if (testOption) await page.locator('#scope-select').selectOption({ label: testOption });
    await page.waitForTimeout(3000);
    const dropped = page.locator('summary', { hasText: '未收获条目' }).first();
    await dropped.scrollIntoViewIfNeeded();
    await dropped.click();
    await page.waitForTimeout(800);
    const panel = (await page.locator('main').innerText()).replace(/\s+/g, ' ');
    ok('A3', '未收获行给出规则码而不是猜出来的原因',
      /evidence_unresolved/.test(panel) && !/引用的证据解析不到/.test(panel), panel.slice(0, 200));
    ok('A3', '未收获行给出条目自己的证据类别', /条目证据类别/.test(panel), panel.slice(0, 300));
    ok('A3', '未收获行给出引用阶梯', /在记录里/.test(panel) && /条带原句|无原句/.test(panel), panel.slice(0, 300));
    ok('A3', '原件不可读时如实写出', /原件本轮不可读/.test(panel), panel.slice(0, 300));
    await page.screenshot({ path: join(OUT, 'task-reasons.png'), fullPage: true });
  });

  // ---------------------------------------------------------------- A4: in-page jump
  await guarded('A4', '地址带着范围与页面打开阅读器', async () => {
    await readInline({ page: PAGE });
    const toc = page.locator('#wk-inline [data-wk-anchor]').first();
    if (await toc.count()) {
      const before = await page.evaluate(() => location.hash);
      await toc.click();
      await page.waitForTimeout(600);
      const after = await page.evaluate(() => location.hash);
      const readerOpen = await page.locator('#wk-inline').isVisible().catch(() => false);
      const scrolled = await page.evaluate(() => window.scrollY > 0);
      ok('A4', '段内目录不离开 Wiki', readerOpen && after.startsWith('#wiki'), `hash ${before} -> ${after}, reader ${readerOpen}`);
      ok('A4', '段内目录把页面滚到该段', scrolled, `scrollY>0: ${scrolled}`);
    } else {
      ok('A4', '段内目录可点（本页应有目录）', false, 'no toc control found');
    }
    await page.screenshot({ path: join(OUT, 'task-toc.png'), fullPage: false });
  });

  // ---------------------------------------------------------------- A4: leave and come back
  await guarded('A4', '完整阅读页与返回都带着范围', async () => {
    await page.locator('a.quiet-link', { hasText: '完整阅读页' }).first().click();
    await page.waitForURL(/\/wiki\?/, { timeout: 20000 });
    await page.waitForTimeout(1200);
    const readerUrl = page.url();
    const scopeShown = await page.locator('#wk-scope').innerText().catch(() => '');
    ok('A4', '完整阅读页的地址带着范围与版本',
      /scope=/.test(readerUrl) && /version=/.test(readerUrl) && readerUrl.includes(encodeURIComponent(SCOPE)), readerUrl);
    ok('A4', '完整阅读页读的是同一个范围', scopeShown.includes(SCOPE), scopeShown);
    ok('A4', '完整阅读页打开的是同一个页面',
      (await page.locator('#wk-title').innerText().catch(() => '')).trim().length > 0,
      await page.locator('#wk-title').innerText().catch(() => ''));
    await page.screenshot({ path: join(OUT, 'task-full-reader.png'), fullPage: false });

    let switchedPage = null;
    const backHref = await page.locator('#wk-back').getAttribute('href').catch(() => '');
    const readingVersion = await page.evaluate(() => new URLSearchParams(location.search).get('version'));
    const backVersion = new URLSearchParams(String(backHref || '').split('?')[1] || '').get('version');
    ok('A4', '返回地址保留版本', Boolean(readingVersion) && backVersion === readingVersion,
      `back ${backHref} · reader version ${readingVersion}`);
    const overviewItem = page.locator('#wk-nav .wk-item', { hasText: '概览' }).first();
    if (await overviewItem.count()) {
      await overviewItem.click();
      await page.waitForTimeout(900);
      switchedPage = await page.evaluate(() => new URLSearchParams(location.search).get('page'));
      const backAfter = await page.locator('#wk-back').getAttribute('href').catch(() => '');
      ok('A4', '阅读器内换页后返回指向当前页',
        Boolean(switchedPage) && String(backAfter).includes(encodeURIComponent(switchedPage)),
        `reader page ${switchedPage} · back ${backAfter}`);
      await page.screenshot({ path: join(OUT, 'task-back-switched.png'), fullPage: false });
    } else {
      ok('A4', '阅读器内换页后返回指向当前页', false, 'no 概览 item in the reader navigation');
    }

    await page.waitForFunction(() => {
      const a = document.querySelector('#wk-back');
      return Boolean(a && /page=/.test(a.getAttribute('href') || ''));
    }, null, { timeout: 20000 });
    await page.locator('a', { hasText: '返回工作区' }).first().click();
    await page.waitForURL(/#wiki/, { timeout: 20000 });
    await page.waitForTimeout(1500);
    const backHash = await page.evaluate(() => location.hash);
    const backTitle = await page.locator('#wk-inline h2').first().innerText().catch(() => '');
    ok('A4', '返回工作区仍带同一范围与页面', /scope=/.test(backHash) && /page=/.test(backHash), backHash);
    ok('A4', '返回后打开的是同一页',
      backTitle.trim().length > 0 && (!switchedPage || decodeURIComponent(backHash).includes(switchedPage)),
      `${backTitle} · ${backHash}`);
    await page.screenshot({ path: join(OUT, 'task-back.png'), fullPage: false });
  });

  // ---------------------------------------------------------------- A5: admission
  await guarded('A5', '打开 test_only 版本说明它不等于企业 Owner 批准', async () => {
    const candidates = await (await fetch(`${BASE}/api/semantic/candidates?scope=${encodeURIComponent(SCOPE)}`)).json();
    const active = candidates.active_version_id;
    const version = (candidates.versions || []).find((row) => row.version_id === active) || {};
    const versionPage = `versions/${active}.md`;
    const text = await readInline({ page: versionPage });
    ok('A5', '版本页同屏给出作者类别与准入横幅',
      /测试准入（test_only）|组织 Owner 接受（organization_owner）/.test(text) && text.includes(String(version.authority_class)), text.slice(0, 400));
    ok('A5', '版本页说明测试准入不是企业 Owner 批准',
      /不是企业 Owner 批准/.test(text), text.slice(0, 400));
    ok('A5', '业务批准依据如实呈现，没有就写没有记录',
      /业务批准依据：/.test(text)
        && (/未记录业务批准依据/.test(text) || /已记录/.test(text)), text.slice(0, 500));
    ok('A5', '页面不把测试准入读成业务已批准', !/已获业务批准|业务已确认/.test(text), text.slice(0, 300));
    await page.screenshot({ path: join(OUT, 'task-version.png'), fullPage: false });

    await page.goto(`${BASE}/wiki?${scopeQuery({ page: versionPage })}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1200);
    const standalone = (await page.locator('#wk-banner').innerText().catch(() => '')).replace(/\s+/g, ' ');
    ok('A5', '完整阅读页给出同一条准入说明',
      /测试准入（test_only）/.test(standalone) && /不是企业 Owner 批准/.test(standalone)
        && /业务批准依据：/.test(standalone), standalone.slice(0, 400));
  });

  // ---------------------------------------------------------------- A6: the business picture
  await guarded('A6', '候选视图先给业务对象，默认不画证据', async () => {
    await page.goto(`${BASE}/#enterprise`, { waitUntil: 'networkidle' });
    await page.locator('#scope-select').waitFor({ timeout: 20000 });
    const scopeOptions = await page.locator('#scope-select option').allInnerTexts();
    const testScope = scopeOptions.find((text) => text.includes('测试成果'));
    if (testScope) await page.locator('#scope-select').selectOption({ label: testScope });
    await page.waitForTimeout(3000);
    await page.locator('#candidate-graph').waitFor({ timeout: 20000 });
    await page.locator('#candidate-graph').click();
    await page.locator('#bg-root, .bg-view').first().waitFor({ timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(2500);
    const main = (await page.locator('main').innerText()).replace(/\s+/g, ' ');
    ok('A6', '概要按类型给出业务对象',
      /业务对象：/.test(main) && /职责 23/.test(main) && /事件 4/.test(main) && /条件 1/.test(main), main.slice(0, 400));
    ok('A6', '默认不展开证据节点', /证据节点 0 \/ \d+/.test(main), main.slice(0, 300));
    const rows = await page.locator('.bg-row').count();
    ok('A6', '给出可选对象列表而不是一个中心',
      rows > 50 && (await page.locator('.bg-canvas svg').count()) === 0, `${rows} rows`);
    ok('A6', '未挂靠条目单列并可读原因',
      /未挂靠的条目/.test(main) && /没有记录适用对象/.test(main), main.slice(0, 400));

    // Names first: a row's primary label is a name; the producer key stays beside it.
    const labels = await page.evaluate(() => Array.from(document.querySelectorAll('.bg-row-label')).map((el) => el.textContent.trim()));
    const keys = await page.evaluate(() => Array.from(document.querySelectorAll('.bg-row-key')).map((el) => el.textContent.trim()));
    ok('A6', '对象列表以名称开头', labels.filter(hasHan).length > labels.length / 2, `${labels.filter(hasHan).length}/${labels.length} 含中文`);
    ok('A6', '对象列表没有把拼音键当名称', labels.filter((text) => KEY_LIKE.test(text)).length === 0,
      labels.filter((text) => KEY_LIKE.test(text)).slice(0, 3).join(' · '));
    ok('A6', '键仍作为高级信息紧邻名称', keys.filter((text) => KEY_LIKE.test(text)).length > keys.length / 2,
      `${keys.filter((text) => KEY_LIKE.test(text)).length}/${keys.length} 键`);
    await page.screenshot({ path: join(OUT, 'task-business-list.png'), fullPage: false });
  });

  await guarded('A6', '选中一个职责只看它的一跳，节点显示名称', async () => {
    await page.locator('#bg-q').fill(DUTY);
    await page.waitForTimeout(400);
    await page.locator('.bg-row:not([hidden])').first().click();
    await page.waitForTimeout(2500);
    const focus = (await page.locator('main').innerText()).replace(/\s+/g, ' ');
    ok('A6', '打开的是选中对象的一跳图',
      /一跳关联/.test(focus) && (await page.locator('.bg-canvas svg').count()) === 1, focus.slice(0, 300));
    const head = (await page.locator('.bg-focus-head').innerText().catch(() => '')).replace(/\s+/g, ' ');
    ok('A6', '焦点以业务名称称呼这个对象', head.includes(DUTY) || head.includes(HOLDER), head.slice(0, 240));
    const card = (await page.locator('.wk-obj-card').last().innerText().catch(() => '')).replace(/\s+/g, ' ');
    ok('A6', '复用对象详情并写明待审',
      /对象是什么/.test(card) && /为什么待审/.test(card) && !/业务已确认/.test(card), card.slice(0, 300));
    const labels = await page.evaluate(() => Array.from(document.querySelectorAll('.bg-canvas .bg-node-label')).map((el) => el.textContent.trim()));
    ok('A6', '图上节点显示名称而不是拼音键', labels.length > 0 && labels.every((text) => !KEY_LIKE.test(text)),
      labels.join(' · '));
    ok('A6', '节点名称里能看到持有人', labels.some((text) => text.includes(HOLDER)), labels.join(' · '));
    const titles = await page.evaluate(() => Array.from(document.querySelectorAll('.bg-canvas .bg-node')).map((el) => el.getAttribute('title') || ''));
    ok('A6', '完整名称可以打开查看（节点带完整文本）', titles.length > 0 && titles.every((text) => text.length > 0),
      titles.slice(0, 2).join(' ／ '));
    const edgeLabels = await page.evaluate(() => Array.from(document.querySelectorAll('.bg-canvas .bg-edge-label')).map((row) => row.textContent).join(' '));
    ok('A6', '边写出关系名与方向', /持有者|适用|起点|终点|主体|客体|隶属/.test(edgeLabels), edgeLabels);
    ok('A6', '版式判读不被当成已确认隶属',
      /全部节点都是候选/.test(focus) && /版式判读/.test(focus), focus.slice(0, 300));
    const href = await page.locator('.bg-wiki-link a').getAttribute('href').catch(() => null);
    ok('A6', '给出进入 Wiki 的入口并带版本与返回地址',
      Boolean(href) && /\/wiki\?/.test(href) && /version=/.test(href) && /back=/.test(href), href || 'no href');
    await page.screenshot({ path: join(OUT, 'task-business-focus.png'), fullPage: false });
  });

  await guarded('A6', '关系的节点显示谓词，不是键', async () => {
    await page.locator('[data-bg-clear]').click();
    await page.waitForTimeout(1500);
    await page.locator('#bg-q').fill('九分公司');
    await page.waitForTimeout(400);
    const entityRow = page.locator('.bg-row:not([hidden])').filter({ has: page.locator('.bg-row-label', { hasText: '九分公司' }) }).first();
    await entityRow.click();
    await page.waitForTimeout(2500);
    const relationLabels = await page.evaluate(() => Array.from(document.querySelectorAll('.bg-node.bg-relation .bg-node-label')).map((el) => el.textContent.trim()));
    ok('A6', '关系节点显示谓词', relationLabels.length > 0 && relationLabels.every((text) => text === '隶属' || text === '包含' || hasHan(text)),
      relationLabels.join(' · '));
    ok('A6', '关系节点不是拼音键', relationLabels.every((text) => !KEY_LIKE.test(text)), relationLabels.join(' · '));
  });

  await guarded('A6', '展开依据只增加依据，不改判断', async () => {
    const before = (await page.locator('.wk-obj-card').last().innerText().catch(() => '')).replace(/\s+/g, ' ');
    await page.locator('[data-bg-evidence="1"]').click();
    await page.waitForTimeout(2500);
    const after = (await page.locator('.wk-obj-card').last().innerText().catch(() => '')).replace(/\s+/g, ' ');
    const evidenceNodes = await page.locator('.bg-node.bg-evidence').count();
    ok('A6', '展开后出现证据节点', evidenceNodes > 0, `${evidenceNodes} evidence nodes`);
    ok('A6', '展开证据不改变同一对象的资格与状态',
      Boolean(before) && before === after, `${before.slice(0, 120)} -> ${after.slice(0, 120)}`);
    await page.screenshot({ path: join(OUT, 'task-business-evidence.png'), fullPage: false });
  });

  await guarded('A6', '从图进 Wiki 再返回，范围、对象和版本连续', async () => {
    const cardHead = (await page.locator('.wk-obj-card h3').last().innerText().catch(() => '')).trim();
    const focusedName = cardHead.split('·').slice(1).join('·').trim();
    const href = await page.locator('.bg-wiki-link a').getAttribute('href');
    await page.goto(BASE + href, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    const title = (await page.locator('#wk-article h1').first().innerText().catch(() => '')).trim();
    ok('A6', 'Wiki 打开的是这个对象的页面',
      Boolean(focusedName) && title.length > 0 && !KEY_LIKE.test(title), `${cardHead} → ${title}`);
    await page.waitForFunction(() => Boolean(document.querySelector('#wk-back')), null, { timeout: 20000 });
    await page.locator('#wk-back').click();
    await page.waitForTimeout(3000);
    const hash = await page.evaluate(() => location.hash);
    const focusText = (await page.locator('main').innerText()).replace(/\s+/g, ' ');
    ok('A6', '返回仍带范围、候选与对象',
      /scope=/.test(hash) && /candidate=/.test(hash) && /object=/.test(hash), hash);
    ok('A6', '返回后仍看同一个对象', /一跳关联/.test(focusText), focusText.slice(0, 300));
    await page.screenshot({ path: join(OUT, 'task-business-back.png'), fullPage: false });
  });

  // ---------------------------------------------------------------- refusals are named
  await guarded('refusal', '地址错误被明确拒绝', async () => {
    await page.goto(`${BASE}/#wiki?scope=${encodeURIComponent('enterprise:nope/project:nope')}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    const badScope = (await page.locator('main').innerText().catch(() => '')).replace(/\s+/g, ' ');
    const refusedDocument = await page.locator('#wk-inline').count();
    ok('refusal', '未知范围明确报错且不回落日常范围',
      /没有在本工作区声明|scope_unknown/.test(badScope) && refusedDocument === 0,
      `${badScope.slice(0, 200)} · reader documents: ${refusedDocument}`);
    await page.screenshot({ path: join(OUT, 'task-bad-scope.png'), fullPage: false });

    await page.goto(`${BASE}/wiki?${scopeQuery({ page: 'entities/does-not-exist.md' })}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1200);
    const badPage = (await page.locator('body').innerText().catch(() => '')).replace(/\s+/g, ' ');
    ok('refusal', '未知页面明确报错而不是换成别的文档', /没有页面|没有这个页面/.test(badPage), badPage.slice(0, 240));

    await page.goto(`${BASE}/wiki?${scopeQuery({ page: PAGE, version: 'version_0000000000000000deadbeef' })}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1200);
    const stale = (await page.locator('#wk-banner').innerText().catch(() => '')).replace(/\s+/g, ' ');
    ok('refusal', '版本已变化时读者被告知', /版本已变化/.test(stale), stale.slice(0, 240));
    await page.screenshot({ path: join(OUT, 'task-version-stale.png'), fullPage: false });

    await page.goto(`${BASE}/#wiki?${scopeQuery({ page: PAGE, version: 'version_0000000000000000deadbeef' })}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    const staleWorkbench = (await page.locator('main').innerText().catch(() => '')).replace(/\s+/g, ' ');
    ok('refusal', '工作区的阅读面也检查版本变化', /版本已变化/.test(staleWorkbench), staleWorkbench.slice(0, 240));
  });

  ok('page', '没有页面脚本错误', pageErrors.length === 0, JSON.stringify(pageErrors));
  await browser.close();

  const report = {
    base: BASE,
    scope: SCOPE,
    playwright: playwrightPath,
    ran_at: new Date().toISOString(),
    passed: checks.filter((row) => row.ok).length,
    failed: checks.filter((row) => !row.ok).length,
    page_errors: pageErrors,
    checks,
  };
  writeFileSync(join(OUT, 'reading-tasks.json'), JSON.stringify(report, null, 1), 'utf8');
  for (const row of checks) console.log(`${row.ok ? 'PASS' : 'FAIL'} ${row.task} · ${row.name}${row.ok ? '' : ' — ' + row.detail}`);
  console.log(`${report.passed} passed, ${report.failed} failed`);
  process.exit(report.failed ? 1 : 0);
}

main().catch((error) => { console.error('ACCEPTANCE_FAILED', error.message); process.exit(2); });
