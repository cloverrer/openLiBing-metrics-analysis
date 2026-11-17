// 临时冒烟：把 out/html/detail.html 的内联脚本放进 Node 沙箱跑一遍（fetch 打到本地 out/），
// 打印区块头 + 根因表行 + 「执行记录」弹窗的分组标题，用来核对同名流水线（openUBMC 的
// codearts / gitcode）是否按身份分别统计、组标题是否补了平台。
const fs = require('fs'), path = require('path'), vm = require('vm');

const file = process.argv[2] || 'out/html/detail.html';
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
  location: { search: process.env.RF_SEARCH || '', href: 'http://localhost/out/html/detail.html' },
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
vm.runInContext(m[1], sandbox, { filename: 'detail.js' });

function strip(s) { return String(s).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim(); }

setTimeout(function () {
  const box = stores['recs'] || {};
  const meta = stores['meta'] || {};
  console.log('概要行: ' + strip(meta.textContent || ''));
  const tbm = (box.innerHTML || '').match(/<table[\s\S]*?<\/table>/);
  if (!tbm) {
    console.log('区块头: ' + strip(box.innerHTML).slice(0, 300));
  } else {
    const rows = tbm[0].split(/<tr[ >]/).slice(1);
    rows.forEach(function (r) {
      if (!/rc-main/.test(r)) return;
      const cells = (('<tr ' + r).match(/<td[^>]*>[\s\S]*?<\/td>/g) || []).slice(0, 3).map(strip);
      console.log('  行 ' + cells.join(' | '));
    });
  }
  // 执行记录弹窗：直接调页面上的函数（入口是 data-execpipes 的 span，沙箱里点不了）
  if (typeof sandbox.openExecByPipe === 'function') {
    sandbox.openExecByPipe();
    Object.keys(stores).forEach(function (k) {
      const s = String(stores[k].innerHTML || '');
      const hd = s.match(/<div class="pexec-hd">[\s\S]*?<\/div>/g);
      if (!hd) return;
      console.log('[' + k + '] 执行记录分组：');
      hd.forEach(function (h) { console.log('   ' + strip(h)); });
      const sum = s.match(/<div class="pexec-sum">[\s\S]*?<\/div>/);
      if (sum) console.log('   概要：' + strip(sum[0]));
    });
  }
}, 900);
