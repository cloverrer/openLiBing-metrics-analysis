(async () => {
const PARAMS = {"startDate": "2026-11-16", "endDate": "2026-11-16", "pageSize": 100, "delay": 250, "conc": 4, "maxTry": 3, "retryBackoffMs": [1000, 2000], "pipelines": [{"key": "HPCKit|kpex", "projectId": 300073, "pipelineId": "fec036d3c59f4d27bb506138f273f113"}, {"key": "HPCKit|hmpi", "projectId": 300073, "pipelineId": "ffe131425ad84d4b8b6c17c4c09476d9"}, {"key": "MindSpeed|DrivingSDK_master", "projectId": 300091, "pipelineId": "0260b812efd04b0ebf649f3a4c533996"}, {"key": "MindSpeed|MindSpeed-MM_master", "projectId": 300091, "pipelineId": "094eb44f70df495783f375641b7143e6"}, {"key": "MindSpeed|MindSpeed-LLM_master", "projectId": 300091, "pipelineId": "b30f40b85cce4153b175379589793abc"}, {"key": "MindSpeed|MindSpeed_master", "projectId": 300091, "pipelineId": "e12bb930ffe84e3b9258f23c41644b58"}, {"key": "MindSpeed|MindSpeed-A3_master", "projectId": 300091, "pipelineId": "e593e0b8911044b69ce9d1be3c19032a"}, {"key": "vllm-ascend|a2.yaml", "projectId": 300127, "pipelineId": "228664975"}, {"key": "vllm-ascend|a3.yaml", "projectId": 300127, "pipelineId": "228664976"}, {"key": "Triton_Ascend|Ascend", "projectId": 300130, "pipelineId": "9a4886d40e544cecb7da63c9597490a6"}, {"key": "SgLang|nightly-test-npu.yml", "projectId": 300134, "pipelineId": "209837578"}]};
return (async () => {
  // 【N2】POST /gateway/openlibing-ops/manage/common/detail  category=nightly-dashboard-detail
  // 返回每流水线逐运行看板明细（即执行记录来源）：pipelineRunNumber/Id/Status/起止时间 +
  // isVersionAvailable / buildCount / buildPassCount / failedTaskType / casePassRate 等，
  // 供 VA 双指标口径判定、双轨道圈定与编译成功率复算；记录超过一页时按 total 翻页拉全
  const csrf = (document.cookie.split('; ').find(c => c.startsWith('csrf-token-open-li-bing=')) || '').split('=').slice(1).join('=');
  if (!csrf) return JSON.stringify({ ok: false, error: 'NOT_LOGGED_IN' });
  const H = { 'Content-Type': 'application/json', 'Csrf-Token-Open-Li-Bing': csrf };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const out = {};
  const CONC = Math.max(1, PARAMS.conc || 1);
  // 重试口径与 step_1（ops-nightly-detail）一致：单次成功 = 响应体非空 + JSON 可解析 +
  // code===200；空响应体 / 解析失败 / code!=200 一律重试，最多 MAX_TRY 次，退避 BACKOFF。
  // 不重试会静默丢运行记录：服务端偶发返回空响应体（Unexpected end of JSON input），
  // 之前 26/49 条流水线整条无执行记录、版本可用度失真（MindStudio 大面积「无运行」）。
  const MAX_TRY = Math.max(1, Number(PARAMS.maxTry) || 3);
  const BACKOFF = (Array.isArray(PARAMS.retryBackoffMs) && PARAMS.retryBackoffMs.length)
    ? PARAMS.retryBackoffMs : [1000, 2000];
  async function fetchPipe(p) {
    const recs = [];
    let page = 1, total = 0, last = null, lastErr = null;
    for (let t = 1; t <= MAX_TRY; t++) {
      try {
        let done = false;
        for (; !done;) {                                      // 成功后连续翻页
          const res = await fetch('/gateway/openlibing-ops/manage/common/detail', {
            method: 'POST', headers: H,
            body: JSON.stringify({ category: 'nightly-dashboard-detail', endDate: PARAMS.endDate,
              page, pageSize: PARAMS.pageSize, pipelineId: p.pipelineId,
              projectId: p.projectId, startDate: PARAMS.startDate })
          });
          const text = (await res.text()) || '';
          if (!text.trim()) { lastErr = 'EMPTY_BODY：响应体为空（http ' + res.status + '）'; break; }
          try { last = JSON.parse(text); } catch (e) {
            lastErr = 'JSON_PARSE_FAIL: ' + String(e && e.message || e); break;
          }
          if (last.code !== 200) { lastErr = last.messageCn || last.msg || ('code=' + last.code); break; }
          const d = (last && last.data) || {};
          const list = d.records || [];
          recs.push(...list);
          total = d.total || recs.length;
          if (!list.length || recs.length >= total) { lastErr = null; done = true; }
          else { page += 1; await sleep(PARAMS.delay); }
        }
      } catch (e) { lastErr = String(e && e.message || e); }
      if (!lastErr) break;                                    // 拉全即出循环，落 out[p.key]
      if (t < MAX_TRY) {                                      // 保留已翻页数据，从当前页重试
        await sleep(Number(BACKOFF[Math.min(t - 1, BACKOFF.length - 1)]) || 1000);
      }
    }
    if (lastErr) out[p.key] = { code: -1, error: lastErr + '（已重试 ' + MAX_TRY + ' 次）' };
    else out[p.key] = Object.assign({}, last, { data: { records: recs, total: total } });
  }
  for (let i = 0; i < PARAMS.pipelines.length; i += CONC) {
    await Promise.all(PARAMS.pipelines.slice(i, i + CONC).map(fetchPipe));
    if (i + CONC < PARAMS.pipelines.length) await sleep(PARAMS.delay);
  }
  return JSON.stringify({ ok: true, dash: out });
})()

})()