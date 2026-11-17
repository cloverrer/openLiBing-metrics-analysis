// 临时冒烟：跑 out/html/index.html 内联脚本，打开 openGauss 一条流水线的「执行记录」弹窗，
// 打印渲染出的起止时间，核对 ISO 的 T 是否已归一成空格。
const fs = require('fs'), path = require('path'), vm = require('vm');

const html = fs.readFileSync(process.argv[2] || 'out/html/index.html', 'utf8');
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
  return { id, value: '', min: '', max: '', innerHTML: '', textContent: '', hidden: false, dataset: {},
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
  location: { search: process.env.RF_SEARCH || '?from=2026-11-10&to=2026-11-13', href: 'http://localhost/out/html/index.html' },
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
setTimeout(function(){
  try{
    var i = -1;
    for (var k = 0; k < ROWS.length; k++){ if (ROWS[k].name === 'openGauss'){ i = k; break; } }
    if (i < 0){ console.log('!! 首页没有 openGauss 行，现有: ' + ROWS.map(function(r){return r.name;}).join(',')); return; }
    var kk = -1;
    (ROWS[i].pipes || []).forEach(function(p, idx){ if (String(p.pipeline).indexOf('centos-x86') >= 0) kk = idx; });
    if (kk < 0){ console.log('!! 没找到 centos-x86 流水线，现有: ' + (ROWS[i].pipes||[]).map(function(p){return p.pipeline;}).join(',')); return; }
    openExecOf(i, kk);
    setTimeout(function(){
      console.log('弹窗标题: ' + document.getElementById('mttl').innerHTML);
      var b = document.getElementById('mbody').innerHTML;
      var tbs = b.match(/<table[\\s\\S]*?<\\/table>/g) || [];
      var tb = tbs[0] || '';
      tb.split(/<tr[ >]/).slice(1).forEach(function(row){
        var c = (('<tr ' + row).match(/<td[^>]*>[\\s\\S]*?<\\/td>/g) || []).map(function(x){
          return x.replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ').trim();
        });
        if (c.length >= 8) console.log('  ' + c[0] + ' | 开始=' + c[6] + ' | 结束=' + c[7]);
      });
      console.log('含 T 的单元格数: ' + ((String(b).match(/\\d{2}:\\d{2}:\\d{2}T|T\\d{2}:\\d{2}/g) || []).length));
    }, 800);
  }catch(e){ console.log('!! ERR ' + e.message + ' | ' + e.stack.split('\\n')[1]); }
}, 900);
`;
vm.runInContext(m[1] + probe, sandbox, { filename: 'index.js' });

setTimeout(function () {}, 2500);
