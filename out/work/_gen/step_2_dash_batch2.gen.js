(async () => {
const PARAMS = {"startDate": "2026-11-19", "endDate": "2026-11-19", "pageSize": 100, "delay": 250, "conc": 4, "maxTry": 3, "retryBackoffMs": [1000, 2000], "pipelines": [{"key": "MindCluster|MindCluster", "projectId": 300038, "pipelineId": "576d7d060dc24749951e0b3abd6a5dcc"}, {"key": "MindCluster|RecSDK", "projectId": 300038, "pipelineId": "610d7853be5a4efa9096ddead93a2d4f"}, {"key": "MindCluster|AgentSDK", "projectId": 300038, "pipelineId": "9f864a61fe8b4268b592e5e2b38f859a"}, {"key": "MindCluster|MultimodalSDK", "projectId": 300038, "pipelineId": "c39c0146a8b2492db59ec77bedb7170c"}, {"key": "Ascend-CANN|os", "projectId": 300057, "pipelineId": "03da2691669a4f2bbfcfd89356bc3576"}, {"key": "boostkit|avx2ki", "projectId": 300059, "pipelineId": "2944ce957b494b72a41150b5467b61b4"}, {"key": "boostkit|kqmalloc", "projectId": 300059, "pipelineId": "452bb706ced24726aa7686b92a966734"}, {"key": "boostkit|OmniStream", "projectId": 300059, "pipelineId": "636f9465b49d4a6591d5572ad6f9456f"}, {"key": "boostkit|Megascan", "projectId": 300059, "pipelineId": "9485ce9d987d4717a944aa3932474391"}, {"key": "boostkit|Bigdata", "projectId": 300059, "pipelineId": "a74a64d931f34c98bc726e5ea599f8a3"}, {"key": "boostkit|KTAG", "projectId": 300059, "pipelineId": "a8c3dbdd3feb4c4ab4a4a336e1323ce3"}, {"key": "boostkit|Ultrascan", "projectId": 300059, "pipelineId": "b0040d6ccaae48b5b623931d34db5d24"}, {"key": "boostkit|KAE", "projectId": 300059, "pipelineId": "eaf0862dd3f84fc2b51862830d7fe19e"}, {"key": "HPCKit|kudnn", "projectId": 300073, "pipelineId": "ca83efb8c37648db8084e31b1e88b62c"}, {"key": "HPCKit|kupl", "projectId": 300073, "pipelineId": "ddb211b1e4a74f55a0e604fa95ef469e"}]};
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