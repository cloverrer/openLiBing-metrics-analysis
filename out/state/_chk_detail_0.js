
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


/* ================= 二级页：同口径区间 → 该流水线每天的归档目录 → 逐条执行记录 ================= */
/* 数据根：同首页，一律相对「当前文档」逐级探测 archive/_index.json，不写死域名和站点根 */
let BACK_TO = '../';
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
      BACK_TO = cand;            /* 命中后固定，后面所有归档请求都拼这个前缀 */
      return x;
    }).catch(function(e){
      if (isNotFound(e)) return step();
      throw e;
    });
  }
  return step();
}
const CATS = {
  compile_failure: ['编译失败', 'red'],
  test_failure:    ['用例失败', 'red'],
  env_not_ready:   ['用例未拉起', 'yellow'],
  job_failure:     ['任务失败', 'yellow'],
  cancelled:       ['运行被取消', ''],
  evidence_missing:['证据缺失', 'blue'],
  /* 归档里 verdict.category=success 的记录 = 任务执行成功、但用例没跑满 100%：
     不写英文 success（对看页面的人没信息量），直接说清是哪一类问题 */
  success:         ['用例未 100%', 'yellow'],
  unknown:         ['证据不足待确认', '']
};
const QS = new URLSearchParams(location.search);
/* 二级页只有一层：组件级根因明细（?comp=组件&dim=va|bs）。
   从首页「待分析流水线数」点进来就是这个页面 —— 中间那层「组件级流水线清单」已下线，
   组件下所有待分析流水线的失败执行记录合成一张表，靠「流水线」列区分是哪一条。
   老链接带 ?key=组件|流水线 的，取出组件名照旧渲染（不会 404 给一张空表）。 */
const COMP = QS.get('comp') || (QS.get('key') ? String(QS.get('key')).split('|')[0] : '');
const DIM = QS.get('dim') || '';        /* 维度过滤：va / bs；不带就是该组件的全部维度 */
const DIMNAME = {va: '版本可用度', bs: '构建成功率'};
const INDEX_PAGE = 'index.html';          /* 首页文件名（构建时注入） */
let DAYS = [];

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
/* ===== 一条流水线归档的统一读法 =====
   归档已从「9 份 JSON + records/run_*.json」合并成一份 pipeline.json（schema=pipeline/1）：
   运行历史在 steps.step_2_runs.runHistory、证据缺失清单在 evidence.missing、
   执行记录就是顶层 records[]（每条只少一层重复的 _doc 题头）。一次 fetch 全拿到。
   碰到还没合并的老归档（pipeline.json 不存在）自动退回「三份分开读」，页面不用分支。 */
function jpipe(dirPath){
  const base = BACK_TO + dirPath + '/';
  return jget(base + 'pipeline.json').then(function(doc){
    doc = doc || {};
    return {base: base, dir: dirPath, merged: true,
            runs: (((doc.steps || {}).step_2_runs || {}).runHistory) || [],
            missing: (((doc.evidence || {}).missing) || []),
            records: doc.records || []};
  }).catch(function(e){
    if (!isNotFound(e)) throw e;
    return Promise.all([
      jget(base + 'step_2_runs.json').catch(function(){ return {}; }),
      jget(base + '_manifest.json').catch(function(){ return {}; })
    ]).then(function(r){
      const s2 = r[0] || {}, mf = r[1] || {};
      return {base: base, dir: dirPath, merged: false,
              runs: s2.runHistory || [],
              missing: (((mf.evidence || {}).missing) || []),
              records: mf.records || []};
    });
  });
}
function nz(v){ return (v === null || v === undefined || v === '') ? '--' : String(v); }
function dotOf(l){ const m = {'绿': 'green', '黄': 'yellow', '红': 'red'}; return m[l] ? '<span class="dot ' + m[l] + '"></span>' : ''; }
/* 灯色不落库：归档只存数值，这里按比率就地判档（老归档的 vaLight/bsLight 只作兜底）。
   版本可用度 >=90% 绿 / >=80% 黄 / 否则红；构建成功率 100% 绿 / >=95% 黄 / 否则红 */
function lightByRate(v, kind){
  if (v === null || v === undefined || v === '' || isNaN(v)) return null;
  const r = Number(v);
  if (kind === 'bs') return r >= 1 ? '绿' : (r >= 0.95 ? '黄' : '红');
  return r >= 0.9 ? '绿' : (r >= 0.8 ? '黄' : '红');
}

/* ===== 一跳直达 + 原路返回 =====
   首页（组件级概览）→ 本页（组件级根因明细 ?comp=&dim=），中间那层「组件级流水线清单」已下线。
   链接显式带上 comp / dim / from / to：返回总览时维度与统计区间都保持不变（不用重新选日期）。 */
function rangeQS(from, to){
  return (from && to) ? 'from=' + encodeURIComponent(from) + '&to=' + encodeURIComponent(to) : '';
}
function levelQS(extra, from, to){
  const parts = [];
  Object.keys(extra || {}).forEach(function(k){
    if (extra[k] !== null && extra[k] !== undefined && extra[k] !== '') parts.push(k + '=' + encodeURIComponent(extra[k]));
  });
  const r = rangeQS(from, to);
  if (r) parts.push(r);
  return parts.length ? '?' + parts.join('&') : '';
}
function indexHref(from, to){
  return INDEX_PAGE + levelQS({}, from, to);
}
/* 只有一层：返回按钮永远回总览（区间不变），不再有「返回上一层清单」 */
function setBack(from, to){
  const el = document.getElementById('back');
  if (!el) return;
  el.href = indexHref(from, to);
  el.textContent = '← 返回总览';
  el.title = '返回首页组件级概览（统计区间不变）';
}
/* 面包屑：总览 › 组件（维度） */
function crumbHead(from, to){
  return '<a href="' + indexHref(from, to) + '">总览</a><span class="sep">›</span>';
}
function statusTag(s){
  const v = String(s || '').toUpperCase();
  if (v === 'FAILED' || v === 'FAILURE') return '<span class="tag red">' + rfEsc(s) + '</span>';
  /* openLiBing 的流水线状态用 COMPLETED 表示成功（SUCCESS/SUCCEEDED 是别的接口的叫法），
     三种都按绿色显示，和 FAILED（红）、CANCELED（灰）区分开 */
  if (v === 'SUCCESS' || v === 'SUCCEEDED' || v === 'COMPLETED') return '<span class="tag green">' + rfEsc(s) + '</span>';
  return '<span class="tag">' + rfEsc(s || '--') + '</span>';
}
function failBox(msg){
  const box = document.getElementById('recs');
  if (box) box.innerHTML = '<div class="err">' + msg + '</div>';
}

function boot(){
  if (!COMP){
    failBox('缺少参数。请从首页表格点击「待分析流水线数」进入该组件的根因明细。');
    return;
  }
  /* 先把返回按钮按层级摆好（数据回来之前也不要显示错层级） */
  setBack(QS.get('from') || '', QS.get('to') || '');
  probeRoot().then(function(idx){
    DAYS = (idx.days || []).slice().sort(function(a, b){ return a.date < b.date ? -1 : 1; });
    if (!DAYS.length){
      failBox(emptyArchiveMsg());
      return;
    }
    rfInit({min: DAYS[0].date, max: DAYS[DAYS.length - 1].date, onChange: load});
  }).catch(function(e){
    /* 归档区为空时 _index.json 本来就不存在（HTTP 404 / ENOENT）→ 提示去采集；
       file:// 直开被浏览器拦截（TypeError）才提示起本地服务 */
    if (isNotFound(e)){
      failBox(emptyArchiveMsg());
      return;
    }
    if (hostedSite()){
      failBox('<b>读取归档索引失败</b><div class="mono" style="margin-top:6px">' + rfEsc(String(e)) + '</div>'
        + '<div style="margin-top:8px">静态托管环境读不到 <span class="mono">archive/_index.json</span>，'
        + '请确认文件已提交、仓库根目录有 <span class="mono">.nojekyll</span>、Pages 已重新部署。</div>');
      return;
    }
    failBox('<b>读取归档索引失败</b><div class="mono" style="margin-top:6px">' + rfEsc(String(e)) + '</div>'
      + '<div style="margin-top:8px">file:// 直开会被浏览器拦截 fetch，请用 '
      + '<span class="mono">python run_pipeline.py --serve</span> 起本地服务后访问。</div>');
  });
}

function load(from, to){
  setBack(from, to);                     /* 返回按钮跟着当前区间走 */
  const box = document.getElementById('recs');
  box.innerHTML = '<div class="loading">正在读取归档记录…</div>';
  document.getElementById('ttl').textContent = COMP;
  const days = DAYS.filter(function(d){ return d.date >= from && d.date <= to; });
  if (!days.length){
    /* 这天没有归档（非工作日不跑数）：照样出区块头，比率 / 达标工作日一律 --，
       不把「昨天」悄悄换成别的日子，也不留一张空表让人以为数据丢了 */
    RUNS = [];
    CTX = {dirs: [], days: days, from: from, to: to, runs: []};
    renderHead(null, [], CTX);
    renderRecs([], CTX);
    return;
  }
  /* 1) 逐日找该组件下所有流水线的归档目录（同一条流水线在区间内可能每天一个目录，
        一个组件下也可能有多条流水线 —— 全部收进来，靠「流水线」列区分） */
  const dirs = [];
  let meta = null;
  let chain = Promise.resolve();
  days.forEach(function(d){
    chain = chain.then(function(){
      return jget(BACK_TO + d.path + '/_day.json').then(function(day){
        (day.pipelines || []).forEach(function(pl){
          if (pl.component !== COMP) return;
          if (DIM && (pl.dims || []).indexOf(DIM) < 0) return;
          dirs.push({date: d.date, path: pl.path, pl: pl});
          if (!meta) meta = {pl: pl, day: day, comp: COMP};
        });
      }).catch(function(){ /* 该日读取失败则跳过，不影响其它日 */ });
    });
  });
  chain.then(function(){
    if (!dirs.length){
      box.innerHTML = '<div class="empty">该区间内没有该组件'
        + (DIM ? '（' + rfEsc(DIMNAME[DIM]) + ' 维度）' : '') + '的归档记录（'
        + rfEsc(from) + ' ~ ' + rfEsc(to) + '）'
        + '<div class="dim" style="margin-top:6px">流水线只在被点灯的日期才会进入待分析集合。</div></div>';
      RUNS = [];
      CTX = {dirs: [], days: days, from: from, to: to, runs: []};
      renderHead(null, [], CTX);
      return;
    }
    /* 2) 逐目录读一次 pipeline.json（jpipe）：运行历史 + 证据缺失清单 + 执行记录一起到手。
          还没合并的老归档由 jpipe 自动退回「step_2_runs.json + _manifest.json」分开读，
          这里只看 pp.merged 决定记录是「已经在手里」还是「还要按 file 再 fetch 一条」。 */
    const recs = [];
    const runs = [];
    const runSeen = {};
    let chain2 = Promise.resolve();
    dirs.forEach(function(d){
      chain2 = chain2.then(function(){
        return jpipe(d.path).then(function(pp){
          /* 这条归档目录属于哪条流水线：组件级明细里多条流水线的运行 / 记录混在一张表，
             「流水线」列靠这个字段区分（归档目录 → _day.json 的 pipelines[]） */
          const plName = (d.pl || {}).pipelineName || (d.pl || {}).pipeline || '';
          /* 2a) 运行历史：同一条流水线的每个归档日都带着同一份「整区间」runHistory，
                按「流水线 + 构建号」去重（不同流水线的构建号可能重号，不能只按 rn 去重）。
                每条运行都打上 __pl，后面补「任务成功但用例未 100%」的行时要知道它属于哪条流水线。
                **归档里那份 runHistory 覆盖整个采集区间**（例如 11-06 的归档里带着 11-06~11-12
                的全部运行）：这里必须先按当前统计区间按「执行结束时间」筛一遍，否则单日筛选时
                会把别的日期的运行补成根因表的行 —— 看起来就像「选了 11-10 却冒出别的日期的数据」。 */
          (pp.runs || []).forEach(function(h){
            const rn = String(h.rn);
            const key = plName + '|' + rn;
            if (!rn || rn === 'undefined' || runSeen[key]) return;
            runSeen[key] = 1;
            const end = String(h.end || '');
            const day = end.slice(0, 10);
            if (day && (day < from || day > to)) return;
            runs.push({rn: h.rn, start: h.start, end: end, day: day,
                       status: h.status, url: h.url, iva: h.iva,
                       bc: h.bc, bpc: h.bpc, cpr: h.cpr, ftt: h.ftt, __pl: plName});
          });
          /* 2b) 执行记录：合并后的归档里记录已经是完整的，老归档按清单里的 file 再逐条 fetch */
          const missing = new Set(pp.missing || []);
          let chain3 = Promise.resolve();
          (pp.records || []).forEach(function(r){
            /* 执行成功的运行不进根因表：它只是「流水线执行记录」里的一天历史运行，
               要看就点「流水线执行记录」；归档里仍保留这条轻量记录，这里只是不取、不渲染。
               分类字段老归档在记录顶层（轻量清单的 category），合并后的归档只在 verdict.category 里，
               两处都认，否则判不出来→成功记录会以「错误信息 -- / 定性 --」的空行混进表里。
               唯一例外：这次运行确实跑出了失败用例（用例通过率 ≠ 100%）——「执行成功但用例没全过」
               值得单独一行，但不给展开（它没有根因可讲，问题就在用例本身）。 */
            const vcat = String(((r.verdict || {}).category || r.category || ''));
            if (vcat === 'success'){
              const ncf = (r.cases || []).filter(function(c){ return c && c.name; }).length;
              if (!ncf) return;
              r.__okRow = 1;
            }
            if (pp.merged){
              r.__base = pp.base;
              r.__dir = d.path;
              r.__missing = missing;
              r.__pl = plName;
              recs.push(r);
              return;
            }
            chain3 = chain3.then(function(){
              return jget(pp.base + r.file).then(function(rec){
                rec.__base = pp.base;
                rec.__dir = d.path;
                rec.__missing = missing;
                rec.__pl = plName;
                recs.push(rec);
              }).catch(function(e){
                recs.push({__err: String(e), __base: pp.base, __dir: d.path, __missing: missing,
                           __pl: plName,
                           recordId: r.recordId, buildNumber: r.buildNumber, endedAt: r.endedAt,
                           category: r.category, tasks: [], cases: [], errorMessages: [], evidence: {files: [], missing: []}});
              });
            });
          });
          return chain3;
        });
      }).catch(function(){ /* 该日这条流水线读不到：跳过，不影响其它日 / 其它流水线 */ });
    });
    chain2.then(function(){
      /* 2c) 「任务执行成功、但用例通过率不是 100%」的运行补一行：
            它们在 runs 里（带 status / cpr），但不在 records 里（records 只收 FAILED / CANCELED），
            所以默认压根不会出现在根因表里。用户口径：这类只需要**标记任务成功 + 给出用例比例**，
            不做 AI 根因、不抓失败用例清单 —— 因此就地合成一条轻量记录。
            去重键是「流水线 + 构建号」：同一组件下不同流水线的构建号可能重号，
            同一次构建如果记录里已经有了（哪怕是失败记录）也不再补。 */
      const taken = {};
      recs.forEach(function(r){ taken[(r.__pl || '') + '|' + nz(r.buildNumber)] = 1; });
      runs.forEach(function(x){
        if (!isOkRun(x)) return;
        const cpr = cprOf(x);
        if (cpr == null || cpr >= 100) return;   /* 100% 通过的正常成功运行不进表 */
        const k = (x.__pl || '') + '|' + nz(x.rn);
        if (taken[k]) return;
        taken[k] = 1;
        recs.push(okRowOf(x));
      });
      /* 行序：**按结束时间降序**（最近结束的那次构建排最上面，和「从最新往回看」的排查习惯一致）。
         时间一律解析成毫秒再比，不做字符串比较——归档里的时间串有带毫秒/时区的、也有缺字段的，
         字符串比大小会错位。结束时间缺失的用开始时间兜底，两者都没有的排到最后；
         时间完全相同时按构建号降序，保证每次刷新顺序稳定。 */
      recs.sort(function(a, b){ return cmpByEndDesc(a, b); });
      runs.sort(function(a, b){ return String(a.end || '') < String(b.end || '') ? 1 : -1; });
      RUNS = runs;
      CTX = {dirs: dirs, days: days, from: from, to: to, runs: runs};
      renderHead(meta, recs, CTX);
      renderRecs(recs, CTX);
    });
  });
}

/* ---------- 组件级页面的维度口径 ----------
   这一页是**从哪个维度点进来的，就只讲哪个维度**：dim=va 只讲版本可用度，dim=bs 只讲构建成功率。
   比率、工作日达标数都按同一个维度取；另一个维度在这一页上完全不出现。 */
function dimOf(){
  if (DIM === 'bs') return 'bs';
  if (DIM === 'va') return 'va';
  /* 没带 dim（直接开链接）时：区间内该组件所有流水线都没有 va 维度才退 bs，否则按 va */
  let hasVa = false, hasBs = false;
  ((CTX || {}).dirs || []).forEach(function(d){
    const ds = (d.pl || {}).dims || [];
    if (ds.indexOf('va') >= 0) hasVa = true;
    if (ds.indexOf('bs') >= 0) hasBs = true;
  });
  return (hasBs && !hasVa) ? 'bs' : 'va';
}

/* 该流水线在区间内的逐日灯态：用于区块头的「可用 N/M 工作日」（按当前维度取灯）
   灯态由当天比率就地判档，归档里不再存灯色 */
function dayLights(ctx){
  const dim = DIM || '';
  const out = [];
  (ctx.dirs || []).forEach(function(d){
    const pl = d.pl || {};
    const ds = pl.dims || [];
    /* 区间内一次都没跑过的流水线（runsInPeriod = 0）：归档里那个 0.0 是「压根没跑」，
       不是「跑了但不可用」，拿它算灯会得到红灯 → 区块头显示 0.00%。
       这里直接不给灯（等同于没有数据），比率就会落到 --。 */
    if (!ranInPeriod(pl)){ out.push({date: d.date, light: null}); return; }
    const useBs = dim ? dim === 'bs' : (ds.indexOf('bs') >= 0 && ds.indexOf('va') < 0);
    const light = useBs
      ? (lightByRate(pl.bsRate, 'bs') || pl.bsLight)
      : (lightByRate(pl.vaRate, 'va') || pl.vaLight);
    out.push({date: d.date, light: light || null});
  });
  return out;
}
/* 区间重算：只统计「执行结束时间落在当前统计区间内」的运行，逐日判定是否达标。
   dim=va：比率 = 达标日 / **区间法定工作日数**（用户口径：当日任一条运行 iva=true 即算当天可用；
           5 个工作日只有 2 天可用 = 2/5 = 40%，分母不含「这天有没有跑数」）
   dim=bs：比率 = Σ编译通过 / Σ编译次数（该维度口径未改）
   区间一变，分子分母同时按新区间重算，不再沿用归档当日写死的比率。 */
function rangeStats(ctx, dim){
  ctx = ctx || {};
  const from = ctx.from || '', to = ctx.to || '';
  /* 该流水线在区间内到底跑没跑过（runsInPeriod 逐日为准）：没跑过就一律 --、
     不参与任何比率，避免把归档退回的看板 0.0 显示成「0.00%」 */
  const ran = (ctx.dirs || []).some(function(d){ return ranInPeriod(d.pl); });
  const inRange = (ctx.runs || []).filter(function(r){
    return r.day && r.day >= from && r.day <= to;
  });
  if (inRange.length){
    const byDay = {}, dayRuns = {};
    inRange.forEach(function(r){
      const d = byDay[r.day] || (byDay[r.day] = {runs: 0, ok: false, bc: 0, bpc: 0});
      d.runs += 1;
      if (r.iva === true) d.ok = true;
      if (r.bc !== null && r.bc !== undefined && r.bc !== ''){
        d.bc += Number(r.bc) || 0;
        d.bpc += Number(r.bpc) || 0;
      }
      (dayRuns[r.day] || (dayRuns[r.day] = [])).push(r);
    });
    const dayList = Object.keys(byDay).sort();
    let okDays = 0, bc = 0, bpc = 0;
    const dayOk = {};
    dayList.forEach(function(k){
      const d = byDay[k];
      const ok = (dim === 'bs') ? (d.bc > 0 && d.bpc >= d.bc) : !!d.ok;
      dayOk[k] = ok;
      if (ok) okDays += 1;
      bc += d.bc; bpc += d.bpc;
    });
    Object.keys(dayRuns).forEach(function(k){
      dayRuns[k].sort(function(a, b){ return String(a.end || '') < String(b.end || '') ? 1 : -1; });
    });
    /* dim=va 的分母是区间工作日数（与首页、与采集口径同一个数）；
       只有日历拿不到（wdInRange 返回 0）时才退回「有运行的天数」，保证不会出现 0/0 */
    const wdN = wdInRange(from, to);
    let total = (dim === 'bs') ? dayList.length : (wdN > 0 ? wdN : dayList.length);
    let availDays = okDays;
    let rate = (dim === 'bs') ? (bc > 0 ? bpc / bc : null)
                              : (total ? Math.min(1, okDays / total) : null);
    /* 组件级版本可用度（用户口径）= 该组件各流水线版本可用度的**算术平均**
       （Σ流水线可用度 ÷ 流水线条数），与首页组件行同一个算法、同一套逐日重算。
       每条流水线的分母都是同一个「区间法定工作日数」，所以算术平均等价于
       Σ各流水线可用日 ÷ Σ各流水线工作日 —— 这里直接用分子分母求和算，避免精度损失，
       二级页区块头的数字就能和首页点进来的数字一眼对上。
       只统计带版本可用度维度的流水线（只做编译的流水线不该被算成 0%）；
       被取消的运行不计入（用户口径：aborted 与进行中都不算）。 */
    let pipeCount = 0;
    if (dim !== 'bs'){
      const dimsOf = {};
      (ctx.dirs || []).forEach(function(d){
        const pl = d.pl || {};
        const n = pl.pipelineName || pl.pipeline || '';
        if (!n) return;
        const ds = dimsOf[n] || (dimsOf[n] = []);
        (pl.dims || []).forEach(function(x){ if (ds.indexOf(x) < 0) ds.push(x); });
      });
      const agg = {};
      inRange.forEach(function(r){
        if (runCanceled(r) || !r.day) return;
        const k = r.__pl || '--';
        if (dimsOf[k] && dimsOf[k].indexOf('va') < 0) return;
        const a = agg[k] || (agg[k] = {ok: {}, ran: {}});
        a.ran[r.day] = 1;
        if (r.iva === true) a.ok[r.day] = 1;
      });
      let num = 0, den = 0;
      Object.keys(agg).forEach(function(k){
        const a = agg[k];
        pipeCount += 1;
        num += Object.keys(a.ok).length;
        den += (wdN > 0 ? wdN : Object.keys(a.ran).length);
      });
      if (pipeCount){
        total = den; availDays = num;
        rate = den > 0 ? Math.min(1, num / den) : null;
      }
    }
    return {source: 'runs', ran: ran, runs: inRange, byDay: byDay, dayRuns: dayRuns,
            dayList: dayList, dayOk: dayOk, total: total, workdays: wdN, availDays: availDays,
            ranDays: dayList.length, bc: bc, bpc: bpc, pipeCount: pipeCount, rate: rate};
  }
  /* 兜底：老归档没有 step_2_runs.json 的运行历史时，退回「归档日逐日灯态」口径（灯态由比率就地算）。
     只统计有灯态的日子：既没有比率也没有灯色字段的日子不计入分母，避免被当成达标日。 */
  const dls = dayLights(ctx).filter(function(d){ return !!d.light; });
  const bad = {};
  dls.forEach(function(d){ if (d.light === '黄' || d.light === '红') bad[d.date] = 1; });
  const total = dls.length;
  const okDays = Math.max(0, total - Object.keys(bad).length);
  return {source: 'lights', ran: ran, runs: [], byDay: {}, dayRuns: {}, dayList: [], dayOk: {},
          total: total, availDays: okDays, bc: 0, bpc: 0,
          rate: total ? okDays / total : null};
}
/* 根因：只取本条记录的 AI 分析结论（不做任何历史结论复用），没有就留空走兜底文案 */
function rootCauseOf(r){
  const an = r.analysis || {};
  return an.rootCause || '';
}
/* ===== 正文清洗：报错码与出处不进页面 =====
   阅读口径：根因 / 建议只留「原因 + 怎么解决」，封装码（DEV-CODECI-35002、DEV.CB.02202002）
   与 文件名:行号 出处都是噪音，不再展示。归档 JSON 一个字都不动（cites 仍留在 analysis 里，
   错误信息列的「证据」弹窗还要用它定位原始行），只在渲染前把这几类片段剥掉：
     1) 贴进正文的原始 JSON：{"errorMessage":"…","errorCode":"…"}
     2) 括注里的出处：（job_logs/x.log:L138、L139）、（case_logs/x.html:L12）、（pipeline.json:L59）
     3) 行内裸出处：job_logs/x.log:L138 / pipeline.json:L59
     4) 封装码 / 错误码：DEV-CODECI-35002、DEV.CB.02202002、error code is 4
     5) 结尾的「已排除的干扰项」整段（旧写法为自证严谨补的，读者不需要）
   剥完收拾残留的空括号、连续标点与行首标点，避免留下「返回 ，如下」这种破句。 */
const RCB_PATH = /(?:[A-Za-z0-9_.\\-]+[\\/])+[A-Za-z0-9_.\\-]+\.(?:log|json|html|txt|xml)/;
const RCB_LC = /:\s*L?\d+(?:\s*[、,，~\-]\s*L?\d+)*/;
const RCB_JSON = /\{[^{}]*"error(?:Message|Code)"[^{}]*\}/g;
/* 行内裸出处：带目录的日志/JSON 路径，以及合并后不带目录的 pipeline.json:L59 */
const RCB_BARE = /(?:(?:[A-Za-z0-9_.\-]+[\\/])+[A-Za-z0-9_.\-]+\.(?:log|json|html|txt|xml)|pipeline\.json)(?::\s*L?\d+(?:\s*[、,，~\-]\s*L?\d+)*)?/g;
/* 全大写 + 数字 + 分隔符的错误码；正常术语（HCCL、OBS、JDK8、OpenEuler22.03）不会被吞 */
const RCB_CODE = /\b[A-Z][A-Z0-9]{1,}(?:[.\-][A-Z0-9]{1,})+\b/g;
const RCB_ERRC = /(?:错误码|错误代码|封装码)?\s*[:：]?\s*"?[A-Z][A-Z0-9]{1,}(?:[.\-][A-Z0-9]{1,})+"?/g;
/* 纯数字码：「error code is 4」「错误码 561002」「返回码：561002」——数字本身没有信息量，
   但只跟着这几个词才剥，避免误伤正常数值（98 个用例、03:25:16、2026-11-09） */
const RCB_ECODE = /(?:error\s*codes?|return\s*code|errno|错误码|错误代码|返回码)\s*(?:is|was|:|=|：|是|为)?\s*-?\d+/gi;

/* 一段文字（不含换行）里的出处括注 → 去掉；括注里没有出处的（如「（2 个用例）」）原样保留 */
function rcbDropParen(line){
  return String(line).replace(/[（(][^（）()\n]{0,200}[）)]/g, function(m){
    const inner = m.slice(1, -1);
    if (RCB_PATH.test(inner) || RCB_LC.test(inner) || /gh_[0-9A-Za-z]+/.test(inner)
        || /\blogs?\s*[:：]/.test(inner)) return '';
    return m;
  });
}
/* 根因 / 建议正文 → 去掉报错码与出处后的展示文本（多段结构保持，空行不动） */
function rcBody(s){
  const raw = String(s == null ? '' : s);
  if (!raw) return '';
  return raw.replace(/\r\n?/g, '\n').split('\n').map(function(ln){
    let t = rcbDropParen(ln);
    t = t.replace(RCB_JSON, ' ').replace(RCB_BARE, ' ')
         .replace(RCB_ECODE, ' ').replace(RCB_ERRC, ' ').replace(RCB_CODE, ' ');
    /* 收拾残留：空括号、连续标点、标点前的空格 */
    t = t.replace(/[（(]\s*[）)]/g, '')
         .replace(/[ \t]+/g, ' ')
         .replace(/\s*([，,。；;：:、])\s*/g, '$1')
         .replace(/[，,、]{2,}/g, '，')
         .replace(/([，,、；;])\s*([。；;])/g, '$2')
         .replace(/^[，,、；;：:\s]+/, '')
         .replace(/[，,、]\s*$/, '');
    return t;
  }).join('\n')
    /* 旧写法结尾的「已排除的干扰项」整段丢掉：读者要的是「原因 + 怎么解决」，
       排除项属于自证严谨的噪音（新契约已要求不写这一段） */
    .split(/\n{2,}/).filter(function(p){ return !/^\s*已排除/.test(p); }).join('\n\n')
    .replace(/\n{3,}/g, '\n\n').trim();
}
/* 根因 / 建议是多行文本，单元格按行渲染、分档给样式，形成层级（两种写法都兼容）：
     【结论】xxx            → .pt-lead（整行加粗，标签单独着色）
     一、xxx / 二、xxx      → .pt-item（旧的分点小标题，加粗）
     第一类（…）：xxx       → .pt-sec（冒号前短语当小标题加粗，正文同一行接着读，散文式）
     已排除的干扰项：       → .pt-item（整行就是标题）
     分析过程：/验证方式：  → .pt-sub（左缩进、标签灰一档）
   空行 → .pt-gap 留间距。改版前 td 不带 pre-wrap，换行会被吃掉，整段糊在一起 */
function richPoints(s){
  const lines = String(s == null ? '' : s).replace(/\r\n?/g, '\n').split('\n');
  const out = [];
  lines.forEach(function(ln){
    const t = String(ln == null ? '' : ln).replace(/\s+$/, '');
    const tt = t.trim();
    if (!tt){ out.push('<div class="pt-gap"></div>'); return; }
    /* 【结论】后面带正文：标签与正文分开渲染，保证结论行整行是重点 */
    const hd = tt.match(/^(【[^】]{1,8}】)([\s\S]*)$/);
    if (hd && hd[2]) {
      out.push('<div class="pt-lead"><span class="pt-tag">' + rfEsc(hd[1]) + '</span>'
        + rfEsc(hd[2].replace(/^\s+/, '')) + '</div>');
      return;
    }
    if (/^【.+】$/.test(tt)){ out.push('<div class="pt-hd">' + rfEsc(tt) + '</div>'); return; }
    /* 一、二、三（含中文序号到十）：旧的分点小标题 */
    if (/^[一二三四五六七八九十]{1,2}、/.test(tt)){ out.push('<div class="pt-item">' + rfEsc(tt) + '</div>'); return; }
    /* 分析过程 / 判定依据 / 验证方式：事实行，与正文错开一层 */
    const lab = tt.match(/^(分析过程|判定依据|依据|证据|验证方式|验证方法)([:：])([\s\S]*)$/);
    if (lab) {
      out.push('<div class="pt-sub"><span class="pt-lab">' + rfEsc(lab[1] + lab[2]) + '</span>'
        + rfEsc(lab[3].replace(/^\s+/, '')) + '</div>');
      return;
    }
    /* 散文分段：「第一类（15 个用例，MC2 多卡通信类算子）：最早在 …」——
       冒号前是短语小标题（不含句末标点，避免把长句里的冒号误判成标题），
       冒号后是同一段的正文 → 标题加粗内联，正文紧跟其后，读起来是一段话 */
    const sec = tt.match(/^([^。！？；\n]{2,30}?)([：:])([\s\S]*)$/);
    if (sec) {
      const body = sec[3].replace(/^\s+/, '');
      if (body) {
        out.push('<div class="pt-sec"><span class="pt-sec-hd">'
          + rfEsc(sec[1] + sec[2]) + '</span>' + rfEsc(body) + '</div>');
      } else {
        /* 冒号后没内容 = 单独一行的段落标题，如「已排除的干扰项：」 */
        out.push('<div class="pt-item">' + rfEsc(tt) + '</div>');
      }
      return;
    }
    out.push('<div class="pt">' + rfEsc(t) + '</div>');
  });
  return out.join('');
}
/* ============ 定性列：把根因正文里「可能是什么坏了」逐条列出来 ============
   读者只想知道「可能是哪几种情况」，所以这一列不做百分比、不做权重排序，只做编号列举：
     1. 镜像拉取超时
     2. 执行机凭据失效
   抽取口径（正文写法见 agent/agent_task.md）：正文按空行分段，分类型的段形如
   「第 N 类（M 条，…）：…更像 X，而非 Y」→ 每段取 X，抽不到因果就用括号里那句标签
   （「宿主 pinned 内存被占满」）；有「第 N 类」标记时只看这些段
   （第一段总述跳过，否则会把「这批都卡在环境准备」当成一条原因）；单一成因的正文不分段，
   取最后一段（结论段）。同一原因只留一条，最多 4 条。
   每条都压到一句话的短语（rcFit 收到 26 字），不做概率推测。 */
const RC_LEAD = /^(?:因此|所以|这说明|说明|可见|由此|从而|综上|其实|主要原因|真实原因|这批|这次|这一|这种|这类|本条|本次|本批|这|本|也|就|都|且|并|是|而|但|却|属|属于|于|条|第\s*[0-9一二三四五六七八九十]+\s*类)+/;
/* 「第一类（2 个 OmniOperator 子任务」/「第 1 类（5 条」两种写法都要认：类号后面允许空格，
   计数单位可能是「条」也可能是「个」；两个捕获组 = 类号、条数 */
const RC_CLS = /^第\s*([0-9一二三四五六七八九十]+)\s*类\s*[（(]\s*([0-9]+)\s*[条个]/;
/* [正则, 取第几个捕获组]：B 取「而是」后面那个（前面的「不是 X」是被否掉的那种）
   前四条服务于「分类式」长根因（…更像 X，而非 Y）；后四条服务于「单一成因」的短根因，
   后者通常就是一句直陈因果：「因为凭据失效」「clone 鉴权失败，所以用例没拉下来」「原因：凭据过期」 */
const RC_PATS = [
  [/更像(?:是)?\s*([^，,。；]{2,60}?)\s*[，,]?\s*(?:而非|而不是|并非)\s*[^，,。；]{2,60}/, 1],
  [/不是([^，,。；]{2,60})[，,]\s*而是\s*([^，,。；]{2,60})/, 2],
  [/更像(?:是)?\s*([^，,。；]{2,60})/, 1],
  /* 单一成因最常见的落点是「某个资源 / 凭据 / 配置坏了」：执行机上的 gitcode 凭据失效、OBS 临时凭证过期、
     编译机 JDK 版本不匹配——这类名词性结论比它后面的「所以用例没拉起来」更接近原因，
     也比泛化的「A 而不是 B」更具体（「是稳定复现而不是随机网络故障」只是现象，不是原因），所以排在它们前面 */
  [/([^，,。；：]{2,34}?(?:凭据|凭证|token|证书|密钥|权限|配置|版本|环境)[^，,。；：]{0,18}?(?:失效|过期|无效|不足|缺失|被拒|不匹配|不可用|没有权限|无权限|未授权))/, 1],
  [/([^，,。；：]{2,60}?)\s*(?:而非|而不是)\s*[^，,。；]{2,60}/, 1],
  [/(?:因为|由于)\s*([^，,。；：]{2,50})/, 1],
  [/([^，,。；：]{2,50}?)\s*[，,]?\s*(?:导致|致使|使得|造成|从而使|所以|因此)/, 1],
  [/(?:失败点|真实原因|根因|原因)(?:只有)?(?:一个)?(?:(?:是|就是)[：:，,]?|[：:，,])\s*([^，,。；]{3,60})/, 1],
];
const RC_TAIL = '的在与和上时并或而是把将从对向给被让其该那个条类中里内下后前及以为有没不也都就还又再';

function rcNorm(s){ return String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); }

/* 原因压成一句话短语：定性列只有 14% 宽，一句长话塞进去会断在半句（「…运行时在这批」），
   所以超长时优先退到最近的顿号/逗号/冒号处收口（保留完整分句），退不到再硬截断并补「…」
   明示是缩略；收口后悬空的连接词与没闭合的括号/引号一并去掉 */
const RC_LABEL_MAX = 26;
const RC_OPEN = '「『“（(';
function rcFit(s, n){
  let t = String(s || '').trim();
  n = n || RC_LABEL_MAX;
  if (t.length > n){
    const head = t.slice(0, n);
    const k = Math.max(head.lastIndexOf('，'), head.lastIndexOf('、'),
                       head.lastIndexOf('；'), head.lastIndexOf('：'));
    if (k >= 8) t = head.slice(0, k);
    else if (/[0-9A-Za-z\-+]$/.test(head)){
      const sp = head.lastIndexOf(' ');
      t = sp >= 10 ? head.slice(0, sp) : head;
    } else t = head;
    t = t.trim();
    while (t.length > 6 && (RC_TAIL.indexOf(t.slice(-1)) >= 0
           || ' ，,、：:；'.indexOf(t.slice(-1)) >= 0
           || RC_OPEN.indexOf(t.slice(-1)) >= 0)){
      t = t.slice(0, -1).trim();
    }
    if (t.length >= 10) t += '…';
  }
  return t.replace(/^[\s，,、：:]+/, '').replace(/[\s，,、：:]+$/, '');
}

/* 去掉句子开头的连接词（「这类」「因此」「第 2 类」…）与不成对的括号/引号 */
function rcClean(s){
  let t = rcNorm(s).replace(/^[\s「」『』“”'"（）()]+/, '').replace(/[\s「」『』“”'"（）()]+$/, '');
  t = t.replace(RC_LEAD, '').replace(/^[\s，,、]+/, '');
  t = t.replace(RC_LEAD, '').replace(/^[\s，,、]+/, '').replace(/[\s，,、]+$/, '');
  [['（', '）'], ['(', ')'], ['「', '」'], ['『', '』'], ['“', '”']].forEach(function(p){
    if (t.split(p[0]).length > t.split(p[1]).length){
      t = t.slice(0, t.lastIndexOf(p[0])).replace(/[\s，,、]+$/, '');
    }
  });
  return rcFit(t);
}

/* 一段正文 → 一条可能原因（按 RC_PATS 的优先级找第一个命中） */
function rcCauseOf(para){
  const clauses = rcNorm(para).split(/[；。]/);
  for (let pi = 0; pi < RC_PATS.length; pi++){
    const pat = RC_PATS[pi][0], gi = RC_PATS[pi][1];
    for (let ci = 0; ci < clauses.length; ci++){
      const m = pat.exec(rcNorm(clauses[ci]));
      if (!m) continue;
      const g = rcClean(m[gi] || '');
      if (g && g.length >= 3) return g;
    }
  }
  return '';
}

/* 「第 N 类（M 个用例，共性：宿主 pinned 内存被占满）：…」→ 括号里那句标签。
   分类段的正文经常只写证据（用例清单、偏差表现），一句「什么坏了」都没点名，
   这时括号里的标签就是这一类的定性（「宿主 pinned 内存被占满」「pod 提前退出」）；
   标签只是分组名（「量化变体」「MoE 分发合并」）时不当原因，跳过。 */
const RC_HEAD = /^第\s*[0-9一二三四五六七八九十]+\s*类\s*[（(][^）)]*?[，,]\s*([^）)]*?)\s*[）)]/;
const RC_CAUSEY = /(失效|过期|无效|不足|缺失|被拒|超时|占满|占用|耗尽|冲突|不匹配|不一致|偏移|不达标|异常|中断|退出|报错|失败|被占|拉取|鉴权|权限)/;
function rcHeadOf(para){
  const m = String(para || '').match(RC_HEAD);
  if (!m) return '';
  const t = rcClean(String(m[1]).replace(/^(?:共性|共性原因|共性特征|特点|特征|表现|现象)[：:]\s*/, ''));
  return (t && RC_CAUSEY.test(t)) ? t : '';
}

/* 根因正文 → [可能原因]（保持正文顺序，最多 4 条，每条是「什么坏了」的一句话）
   有「第 N 类（M 条…）」分段时逐类取一条：先按 RC_PATS 抽因果，抽不到再用括号里的标签；
   分类段一条都抽不到（正文只写证据、原因写在结论段）才回头扫非分类段。
   没有分类标记（单一成因的短根因）就只看结论段——第一段往往是总述，抽出来是
   「这批都卡在环境准备」这种覆盖全批的话，不该当原因。最后还用结论段首句兜底，保证不空。 */
function causesFromRootCause(rc){
  const paras = String(rc || '').split(/\n\s*\n/).map(rcNorm)
    .filter(function(p){ return !!p && !/^已排除的干扰项/.test(p); });
  if (!paras.length) return [];
  const cls = paras.filter(function(p){ return RC_CLS.test(p); });
  const out = [], seen = {};
  const push = function(c){
    if (c && !seen[c]){ seen[c] = 1; out.push(c); }
  };
  if (cls.length){
    cls.forEach(function(p){ push(rcCauseOf(p) || rcHeadOf(p)); });
    if (!out.length){
      paras.filter(function(p){ return !RC_CLS.test(p); })
        .forEach(function(p){ push(rcCauseOf(p)); });
    }
  } else {
    push(rcCauseOf(paras[paras.length - 1]));
  }
  if (!out.length) push(rcClean(String(paras[paras.length - 1]).split(/[；。]/)[0]));
  return out.slice(0, 4);
}
function cut(s, n){
  const t = String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
  if (!t) return '--';
  return t.length > n ? t.slice(0, n) + '…' : t;
}

/* ===== 问题分类列：一个色标，参考仓的 10 类根因 =====
   大类是十个固定值（AI 在 analysis.issueType 里写，白名单校验在 tools/write_analysis.py），
   页面只负责把它染色展示。分类和「定性」是两件事：分类回答「哪一类问题」（编译 / 单测 / 依赖环境 /
   网络下载 / 资源 / 超时 / 权限 / 配置参数 / 平台 / 无法判定），
   定性回答「具体是什么坏了」——资源规格、节点、镜像、端口、ranktable 这些细节一律留在根因分析里。 */
const ISSUE_CLASSES = ['代码编译错误', '单元测试失败', '依赖/环境缺失', '网络/下载失败', '资源不足',
                       '超时', '权限问题', '配置/参数错误', '基础设施/平台', '无法判定'];
/* AI 常写的近义标签 → 十类标准名（老归档写的是上一版的六个大类，这里一并折过来，避免整列显示 --） */
const IC_ALIAS = {
  '编译错误': '代码编译错误', '编译失败': '代码编译错误', '构建失败': '代码编译错误',
  '单测失败': '单元测试失败', '用例问题': '单元测试失败', '测试失败': '单元测试失败',
  '环境问题': '依赖/环境缺失', '依赖缺失': '依赖/环境缺失', '环境缺失': '依赖/环境缺失',
  '网络问题': '网络/下载失败', '下载失败': '网络/下载失败', '网络失败': '网络/下载失败',
  '资源问题': '资源不足', '磁盘满': '资源不足', '内存不足': '资源不足',
  '运行超时': '超时', 'timeout': '超时',
  '鉴权失败': '权限问题', '认证失败': '权限问题', '凭据失效': '权限问题',
  '配置错误': '配置/参数错误', '参数错误': '配置/参数错误', '工程问题': '配置/参数错误',
  '平台问题': '基础设施/平台', '调度问题': '基础设施/平台', '工具问题': '基础设施/平台',
  '待判定': '无法判定', '未知': '无法判定'
};
/* 老归档没有 issueType 时的兜底：只认信号最强的几类关键词，认不出就不猜（分类列显示 --，
   不硬贴大类——贴错了比不贴更误导）；其余一律等重分析补字段。 */
const IC_GUESS = [
  ['权限问题', /Permission denied|403 Forbidden|Authentication failed|鉴权失败|认证失败|凭据|凭证|token 过期|证书/],
  ['资源不足', /No space left on device|Out of memory|OOM|Killed|磁盘满|空间不足/],
  ['依赖/环境缺失', /No module named|command not found|package not found|依赖缺失|镜像拉不下来/],
  ['代码编译错误', /undefined reference|syntax error|\berror:|编译失败/],
  ['单元测试失败', /AssertionError|FAILED test|精度比对不过/],
  ['网络/下载失败', /Could not resolve host|Connection timed out|404 Not Found|网络下载失败/],
  ['超时', /exceeded the time limit|timeout !!!|执行超时/]
];
/* 分类名归一到十类标准名：先认白名单原值，再认近义标签，最后按关键词兜底 */
function issueTypeOf(r){
  const an = (r || {}).analysis || {};
  const raw = String(an.issueType || '').trim();
  if (ISSUE_CLASSES.indexOf(raw) >= 0) return raw;
  if (raw && IC_ALIAS[raw]) return IC_ALIAS[raw];
  const rc = rcBody(an.rootCause || '');
  for (let i = 0; i < IC_GUESS.length; i++){
    if (IC_GUESS[i][1].test(rc)) return IC_GUESS[i][0];
  }
  return '';
}
/* 问题分类列：只给一个染色的大类标签，判不出大类就交给调用方显示 -- / 待分析 */
function classTag(type){
  const k = ISSUE_CLASSES.indexOf(String(type || ''));
  return '<span class="ic-tag' + (k >= 0 ? ' ic-c' + k : '') + '">' + rfEsc(type) + '</span>';
}
/* ===== 定性列：把根因里的「可能是哪几种情况」逐条列出来 =====
   取的是根因正文里「是什么坏了」的那句话（凭据失效 / 资源没申请到 / 镜像拉不下来…），
   一条就能说清时不带编号，多条才按 1. 2. 3. 排。AI 没写根因正文时退回 issueDetail 那一句。 */
function causeList(r){
  const an = (r || {}).analysis || {};
  const cs = causesFromRootCause(rcBody(an.rootCause || '')).filter(function(c){ return !!c; });
  if (cs.length) return cs;
  const d = String(an.issueDetail || '').trim();
  return d ? [d] : [];
}
function causeCell(r){
  const cs = causeList(r);
  if (!cs.length) return '';
  if (cs.length === 1) return '<div class="ct-item">' + rfEsc(cs[0]) + '</div>';
  return cs.map(function(c, k){
    return '<div class="ct-item ct-num"><span class="ct-k">' + (k + 1) + '.</span>'
      + rfEsc(c) + '</div>';
  }).join('');
}
/* 2026-10-28T21:10:17 → 2026-10-28 21:10:17 */
function tm(s){
  const v = String(s == null ? '' : s).replace('T', ' ');
  return v ? v.slice(0, 19) : '--';
}
/* 根因表的「开始/结束时间」列：归档里是 2026-11-09T02:05:47（ISO，可能带毫秒/时区），
   统一压成 yyyy-MM-dd hh:mm:ss（2026-11-09 02:05:47）——标准可读格式，列内等宽对齐、扫一眼就能定位，
   需要精确到毫秒的原始值在首页「执行记录」弹窗 / 归档 JSON 里看。 */
function ymd(s){
  const m = String(s == null ? '' : s)
    .match(/(\d{4})[-\/](\d{1,2})[-\/](\d{1,2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?/);
  if (!m) return '--';
  const p2 = function(x){ return ('0' + x).slice(-2); };
  return m[1] + '-' + p2(m[2]) + '-' + p2(m[3]) + ' ' + p2(m[4]) + ':' + m[5] + ':' + (m[6] == null ? '00' : m[6]);
}
/* 一条执行记录的「排序时间」：优先结束时间，缺失/非法就用开始时间，都没有返回 null。
   归档里可能带毫秒或时区（2026-11-09T21:03:53.000Z），一律用 Date.parse 归一成毫秒。 */
function recEndMs(r){
  const cand = [r && r.endedAt, r && r.startedAt];
  for (let i = 0; i < cand.length; i++){
    const s = String(cand[i] == null ? '' : cand[i]).trim();
    if (!s) continue;
    const t = Date.parse(s.indexOf(' ') > 0 && s.indexOf('T') < 0 ? s.replace(' ', 'T') : s);
    if (!isNaN(t)) return t;
  }
  return null;
}
/* 根因表行序比较器：按结束时间**降序**（最新在上）；时间相同按构建号降序，保证顺序稳定 */
function cmpByEndDesc(a, b){
  const ta = recEndMs(a), tb = recEndMs(b);
  if (ta !== tb){
    if (ta === null) return 1;    /* 没有时间的排到最后，不要插在最前面挡住最新构建 */
    if (tb === null) return -1;
    return tb - ta;
  }
  const na = Number(a && a.buildNumber), nb = Number(b && b.buildNumber);
  if (!isNaN(na) && !isNaN(nb) && na !== nb) return nb - na;
  return String((b && b.buildNumber) || '').localeCompare(String((a && a.buildNumber) || ''));
}
/* job 日志的每一行本来就带时间戳（[2026/11/06 01:11:47.479 GMT+08:00] ...），
   而 errorMessages 这一层只有行号没有时间字段 → 从原文行首把时间抽出来，供「证据」弹窗的时间列用 */
function timeFromLine(s){
  const m = String(s == null ? '' : s)
    .match(/(\d{4})[-\/](\d{1,2})[-\/](\d{1,2})[ T](\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)/);
  if (!m) return '';
  const p2 = function(x){ return ('0' + x).slice(-2); };
  return m[1] + '-' + p2(m[2]) + '-' + p2(m[3]) + ' ' + m[4];
}
/* 一条记录的「证据」行 = 用例级 errorMessages（带 time/loc，测试报告路线）
   + 顶层 errorMessages（脚本筛过的「重要节点」）。
   去重口径（用户要求）：**只去掉整行完全一致的**——时间、级别、任务/用例、位置（文件:行号）、
   原文全都相同才算重复行；只要时间不一致或行号不一致就保留（那往往是同一个用例的多次重试、
   或多卡并行打印在不同行上的同一条消息，各自是独立的证据）。
   这里不再合成「AI 定位」行：错误信息列已不再展示 AI 结论，证据只保留归档里的原文行。 */
function evidenceRows(r){
  if (!r) return [];
  if (r.__ev) return r.__ev;
  const out = [], seen = new Set();
  const sig = function(s){ return String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); };
  const push = function(o){
    const body = sig(o.text);
    const k = [sig(o.time), sig(o.level), sig(o.loc), String(o.line == null ? '' : o.line),
               sig(o.task), sig(o.case), body].join('\u0001');
    if (body && seen.has(k)) return;
    seen.add(k);
    out.push(o);
  };
  (r.cases || []).forEach(function(c){
    (c.errorMessages || []).forEach(function(m){
      push({time: m.time || timeFromLine(m.msg), level: nz(m.level), loc: m.loc || '',
            line: m.line, text: m.msg || '', task: c.task || '', case: c.name || ''});
    });
  });
  (r.errorMessages || []).forEach(function(e){
    if (e.isSummary) return;                 /* pytest 汇总行不是一条证据 */
    push({time: e.time || timeFromLine(e.text), level: nz(e.level), loc: '',
          line: e.line, text: e.text || '', task: e.task || '', case: e.case || ''});
  });
  const withT = out.filter(function(x){ return x.time; });
  const noT = out.filter(function(x){ return !x.time; });
  withT.sort(function(a, b){ return String(a.time).localeCompare(String(b.time)); });
  r.__ev = withT.concat(noT);
  return r.__ev;
}

/* ===== 一行 = 一条执行记录（不再做「同日同报错」聚合） =====
   用户口径：构建拆开看，一次构建一行，靠「开始/结束时间」列定位，
   同一天同一报错的几次构建各自成行、各自带自己的根因/建议（分析本来就是按记录写的）。
   所以这里不再按报错指纹分组，原有 groupRecs / errSigOf / groupCases / groupEvidenceRows /
   groupAnalyses 一族聚合函数已下线。 */

/* 区间内该组件下有归档的流水线名（去重后按名字排序）：页头 / 区块头 / 概要行都用它 */
function plNames(ctx){
  const seen = {}, out = [];
  ((ctx || {}).dirs || []).forEach(function(d){
    const pl = d.pl || {};
    const n = pl.pipelineName || pl.pipeline || '';
    if (!n || seen[n]) return;
    seen[n] = 1;
    out.push(n);
  });
  return out.sort();
}

/* 组件级页头：标题 = 组件名（带维度），面包屑只到组件这一层（中间那层流水线清单已下线），
   概要行给区间内几条流水线、需根因的执行记录数——不再有单条流水线的「平台」字段 */
function renderHead(meta, recs, ctx){
  const el = document.getElementById('meta');
  let tasks = 0, cases = 0, errs = 0, evs = 0;
  recs.forEach(function(r){
    const c = r.counts || {};
    tasks += Number(c.tasks || 0); cases += Number(c.cases || 0);
    errs += Number(c.errorMessages || 0); evs += Number(c.evidenceFiles || 0);
  });
  const comp = (meta && (meta.comp || (meta.pl || {}).component)) || COMP;
  const names = plNames(ctx);
  const dayN = {};
  (ctx.dirs || []).forEach(function(d){ dayN[d.date] = 1; });
  const ttl = document.getElementById('ttl');
  if (ttl) ttl.innerHTML = '<b>' + rfEsc(comp) + '</b>'
    + ' <span class="dim" style="font-weight:400;font-size:12px">'
    + rfEsc(DIM ? DIMNAME[DIM] : '全部维度') + ' · 组件级根因明细</span>';
  const crumb = document.getElementById('crumb');
  if (crumb) crumb.innerHTML = crumbHead(ctx.from, ctx.to)
    + '<b>' + rfEsc(comp) + '</b>'
    + (DIM ? '<span class="dim">（' + rfEsc(DIMNAME[DIM]) + '）</span>' : '')
    + '<span class="dim">（组件级 · 区间内 ' + Object.keys(dayN).length + ' 天有归档记录 · '
    + names.length + ' 条流水线 · 每条执行记录一行根因）</span>';
  /* 「任务成功但用例未 100%」的行没有根因，不能混进「需根因执行记录」的条数里，
     单独给一个数（这些行是 load() 从运行历史补的，见 okRowOf） */
  const okRows = recs.filter(function(r){ return r.__okRow; }).length;
  if (el) el.textContent = '区间 ' + ctx.from + ' ~ ' + ctx.to
    + ' · 流水线 ' + (names.length || '--')
    + ' · 需根因执行记录 ' + (recs.length - okRows)
    + (okRows ? ' · 任务成功但用例未 100% ' + okRows : '')
    + ' · 任务 ' + tasks + ' · 用例 ' + cases
    + ' · 错误信息 ' + errs + ' · 证据 ' + evs;
  renderDist(recs);
}

/* 失败类型分布：二级页字段，按执行记录计数（含占比）。纯展示、不可点 —— 行序由根因表自己按结束时间排。
   这里数的是归档时的规则分类（verdict.category），和「问题分类」列不是一回事：后者是 AI 判的
   十类根因（编译/单测/依赖环境/网络下载/资源/超时/权限/配置参数/平台/无法判定），
   一条记录一个大类、口径按问题性质而不是按失败形态，
   所以这一条只做「这批失败里各类型各占多少条」的概览，标题也就叫「失败类型分布」不再叫「定性分布」 */
function catOfRec(r){
  return (r.verdict || {}).category || r.category || 'unknown';
}
function renderDist(recs){
  const el = document.getElementById('dist');
  if (!el) return;
  const byCat = {};
  recs.forEach(function(r){
    /* 「任务成功但用例未 100%」的行照常计数（它们是表里真实存在的一行），
       只是分类名走 CATS.success = 「用例未 100%」，不出现英文 success */
    const k = catOfRec(r);
    byCat[k] = (byCat[k] || 0) + 1;
  });
  const ks = Object.keys(byCat).sort(function(a, b){ return byCat[b] - byCat[a]; });
  const total = recs.length || 1;
  const tags = ks.map(function(k){
    const c = CATS[k] || [k, ''];
    const p = (byCat[k] / total * 100).toFixed(byCat[k] === total ? 0 : 1);
    return '<span class="tag ' + c[1] + '">'
      + rfEsc(c[0]) + ' ' + byCat[k]
      + ' <span class="dim">' + p + '%</span></span>';
  }).join('');
  el.innerHTML = '<span class="dt" title="按归档时的规则分类统计执行记录条数'
    + '（「用例未 100%」= 任务执行成功但用例通过率没到 100% 的运行）；'
    + '「问题分类」列给的是 AI 判的十类根因（编译/单测/依赖环境/网络下载/资源/超时/权限/配置参数/平台/无法判定），两者口径不同">失败类型分布</span>'
    + (ks.length ? tags : '<span class="dim">--</span>')
    + '<span class="sp"></span><span class="dim">按执行记录计数，共 ' + recs.length + ' 条</span>';
}

let RECS = [];      /* 区间内该流水线的全部失败执行记录（平铺，一条记录一行） */
let RUNS = [];      /* 区间内该流水线的全部运行（每日归档 runHistory，按构建号去重） */
let CTX = null;     /* 当前统计区间上下文：dirs / days / from / to / runs */

/* ---------- 「任务执行成功，但用例通过率没到 100%」这一类运行 ----------
   用户口径：这类运行只需要**标记任务成功 + 给出用例比例**，不做 AI 根因、不抓失败用例清单。
   数据来源是 runHistory（load 收的 runs 里带了全部运行，含 status / cpr），
   归档的 records 只收 FAILED / CANCELED，所以它们默认不会出现在根因表里 —— 由 load 就地补一行。 */
function isOkRun(x){
  const s = String((x || {}).status || '').toUpperCase();
  return s === 'SUCCESS' || s === 'SUCCEEDED' || s === 'COMPLETED'
      || s === 'FINISH' || s === 'FINISHED' || s === 'PASS' || s === 'PASSED';
}
/* 用例通过率：归档里 cpr 是 0~100 的百分数，缺失 / 非法返回 null（不猜、不补 0） */
function cprOf(x){
  const v = (x || {}).cpr;
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return isNaN(n) ? null : n;
}
/* 由一条 runHistory 运行合成一行「任务成功 · 用例 xx%」的记录：
   没有 tasks / cases / analysis，recRow 里走 isOk 分支 —— 不给 ▸、不给根因/建议，
   问题分类只标「任务成功」，定性写用例通过率。 */
function okRowOf(x){
  return {
    __pl: x.__pl || '',
    __okRow: 1,
    __cpr: cprOf(x),
    buildNumber: x.rn,
    links: {openlibing: x.url || ''},
    startedAt: x.start || '',
    endedAt: x.end || '',
    tasks: [], cases: [], errorMessages: [],
    evidence: {files: [], missing: []},
    verdict: {category: 'success'},
    analysis: {status: 'na'}
  };
}

/* 区间内没有失败记录时的提示：不能再只写一句「没有需要根因分析的失败执行记录」——
   最常见的原因是「运行全部执行成功，但测试用例通过率不是 100%」（iva=false），
   只看这一页的根因表根本看不出可用度为什么是 0%。这里直接从区间运行历史里算出
   「哪几次不是 100%、最低多少、是哪次构建」，用醒目底色摆在区块头下面。 */
function noFailNotice(st){
  const runs = (st && st.runs) || [];
  const total = st ? (st.total || 0) : 0;
  const ok = st ? (st.availDays || 0) : 0;
  if (!runs.length){
    /* 区间内一次都没跑过：这不叫「可用度 0%」，也不该让人点进去找失败记录 */
    if (st && st.ran === false){
      return '<div class="nofail mute"><span class="nf-hd">该组件在区间内 0 次运行</span>'
        + '既没有可用日，也没有可做根因分析的失败执行记录；'
        + '比率显示 <b>--</b>，不纳入统计。</div>';
    }
    const noHist = st && st.source !== 'runs';
    return '<div class="nofail mute"><span class="nf-hd">区间内没有需要根因分析的失败执行记录</span>'
      + (noHist
          ? '该区间归档里没有这个组件的运行历史（只有日级灯态），无法逐条对照执行结果。'
          : '该组件在这个区间内 0 次运行，既没有可用日，也没有可做根因分析的失败记录。')
      + '</div>';
  }
  /* 执行成功但用例没全通过：iva=false 的典型成因，也是「没有失败记录却不可用」的答案
     （用例通过率统一走全局 cprOf，与根因表「任务成功但用例未 100%」的行同一个口径） */
  const notFull = runs.filter(function(r){ const c = cprOf(r); return c !== null && c < 100; });
  if (notFull.length){
    notFull.sort(function(a, b){ return cprOf(a) - cprOf(b); });
    const low = notFull[0];
    const allOk = runs.every(function(r){
      return /COMPLETED|SUCCESS|FINISH|PASS/i.test(String(r.status || ''));
    });
    const where = (low.rn === null || low.rn === undefined || low.rn === '')
      ? (low.day || '') : ('构建 #' + low.rn + (low.day ? ' · ' + low.day : ''));
    const head = allOk
      ? '区间内 ' + runs.length + ' 次运行全部执行成功，但测试用例通过率不是 100%'
      : '区间内 ' + runs.length + ' 次运行里有 ' + notFull.length + ' 次测试用例通过率不是 100%';
    return '<div class="nofail"><span class="nf-hd">' + rfEsc(head) + '</span>'
      + '最低 <b>' + cprOf(low).toFixed(2) + '%</b>'
      + (where ? '（' + rfEsc(where) + '）' : '') + '。'
      + '版本可用度的口径是「当天要有编译通过且用例 100% 通过的运行才算可用」，'
      + '这类运行属于执行成功、用例没全过，所以当天不计为可用'
      + (total ? '（本区间可用 ' + ok + '/' + total + ' 工作日）' : '')
      + '，也不会产生失败执行记录，因此没有根因分析行。'
      + '要逐次核对通过率：回首页点「流水线数 → 查看」看该流水线的执行记录。</div>';
  }
  return '<div class="nofail mute"><span class="nf-hd">区间内没有需要根因分析的失败执行记录</span>'
    + '共 ' + runs.length + ' 次运行，均未判为失败或取消'
    + (total ? '；本区间' + DIMNAME[dimOf()] + '达标 ' + ok + '/' + total + ' 工作日' : '')
    + '。</div>';
}

/* ===== 组件级：一个组件一个区块（h3 浅蓝区块头）+ 一张 9 列固定列宽的根因明细表 =====
   组件下所有待分析流水线的失败执行记录合成一张表，靠最前面的「流水线」列区分是哪一条。
   区块头的比率 / 达标工作日按**组件级**算：rangeStats 收到的是该组件全部流水线的运行历史，
   版本可用度 = 各流水线版本可用度的算术平均（与首页组件行同源），构建成功率 = Σ编译通过 ÷ Σ编译次数。 */
function renderRecs(recs, ctx){
  const box = document.getElementById('recs');
  RECS = recs;
  const dim = dimOf();
  const st = rangeStats(ctx, dim);
  const total = st.total;
  const okDays = st.availDays;
  const rate = st.rate;
  const names = plNames(ctx);
  /* 表里混着两类行：有根因的失败记录 + 「任务成功但用例未 100%」的补行（后者没有根因） */
  const okRows = recs.filter(function(r){ return r.__okRow; }).length;
  /* 只看数字（85.71%），不带黄/绿/红标记：灯色只在首页组件级出现，
     往下钻一律看数字 + 达标工作日数。 */
  const okWord = dim === 'bs' ? '达标' : '可用';
  const isVA = dim !== 'bs';
  const pipeN = st.pipeCount || 0;
  /* dim=va 的组件级口径 = 各流水线版本可用度的算术平均（与首页组件行同一个算法、同一套逐日重算）：
     每条流水线的分母都是同一个区间法定工作日数，所以等价于 Σ可用日 ÷ Σ流水线工作日。
     区块头写「Σ可用日/Σ流水线工作日」并标明几条流水线平均，首页点进来的数字就能一眼对上。
     dim=bs 仍是 Σ编译通过 ÷ Σ编译次数，分母是「区间内有运行的工作日数」。 */
  const denomTip = (dim === 'bs')
    ? ('区间内有运行的工作日 ' + total + ' 天，其中 ' + okDays + ' 天' + okWord)
    : ('各流水线版本可用度平均：区间法定工作日 ' + st.workdays + ' 天 × ' + pipeN
       + ' 条流水线，Σ' + okWord + ' ' + okDays + ' ÷ Σ工作日 ' + total);
  const denomRule = (dim === 'bs')
    ? '分母 = 区间内有运行的工作日数'
    : '分母 = 区间法定工作日数（不是有运行的天数）';
  const h3 = '<h3 title="' + DIMNAME[dim] + '（组件级）：' + (st.source === 'runs'
      ? denomTip + '（逐日按执行结果重算，统计区间一变即重算；' + denomRule + '）'
      : (st.ran
          ? '区间内归档 ' + total + ' 天，其中 ' + okDays + ' 天该组件在此维度上没有黄/红'
          : '该组件在本区间内一次都没有运行过（runsInPeriod = 0），'
            + '归档里没有可比对的执行结果，比率显示 --、不纳入统计'))
    + '">' + rfEsc(COMP)
    + ' ｜ ' + DIMNAME[dim] + ' ' + (rate == null ? '--' : (rate * 100).toFixed(2) + '%')
    /* 组件级版本可用度 = 各流水线平均：只在比率后面标明几条流水线平均，
       不再跟「可用 N/M 工作日」——N/M 就是比率本身，写出来是重复（用户口径）。 */
    + (isVA && pipeN ? '（' + pipeN + ' 条流水线平均）' : '')
    /* 区间内没跑过（或整个区间没有归档日）：写明没有执行记录、不纳入统计，
       不给「可用 0/0 工作日」这种看着像 0 分的写法 */
    + ((st.ran && total > 0)
        ? ' '
        : ' <span class="dim">｜ '
          + ((ctx && (ctx.dirs || []).length)
              ? (st.ran ? '区间内无可比对的执行结果 · 不纳入统计' : '区间内无执行记录 · 不纳入统计')
              : '区间内无归档日')
          + '</span> ')
    /* 比率之后紧跟「执行记录」入口（用户口径）：按流水线列出该组件区间内的运行，
       不再把「N 条流水线：a、b、c…」这串名字摊在区块头里（太长且不可点）。 */
    + ((ctx && (ctx.dirs || []).length)
        ? '<span class="lnk hd-exec" data-execpipes="1" title="按流水线查看该组件在区间 '
          + rfEsc(ctx.from || '') + ' ~ ' + rfEsc(ctx.to || '') + ' 内的全部执行记录'
          + (names.length ? '（共 ' + names.length + ' 条流水线）' : '') + '">执行记录</span>'
        : '')
    + (okRows
        ? '<span class="dim" style="font-weight:400;font-size:12px;margin-left:8px">'
          + '（含 ' + okRows + ' 条任务成功但用例未 100%）</span>'
        : '')
    + '</h3>';
  if (!recs.length){
    /* 区间内没有失败记录也要出区块头：比率/工作日是区间重算的结果，不是记录数的函数。
       提示按「为什么没有失败记录」分情况给（用例没到 100% / 一次没跑 / 无运行历史），
       见 noFailNotice；不再是「自己翻归档」的一句灰字。 */
    box.innerHTML = '<div class="subview">' + h3 + noFailNotice(st) + '</div>';
    return;
  }
  /* 10 列：流水线 → 流水线编号 → 开始时间 → 结束时间 → 任务 → 用例 → 错误信息 → 问题分类 → 定性 → 展开
     一条执行记录一行（不再把同日同报错聚合成一行），开始/结束时间给出 yyyy-MM-dd hh:mm:ss，
     行序由 recs 自己带过来（加载时已按结束时间降序排好，见 cmpByEndDesc），
     所以是「最近结束的在最上面」，方便从最新往回看。
     最前面的「流水线」列是组件级才有的：同一张表里混着多条流水线的记录，必须能一眼看出是哪条。
     最后一列「展开」放稍大的三角按钮，整行 hover: pointer（用户口径）。 */
  const cols = ['12%', '7%', '10.5%', '10.5%', '10%', '12%', '16%', '9%', '10%', '3%'];
  const ths = ['流水线', '流水线编号', '开始时间', '结束时间', '任务', '用例', '错误信息', '问题分类', '定性', ''];
  const table = '<table class="rca rca-rec"><colgroup>'
    + cols.map(function(w){ return '<col style="width:' + w + '">'; }).join('')
    + '</colgroup><thead><tr>' + ths.map(function(t){ return '<th>' + t + '</th>'; }).join('') + '</tr></thead>'
    + '<tbody>' + recs.map(function(r, i){ return recRow(r, i); }).join('') + '</tbody></table>';
  box.innerHTML = '<div class="subview">' + h3 + table + '</div>';
}

/* ===== 区块头「执行记录」入口：本组件区间内的运行按流水线分组 =====
   取代原先摊在区块头的「N 条流水线：a、b、c…」文字。数据就是 load() 收进来的 ctx.runs
   （已按「执行结束时间落在区间内」筛过、按流水线+构建号去重）。
   版式（用户口径）：一个弹窗里按流水线分组，组内按日期倒序逐天给灯态——
   组头 = 流水线名 + 该流水线达成率（成功工作日 / 已执行工作日）+「逐条」入口；
   逐日行 = 灯 + 日期 + 「成功 x / 共 y 次」。EXEC_GROUPS 供「逐条」回调按下标取用。 */
let EXEC_GROUPS = [];
/* 该次运行在当前维度算不算「成功」：va 看归档算好的 iva；bs 看编译是否全过 */
function runOkIn(x, dim){
  if (dim === 'bs'){
    if (x.bc === null || x.bc === undefined || x.bc === '') return false;
    return (Number(x.bpc) || 0) >= Number(x.bc);
  }
  return x.iva === true;
}
/* 归档里被取消的运行不计入统计（用户口径：aborted 与进行中都不算） */
function runCanceled(x){ return String(x.status || '').toUpperCase() === 'CANCELED'; }
function execDot(ok){
  return '<i class="' + (ok === true ? 'g' : (ok === false ? 'r' : 'n')) + '"></i>';
}
function openExecByPipe(){
  const ctx = CTX || {};
  const dim = dimOf();
  const from = ctx.from || '', to = ctx.to || '';
  const wdN = wdInRange(from, to);
  const grp = {}, order = [];
  (ctx.runs || []).forEach(function(x){
    const k = x.__pl || '--';
    if (!grp[k]){ grp[k] = []; order.push(k); }
    grp[k].push(x);
  });
  /* 区间内有归档目录但一次都没跑的流水线也列出来（该组没有逐日行） */
  plNames(ctx).forEach(function(n){ if (!grp[n]){ grp[n] = []; order.push(n); } });
  if (!order.length){
    openModal('执行记录｜' + rfEsc(COMP),
      '<div class="dim">该组件在区间 ' + rfEsc(from) + ' ~ ' + rfEsc(to) + ' 内没有归档记录。</div>');
    return;
  }
  EXEC_GROUPS = order.map(function(k){ return {pl: k, runs: grp[k]}; });
  /* 两条轨道各自保持「与区块头同口径」，否则点开弹窗会看到组头 100%、组件头 96%：
     va  组头 = 成功工作日 / 区间法定工作日（各流水线平均，分子分母分别求和 = 组件级）；
     bs  组头 = Σ编译通过 / Σ编译次数（用户口径：最终编译成功率 = 所有通过次数 ÷ 所有编译次数，
          各流水线的分子分母分别求和就是组件级的值，所以逐条也能加得起来）。
     aborted / 进行中一律不计入。 */
  const isBS = (dim === 'bs');
  let sumNum = 0, sumDen = 0, sumPass = 0, sumCnt = 0;
  const blocks = EXEC_GROUPS.map(function(g, gi){
    const byDay = {};
    let pPass = 0, pCnt = 0;
    g.runs.forEach(function(x){
      if (!x.day || runCanceled(x)) return;
      const c = (x.bc === null || x.bc === undefined || x.bc === '') ? 0 : (Number(x.bc) || 0);
      const p = (x.bpc === null || x.bpc === undefined || x.bpc === '') ? 0 : (Number(x.bpc) || 0);
      const d = byDay[x.day] || (byDay[x.day] = {total: 0, ok: 0, p: 0, c: 0});
      d.total += 1;
      if (runOkIn(x, dim)) d.ok += 1;
      d.p += p; d.c += c;
      pPass += p; pCnt += c;
    });
    /* 组内按日期倒序（最新的工作日排在最上面） */
    const days = Object.keys(byDay).sort(function(a, b){ return a < b ? 1 : -1; });
    let num, den, head, dayOk;
    if (isBS){
      num = pPass; den = pCnt;
      head = (pCnt > 0 ? (pPass / pCnt * 100).toFixed(2) + '%' : '--')
           + '（Σ编译通过 ' + pPass + ' / Σ编译次数 ' + pCnt + '）';
      dayOk = function(e){ return e.c > 0 && e.p >= e.c; };
    } else {
      den = wdN; num = days.filter(function(d){ return byDay[d].ok > 0; }).length;
      head = (den > 0 ? (num / den * 100).toFixed(2) + '%' : '--')
           + '（成功 ' + num + ' / 已执行工作日 ' + den + '）';
      dayOk = function(e){ return e.ok > 0; };
    }
    sumNum += num; sumDen += den; sumPass += pPass; sumCnt += pCnt;
    const rows = days.map(function(d){
      const e = byDay[d];
      const txt = isBS ? ('编译通过 <b>' + e.p + '</b> / 编译 ' + e.c + ' 次')
                       : ('成功 <b>' + e.ok + '</b> / 共 ' + e.total + ' 次');
      return '<div class="pexec-row">' + execDot(dayOk(e))
        + '<span class="dt">' + rfEsc(d.replace(/-/g, '/')) + '</span>'
        + '<span class="rt">' + txt + '</span></div>';
    }).join('');
    return '<div class="pexec-grp">'
      + '<div class="pexec-hd"><span class="pl">' + rfEsc(g.pl) + '</span>'
      + '<span class="rt">' + head
      + (g.runs.length ? '<span class="lnk" data-plruns="' + gi + '">逐条</span>' : '')
      + '</span></div>'
      + (rows || '<div class="pexec-row pexec-none"><span class="dim">区间内没有执行记录</span></div>')
      + '</div>';
  }).join('');
  openModal('执行记录 · 按流水线 · ' + rfEsc(COMP),
    '<div class="pexec-sum">区间 ' + rfEsc(from) + ' ~ ' + rfEsc(to) + ' · ' + EXEC_GROUPS.length
    + ' 条流水线' + (isBS ? ' · 合计编译通过 ' + sumPass + ' / 合计编译 ' + sumCnt + ' 次'
                          : '平均 · 合计可用 ' + sumNum + ' 天 / 合计执行 ' + sumDen + ' 个工作日')
    + ' · 按流水线分组，组内按日期倒序</div>'
    + '<div class="pexec-lg">' + execDot(true)
    + (isBS ? '当天编译全部通过' : '当天存在成功构建') + execDot(false)
    + (isBS ? '当天有编译失败' : '有构建但无成功') + execDot(null) + '无记录（未计入）</div>'
    + '<div class="mtbl">' + blocks + '</div>'
    + '<div class="mrec-note">共 ' + EXEC_GROUPS.length + ' 条流水线，组件' + DIMNAME[dim]
    + (isBS ? ' = Σ编译通过 ÷ Σ编译次数（无编译次数的不计入）· '
            : ' = Σ流水线' + DIMNAME[dim] + ' ÷ 流水线条数（无执行记录的不计入）· ')
    + '只统计执行结束时间落在区间内的运行，aborted 与进行中均不计入；'
    + '点「逐条」看该流水线区间内的逐条运行。</div>');
}
/* 二级弹窗：某条流水线在区间内的逐条运行（不按天汇总，按结束时间倒序） */
function runsTable(rs, from, to){
  const sorted = rs.slice().sort(function(a, b){
    return String(b.end || '').localeCompare(String(a.end || ''));
  });
  const rows = sorted.map(function(x){
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
  return '<div class="mtbl"><table class="rca"><colgroup><col style="width:8%"><col style="width:9%">'
    + '<col style="width:12%"><col style="width:8%"><col style="width:11%">'
    + '<col style="width:9%"><col style="width:21.5%"><col style="width:21.5%"></colgroup>'
    + '<thead><tr><th>流水线编号</th><th>状态</th><th>失败类型</th><th>版本可用</th>'
    + '<th>编译成功/次数</th><th>用例通过率</th><th>开始时间</th><th>结束时间</th></tr></thead>'
    + '<tbody>' + rows + '</tbody></table></div>'
    + '<div class="mrec-note">区间 ' + rfEsc(from) + ' ~ ' + rfEsc(to)
    + ' · 区间内每一次运行逐条平铺（不按天汇总），按结束时间倒序 · 运行来自归档 pipeline.json 的 '
    + 'runHistory（按执行结束时间归属日期，只保留区间内的）· 点构建号直接在 openLiBing 打开该次执行。</div>';
}

/* 一行 = 一条执行记录（一次构建）
   任务取该记录自己的任务列表（多任务时列首条 + 「共 N 个任务」），
   用例与证据都只取这一条记录，根因/建议也只取这一条记录的分析结论——不再跨构建合并，
   避免「一行的结论其实来自另一次构建」这种对不上的情况。 */
function recRow(r, i){
  const v = r.verdict || {};
  const an = r.analysis || {};

  /* 任务：该记录内的任务名去重（一次构建可能跑多个 job，都算这条记录的上下文） */
  const tnames = [], tseen = new Set();
  (r.tasks || []).forEach(function(t){
    const n = String(t.jobName || '');
    if (!n || tseen.has(n)) return;
    tseen.add(n);
    tnames.push(n);
  });
  const taskCell = tnames.length
    ? '<b>' + rfEsc(nz(tnames[0])) + '</b>'
      + (tnames.length > 1 ? '<span class="exec-sub">共 ' + tnames.length + ' 个任务</span>' : '')
    : '<span class="dim">--</span>';

  /* 用例列：没有失败用例就只显示 --（成功运行、编译失败、日志类失败都没有用例，
     不套任何解释文案——「setup 阶段批量失败」这种说法对编译任务/日志任务本来就是错的） */
  const isOk = (v.category === 'success');
  const cases = (r.cases || []).filter(function(c){ return c && c.name; });
  let caseCell;
  if (cases.length){
    /* 用例列：第一条用例名打头，「共 N 条失败用例」是可点链接 → 弹窗里逐条给用例详情
       （用例名 / 状态 / 起止时间 / 报告里的断言原文 / 该用例日志） */
    caseCell = rfEsc(cut(cases[0].name, 70))
      + '<span class="lnk exec-sub" data-cases="' + i + '"'
      + ' title="点击查看 ' + cases.length + ' 条失败用例的详情">共 '
      + cases.length + ' 条失败用例</span>';
  } else if (r.__cpr != null){
    /* 任务执行成功、用例没全过：这一行是 load() 从运行历史里补出来的，
       没有抓失败用例清单（不需要），只给「用例比例」——这是用户口径要求的最小信息。 */
    caseCell = '<span class="cpr-cell" title="该次运行任务执行成功，测试用例通过率 '
      + Number(r.__cpr).toFixed(2) + '%，没有达到 100%">用例通过率 '
      + Number(r.__cpr).toFixed(2) + '%</span>';
  } else {
    caseCell = '<span class="dim">--</span>';
  }

  /* 证据行：这条记录的用例级 errorMessages（带时间/位置）+ job 日志错误行；
     只按「整行完全一致」去重（时间或行号不同就各自保留，见 evidenceRows）。
     错误信息列不再展示 AI 结论正文（用户口径：照那句话去证据里根本对不上这些问题）——
     这一列只留「证据」两个字，点开就是本次构建的日志/报告原始行；结论性内容只在展开区的根因/建议里。 */
  const evs = evidenceRows(r);
  const errCell = r.__okRow
    ? '<span class="dim">任务执行成功，无失败日志</span>'
    : (evs.length
        ? '<span class="lnk ev-lnk" data-evidence="' + i + '" title="点击查看日志证据：'
          + evs.length + ' 行（时间 / 级别 / 位置 / 原文）">证据</span>'
        : '<span class="dim">证据 --</span>');

  /* 流水线编号：单条记录的构建号，跳 openLiBing。行首不再带三角（用户口径），
     展开开关挪到最后一列（见下 expCell）。 */
  const flat = isOk;
  const lb = (r.links || {}).openlibing;
  const bn = nz(r.buildNumber);
  const buildCell = (lb
      ? '<a href="' + rfEsc(lb) + '" target="_blank" rel="noopener" title="在 openLiBing 查看构建 #'
        + rfEsc(bn) + '">#' + rfEsc(bn) + '</a>'
      : '<span class="mono">#' + rfEsc(bn) + '</span>')
    + (r.__err ? '<span class="exec-sub" style="color:#f5222d">记录读取失败</span>' : '');

  /* 根因：不做 AI 分析的记录（成功运行 / 指标达标的失败运行，analysis.status=na）显示 --；
     内容按行渲染（见 richPoints），行高随内容自然增长，不做任何字符截断；
     渲染前过一遍 rcBody：报错码与 文件名:行号 出处都剥掉（用户口径：只留原因与怎么解决） */
  const noAI = isOk || an.status === 'na';
  const rc = isOk ? '' : rcBody(an.rootCause || '');
  const rcCell = rc ? richPoints(rc)
    : (noAI ? '<span class="dim">--</span>' : '<span class="dim">待 AI 根因分析</span>');

  const adv = isOk ? '' : rcBody(an.advice || (((r.suggestions || [])[0]) || ''));
  const advCell = adv ? richPoints(adv)
    : (noAI ? '<span class="dim">--</span>' : '<span class="dim">待 AI 根因分析</span>');

  /* 问题分类列：只给一个染色的十类标签（代码编译错误 / 单元测试失败 / 依赖/环境缺失 / 网络/下载失败 /
     资源不足 / 超时 / 权限问题 / 配置/参数错误 / 基础设施/平台 / 无法判定），
     大类由 AI 在 analysis.issueType 里给定；不带大类说明的任何细节（那是定性列和根因分析的事）。
     不必分析的记录（analysis.status=na）没有结论 → --；还没分析的 → 待 AI 根因分析。 */
  /* 定性列：把「可能是哪几种情况」逐条列出来（不带百分比），只有一条时不编号。
     资源规格、节点、镜像、端口、通信域这些细节都放进根因分析，不在这列铺开。 */
  let clsCell, catCell;
  if (isOk){
    /* 成功运行里只有「执行成功但用例没全过」会进表：**标记任务成功 + 给出用例比例**，
       不再套「单元测试失败」分类（这次构建本身是成功的，问题在用例层面，不是任务失败）。
       没有失败用例清单时（load 补的行）只有 cpr，就直接写通过率。 */
    const cprTxt = (r.__cpr == null) ? '' : Number(r.__cpr).toFixed(2) + '%';
    clsCell = r.__okRow ? '<span class="tag green">任务成功</span>' : '<span class="dim">--</span>';
    catCell = r.__okRow
      ? '<div class="ct-item">执行成功，'
        + (cprTxt ? '用例通过率 ' + cprTxt + '（未达 100%）'
                  : '但有 ' + cases.length + ' 条用例没通过') + '</div>'
      : '<span class="dim">--</span>';
  } else {
    const ty = issueTypeOf(r);
    const cc = causeCell(r);
    const naTxt = an.status === 'na' ? '<span class="dim">--</span>'
      : '<span class="dim">待 AI 根因分析</span>';
    clsCell = ty ? classTag(ty) : naTxt;
    catCell = cc || naTxt;
  }

  /* 展开区：根因分析 + 修复建议（这两段原来各占一列，动辄上千字把整张表拉得没法扫读）。
     出处块已下线：正文里的 file:line 与单独一列胶囊都属于噪音，结论本来就该是「原因 + 怎么解决」；
     原始出处仍留在 analysis.cites，错误信息列点「证据」看到的首行「AI 定位」就是它。
     默认 hidden，点末列 ▸ 或点主行任意位置展开；只渲染一次，展开/收缩只切 hidden，不重排内容。 */
  const det = flat ? '' : '<tr class="rc-det" data-exp-of="' + i + '" hidden>'
    + '<td colspan="10" class="rc-det-cell">'
    + '<div class="rc-blk"><span class="rc-hd">根因分析</span>' + rcCell + '</div>'
    + '<div class="rc-blk"><span class="rc-hd">修复建议</span>' + advCell + '</div>'
    + '</td></tr>';

  /* rc-alt：斑马纹只按主行数奇偶（展开行 rc-det 不参与，否则底纹会跳变） */
  return '<tr class="rc-main' + (i % 2 ? ' rc-alt' : '') + '"'
    + (flat ? '' : ' data-exp-row="' + i + '"') + '>'
    + '<td class="cw1 pl-cell">' + (r.__pl ? rfEsc(r.__pl) : '<span class="dim">--</span>') + '</td>'
    + '<td class="bldg-cell">' + buildCell + '</td>'
    + '<td class="nowrap mono dt-c">' + rfEsc(ymd(r.startedAt)) + '</td>'
    + '<td class="nowrap mono dt-c">' + rfEsc(ymd(r.endedAt)) + '</td>'
    + '<td>' + taskCell + '</td>'
    + '<td>' + caseCell + '</td>'
    + '<td class="err-cell">' + errCell + '</td>'
    + '<td class="cls-cell">' + clsCell + '</td>'
    + '<td class="cat-cell">' + catCell + '</td>'
    + '<td class="exp-cell">'
    + (flat ? '' : '<span class="exp-ic" title="展开 / 收起根因分析与修复建议">▸</span>')
    + '</td>'
    + '</tr>'
    + det;
}

/* 单条记录的定位标签：#168 · 20261109 02:05:47，弹窗标题用（一条记录一行后不再有组标签） */
function buildTag(r){
  const t = ymd((r || {}).endedAt);
  return '#' + nz((r || {}).buildNumber) + (t === '--' ? '' : ' · ' + t);
}

/* ===== 弹窗骨架：两个入口共用（失败用例 / 日志证据） ===== */
function openModal(title, html){
  const m = document.getElementById('mrec');
  const t = document.getElementById('mttl');
  const b = document.getElementById('mbody');
  if (!m || !b) return;
  if (t) t.innerHTML = title;
  b.innerHTML = html;
  m.classList.add('on');
  m.scrollTop = 0;
}
function closeModal(){
  const m = document.getElementById('mrec');
  if (m) m.classList.remove('on');
}

/* ===== 用例列「共 N 条失败用例」→ 弹窗逐条给出用例详情 =====
   数据源 = 该行执行记录（pipeline.json 的 records[N]）的 cases[]（测试报告 failedCases）：
   name / state / beginTime / endTime / description（报告里的断言原文）/ localLog（归档的用例 HTML）。
   一条记录一行后，这里只列这一次构建的失败用例，不再跨构建合并。
   这里只做「有哪些用例失败、失败在哪一步」，日志原文行在「证据」弹窗里看。 */
function openCases(i){
  const r = RECS[i] || {};
  const cases = (r.cases || []).filter(function(c){ return c && c.name; });
  if (!cases.length) return;
  const base = r.__base || '';
  const rows = cases.map(function(c, k){
    /* 用例日志：优先归档里的本地 HTML（localLog），没有再给 openLiBing 的远程报告地址 */
    const lg = c.localLog ? (base + c.localLog) : (c.logUrl || '');
    const lgCell = lg
      ? '<a href="' + rfEsc(lg) + '" target="_blank" rel="noopener">用例日志</a>'
      : '<span class="dim">--</span>';
    return '<tr>'
      + '<td class="expr-txt"><span class="dim">' + (k + 1) + '</span> ' + rfEsc(nz(c.name)) + '</td>'
      + '<td class="nowrap">' + statusTag(c.state) + '</td>'
      + '<td class="cw1 dim">' + rfEsc(nz(c.beginTime)) + '</td>'
      + '<td class="cw1 dim">' + rfEsc(nz(c.endTime)) + '</td>'
      + '<td class="expr-txt">' + rfEsc(nz(c.description)) + '</td>'
      + '<td class="nowrap">' + lgCell + '</td>'
      + '</tr>';
  }).join('');
  openModal('失败用例（' + cases.length + ' 条）｜' + rfEsc(buildTag(r))
      + ' · ' + rfEsc(nz(r.pipeline)),
    '<div class="mtbl"><table class="rca"><colgroup><col style="width:21%"><col style="width:7%">'
    + '<col style="width:13%"><col style="width:13%"><col style="width:39%"><col style="width:7%"></colgroup>'
    + '<thead><tr><th>用例</th><th>状态</th><th>开始时间</th><th>结束时间</th>'
    + '<th>失败详情（测试报告断言原文）</th><th>日志</th></tr></thead>'
    + '<tbody>' + rows + '</tbody></table></div>'
    + '<div class="mrec-note">用例清单取自测试报告 failedCases（本次构建共 '
    + cases.length + ' 条全部失败用例），失败详情按原文完整输出、不做截断；'
    + '「用例日志」打开归档里的该用例 HTML 报告。日志原始错误行见「错误信息」列的「证据」。</div>');
}

/* ===== 错误信息列「证据」→ 弹窗逐行输出日志证据（时间 / 级别 / 位置 / 整行原文） =====
   行级信息（time / level / loc / line / 原文）直接从归档记录里取，不再堆在单元格里，
   单元格只留「证据」两个字。证据只取这一行对应的那一次构建，且只做「整行完全一致」的去重。 */
function openEvidence(i){
  const r = RECS[i] || {};
  const evs = evidenceRows(r);
  if (!evs.length) return;
  const rows = evs.map(function(x){
    /* 位置：log 行给 line（L3340），用例内错误给 loc:line（plugin.py:999:3340） */
    const loc = x.loc
      ? rfEsc(x.loc).replace(/\n/g, '<br>') + (x.line == null ? '' : ':' + rfEsc(x.line))
      : (x.line == null ? '<span class="dim">--</span>' : 'L' + rfEsc(x.line));
    const who = [nz(x.task), x.case || ''].filter(function(s){ return s && s !== '--'; }).join(' / ');
    const lv = (x.level && x.level !== '--') ? rfEsc(x.level) : '<span class="dim">--</span>';
    return '<tr>'
      + '<td class="cw1">' + (x.time ? rfEsc(x.time) : '<span class="dim">--</span>') + '</td>'
      + '<td class="cw">' + lv + '</td>'
      + '<td class="cw dim">' + rfEsc(who || '--') + '</td>'
      + '<td class="cw dim">' + loc + '</td>'
      + '<td class="expr-txt">' + rfEsc(nz(x.text)) + '</td>'
      + '</tr>';
  }).join('');
  openModal('日志证据（' + evs.length + ' 行）｜' + rfEsc(buildTag(r))
      + ' · ' + rfEsc(nz(r.pipeline)),
    '<div class="mtbl"><table class="rca"><colgroup><col style="width:14%"><col style="width:8%">'
    + '<col style="width:20%"><col style="width:14%"><col style="width:44%"></colgroup>'
    + '<thead><tr><th>时间</th><th>级别</th><th>任务 / 用例</th><th>位置</th>'
    + '<th>证据原文（整行，不截断）</th></tr></thead>'
    + '<tbody>' + rows + '</tbody></table></div>'
    + '<div class="mrec-note">'
    + '证据全部取自本次构建的归档原文（用例级 errorMessages 与 job 日志行），'
    + '只去掉整行完全一致的重复行：时间或行号不同就各自保留（那是同一条消息在不同时刻/不同行的发生）。'
    + '行级错误行每任务最多 8 条（首尾各取一半，尾部通常是致命行），用例级消息每用例最多 3 条，'
    + 'pytest 汇总行不计入（它只列失败用例名、不含原因）。'
    + '用例级证据取自测试报告 errorMessages（自带时间与位置）；'
    + 'job 日志证据的源行本就带时间戳，已抽到「时间」列；没有时间戳的「测试报告」断言显示 --。'
    + '需要完整原文时按「位置」列的文件名:行号取同一归档目录的 pipeline.evidence.json'
      + '（证据原文已逐行内嵌，路径与行号跟「位置」列完全一致）。</div>');
}

/* 弹窗入口（记录明细页已下线，点构建号直接跳 openLiBing）：
   data-cases       → 根因表「共 N 条失败用例」→ 该次构建的失败用例详情
   data-evidence    → 根因表「证据」→ 该次构建的日志证据逐行
   data-exp-row     → 根因表主行 → 展开 / 收起该行的根因分析与修复建议全文
   注意：data-cases / data-evidence 的取值是「记录下标」（RECS[i]）——
   表格已拆成一条构建一行，不再有聚合行 */
/* 展开 / 收起：根因/建议已经从列里搬进紧跟主行的那条 rc-det 行（colspan 撑满全列），
   这里只切 hidden，不重排内容；同时把末列的大三角在 ▸ / ▾ 之间换一下 */
function toggleExp(i){
  const det = document.querySelector('tr.rc-det[data-exp-of="' + i + '"]');
  const main = document.querySelector('tr.rc-main[data-exp-row="' + i + '"]');
  if (!det) return;
  const open = det.hasAttribute('hidden');
  if (open) det.removeAttribute('hidden'); else det.setAttribute('hidden', '');
  const ic = main && main.querySelector('.exp-ic');
  if (ic) ic.textContent = open ? '▾' : '▸';
}
document.addEventListener('click', function(ev){
  const el = (ev.target && ev.target.closest)
    ? ev.target.closest('[data-cases],[data-evidence],[data-exp-row],[data-execpipes],[data-plruns],.exp-ic,#mclose,#mrec')
    : null;
  if (!el) return;
  if (el.id === 'mclose'){ closeModal(); return; }
  if (el.id === 'mrec' && ev.target === el){ closeModal(); return; }
  if (el.hasAttribute('data-execpipes')){ ev.preventDefault(); openExecByPipe(); return; }
  if (el.hasAttribute('data-plruns')){
    ev.preventDefault();
    const g = EXEC_GROUPS[Number(el.getAttribute('data-plruns'))];
    if (!g) return;
    const ctx = CTX || {};
    openModal2('执行记录（' + g.runs.length + ' 次运行）｜' + rfEsc(g.pl),
      runsTable(g.runs, ctx.from || '', ctx.to || ''));
    return;
  }
  if (el.hasAttribute('data-cases')){ ev.preventDefault(); openCases(Number(el.getAttribute('data-cases'))); return; }
  if (el.hasAttribute('data-evidence')){ ev.preventDefault(); openEvidence(Number(el.getAttribute('data-evidence'))); return; }
  if (ev.target.closest('.exp-ic') || el.hasAttribute('data-exp-row')){
    /* 主行内的构建号链接 / 共 N 条失败用例 / 证据 各有自己的动作，不抢它们的点击 */
    if (ev.target.closest('a,.lnk')) return;
    ev.preventDefault();
    const row = ev.target.closest('tr.rc-main[data-exp-row]');
    if (row){ toggleExp(row.getAttribute('data-exp-row')); }
  }
});
document.addEventListener('keydown', function(ev){ if (ev.key === 'Escape') closeModal(); });

boot();

