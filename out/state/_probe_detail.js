// 在 Node 里跑真实详情页脚本，渲染「执行记录」弹窗内容（DOM 用最小桩）
// 用法: node out/state/_probe_detail.js <comp> <dim> <from> [to]
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const OUT = path.resolve(__dirname, '..');
const HTML = path.join(OUT, 'html', 'detail.html');
const html = fs.readFileSync(HTML, 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.error('no script'); process.exit(1); }
const js = m[1];

const argv = process.argv.slice(2);
const COMP_ARG = argv[0] || 'HPCKit';
const DIM_ARG = argv[1] || 'va';
const FROM = argv[2] || '2026-11-06';
const TO = argv[3] || FROM;

const elements = {};
function el(id) {
  if (!elements[id]) {
    elements[id] = {
      id, innerHTML: '', textContent: '', value: '', hidden: false, scrollTop: 0,
      classList: { add() {}, remove() {}, toggle() {} },
      addEventListener() {}, setAttribute() {}, removeAttribute() {}, hasAttribute() { return false; },
      getAttribute() { return null; }, querySelector() { return null; }, querySelectorAll() { return []; },
      appendChild() {}, style: {}, dataset: {}, removeProperty() {}, setProperty() {},
      min: '', max: '', tHead: null, tBodies: [], offsetHeight: 0, clientHeight: 0,
    };
  }
  return elements[id];
}
['hsub', 'tb', 'tnote', 'foot', 'rf-from', 'rf-to', 'rf-hint', 'mrec', 'mttl', 'mbody',
 'mback', 'mclose', 'recs', 'ttl', 'plant-tip', 'back-btn'].forEach(el);

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
const qs = '?comp=' + encodeURIComponent(COMP_ARG) + '&dim=' + encodeURIComponent(DIM_ARG)
  + '&from=' + FROM + '&to=' + TO;
const location = { search: qs, href: 'http://localhost/html/detail.html', protocol: 'http:', hostname: 'localhost' };
const history = { replaceState() {} };
const fetchStub = function (p) {
  const clean = String(p).replace(/^[./]*/, '');
  const fp = path.join(OUT, clean);
  return new Promise(function (resolve) {
    fs.readFile(fp, 'utf8', function (err, data) {
      if (err) return resolve({ ok: false, status: 404, json() { throw new Error('HTTP 404 ' + p); } });
      resolve({ ok: true, status: 200, json() { return Promise.resolve(JSON.parse(data)); } });
    });
  });
};

const ctx = { document, localStorage, location, history, fetch: fetchStub, console,
  URLSearchParams, Promise, JSON, Number, String, Math, Date, isNaN, Set, Map, Array, Object,
  setTimeout, clearTimeout, parseInt, parseFloat, encodeURIComponent, decodeURIComponent, URL };
ctx.addEventListener = function () {};
ctx.window = ctx;
ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(js.replace(/\nboot\(\);\s*$/m, '\n'), ctx, { filename: 'detail.js' });

const script2 = `
render_out = (async function(){
  const idx = await jget('../archive/_index.json');
  DAYS = (idx.days || []).slice().sort(function(a,b){ return a.date < b.date ? -1 : 1; });
  load(${JSON.stringify(FROM)}, ${JSON.stringify(TO)});
  await new Promise(function(r){ setTimeout(r, 2500); });
  const h3 = document.getElementById('recs').innerHTML;
  openExecByPipe();
  return {h3runs: (CTX && (CTX.runs||[]).length) || 0,
          title: document.getElementById('mttl').innerHTML,
          body: document.getElementById('mbody').innerHTML,
          h3head: h3.slice(0, 900)};
})();
`;
vm.runInContext(script2, ctx, { filename: 'probe.js' });

ctx.render_out.then(function (r) {
  const strip = function (s) {
    return s.replace(/<div class="pexec-grp">/g, '\n  --- GROUP ---')
      .replace(/<div class="pexec-hd">/g, '\n  [HD] ')
      .replace(/<div class="pexec-row">/g, '\n       ')
      .replace(/<div class="pexec-lg">/g, '\n  [LG] ')
      .replace(/<div class="pexec-sum">/g, '\n  [SUM] ')
      .replace(/<div class="mrec-note">/g, '\n  [NOTE] ')
      .replace(/<[^>]+>/g, ' ')
      .replace(/[ \t]+/g, ' ');
  };
  console.log('=== 组件 ' + COMP_ARG + ' 维度 ' + DIM_ARG + ' 区间 ' + FROM + ' ~ ' + TO + ' ===');
  console.log('ctx.runs =', r.h3runs);
  console.log('二级页区块头(前 900 字):');
  console.log(strip(r.h3head));
  console.log('\n弹窗标题:', r.title.replace(/<[^>]+>/g, ''));
  console.log('弹窗内容:');
  console.log(strip(r.body));
}).catch(function (e) { console.error('ERR', e && e.stack || e); process.exit(1); });
