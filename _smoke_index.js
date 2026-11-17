// 临时冒烟：把 out/html/index.html 里的脚本放进 Node 沙箱跑一遍（fetch 打到本地 out/），
// 打印社区组件行实际渲染出的比率与 title，用来核对两套分母口径。
const fs = require('fs'), path = require('path'), vm = require('vm');

const file = process.argv[2] || 'out/html/index.html';
const html = fs.readFileSync(file, 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.error('没有找到内联脚本'); process.exit(2); }

const OUT = path.resolve('out');
function norm(u) {
  u = String(u).replace(/^\.\//, '');
  while (u.startsWith('../')) u = u.slice(3);
  return path.join(OUT, u);
}
const stores = {};
function mkEl(id) {
  return { id, value: '', min: '', max: '', innerHTML: '', textContent: '', dataset: {},
           style: { setProperty() {}, removeProperty() {} },
           classList: { toggle() {}, add() {}, remove() {} },
           addEventListener() {}, getAttribute() { return null; }, setAttribute() {}, focus() {} };
}
function el(id) { if (!stores[id]) stores[id] = mkEl(id); return stores[id]; }

const sandbox = {
  console,
  document: { getElementById: el, querySelector: () => null, querySelectorAll: () => [],
              addEventListener() {}, body: mkEl('body') },
  window: { addEventListener() {} },
  location: { search: process.env.RF_SEARCH || '', href: 'http://localhost/out/html/index.html' },
  history: { replaceState() {} },
  URLSearchParams,
  fetch: (u) => new Promise((res, rej) => {
    const f = norm(u);
    fs.readFile(f, 'utf8', (e, t) => {
      if (e) return rej(Object.assign(new Error('ENOENT ' + f), { status: 404 }));
      res({ ok: true, status: 200, text: () => Promise.resolve(t), json: () => Promise.resolve(JSON.parse(t)) });
    });
  }),
  setTimeout, clearTimeout, Promise, Map, Set,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(m[1], sandbox, { filename: 'index.js' });

setTimeout(function () {
  if (stores['ttl']) console.log('标题:', (stores['ttl'].innerHTML || stores['ttl'].textContent));
  if (stores['crumb']) console.log('面包屑:', (stores['crumb'].innerHTML || '').replace(/<[^>]*>/g, ' '));
  if (stores['recs']) {
    const h3 = ((stores['recs'].innerHTML || '').match(/<h3[^>]*>([\s\S]*?)<\/h3>/) || [])[1] || '(无 h3)';
    console.log('\n区块头:', h3.replace(/<[^>]*>/g, '').trim());
    const h3t = ((stores['recs'].innerHTML || '').match(/<h3 title="([\s\S]*?)"/) || [])[1] || '';
    console.log('区块头 title:\n  ' + h3t.replace(/&quot;/g, '"').split('（逐日').join('\n  （逐日'));
  }
  if (process.env.SMOKE_EXEC === '1' && typeof sandbox.openExecByPipe === 'function') {
    sandbox.openExecByPipe();
    console.log('\n执行记录弹窗标题:', (stores['mttl'] || {}).innerHTML);
    const body = (stores['mbody'] || {}).innerHTML || '';
    console.log('汇总:', ((body.match(/<div class="pexec-sum">([\s\S]*?)<\/div>/) || [])[1] || '').replace(/<[^>]*>/g, ''));
    const heads = body.match(/<div class="pexec-hd">[\s\S]*?<\/div><\/div>/g) || [];
    heads.forEach(function (h) { console.log('  组头:', h.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()); });
  }
  const tb = (stores['tb'] || {}).innerHTML || '';
  if (!tb) return;
  const rows = tb.split('<tr>').slice(1);
  console.log('渲染行数:', rows.length);
  rows.forEach(function (r) {
    const tr = '<tr>' + r;
    const name = ((tr.match(/c-name">([^<]*)</) || [])[1] || '');
    if (['openGauss', 'openEuler'].indexOf(name) < 0) return;
    const cells = (tr.match(/<td[^>]*>[\s\S]*?<\/td>/g) || []);
    const vaCell = cells[1] || '', bsCell = cells[2] || '';
    const vaT = ((vaCell.match(/title="([^"]*)"/) || [])[1] || '').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
    const bsT = ((bsCell.match(/title="([^"]*)"/) || [])[1] || '').replace(/&quot;/g, '"');
    console.log('\n== ' + name);
    console.log('  版本可用度单元格:', vaCell.replace(/<[^>]*>/g, ''));
    console.log('  构建成功率单元格:', bsCell.replace(/<[^>]*>/g, ''));
    console.log('  可用度 title:\n    ' + vaT.split('\n').join('\n    '));
    console.log('  成功率 title:\n    ' + bsT.split('\n').join('\n    '));
    console.log('  流水线数/待分析:', cells.slice(3).map(function (c) { return c.replace(/<[^>]*>/g, ' ').trim(); }).join(' | '));
  });
  const foot = (stores['foot'] || {}).innerHTML || '';
  console.log('\n页脚:', foot.replace(/<[^>]*>/g, ''));
}, 800);
