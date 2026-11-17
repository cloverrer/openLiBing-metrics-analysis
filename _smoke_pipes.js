// 临时冒烟：跑 out/html/index.html 的内联脚本，打开 openUBMC 的「流水线数」弹窗与
// 其中一条流水线的「执行记录」二级弹窗，打印实际渲染出的流水线名，核对撞名兜底短名的展示。
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
    for (var k = 0; k < ROWS.length; k++){ if (ROWS[k].name === 'openUBMC'){ i = k; break; } }
    if (i < 0){ console.log('!! 首页没有 openUBMC 行，现有: ' + ROWS.map(function(r){return r.name;}).join(',')); return; }
    pipesModal(i);
    console.log('弹窗标题: ' + document.getElementById('mttl').innerHTML);
    var b = document.getElementById('mbody');
    var tb = (b.innerHTML.match(/<table[\\s\\S]*?<\\/table>/) || [''])[0];
    tb.split(/<tr[ >]/).slice(1).forEach(function(row){
      var c = (('<tr ' + row).match(/<td[^>]*>[\\s\\S]*?<\\/td>/g) || []).slice(0, 2).map(function(x){
        return x.replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ').trim();
      });
      if (c.length === 2) console.log('  弹窗行 名称=' + c[0] + ' ｜ 平台=' + c[1]);
    });
    var kk = -1;
    (ROWS[i].pipes || []).forEach(function(p, idx){ if (p.pipeline.indexOf('~') >= 0) kk = idx; });
    if (kk >= 0){
      openExecOf(i, kk);
      setTimeout(function(){
        console.log('执行记录弹窗标题: ' + document.getElementById('mttl').innerHTML);
      }, 700);
    }
    /* 首页行内（含组件级比率单元格的 title tooltip）里出现的 openUBMC 文案 */
    var seen = {}, hits = [];
    (String(document.getElementById('tb').innerHTML).match(/openUBMC[^"'<\\\\]*/g) || []).forEach(function(s){
      if (!seen[s]){ seen[s] = 1; hits.push(s); }
    });
    console.log('首页行内 openUBMC 文案: ' + hits.join(' ｜ '));
  }catch(e){ console.log('!! ERR ' + e.message + ' | ' + e.stack.split('\\n')[1]); }
}, 900);
`;
vm.runInContext(m[1] + probe, sandbox, { filename: 'index.js' });

setTimeout(function () {}, 2000);
