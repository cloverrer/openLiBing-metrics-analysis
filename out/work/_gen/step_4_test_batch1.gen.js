(async () => {
const PARAMS = {"items": [{"key": "MindStudio|msprof", "pipeline": "msprof", "pipelineName": "Nightly-CI-Component-pipeline_msprof", "projectId": 300037, "pipelineId": "6cf1bab4d4444a2b836c7b106901af49", "rid": "f6a8025929fc49b9ab6afb2fc55e7ca7", "rn": 281, "st": "11-19 14:11", "jobId": "53b5cbb170844e238ecfc33f38c095d5", "jobName": "Test_msprof_smoke_A3_large_model", "stepIds": ["7598cc92ae884b14a988bdb6af0e61a4"], "steps": [{"id": "7598cc92ae884b14a988bdb6af0e61a4", "name": "Test_msprof_smoke_A3_large_model", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "162ed6c0c9ce4a0eb2d257d5f26fb513", "jobIdParam": "ab62b54077964cfbbf5fb83cfcfaaefd"}], "jobErrMsg": "步骤Test_msprof_smoke_A3_large_model执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "f43ae7ddf377440b868a8a51e06429e1", "route": "test", "isBuild": false, "buildJobId": "ab62b54077964cfbbf5fb83cfcfaaefd"}, {"key": "MindStudio|msprof", "pipeline": "msprof", "pipelineName": "Nightly-CI-Component-pipeline_msprof", "projectId": 300037, "pipelineId": "6cf1bab4d4444a2b836c7b106901af49", "rid": "10d7c5c6736348949a656389dcbc8adf", "rn": 280, "st": "11-19 11:50", "jobId": "8ea73094f20a4ccab7c2b1ea04101c41", "jobName": "Test_msprof_smoke_large_model", "stepIds": ["49589afac3804d0a89a4c7492ed4e82d"], "steps": [{"id": "49589afac3804d0a89a4c7492ed4e82d", "name": "Test_msprof_smoke_large_model", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "ec768cf94625464baa6ef342e6d572ed", "jobIdParam": "d1808247dd8844799de2e3c74beb7455"}], "jobErrMsg": "步骤Test_msprof_smoke_large_model执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "5f3d08acf98b496f906aebcc74406710", "route": "test", "isBuild": false, "buildJobId": "d1808247dd8844799de2e3c74beb7455"}, {"key": "MindStudio|msprof", "pipeline": "msprof", "pipelineName": "Nightly-CI-Component-pipeline_msprof", "projectId": 300037, "pipelineId": "6cf1bab4d4444a2b836c7b106901af49", "rid": "6099f67d2d1f42548c33f8734618c711", "rn": 279, "st": "11-19 04:00", "jobId": "ca957e1bfa664f76abd059d99ca2c3ab", "jobName": "Test_msprof_smoke", "stepIds": ["4cbba7a328af486a919e762944a688cc"], "steps": [{"id": "4cbba7a328af486a919e762944a688cc", "name": "Test_msprof_smoke", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "1c0c2c905c48473abe8fe0d8e6f1c158", "jobIdParam": "d1808247dd8844799de2e3c74beb7455"}], "jobErrMsg": "步骤Test_msprof_smoke执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "91230b9ae31442059b4e1c80dc63523f", "route": "test", "isBuild": false, "buildJobId": "d1808247dd8844799de2e3c74beb7455"}, {"key": "MindStudio|msprof", "pipeline": "msprof", "pipelineName": "Nightly-CI-Component-pipeline_msprof", "projectId": 300037, "pipelineId": "6cf1bab4d4444a2b836c7b106901af49", "rid": "6099f67d2d1f42548c33f8734618c711", "rn": 279, "st": "11-19 04:00", "jobId": "1edebbb82ddc4698b0b13ce38aee1ae1", "jobName": "Test_msprof_smoke_A3", "stepIds": ["3d4eb644e9234e5a86ea8698da8fec68"], "steps": [{"id": "3d4eb644e9234e5a86ea8698da8fec68", "name": "Test_msprof_smoke_A3", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "ad5c4f052dd44ed6b535fa1a0fc4f673", "jobIdParam": "ab62b54077964cfbbf5fb83cfcfaaefd"}], "jobErrMsg": "步骤Test_msprof_smoke_A3执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "f47f4c9061d04c78ad5045832d689a32", "route": "test", "isBuild": false, "buildJobId": "ab62b54077964cfbbf5fb83cfcfaaefd"}], "pageSize": 100, "delay": 250, "conc": 4, "maxTry": 3, "retryBackoffMs": [1000, 2000]};
return (async () => {
  const csrf = (document.cookie.split('; ').find(c => c.startsWith('csrf-token-open-li-bing=')) || '').split('=').slice(1).join('=');
  if (!csrf) return JSON.stringify({ ok: false, error: 'NOT_LOGGED_IN' });
  const H = { 'Content-Type': 'application/json', 'Csrf-Token-Open-Li-Bing': csrf };
  const G = '/gateway/openlibing-cicd';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const results = [], errors = [];
  const CONC = Math.max(1, PARAMS.conc || 1);
  // 重试口径与 step_2/step_1 一致：空响应体 / 解析失败 / code!=200 重试，最多 MAX_TRY 次。
  // T6 测试报告接口同样偶发空响应体，不重试会静默漏失败用例，根因结论只剩任务级封装码。
  const MAX_TRY = Math.max(1, Number(PARAMS.maxTry) || 3);
  const BACKOFF = (Array.isArray(PARAMS.retryBackoffMs) && PARAMS.retryBackoffMs.length)
    ? PARAMS.retryBackoffMs : [1000, 2000];
  async function fetchOnce(it) {
    const res = await fetch(G + '/project/pipeline/test-report', {
      method: 'POST', headers: H,
      body: JSON.stringify({
        projectId: it.projectId, pipelineId: it.pipelineId, pipelineRunId: it.rid,
        stepRunIds: it.stepIds.join(','), name: '', number: '',
        state: ['failed'], pageNumber: 1, pageSize: PARAMS.pageSize
      })
    });
    const text = (await res.text()) || '';
    if (!text.trim()) throw new Error('EMPTY_BODY：响应体为空（http ' + res.status + '）');
    let j;
    try { j = JSON.parse(text); } catch (e) {
      throw new Error('JSON_PARSE_FAIL: ' + String(e && e.message || e));
    }
    if (j.code !== 200) throw new Error(j.messageCn || j.msg || ('code=' + j.code));
    const d = j.data || {};
    const list = d.list || d.items || d.taskResults || [];
    const cases = (Array.isArray(list) ? list : []).map(c => ({
      name: c.name, number: c.number, state: c.state, description: c.description,
      beginTime: c.beginTime, endTime: c.endTime,
      resultDownloadUrl: c.resultDownloadUrl, envDownloadUrl: c.envDownloadUrl
    }));
    results.push({
      route: 'test', key: it.key, pipeline: it.pipeline, pipelineName: it.pipelineName,
      rn: it.rn, st: it.st,
      projectId: it.projectId, pipelineId: it.pipelineId, rid: it.rid,
      jobId: it.jobId, jobName: it.jobName, stepIds: it.stepIds,
      steps: it.steps || [], jobErrMsg: it.jobErrMsg || null,
      jobLastDispatchId: it.jobLastDispatchId || null,
      code: j.code,
      summary: { total: d.totalCount ?? d.total, passed: d.passedCount, failed: d.failedCount, passRate: d.passRate },
      failedCases: cases,
      empty: cases.length === 0
    });
  }
  async function fetchOne(it) {
    let lastErr = null;
    for (let t = 1; t <= MAX_TRY; t++) {
      try { await fetchOnce(it); return; }
      catch (e) { lastErr = e; }
      if (t < MAX_TRY) {
        await sleep(Number(BACKOFF[Math.min(t - 1, BACKOFF.length - 1)]) || 1000);
      }
    }
    errors.push({ key: it.key, rn: it.rn, jobName: it.jobName,
                  err: String(lastErr && lastErr.message || lastErr) + '（已重试 ' + MAX_TRY + ' 次）' });
  }
  for (let i = 0; i < PARAMS.items.length; i += CONC) {
    await Promise.all(PARAMS.items.slice(i, i + CONC).map(fetchOne));
    if (i + CONC < PARAMS.items.length) await sleep(PARAMS.delay);
  }
  return JSON.stringify({ ok: true, collected: results.length, results, errors });
})()

})()