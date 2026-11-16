
const WD_CAL = ["2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13", "2026-11-16"];

/* ==== 公共日期筛选组件（唯一来源 lib/ui.py，口径 = 执行结束时间）==== */
const RF_FIELD = "pipelineRunEndtime";
const rfState = {min:null, max:null, prev:null, seg:null, onChange:null};

function rfYmd(d){const p=n=>String(n).padStart(2,'0');return d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate());}
function rfShift(ymd, days){const d=new Date(ymd+'T00:00:00');d.setDate(d.getDate()+days);return rfYmd(d);}
/* 区间内工作日数（周一~周五）。只是**兜底**：真正的法定工作日（含节假日/调休补班）
   由第 9 步把 lib/workdays.py 算出的日历注入成 WD_CAL，见下面的 wdInRange()。 */
function rfWorkdays(f, t){
  if (!f || !t) return 0;
  let d = new Date(f + 'T00:00:00'), end = new Date(t + 'T00:00:00'), n = 0;
  while (d <= end && n < 4000){
    const w = d.getDay();
    if (w !== 0 && w !== 6) n++;
    d.setDate(d.getDate() + 1);
  }
  return n;
}
/* 区间内「法定工作日数」= 版本可用度的分母（顶部「工作日 N 天」也用它）。
   WD_CAL 由第 9 步注入（lib/workdays.build_workday_set 的结果，含节假日与调休补班），
   与后端 step_2/step_7 的分母同源；只有区间超出日历覆盖范围
   （早于归档首日 / 晚于今天）时才退回周一~周五估算。 */
function wdInRange(f, t){
  if (!f || !t) return 0;
  const cal = (typeof WD_CAL !== 'undefined' && WD_CAL && WD_CAL.length) ? WD_CAL : null;
  if (cal && f >= cal[0] && t <= cal[cal.length - 1]){
    let n = 0;
    for (let i = 0; i < cal.length; i++){ const d = cal[i]; if (d >= f && d <= t) n++; }
    return n;
  }
  return rfWorkdays(f, t);
}
/* 「这条流水线在这里到底跑没跑过」的唯一判据：runsInPeriod 是第 7 步按区间运行数写死的，
   0 就是一次都没跑（RAGSDK / VisionSDK 这类只有看板配置、从没执行过的流水线）。
   为什么必须判：归档对「区间内无运行」的流水线会退回看板值（历史上是 0.0），
   那个 0 表示「压根没跑」而不是「跑了但不可用」；一旦被当成算出过的比率收进平均值，
   「无执行记录」就会被统计成 0.00%（用户反馈过两次）。老归档缺该字段时放行。 */
function ranInPeriod(pl){
  const v = pl ? pl.runsInPeriod : null;
  if (v === null || v === undefined || v === '') return true;
  return Number(v) > 0;
}
function rfClamp(v){return (v && rfState.min && v<rfState.min) ? rfState.min : ((v && rfState.max && v>rfState.max) ? rfState.max : v);}

/* 快捷段 → 实际区间：7/30/90 以归档最大日为右端，左端不早于归档最小日（数据不足时自动收缩）；
   「昨天」是唯一的例外 —— 它永远是「真实今天减一天」那一天，不吸附归档最大日、不跳过非工作日，
   那天没跑数（周末/节假日）就由页面把指标显示成 -- */
function rfSegRange(r){
  const max = rfState.max || rfYmd(new Date());
  if (r === 'prev'){ const p = rfState.prev || rfShift(rfYmd(new Date()), -1); return {f: p, t: p}; }
  const n = Number(r);
  if (!n) return null;
  let f = rfShift(max, -(n - 1));
  if (rfState.min && f < rfState.min) f = rfState.min;
  return {f: f, t: max};
}

function rfInit(opts){
  opts = opts || {};
  rfState.min = opts.min || null;
  rfState.max = opts.max || null;
  /* 「昨天」的锚点 = 真实今天减一天，不做任何夹取。
     以前这里会把昨天吸附到「归档最大日」，于是周末/节假日点「昨天」，
     看到的其实是上一个工作日的备份数据 —— 看起来就像页面自动跳过了工作日。
     现在昨天就是昨天：那天没有归档，指标就显示 --（不再拿别的日子顶替）。 */
  rfState.prev = rfShift(rfYmd(new Date()), -1);
  rfState.onChange = opts.onChange || null;   /* 不接上 onChange，页面就永远不会按区间取数 */
  const fromEl = document.getElementById('rf-from');
  const toEl   = document.getElementById('rf-to');
  if (rfState.min) { fromEl.min = rfState.min; toEl.min = rfState.min; }
  /* 日期框上界放到「今天」（而不是归档最大日）：归档还没落到昨天时，
     昨天也必须能在日历里选中，选中后由页面显示 -- */
  const cap = (rfState.max && rfState.max > rfYmd(new Date())) ? rfState.max : rfYmd(new Date());
  fromEl.max = cap; toEl.max = cap;

  const qs = new URLSearchParams(location.search);
  const storedSeg = localStorage.getItem('rf_seg') || null;
  /* 默认段取「近 7 天」（用户口径）：打开页面即选中近 7 天快捷段 */
  const def = rfSegRange('7') || {f: rfState.min, t: rfState.max};
  let from, to;
  if (storedSeg === 'prev'){
    /* 「昨天」是相对日期，每次打开都按当天重算，不沿用上次存下来的旧日期 */
    const rg = rfSegRange('prev');
    from = rg.f; to = rg.t;
  } else if (storedSeg && rfSegRange(storedSeg)){
    /* 近 7 / 30 / 90 天也是相对日期：按归档最大日重新锚定，
       归档长了一天后打开，看到的仍是「最近的 N 天」而不是上次冻结的旧区间 */
    const rg = rfSegRange(storedSeg);
    from = rg.f; to = rg.t;
  } else {
    from = qs.get('from') || localStorage.getItem('rf_from') || def.f;
    to   = qs.get('to')   || localStorage.getItem('rf_to')   || def.t;
  }
  /* 只兜最小日：右端不再夹到归档最大日，否则「昨天」会被悄悄换成别的日子 */
  if (rfState.min && from < rfState.min) from = rfState.min;
  if (from > to) from = to;
  fromEl.value = from || ''; toEl.value = to || '';

  /* 选中态：seg 只在「当前区间仍是该段算出来的区间」时才算数。
     原实现的致命问题：paintSeg() 读的是 rfInit 的闭包变量 from/to，初始化后永不更新，
     所以点任何快捷段，高亮都停在初始那一段（表现为「点了没反应」）。 */
  let seg = storedSeg;
  function segHit(r, f, t){
    const rg = rfSegRange(r);
    return !!rg && rg.f === f && rg.t === t;
  }
  function deriveSeg(f, t){
    if (!f || !t) return null;
    let hit = null;
    document.querySelectorAll('#rf-seg button').forEach(function(b){
      if (hit === null && segHit(b.dataset.range, f, t)) hit = b.dataset.range;
    });
    return hit;
  }
  function paintSeg(){
    const f = fromEl.value, t = toEl.value;
    if (seg && !segHit(seg, f, t)) seg = null;      // 日期被手动改过 → 丢弃旧段
    const r = seg || deriveSeg(f, t);
    rfState.seg = r;
    document.querySelectorAll('#rf-seg button').forEach(function(b){
      b.classList.toggle('on', b.dataset.range === r);
    });
  }

  function commit(){
    const f = fromEl.value || rfState.min, t = toEl.value || rfState.max;
    fromEl.value = f || ''; toEl.value = t || '';
    localStorage.setItem('rf_from', f || ''); localStorage.setItem('rf_to', t || '');
    localStorage.setItem('rf_seg', seg || '');
    const u = new URL(location.href); u.searchParams.set('from', f || ''); u.searchParams.set('to', t || '');
    history.replaceState(null, '', u);
    paintSeg(); paintHint();
    if (rfState.onChange) rfState.onChange(f, t);
  }
  window.__rfCommit = commit;

  function paintHint(){
    const f = fromEl.value, t = toEl.value;
    const el = document.getElementById('rf-hint');
    if (!f || !t) { if (el) el.textContent = ''; return; }
    const wd = wdInRange(f, t);
    /* 单日且不是工作日：明确写清楚「不是跳过工作日，是这天本来就没跑数」 */
    const idle = (f === t && wd === 0);
    if (el) el.innerHTML = '当前区间 <b>' + f + '</b> ~ <b>' + t + '</b> ｜ 工作日 ' + wd + ' 天'
      + (idle ? ' ｜ <span class="dim">非工作日，当日无跑数，指标显示 --</span>' : '');
  }
  rfState.paintHint = paintHint;

  document.querySelectorAll('#rf-seg button').forEach(function(b){
    b.addEventListener('click', function(){
      const rg = rfSegRange(b.dataset.range);
      if (!rg) return;
      seg = b.dataset.range;                       // 先记下要选中的段，再由 commit 统一落盘
      fromEl.value = rg.f; toEl.value = rg.t;
      commit();
    });
  });
  fromEl.addEventListener('change', function(){ seg = null; if (fromEl.value > toEl.value) toEl.value = fromEl.value; commit(); });
  toEl.addEventListener('change',   function(){ seg = null; if (toEl.value < fromEl.value) fromEl.value = toEl.value; commit(); });
  paintSeg(); paintHint();
  if (rfState.onChange) rfState.onChange(fromEl.value, toEl.value);
}
function rfDays(a, b){ const d1=new Date(a+'T00:00:00'), d2=new Date(b+'T00:00:00'); return Math.round((d2-d1)/86400000)+1; }
function rfIn(ymd){ const f=document.getElementById('rf-from').value, t=document.getElementById('rf-to').value;
  return !!ymd && ymd >= f && ymd <= t; }
function rfEsc(s){ return String(s==null?'':s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }


/* ================= 统计口径（只在首页，按条展示） =================
   纯口径、与取数无关，所以脚本一执行就填好，不用等归档数据回来。
   每条 = <li><b>小标题</b>：说明</li>；唯一来源是本文件的 CALIBER_JS，二级页不再挂一份。 */
function caliberItems(){
  return [
    ['统计区间',
     '按流水线<b>执行结束时间</b>归属日期（GitHub 平台取 <span class="mono">run.updated_at</span>），'
     + '结束时间落在所选区间内才计入；换区间即按新区间整体重算。'],
    ['版本可用度（流水线）',
     '<b>可用日 ÷ 区间法定工作日数</b>。可用日 = 当天有<b>执行成功</b>的运行，'
     + '<b>并且该运行的测试用例通过率 100%</b>。'],
    ['版本可用度（组件）',
     '该组件各流水线版本可用度之和 ÷ 流水线条数（算术平均），'
     + '不是 Σ可用日 ÷ Σ有运行日。'],
    ['特例',
     '（GitHub 平台流水线不看用例 100%；'
     + 'vllm-ascend 的流水线只采集定时任务（schedule）触发的运行。）'],
    ['区间内无执行记录',
     '只有看板配置、一次都没跑过的流水线显示 <span class="mono">--</span>，'
     + '不参与平均、不计入流水线条数、也不算「待分析流水线数」。'],
    ['构建成功率',
     'Σ编译通过 ÷ Σ编译次数；GitHub 平台不采集编译次数，显示 <span class="mono">--</span>。'],
    ['区间重算与灯色',
     '区间一变就按分子/分母重算（不是逐日比率取平均）；灯色不落库，'
     + '按重算后的比率就地判档：版本可用度 &ge;90% 绿 / &ge;80% 黄 / 否则红，'
     + '构建成功率 100% 绿 / &ge;95% 黄 / 否则红，区间内只出这一档。'],
    ['待分析流水线数',
     '该组件在区间内进入待分析集合、且对应维度重算后未达标的流水线条数，'
     + '与看板「待分析」判定一致，不是失败次数。'],
  ];
}
function caliberHTML(){
  const items = caliberItems();
  return '<div class="tn-hd">统计口径（' + items.length + ' 条）</div>'
    + '<ul class="tn-list">'
    + items.map(function(kv){ return '<li><b>' + kv[0] + '</b>：' + kv[1] + '</li>'; }).join('')
    + '</ul>';
}
/* 页面脚本都在 body 末尾执行，容器已在 DOM 里 → 直接填一次（首页才有这份口径） */
(function(){
  const el = document.getElementById('tnote');
  if (el) el.innerHTML = caliberHTML();
})();

/* ================= 首页：读归档 JSON，按执行结束时间区间聚合 ================= */
/* 数据根：一律相对「当前文档」算，全程不出现域名也不写死站点根。
   正常情况页面在 out/html/ 下，第一枪 '../' 就命中 out/archive/；
   万一整站被放到别的层级（比如直接以 out/ 为站点根），后面几枪能自己找到，
   不会因为层级差一层就整页空白。 */
let ARCH_ROOT = '../';
const ROOT_CANDIDATES = ['../', './', '../../', '../../../'];
function probeRoot(){
  let i = 0;
  function step(){
    if (i >= ROOT_CANDIDATES.length){
      return Promise.reject(new Error('archive/_index.json → HTTP 404（已依次试过：'
        + ROOT_CANDIDATES.join('  ') + '）'));
    }
    const cand = ROOT_CANDIDATES[i++];
    return jget(cand + 'archive/_index.json').then(function(x){
      ARCH_ROOT = cand;          /* 命中后就固定下来，后面所有数据都拼这个前缀 */
      return x;
    }).catch(function(e){
      if (isNotFound(e)) return step();
      throw e;
    });
  }
  return step();
}

const DETAIL_PAGE = 'detail.html';   /* 二级页文件名（构建时注入，避免 JS 里出现未定义变量） */
const LIGHT_RANK = {'红': 3, '黄': 2, '绿': 1};
let IDX = null;
let CATALOG = [];        /* archive/_products.json：全部开源组件（含无待分析流水线的） */
let ROWS = [];           /* 最近一次 render 的组件行：点「流水线数」时从这里取该组件的流水线清单 */

function jget(p){
  return fetch(p, {cache: 'no-store'}).then(function(r){
    if (!r.ok) throw new Error(p + ' → HTTP ' + r.status);
    return r.json();
  });
}
/* 文件不存在（归档区还没跑过采集）与「读取失败」要分开：前者提示去采集，后者才是环境问题 */
function isNotFound(e){
  const m = String((e && e.message) || e);
  return /HTTP 40[34]/.test(m) || /\b(404|ENOENT)\b/.test(m) || /not\s*found/i.test(m);
}
/* ===== 一条流水线归档的统一读法（与二级页同一套） =====
   归档已把「9 份 JSON + records/run_*.json」合并成一份 pipeline.json（schema=pipeline/1），
   运行历史在 steps.step_2_runs.runHistory —— 一次 fetch 就拿到，弹窗里点「查看」时才按需读。
   碰到还没合并的老归档（pipeline.json 不存在）自动退回 step_2_runs.json，页面不用分支。 */
function jpipe(dirPath){
  const base = ARCH_ROOT + dirPath + '/';
  return jget(base + 'pipeline.json').then(function(doc){
    doc = doc || {};
    return {base: base, merged: true,
            runs: (((doc.steps || {}).step_2_runs || {}).runHistory) || []};
  }).catch(function(e){
    if (!isNotFound(e)) throw e;
    return jget(base + 'step_2_runs.json').catch(function(){ return {}; }).then(function(s2){
      return {base: base, merged: false, runs: (s2 || {}).runHistory || []};
    });
  });
}
function nz(v){ return (v === null || v === undefined || v === '') ? '--' : String(v); }
function fmtPct(v){
  return (v === null || v === undefined || v === '' || isNaN(v)) ? '--' : (Number(v) * 100).toFixed(1) + '%';
}
function avgOf(a){ if (!a.length) return null; let s = 0; a.forEach(function(v){ s += Number(v); }); return s / a.length; }
/* 灯色一律就地按比率判档（归档只存数值，不存黄/绿/红）：
     版本可用度 >=90% 绿 / >=80% 黄 / 否则红；构建成功率 100% 绿 / >=95% 黄 / 否则红
   老归档里还留着 vaLight/bsLight 字段，仅作字段缺失时的兜底。 */
function lightByRate(v, kind){
  if (v === null || v === undefined || v === '' || isNaN(v)) return null;
  const r = Number(v);
  if (kind === 'bs') return r >= 1 ? '绿' : (r >= 0.95 ? '黄' : '红');
  return r >= 0.9 ? '绿' : (r >= 0.8 ? '黄' : '红');
}
function worstLight(a, b){
  if (!a || a === '无数据') return b || a;
  if (!b || b === '无数据') return a;
  return (LIGHT_RANK[b] || 0) > (LIGHT_RANK[a] || 0) ? b : a;
}
function dotOf(l){ const m = {'绿': 'green', '黄': 'yellow', '红': 'red'}; return m[l] ? '<span class="dot ' + m[l] + '"></span>' : ''; }

/* 组件级版本可用度的 title：把「哪几条流水线、各是多少、加起来除以几条」摊开写，
   口径变了要能一眼核对 —— 组件级 = Σ各流水线版本可用度 ÷ 流水线条数。 */
function vaTitleOf(mineVA, vals, rate, wdN, from, to){
  const lines = ['版本可用度（组件级 = 各流水线版本可用度之和 ÷ 流水线条数）',
                 '统计区间 ' + from + ' ~ ' + to + ' ｜ 法定工作日 ' + wdN + ' 天'];
  if (!vals.length){
    lines.push(mineVA.length
      ? '该组件的流水线在本区间内都没有执行记录，可用度显示 --（不纳入统计）'
      : '该区间内没有带版本可用度维度的流水线，比值取自归档当日值');
    return lines.join('\n');
  }
  let sum = 0;
  vals.forEach(function(v){ sum += Number(v); });
  mineVA.forEach(function(p){
    const skipped = (p.vaRate === null || p.vaRate === undefined || isNaN(p.vaRate));
    lines.push('  ' + p.pipeline + (skipped
      ? '  区间内无执行记录 → --（不纳入统计）'
      : '  可用日 ' + p.vaA + ' / ' + wdN + ' → ' + fmtPct(p.vaRate)));
  });
  lines.push('合计 ' + fmtPct(sum) + ' ÷ ' + vals.length + ' 条流水线 = ' + fmtPct(rate)
    + (mineVA.length > vals.length
      ? '（另有 ' + (mineVA.length - vals.length) + ' 条区间内无执行记录，已排除）' : ''));
  lines.push('流水线级口径：当日存在任一条成功运行即算「当天有可用版本」，'
             + '分母是区间法定工作日数（不是有运行的天数）');
  return lines.join('\n');
}

/* 组件级构建成功率的 title：把「哪几条流水线、各自编译通过/次数、合计」摊开写。
   组件级 = Σ编译通过 ÷ Σ编译次数，且只累加**当前统计区间内逐日**的流水线级 bsDetail
   （与版本可用度同一套「逐日分子/分母」口径），所以单日筛选时不会混入别的日期的编译结果。 */
function bsTitleOf(mineBS, bsP, bsC, bsRate, from, to){
  const lines = ['构建成功率（组件级 = Σ编译通过 ÷ Σ编译次数）',
                 '统计区间 ' + from + ' ~ ' + to];
  if (!mineBS.length){
    lines.push('该组件在本区间内没有可比对的编译次数，比率显示 --');
    return lines.join('\n');
  }
  mineBS.forEach(function(p){
    const v = p.bsC > 0 ? p.bsP / p.bsC : null;
    lines.push('  ' + p.pipeline + '  编译通过 ' + p.bsP + ' / ' + p.bsC
      + ' = ' + (v === null ? '--' : fmtPct(v)));
  });
  lines.push('合计 ' + bsP + ' ÷ ' + bsC + ' = ' + fmtPct(bsRate));
  return lines.join('\n');
}
function failBox(msg){
  const box = document.getElementById('tb');
  if (box) box.innerHTML = '<tr><td colspan="6"><div class="err">' + msg + '</div></td></tr>';
}

/* 静态托管（GitHub Pages 等）上归档取不到，九成是 Jekyll 把 _ 开头的文件整批过滤了：
   归档索引正好叫 archive/_index.json、archive/<日>/_day.json（流水线目录里的 pipeline.json
   不以 _ 开头，不受影响；老归档里的 _manifest.json 仍会被过滤）。
   本地 http 服务上取不到才是「还没采集」。两种环境给两种提示，
   避免页面在线上让人去跑 run_pipeline（静态页本来就不该跑采集）。 */
function hostedSite(){
  const p = location.protocol, h = String(location.hostname || '');
  if (p !== 'http:' && p !== 'https:') return false;
  if (!h || h === 'localhost' || h === '127.0.0.1') return false;
  if (/^(10|192\.168)\./.test(h) || /^172\.(1[6-9]|2\d|3[01])\./.test(h)) return false;
  return true;
}
function emptyArchiveMsg(){
  if (!hostedSite()) {
    return '归档区暂无数据：请先执行 <span class="mono">python run_pipeline.py</span> 采集并归档。';
  }
  /* 线上还取不到，先别急着怪静态托管：把实际请求的地址打出来，
     一按 F12 就能看出是路径拼错还是托管层没发布这个文件。 */
  return '<b>归档索引没取到（HTTP 404）</b>'
    + '<div style="margin-top:8px">实际请求：<span class="mono">' + rfEsc(ARCH_ROOT + 'archive/_index.json') + '</span></div>'
    + '<div style="margin-top:8px">请按 F12 → Network 看这条请求的最终 URL 与状态码：</div>'
    + '<div style="margin-top:6px">· 若最终 URL 少了 <span class="mono">out/</span> 或多了一层目录 → 页面层级不对，'
    + '应该访问 <span class="mono">&lt;站点根&gt;/out/html/index.html</span>；</div>'
    + '<div style="margin-top:6px">· 若状态码就是 404 但这个文件仓库里确实有 → 是托管层没把它发布出去'
    + '（GitHub Pages 的 Jekyll 会跳过 <span class="mono">_</span> 开头的文件，'
    + '需要在仓库根加一份空的 <span class="mono">.nojekyll</span>）。</div>';
}

function boot(){
  /* 先用相对路径探测数据根，命中后再取组件清单：
       _index.json    → 归档日清单（决定日期控件上下界）
       _products.json → 全部开源组件清单（首页要「列出全部开源组件」，不能只列有待分析的） */
  const sub = document.getElementById('hsub');
  probeRoot().then(function(idx){
    IDX = idx;
    return jget(ARCH_ROOT + 'archive/_products.json').catch(function(){ return {products: []}; });
  }).then(function(prod){
    CATALOG = (prod && prod.products) || [];
    const days = (IDX.days || []).slice().sort(function(a, b){ return a.date < b.date ? -1 : 1; });
    if (!days.length){
      if (sub) sub.textContent = '归档区暂无数据';
      failBox(emptyArchiveMsg());
      return;
    }
    if (sub) sub.textContent = '归档 ' + days.length + ' 天（' + days[0].date + ' ~ '
      + days[days.length - 1].date + '）· 开源组件 ' + (CATALOG.length || '--') + ' 个';
    rfInit({
      min: days[0].date,
      max: days[days.length - 1].date,
      onChange: load
    });
  }).catch(function(e){
    /* 归档区为空时 _index.json 本来就不存在（HTTP 404 / ENOENT），这不叫「读取失败」，
       直接提示去采集；只有 file:// 直开被浏览器拦截（TypeError）才需要提示起本地服务 */
    if (isNotFound(e)){
      if (sub) sub.textContent = '归档区暂无数据';
      failBox(emptyArchiveMsg());
      return;
    }
    if (sub) sub.textContent = '读取归档索引失败';
    if (hostedSite()){
      /* 线上取索引被拦（403/5xx/跨域）——不是本地环境问题，别教人跑 python */
      failBox('<b>读取归档索引失败</b>'
        + '<div class="mono" style="margin-top:6px">' + rfEsc(String(e)) + '</div>'
        + '<div style="margin-top:8px">静态托管环境读不到 '
        + '<span class="mono">archive/_index.json</span>。请确认该文件已随仓库提交、'
        + '仓库根目录有 <span class="mono">.nojekyll</span>、Pages 已重新部署。</div>');
      return;
    }
    failBox('<b>读取归档索引失败</b>'
      + '<div class="mono" style="margin-top:6px">' + rfEsc(String(e)) + '</div>'
      + '<div style="margin-top:8px">直接双击打开（file://）时浏览器会拦截 fetch 读取本地 JSON。'
      + '请在 out 目录起本地服务后访问：<br><span class="mono">python run_pipeline.py --serve</span>'
      + '<br>或 <span class="mono">python -m http.server 8765 --directory out</span>'
      + '，再打开 <span class="mono">http://localhost:8765/html/index.html</span></div>');
  });
}

function load(from, to){
  const tb = document.getElementById('tb');
  /* 区间提示统一由公共筛选条右侧的 #rf-hint 负责（「当前区间 X ~ Y ｜ 工作日 N 天」），
     页面自身标题/副标题保持恒定，切页与改区间都不会让顶部内容跳动。 */
  const days = (IDX.days || []).filter(function(d){ return d.date >= from && d.date <= to; });
  if (!days.length){
    /* 区间内没有归档日（最常见的是「昨天」落在周末/节假日，那天本来就不跑数）：
       表格照常铺满全部开源组件，比率与待分析数一律显示 -- / 0，
       不再用一行提示把整张表替换掉 —— 「不是工作日」就该看到 --，而不是别的日子。 */
    render([], from, to);
    return;
  }
  tb.innerHTML = '<tr><td colspan="6" class="loading">正在读取 ' + days.length + ' 个归档日…</td></tr>';
  Promise.all(days.map(function(d){
    return jget(ARCH_ROOT + d.path + '/_day.json').then(function(x){ x.__path = d.path; return x; })
      .catch(function(e){ return {date: d.date, products: [], pipelines: [], __err: String(e), __path: d.path}; });
  })).then(function(docs){
    docs.sort(function(a, b){ return a.date < b.date ? -1 : 1; });
    render(docs, from, to);
  });
}

function render(docs, from, to){
  const prods = new Map();
  const pipes = new Map();
  const broken = docs.filter(function(d){ return d.__err; });

  /* 先铺全量组件清单：归档日只记录「当天下钻到的产品」，当天没有待分析流水线的产品
     不会出现在 _day.json 里；不全量铺底就会整行消失（用户要求：全部开源组件都列出，
     没有待分析流水线的显示 0）。 */
  CATALOG.forEach(function(p){
    prods.set(p.name, {name: p.name, projectId: p.projectId, days: {}, inCatalog: true});
  });

  docs.forEach(function(dd){
    (dd.products || []).forEach(function(p){
      let r = prods.get(p.product);
      if (!r){ r = {name: p.product, projectId: p.projectId, days: {}}; prods.set(p.product, r); }
      r.days[dd.date] = p;
    });
    (dd.pipelines || []).forEach(function(pl){
      let r = pipes.get(pl.key);
      if (!r){
        r = {key: pl.key, component: pl.component, pipeline: pl.pipeline, name: pl.pipelineName || pl.pipeline,
             platform: pl.platform || '', dims: {}, dates: [], path: pl.path,
             vaA: 0, vaN: 0, bsP: 0, bsC: 0, vaVals: [], bsVals: [],
             vaLightOld: null, bsLightOld: null};
        pipes.set(pl.key, r);
      }
      (pl.dims || []).forEach(function(d){ r.dims[d] = 1; });
      /* 区间重算：逐日累加分子/分母，区间一变就按新的 Σ分子/Σ分母 重算，
         不是把逐日比率做算术平均。老归档无 vaDetail/bsDetail 才退回逐日比率平均。 */
      const vd = pl.vaDetail, bd = pl.bsDetail;
      if (vd && Number(vd.daysInPeriod) > 0){
        r.vaA += Number(vd.availDays) || 0; r.vaN += Number(vd.daysInPeriod) || 0;
      } else if (pl.vaRate !== null && pl.vaRate !== undefined && ranInPeriod(pl)){
        r.vaVals.push(Number(pl.vaRate));
      }
      if (bd && Number(bd.buildCount) > 0){
        r.bsP += Number(bd.buildPassCount) || 0; r.bsC += Number(bd.buildCount) || 0;
      } else if (pl.bsRate !== null && pl.bsRate !== undefined && ranInPeriod(pl)){
        r.bsVals.push(Number(pl.bsRate));
      }
      r.vaLightOld = worstLight(r.vaLightOld, pl.vaLight || null);
      r.bsLightOld = worstLight(r.bsLightOld, pl.bsLight || null);
      if (r.dates.indexOf(dd.date) < 0) r.dates.push(dd.date);
      r.path = pl.path;
    });
  });

  const pipeList = Array.from(pipes.values());
  /* 版本可用度的分母 = **区间法定工作日数**（不是「这区间里有几天跑了数」）。
     wdInRange 数的是注入进来的法定工作日历（含节假日/调休补班），
     与后端 step_2 采集、step_7 归档用的分母同源：区间从 1 天拉到 5 天，分母就变 5。
     例：5 个工作日里只有 2 天出过可用版本 → 2/5 = 40%。 */
  const wdN = wdInRange(from, to);
  pipeList.forEach(function(p){
    /* 流水线级：分子 = 可用日（当日存在任一条 iva=true 的运行即算「当天有可用版本」），
       分母 = 区间工作日数；构建成功率仍是 Σ编译通过 / Σ编译次数。
       **区间内完全没有执行记录**的流水线（RAGSDK、VisionSDK 这类只有看板配置、一次都没跑过的）
       不参与任何计算：既不能算 0%（会被当成「全部不可用」并拉低组件均值），也不能算 100%，
       比率一律给 null → 页面显示 --，组件级平均与「流水线条数」都不含它。
       判据只看分子分母有没有落过数（vaN>0 / vaA>0 / 比率数组非空），且比率数组只收
       「区间内真的跑过」的流水线（ranInPeriod）：归档对零运行的流水线会退回看板值 0.0，
       那个 0 不是「跑了但不可用」，收进来就会把「无执行记录」显示成 0.00%。 */
    const noVA = !(p.vaN > 0 || p.vaVals.length);
    const noBS = !(p.bsC > 0 || p.bsVals.length);
    p.noRun = noVA && noBS;                 /* 两个维度都没有任何运行 = 该流水线无执行记录 */
    p.vaRate = noVA ? null : (wdN > 0 ? Math.min(1, p.vaA / wdN) : avgOf(p.vaVals));
    p.bsRate = noBS ? null : (p.bsC > 0 ? p.bsP / p.bsC : avgOf(p.bsVals));
    p.vaLight = lightByRate(p.vaRate, 'va') || (noVA ? null : p.vaLightOld);
    p.bsLight = lightByRate(p.bsRate, 'bs') || (noBS ? null : p.bsLightOld);
  });

  const rows = Array.from(prods.values()).map(function(r){
    const ds = Object.keys(r.days).sort();
    const dayDocs = ds.map(function(d){ return r.days[d]; });
    const mine = pipeList.filter(function(p){ return p.component === r.name; });
    /* 组件级版本可用度 = 该组件各流水线版本可用度的**算术平均**
       （Σ流水线可用度 ÷ 流水线条数），不是「Σ可用日 / Σ有运行日」。
       只统计带版本可用度维度的流水线：只做编译的流水线不该被算成 0%。 */
    const mineVA = mine.filter(function(p){ return p.dims.va; });
    const vaVals = mineVA.map(function(p){ return p.vaRate; })
                        .filter(function(v){ return v !== null && v !== undefined && !isNaN(v); });
    const vaRate = vaVals.length ? avgOf(vaVals) : null;
    /* 区间内一次都没跑过的流水线：在清单里照常列出（它不是不存在），但不计入上面那个平均 */
    const noRun = mine.filter(function(p){ return p.noRun; });
    /* 组件级构建成功率 = 该组件各流水线的 Σ编译通过 ÷ Σ编译次数（只累加**当前统计区间内的逐日**
       流水线级 bsDetail，与版本可用度同一套「逐日分子/分母」口径）。
       不能读产品级 buildSuccessDetail：那是**采集区间**的聚合 —— 例如 11-11 的归档里
       写的是 11-06~11-12 五天的合计数，单日筛选时会把别的日期的编译结果混进来
       （用户反馈：单日区间仍能看到其它日期的数据）。 */
    const mineBS = mine.filter(function(p){ return p.bsC > 0; });
    const bsP = mineBS.reduce(function(s, p){ return s + p.bsP; }, 0);
    const bsC = mineBS.reduce(function(s, p){ return s + p.bsC; }, 0);
    const bsRate = bsC > 0 ? bsP / bsC : null;
    return {
      name: r.name,
      nd: ds.length,
      days: ds,
      from: from, to: to, wdN: wdN,
      vaRate: vaRate,
      bsRate: bsRate,
      vaLight: lightByRate(vaRate, 'va') || ds.reduce(function(a, d){ return worstLight(a, r.days[d].vaLight); }, null),
      bsLight: lightByRate(bsRate, 'bs') || ds.reduce(function(a, d){ return worstLight(a, r.days[d].bsLight); }, null),
      vaTitle: vaTitleOf(mineVA, vaVals, vaRate, wdN, from, to),
      bsTitle: bsTitleOf(mineBS, bsP, bsC, bsRate, from, to),
      pipes: mine,
      pipeCount: mine.length,
      pipeNoRun: noRun.length,
      noRunNames: noRun.map(function(p){ return p.pipeline; }),
      badVA: mine.filter(function(p){ return p.dims.va && p.vaLight && p.vaLight !== '绿'; }).length,
      badBS: mine.filter(function(p){ return p.dims.bs && p.bsLight && p.bsLight !== '绿'; }).length
    };
  });
  rows.sort(function(a, b){ return ((b.badVA + b.badBS) - (a.badVA + a.badBS)) || (a.name < b.name ? -1 : 1); });
  ROWS = rows;                     /* 供「流水线数」弹窗按行号取该组件的流水线清单 */

  const tb = document.getElementById('tb');
  if (!rows.length && !pipeList.length){
    tb.innerHTML = '<tr><td colspan="6" class="empty">'
      + (docs.length ? '该区间内的归档日没有流水线进入待分析集合'
                     : '该区间内没有归档日（非工作日不跑数），指标显示 --')
      + '</td></tr>';
    paintNotes(docs, [], from, to);
    return;
  }
  const html = rows.map(function(r, i){ return prodRow(r, i, from, to); }).join('');
  tb.innerHTML = html + (broken.length
    ? '<tr><td colspan="6"><div class="err" style="margin:8px 0">'
      + broken.length + ' 个归档日的 _day.json 读取失败：'
      + broken.map(function(b){ return rfEsc(b.date); }).join('、') + '</div></td></tr>' : '');
  paintNotes(docs, rows, from, to);
  fitRows();
}

/* 首页只有这一张表，所以行高要跟着可视区走：整张表恰好铺满表格区（13 条数据刚好吃满），
   既不出现外层滚动条，也不在下面留一大片空白。
   做法：表格容器拿的是卡片内的剩余高度（.tbl-wrap 是 flex:1）→ 减掉表头后按行数均分，
   结果写进 --rowh（table.ov tbody tr 直接用它作行高）。
   行高有 30~70px 的下限/上限：条数多时保持紧凑、条数少时也不会被拉成一根细条。 */
function fitRows(){
  const wrap = document.querySelector('.tbl-wrap');
  const tbl = document.getElementById('tbl');
  if (!wrap || !tbl || !tbl.tBodies.length) return;
  const tb = tbl.tBodies[0];
  const n = tb.rows.length;
  if (!n || (n === 1 && tb.rows[0].cells.length === 1)){
    tbl.style.removeProperty('--rowh');      /* loading / 无数据 提示行不参与铺满 */
    return;
  }
  const th = tbl.tHead ? tbl.tHead.offsetHeight : 0;
  const avail = wrap.clientHeight - th - 2;  /* 减掉表格上下边框，避免差 1~2px 撑出滚动条 */
  if (avail <= 0) return;
  const h = Math.floor(avail / n);
  if (h < 34){                                /* 可视区太矮：回到自然行高，允许表格内滚动 */
    tbl.style.removeProperty('--rowh');
    return;
  }
  tbl.style.setProperty('--rowh', Math.min(h, 120) + 'px');
}
window.addEventListener('resize', function(){ if (IDX) fitRows(); });
window.addEventListener('load', function(){ if (IDX) fitRows(); });

/* 有数据时版本可用度/构建成功率单元格：百分比 + 灯点，title 里带逐日明细 */
function rateCell(light, title, rate){
  const t = title ? ' title="' + rfEsc(title) + '"' : '';
  if (!light || light === '无数据') return '<span class="rate-line"' + t + '><span class="pct">--</span></span>';
  return '<span class="rate-line"' + t + '><span class="pct">' + fmtPct(rate) + '</span>'
       + dotOf(light) + '</span>';
}

/* 待分析流水线数：0 就写 0；大于 0 才是可点数字（同旧版 .lnk），点进二级页看该组件的流水线清单 */
function numCell(n, comp, dim, q){
  if (!n) return '0';
  return '<a class="lnk" href="' + DETAIL_PAGE + '?comp=' + encodeURIComponent(comp)
    + '&dim=' + dim + q + '">' + n + '</a>';
}

/* 「流水线数」：蓝色可点数字（0 不可点），点开弹窗看该组件全部流水线的
   版本可用度与构建成功率（数据来自 render 已经算好的 r.pipes，不额外取数） */
function pipeCountCell(r, i){
  if (!r.pipeCount) return '0';
  return '<span class="lnk" data-pipes="' + i + '"'
    + ' title="点击查看该组件 ' + r.pipeCount + ' 条流水线的版本可用度与构建成功率'
    + (r.pipeNoRun ? '（其中 ' + r.pipeNoRun + ' 条区间内无执行记录，显示 -- 且不纳入统计：'
        + rfEsc(r.noRunNames.join('、')) + '）' : '') + '">'
    + r.pipeCount + '</span>';
}

/* 组件行：严格对齐旧版 6 列，不做任何展开（明细一律在二级页看） */
function prodRow(r, i, from, to){
  const q = '&from=' + encodeURIComponent(from) + '&to=' + encodeURIComponent(to);
  return '<tr>'
    + '<td class="c-name">' + rfEsc(r.name) + '</td>'
    + '<td class="c-rate">' + rateCell(r.vaLight, r.vaTitle, r.vaRate) + '</td>'
    + '<td class="c-rate">' + rateCell(r.bsLight, r.bsTitle, r.bsRate) + '</td>'
    + '<td class="c-num">' + pipeCountCell(r, i) + '</td>'
    + '<td class="c-num">' + numCell(r.badVA, r.name, 'va', q) + '</td>'
    + '<td class="c-num">' + numCell(r.badBS, r.name, 'bs', q) + '</td>'
    + '</tr>';
}

/* 表下统计口径 + 页脚：口径本体在 CALIBER_JS（按条展示，只在首页出现），
   这里只负责「确认它已在位」+ 画页脚，避免两处文案各写一遍后走岔 */
function paintNotes(docs, rows, from, to){
  let badVA = 0, badBS = 0, pipes = 0, comps = 0, red = 0;
  rows.forEach(function(r){
    badVA += r.badVA; badBS += r.badBS; pipes += r.pipeCount;
    if (r.pipeCount) comps += 1;
    if (r.vaLight === '红' || r.bsLight === '红') red += 1;
  });
  const note = document.getElementById('tnote');
  if (note && !note.innerHTML) note.innerHTML = caliberHTML();
  const foot = document.getElementById('foot');
  if (foot) foot.innerHTML =
    '生成时间 <span class="mono">' + rfEsc(nz(IDX && IDX.generatedAt)) + '</span> ｜ '
    + '统计区间 <span class="mono">' + rfEsc(from) + ' ~ ' + rfEsc(to) + '</span>（归档 '
    + docs.length + ' 天）｜ 开源组件 ' + rows.length + ' 个（有待分析流水线 ' + comps
    + ' 个，红灯 ' + red + '）｜ 待分析流水线 ' + pipes + ' 条（版本可用度 ' + badVA
    + ' · 构建成功率 ' + badBS + '）'
    /* 区间内一天归档都没有：说明白是「这天没跑数」，指标才显示 -- */
    + (docs.length ? '' : ' ｜ <b>该区间内无归档日</b>（非工作日不跑数，指标显示 --）');
}

/* ================= 「流水线数」弹窗：该组件全部流水线的版本可用度 / 构建成功率 =================
   数据不用现取：render() 已按当前统计区间把每条流水线重算好放进 rows[i].pipes，
   这里只管排版。骨架与二级页同一套（外框定高不滚，滚动条只出现在表格里）。 */
/* 弹窗是一个单例外框（#mrec），所以「二级弹窗」用栈实现：
   MODAL_UP 里压着被盖住的那一层（标题 + 正文），点「← 返回」原样贴回来。
   这样弹窗里再开弹窗不会出现两层遮罩，也不会把一级弹窗的内容弄丢。
   MODAL_SEQ 是异步回填的守卫：层级一变（返回/关闭）就把还没回来的运行历史结果丢掉，
   避免慢请求回来时把人已经切走的弹窗又盖掉。 */
let MODAL_UP = [];
let MODAL_SEQ = 0;
function paintModal(title, html){
  const m = document.getElementById('mrec');
  const t = document.getElementById('mttl');
  const b = document.getElementById('mbody');
  if (!m || !b) return;
  if (t) t.innerHTML = title || '';
  b.innerHTML = html || '';
  const bk = document.getElementById('mback');
  if (bk) bk.hidden = !MODAL_UP.length;
  m.classList.add('on');
}
function openModal(title, html){
  MODAL_UP = [];
  MODAL_SEQ += 1;
  paintModal(title, html);
}
function openModal2(title, html){
  const t = document.getElementById('mttl'), b = document.getElementById('mbody');
  MODAL_UP.push({title: t ? t.innerHTML : '', html: b ? b.innerHTML : ''});
  MODAL_SEQ += 1;
  paintModal(title, html);
}
function modalBack(){
  if (!MODAL_UP.length) return;
  const prev = MODAL_UP.pop();
  MODAL_SEQ += 1;
  paintModal(prev.title, prev.html);
}
function closeModal(){
  MODAL_UP = [];
  MODAL_SEQ += 1;
  const m = document.getElementById('mrec');
  if (m) m.classList.remove('on');
}
/* 弹窗内的一列比率：百分比（不按灯色上色）+ 灯点（没有该维度/无执行记录则 --）。
   居中由 td.ctr 负责，这里只出内容，和首页组件级的 .rate-line 完全一致。 */
function ctrRate(rate, light, title){
  const t = title ? ' title="' + rfEsc(title) + '"' : '';
  if (rate === null || rate === undefined || isNaN(rate)) return '<span class="dim">--</span>';
  const l = light || lightByRate(rate, 'va');
  return '<span class="rate-line"' + t + '><span class="pct">'
    + fmtPct(rate) + '</span>' + dotOf(l) + '</span>';
}
/* 一行 = 一条流水线：版本可用度（可用日/区间工作日）与构建成功率（编译通过/编译次数）。
   没有该维度（dims 里没有 va / bs）的显示 --：它们不参与该维度的比较，也不该被当成 0%。
   最后一列「执行记录」是入口：点「查看」在弹窗里再开一层，看这条流水线区间内的全部运行。 */
function pipesModal(i){
  const r = ROWS[i];
  if (!r) return;
  const list = (r.pipes || []).slice().sort(function(a, b){ return a.pipeline < b.pipeline ? -1 : 1; });
  if (!list.length){
    openModal('流水线｜' + rfEsc(r.name),
      '<div class="dim">该组件在当前统计区间内没有进入待分析集合的流水线。</div>');
    return;
  }
  const wdN = r.wdN || 0;
  /* 分母只数「真的能算出可用度」的流水线：区间内一次都没跑过的（无执行记录）显示 --，
     既不进这个平均、也不算条数，否则一条没跑过的流水线会把组件均值直接拉成 0% */
  const vaList = list.filter(function(p){ return p.dims.va && p.vaRate !== null && p.vaRate !== undefined; });
  const trs = list.map(function(p, k){
    const hasVA = !!p.dims.va, hasBS = !!p.dims.bs;
    const va = (hasVA && p.vaRate !== null && p.vaRate !== undefined) ? fmtPct(p.vaRate) : '--';
    const bs = (hasBS && p.bsRate !== null && p.bsRate !== undefined) ? fmtPct(p.bsRate) : '--';
    const vaT = !hasVA ? '该流水线在区间内没有版本可用度维度'
      : (p.noRun || p.vaRate === null || p.vaRate === undefined)
        ? '该流水线在区间内没有执行记录 → 显示 --，不纳入统计'
        : ('可用日 ' + p.vaA + ' / 区间工作日 ' + wdN + ' = ' + va);
    const bsT = hasBS
      ? ('编译通过 ' + p.bsP + ' / 编译次数 ' + p.bsC + ' = ' + bs)
      : '该流水线在区间内没有构建成功率维度';
    const execT = p.noRun
      ? '该流水线在区间内没有执行记录'
      : '查看该流水线在区间 ' + r.from + ' ~ ' + r.to + ' 内的全部执行记录';
    return '<tr>'
      + '<td class="cw">' + rfEsc(p.pipeline)
        + ((p.name && p.name !== p.pipeline)
            ? '<div class="dim" style="font-size:11px">' + rfEsc(p.name) + '</div>' : '')
        + (p.noRun ? '<div class="dim" style="font-size:11px">区间内无执行记录 · 不纳入统计</div>' : '')
        + '</td>'
      + '<td class="ctr">' + rfEsc(p.platform || '--') + '</td>'
      + '<td class="ctr">'
        + (hasVA ? ctrRate(p.vaRate, p.vaLight || lightByRate(p.vaRate, 'va'), vaT)
                 : '<span class="dim">--</span>') + '</td>'
      + '<td class="ctr">'
        + (hasBS ? ctrRate(p.bsRate, p.bsLight || lightByRate(p.bsRate, 'bs'), bsT)
                 : '<span class="dim">--</span>') + '</td>'
      + '<td class="ctr">'
        + (p.noRun ? '<span class="dim" title="' + rfEsc(execT) + '">--</span>'
                   : '<span class="lnk" data-exec="' + i + ':' + k + '" title="'
                     + rfEsc(execT) + '">查看</span>')
        + '</td>'
      + '</tr>';
  }).join('');
  openModal('流水线（' + list.length + ' 条）｜' + rfEsc(r.name),
    '<div class="mtbl"><table class="rca"><colgroup><col style="width:38%"><col style="width:14%">'
    + '<col style="width:15%"><col style="width:15%"><col style="width:18%"></colgroup>'
    + '<thead><tr><th>流水线</th><th>平台</th><th>版本可用度</th><th>构建成功率</th>'
    + '<th>执行记录</th></tr></thead>'
    + '<tbody>' + trs + '</tbody></table></div>'
    + '<div class="mrec-note">区间 ' + rfEsc(r.from) + ' ~ ' + rfEsc(r.to)
    + ' · 法定工作日 ' + wdN + ' 天 ｜ 版本可用度 = 可用日 ÷ 区间工作日数'
    + '（本组件 ' + fmtPct(r.vaRate) + ' = 各流水线之和 ÷ ' + vaList.length + ' 条可统计流水线'
    + (list.length > vaList.length ? '，另有 ' + (list.length - vaList.length) + ' 条无执行记录已排除' : '')
    + '）'
    + ' ｜ 构建成功率 = Σ编译通过 ÷ Σ编译次数（本组件 ' + fmtPct(r.bsRate) + '）'
    + ' ｜ 该流水线没有的维度显示 -- ｜ 点「查看」看该流水线区间内的全部执行记录。</div>');
}

/* ===== 二级弹窗：一条流水线在统计区间内的全部执行记录（原二级页区块头的入口搬到这里） =====
   数据源与原「流水线执行记录」完全一致：归档每天的 pipeline.json 里带着一份整区间 runHistory，
   逐日读、按构建号去重即可；区间内每一次运行逐条平铺（不按天汇总），按结束时间倒序。 */
/* 运行状态色标：成功（COMPLETED/SUCCESS/SUCCEEDED）绿、失败红、其它灰 */
function statusTag(s){
  const v = String(s || '').toUpperCase();
  if (v === 'FAILED' || v === 'FAILURE') return '<span class="tag red">' + rfEsc(s) + '</span>';
  if (v === 'SUCCESS' || v === 'SUCCEEDED' || v === 'COMPLETED') return '<span class="tag green">' + rfEsc(s) + '</span>';
  return '<span class="tag">' + rfEsc(s || '--') + '</span>';
}
/* 执行记录表：8 列（编号/状态/失败类型/版本可用/编译/用例/起止时间），构建号可直接跳 openLiBing */
function execTable(runs, r){
  const from = r.from, to = r.to;
  if (!runs.length){
    return '<div class="dim">该流水线在区间 ' + rfEsc(from) + ' ~ ' + rfEsc(to)
      + ' 内没有读到运行历史（归档缺少 runHistory）。</div>';
  }
  runs.sort(function(a, b){ return String(b.end || '').localeCompare(String(a.end || '')); });
  const okDay = {}, bsDay = {};
  runs.forEach(function(x){
    if (!x.day) return;
    if (x.iva === true) okDay[x.day] = 1;
    if (x.bc !== null && x.bc !== undefined && x.bc !== ''
        && (Number(x.bpc) || 0) >= Number(x.bc)) bsDay[x.day] = 1;
  });
  const rows = runs.map(function(x){
    const bn = x.url
      ? '<a href="' + rfEsc(x.url) + '" target="_blank" rel="noopener" title="在 openLiBing 查看构建 #'
        + rfEsc(nz(x.rn)) + '">#' + rfEsc(nz(x.rn)) + '</a>'
      : '<span class="mono">#' + rfEsc(nz(x.rn)) + '</span>';
    const va = (x.iva === true) ? '可用'
      : ((x.iva === false) ? '<span class="dim">不可用</span>' : '<span class="dim">--</span>');
    const bs = (x.bc === null || x.bc === undefined || x.bc === '')
      ? '<span class="dim">--</span>' : (Number(x.bpc) || 0) + '/' + Number(x.bc);
    const cpr = (x.cpr === null || x.cpr === undefined || x.cpr === '')
      ? '<span class="dim">--</span>' : Number(x.cpr).toFixed(1) + '%';
    /* 失败类型 = 服务端 failedTaskType（如「用例失败」「编译失败」）；执行成功时为 null */
    const ftt = (x.ftt === null || x.ftt === undefined || x.ftt === '' || x.ftt === '流水线未失败')
      ? '<span class="dim">--</span>' : rfEsc(String(x.ftt));
    return '<tr>'
      + '<td class="nowrap">' + bn + '</td>'
      + '<td class="nowrap">' + statusTag(x.status) + '</td>'
      + '<td class="nowrap dim">' + ftt + '</td>'
      + '<td class="nowrap">' + va + '</td>'
      + '<td class="nowrap">' + bs + '</td>'
      + '<td class="nowrap dim">' + cpr + '</td>'
      + '<td class="nowrap dim">' + rfEsc(String(x.start || '') || '--') + '</td>'
      + '<td class="nowrap dim">' + rfEsc(String(x.end || '') || '--') + '</td>'
      + '</tr>';
  }).join('');
  const wdN = r.wdN || 0;
  return '<div class="mtbl"><table class="rca"><colgroup><col style="width:8%"><col style="width:9%">'
    + '<col style="width:12%"><col style="width:8%"><col style="width:11%">'
    + '<col style="width:9%"><col style="width:21.5%"><col style="width:21.5%"></colgroup>'
    + '<thead><tr><th>流水线编号</th><th>状态</th><th>失败类型</th><th>版本可用</th>'
    + '<th>编译成功/次数</th><th>用例通过率</th><th>开始时间</th><th>结束时间</th></tr></thead>'
    + '<tbody>' + rows + '</tbody></table></div>'
    + '<div class="mrec-note">区间 ' + rfEsc(from) + ' ~ ' + rfEsc(to)
    + ' · 区间内每一次运行逐条平铺（不按天汇总），按结束时间倒序 · 可用日 '
    + Object.keys(okDay).length + '/' + wdN + ' 个工作日 · 编译全通过 '
    + Object.keys(bsDay).length + ' 天 · 运行来自归档 pipeline.json 的 runHistory'
    + '（按执行结束时间归属日期）· 执行成功也逐条列出 · 点构建号直接在 openLiBing 打开该次执行。</div>';
}
/* 点「查看」：按流水线 key 逐日找到归档目录，再按需读 pipeline.json 取运行历史
   （首页首屏只算比率、不带运行明细，所以这里现取；多个归档日各带同一份整区间历史，按 rn 去重） */
function openExecOf(i, k){
  const r = ROWS[i];
  const p = (r && r.pipes) ? r.pipes[k] : null;
  if (!r || !p) return;
  const label = p.pipeline || p.key || '流水线';
  const from = r.from, to = r.to;
  const days = ((IDX && IDX.days) || []).filter(function(d){ return d.date >= from && d.date <= to; });
  if (!days.length){
    openModal2('执行记录｜' + rfEsc(label),
      '<div class="dim">该区间内没有归档日（' + rfEsc(from) + ' ~ ' + rfEsc(to) + '）。</div>');
    return;
  }
  openModal2('执行记录｜' + rfEsc(label), '<div class="loading">正在读取运行历史…</div>');
  const seq = MODAL_SEQ;
  const runs = [], seen = {};
  let chain = Promise.resolve();
  days.forEach(function(d){
    chain = chain.then(function(){
      return jget(ARCH_ROOT + d.path + '/_day.json').then(function(day){
        let pl = null;
        (day.pipelines || []).forEach(function(x){ if (x.key === p.key) pl = x; });
        if (!pl || !pl.path) return;
        return jpipe(pl.path).then(function(pp){
          (pp.runs || []).forEach(function(h){
            const rn = String(h.rn);
            if (!rn || rn === 'undefined' || seen[rn]) return;
            seen[rn] = 1;
            const end = String(h.end || '');
            const dy = end.slice(0, 10);
            /* 归档里带的是整区间历史，可能越过当前统计区间：先按区间筛一遍 */
            if (dy && (dy < from || dy > to)) return;
            runs.push({rn: h.rn, start: h.start, end: end, day: dy, status: h.status,
                       url: h.url, iva: h.iva, bc: h.bc, bpc: h.bpc, cpr: h.cpr, ftt: h.ftt});
          });
        }).catch(function(){ /* 老归档没有 runHistory：下面统一提示 */ });
      }).catch(function(){ /* 单日读取失败跳过，不影响其它日 */ });
    });
  });
  chain.then(function(){
    if (seq !== MODAL_SEQ) return;   /* 已经返回上一级或关掉弹窗：丢弃过期结果 */
    paintModal('执行记录（' + runs.length + ' 次运行）｜' + rfEsc(label), execTable(runs, r));
  });
}

/* 首页表格的点按入口：「流水线数」数字（可点）→ 流水线弹窗 → 「查看」→ 执行记录二级弹窗；
   弹窗关闭（关闭按钮 / 点遮罩 / Esc），二级弹窗按「← 返回」或 Esc 先回上一层 */
document.addEventListener('click', function(ev){
  const t = ev.target;
  if (t && t.closest){
    const ex = t.closest('[data-exec]');
    if (ex){
      ev.preventDefault();
      const a = String(ex.getAttribute('data-exec') || '').split(':');
      openExecOf(Number(a[0]), Number(a[1]));
      return;
    }
    const el = t.closest('[data-pipes]');
    if (el){
      ev.preventDefault();
      pipesModal(Number(el.getAttribute('data-pipes')));
      return;
    }
  }
  if (t && t.id === 'mback'){ modalBack(); return; }
  if (t && (t.id === 'mrec' || t.id === 'mclose')) closeModal();   /* 遮罩/关闭按钮都关，点表格内容不关 */
});
document.addEventListener('keydown', function(ev){
  if (ev.key !== 'Escape') return;
  if (MODAL_UP.length) modalBack(); else closeModal();   /* Esc 先退出二级弹窗，再关整层 */
});

/* 说明：首页表格不做任何展开/下钻；「流水线数」点开看该组件全部流水线的两个比率与执行记录，
   「待分析流水线数」是可点数字，点进二级页看该组件的执行记录根因明细（无中间层） */

boot();

