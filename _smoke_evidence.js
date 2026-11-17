// 临时冒烟：跑 out/html/detail.html 的内联脚本（fetch 打到本地 out/），
// 逐条打开「证据」弹窗，核对 openGauss 两条失败记录的证据里是否出现磁盘写满原文行。
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
  return { id, value: '', min: '', max: '', innerHTML: '', textContent: '', dataset: {}, hidden: false,
           style: { setProperty() {}, removeProperty() {} },
           classList: { toggle() {}, add() {}, remove() {} },
           addEventListener() {}, getAttribute() { return null; }, setAttribute() {}, focus() {} };
}
function el(id) { if (!stores[id]) stores[id] = mkEl(id); return stores[id]; }

const handlers = { doc: {}, win: {} };
const on = (bag) => (t, f) => { (bag[t] = bag[t] || []).push(f); };

const sandbox = {
  console,
  document: { getElementById: el, querySelector: () => null, querySelectorAll: () => [],
              addEventListener: on(handlers.doc), readyState: 'complete',
              body: mkEl('body') },
  window: { addEventListener: on(handlers.win) },
  location: { search: process.env.RF_SEARCH || '', href: 'http://localhost/out/html/detail.html' },
  history: { replaceState() {} },
  URLSearchParams,
  fetch: (u) => new Promise((res, rej) => {
    const f = norm(u);
    if (process.env.RF_DEBUG) console.log('FETCH ' + u + '  ->  ' + f);
    fs.readFile(f, 'utf8', (e, t) => {
      if (e) { if (process.env.RF_DEBUG) console.log('  404 ' + f); return rej(Object.assign(new Error('ENOENT ' + f), { status: 404 })); }
      res({ ok: true, status: 200, text: () => Promise.resolve(t), json: () => Promise.resolve(JSON.parse(t)) });
    });
  }),
  setTimeout, clearTimeout, Promise, Map, Set, Number, String, JSON, Date, RegExp, Array, Object,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(m[1], sandbox, { filename: 'detail.js' });

/* 页面是等 DOMContentLoaded / load 才启动的，沙箱里没有真实事件，这里手动派发一遍 */
['DOMContentLoaded', 'load', 'readystatechange'].forEach(function (t) {
  (handlers.doc[t] || []).concat(handlers.win[t] || []).forEach(function (f) {
    try { f({ type: t }); } catch (e) { console.log('boot[' + t + '] 抛错: ' + (e && e.message)); }
  });
});

const strip = (s) => String(s || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
const fn = sandbox.openEvidence;

/* 记录是异步 fetch 回来的，反复试开第 0 条直到弹窗真的画出来为止 */
let tries = 0;
function waitReady() {
  tries++;
  try { fn(0); } catch (e) { /* 数据还没到 */ }
  const t = (stores['mttl'] || {}).innerHTML;
  if (!t && tries < 80) return setTimeout(waitReady, 400);
  main();
}

function main() {
  const n = parseInt(process.env.RF_N || '80', 10);
  let shown = 0;
  for (let i = 0; i < n && shown < 6; i++) {
    try { fn(i); } catch (e) { continue; }
    const title = strip((stores['mttl'] || {}).innerHTML);
    const body = String((stores['mbody'] || {}).innerHTML || '');
    if (!title || !/opengauss|openeuler/i.test(title)) continue;
    const rows = (body.match(/<tr[ >]/g) || []).length - 1;      /* 减去表头行 */
    const hits = (body.match(/No space left on device/g) || []).length;
    const cells = strip(body).split('L').slice(-1)[0];
    console.log('  [' + i + '] ' + title);
    console.log('        证据行数=' + rows + '  含 No space left on device 的行=' + hits);
    console.log('        末行原文: ' + cells.slice(0, 120));
    shown++;
  }
  if (!shown) console.log('（没有匹配到 openGauss/openEuler 的证据弹窗）');
}

waitReady();
