(async () => {
const PARAMS = {"startDate": "2026-11-17", "endDate": "2026-11-17", "pageSize": 100, "delay": 250, "conc": 4, "maxTry": 3, "retryBackoffMs": [1000, 2000], "pipelines": [{"key": "openUBMC|openUBMC~c43117", "projectId": 2, "pipelineId": "da4f9f2c5686451594d2dd1a0b843824"}, {"key": "AscendForPyTorch|master", "projectId": 4, "pipelineId": "c5fb1178a82e4121bd7033824630a47f"}, {"key": "MindIE|MindIE-SD", "projectId": 300036, "pipelineId": "921e6a7215ec4bf3972bbe13e9e41bb6"}, {"key": "MindIE|MindIE-Motor", "projectId": 300036, "pipelineId": "d05b26dfc2e5450e8fff23ddf4cd0eb6"}, {"key": "MindStudio|msprof", "projectId": 300037, "pipelineId": "6cf1bab4d4444a2b836c7b106901af49"}, {"key": "MindStudio|msprobe", "projectId": 300037, "pipelineId": "9de3361a26304f96a7ac8ebf571d0b57"}, {"key": "MindStudio|msserviceprofiler", "projectId": 300037, "pipelineId": "af61355154f54c85adac46449f506edc"}, {"key": "MindStudio|msmemscope", "projectId": 300037, "pipelineId": "b4bf5a6de15549c59ce223fe03922413"}, {"key": "MindStudio|msot", "projectId": 300037, "pipelineId": "b67d335347fa4646acd3b96d1c55573e"}, {"key": "MindStudio|msmodelslim", "projectId": 300037, "pipelineId": "b9948b4f145e4063a094356af192513c"}, {"key": "MindCluster|IndexSDK", "projectId": 300038, "pipelineId": "12313bdcc9bb435bb8755eb51548157a"}, {"key": "MindCluster|Agentsdk~5992cb", "projectId": 300038, "pipelineId": "3920b07ff31c48d8aaddbae6f4db072d"}, {"key": "MindCluster|ascend-deployer", "projectId": 300038, "pipelineId": "3bf413db452e4b2d8e26dd521bc9b78b"}, {"key": "MindCluster|MindCluster", "projectId": 300038, "pipelineId": "576d7d060dc24749951e0b3abd6a5dcc"}, {"key": "MindCluster|RecSDK", "projectId": 300038, "pipelineId": "610d7853be5a4efa9096ddead93a2d4f"}]};
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