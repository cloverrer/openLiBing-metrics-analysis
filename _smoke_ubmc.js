// 临时冒烟：核对 openUBMC 两条同名流水线的「执行记录」各自取到哪批运行（按 key/pipelineId 归属）。
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
  location: { search: process.env.RF_SEARCH || '?from=2026-11-16&to=2026-11-16', href: 'http://localhost/out/html/index.html' },
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
    if (i < 0){ console.log('!! 首页没有 openUBMC 行'); return; }
    var r = ROWS[i];
    console.log('区间 ' + r.from + ' ~ ' + r.to + ' | 流水线 ' + r.pipeCount + ' 条 | 组件VA=' + r.vaRate + ' BS=' + r.bsRate);
    (r.pipes || []).forEach(function(p, idx){
      console.log('  [' + idx + '] key=' + p.key + ' | short=' + p.pipeline + ' | disp=' + plDisp(p)
        + ' | platform=' + p.platform + ' | VA=' + p.vaRate + ' BS=' + p.bsRate + ' | noRun=' + p.noRun);
    });
    var idxs = (r.pipes || []).map(function(p, idx){ return idx; });
    function step(n){
      if (n >= idxs.length) return;
      var k = idxs[n];
      openExecOf(i, k);
      setTimeout(function(){
        var ttl = String(document.getElementById('mttl').innerHTML || '').replace(/<[^>]*>/g, '');
        var body = String(document.getElementById('mbody').innerHTML || '');
        var nums = (body.match(/#\\d+/g) || []).slice(0, 12);
        var urls = (body.match(/pipelineId=[0-9a-f]{8}/g) || []).slice(0, 3);
        console.log('  弹窗[' + k + '] ' + ttl + ' -> 构建号 ' + nums.join(',') + ' | ' + urls.join(','));
        step(n + 1);
      }, 900);
    }
    step(0);
  }catch(e){ console.log('!! ERR ' + e.message + ' | ' + e.stack.split('\\n')[1]); }
}, 1200);
`;
vm.runInContext(m[1] + probe, sandbox, { filename: 'index.js' });

setTimeout(function () {}, 4000);
