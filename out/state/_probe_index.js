// 在 Node 里跑真实页面脚本，抓取首页表格渲染结果（DOM 用最小桩）
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = path.resolve(__dirname, '..', 'html', 'index.html');
const OUT = path.resolve(__dirname, '..');
const html = fs.readFileSync(HTML, 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.error('no script'); process.exit(1); }
const js = m[1];

const elements = {};
function el(id) {
  if (!elements[id]) {
    elements[id] = {
      id, innerHTML: '', textContent: '', value: '', hidden: false,
      classList: { add() {}, remove() {}, toggle() {} },
      addEventListener() {}, setAttribute() {}, removeAttribute() {}, hasAttribute() { return false; },
      getAttribute() { return null; }, querySelector() { return null; }, querySelectorAll() { return []; },
      appendChild() {}, style: {}, dataset: {}, removeProperty() {}, setProperty() {},
      min: '', max: '', tHead: null, tBodies: [], offsetHeight: 0, clientHeight: 0,
    };
  }
  return elements[id];
}
// 预置页面里存在的容器
['hsub', 'tb', 'tnote', 'foot', 'rf-from', 'rf-to', 'rf-hint', 'mrec', 'mttl', 'mbody', 'mback', 'mclose'].forEach(el);

const document = {
  getElementById: el,
  querySelector() { return null; },
  querySelectorAll() { return []; },
  addEventListener() {},
  createElement() { return el('__tmp' + Math.random()); },
};
const store = {};
const localStorage = {
  getItem(k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
  setItem(k, v) { store[k] = String(v); },
  removeItem(k) { delete store[k]; },
};
const location = { search: '', href: 'http://localhost/html/index.html', protocol: 'http:', hostname: 'localhost' };
const history = { replaceState() {} };
const fetchStub = function (p) {
  const clean = String(p).replace(/^[./]*/, '');
  const fp = path.join(OUT, clean.replace(/^out[\\/]/, ''));
  return new Promise(function (resolve) {
    fs.readFile(fp, 'utf8', function (err, data) {
      if (err) return resolve({ ok: false, status: 404, json() { throw new Error('HTTP 404 ' + p); } });
      resolve({ ok: true, status: 200, json() { return Promise.resolve(JSON.parse(data)); } });
    });
  });
};

const ctx = { document, localStorage, location, history, fetch: fetchStub, console,
  URLSearchParams, Promise, JSON, Number, String, Math, Date, isNaN, Set, Map, Array, Object,
  setTimeout, clearTimeout, parseInt, parseFloat, encodeURIComponent, decodeURIComponent, URL: URL };
ctx.addEventListener = function () {};
ctx.window = ctx;
ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(js.replace(/\nboot\(\);\s*$/m, '\n'), ctx, { filename: 'index.js' });

const range = process.argv.slice(2);
const from = range[0] || '2026-11-11';
const to = range[1] || from;

const script2 = `
render_out = (async function(){
  const idx = await jget(ARCH_ROOT + 'archive/_index.json');
  IDX = idx;
  const prod = await jget(ARCH_ROOT + 'archive/_products.json').catch(function(){ return {products: []}; });
  CATALOG = (prod && prod.products) || [];
  load(${JSON.stringify(from)}, ${JSON.stringify(to)});
  await new Promise(function(r){ setTimeout(r, 800); });
  return {tb: document.getElementById('tb').innerHTML, foot: document.getElementById('foot').innerHTML,
          hint: document.getElementById('rf-hint').innerHTML};
})();
`;
vm.runInContext(script2, ctx, { filename: 'probe.js' });

ctx.render_out.then(function (r) {
  // 只抽取每个组件行的关键数字，避免刷屏
  const rows = r.tb.split('<tr>').slice(1).map(function (s) {
    const cells = [...s.matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map(function (x) { return x[1]; });
    const txt = cells.map(function (c) { return c.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(); });
    return txt.join(' | ');
  });
  console.log('=== 区间 ' + from + ' ~ ' + to + ' ===');
  console.log('hint: ' + r.hint.replace(/<[^>]+>/g, ''));
  rows.forEach(function (x) { console.log('  ' + x); });
  console.log('foot: ' + r.foot.replace(/<[^>]+>/g, ''));
});
