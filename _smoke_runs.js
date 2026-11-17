// 临时冒烟：跑 out/html/detail.html 内联脚本，直接调 runsTable 渲染一条 ISO 时间的运行，
// 核对二级页「执行记录」弹窗的起止时间是否已去掉 T。
const fs = require('fs'), path = require('path'), vm = require('vm');

const html = fs.readFileSync(process.argv[2] || 'out/html/detail.html', 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.error('没有找到内联脚本'); process.exit(2); }

const OUT = path.resolve('out');
function norm(u) { u = String(u).replace(/^\.\//, ''); while (u.startsWith('../')) u = u.slice(3); return path.join(OUT, u); }
const stores = {};
function mkEl(id) {
  return { id, value: '', min: '', max: '', innerHTML: '', textContent: '', hidden: false, dataset: {},
           style: { setProperty() {}, removeProperty() {} },
           classList: { toggle() {}, add() {}, remove() {} },
           addEventListener() {}, getAttribute() { return null; }, setAttribute() {}, focus() {} };
}
function el(id) { if (!stores[id]) stores[id] = mkEl(id); return stores[id]; }

const sandbox = {
  console,
  document: { getElementById: el, querySelector: () => null, querySelectorAll: () => [], addEventListener() {}, body: mkEl('body') },
  window: { addEventListener() {} },
  location: { search: '', href: 'http://localhost/out/html/detail.html' },
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

const probe = `
try{
  var html = runsTable([
    {rn:2020, status:'SUCCESS', start:'2026-11-13T03:05:02', end:'2026-11-13T03:52:02', iva:true, bc:1, bpc:1, cpr:null, ftt:null},
    {rn:2019, status:'SUCCESS', start:'2026-11-12 02:34:43', end:'2026-11-12 03:21:43', iva:true, bc:1, bpc:1, cpr:null, ftt:null}
  ], '2026-11-10', '2026-11-13');
  var tbs = html.match(/<table[\\s\\S]*?<\\/table>/g) || [];
  var tb = tbs[0] || '';
  tb.split(/<tr[ >]/).slice(1).forEach(function(row){
    var c = (('<tr ' + row).match(/<td[^>]*>[\\s\\S]*?<\\/td>/g) || []).map(function(x){ return x.replace(/<[^>]*>/g,' ').replace(/\\s+/g,' ').trim(); });
    if (c.length >= 8) console.log('  ' + c[0] + ' | 开始=' + c[6] + ' | 结束=' + c[7]);
  });
  console.log('含 T 的单元格数: ' + ((String(html).match(/\\d{2}:\\d{2}:\\d{2}T|T\\d{2}:\\d{2}/g) || []).length));
}catch(e){ console.log('!! ERR ' + e.message + ' | ' + e.stack.split('\\n')[1]); }
`;
vm.runInContext(m[1] + probe, sandbox, { filename: 'detail.js' });
