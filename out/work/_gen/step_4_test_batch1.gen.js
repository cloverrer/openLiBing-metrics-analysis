(async () => {
const PARAMS = {"items": [{"key": "MindIE|MindIE-Motor", "pipeline": "MindIE-Motor", "pipelineName": "Nightly-CI-Component-pipeline_MindIE-Motor", "projectId": 300036, "pipelineId": "d05b26dfc2e5450e8fff23ddf4cd0eb6", "rid": "1bb96b73e8214e53ae7b1420a47ec8d3", "rn": 140, "st": "11-20 07:04", "jobId": "33d75f88994f4d078b73c33a086fd503", "jobName": "Test_MindIE-Motor_4", "stepIds": ["8ca5679a156747749b5a661302733707"], "steps": [{"id": "8ca5679a156747749b5a661302733707", "name": "Test_MindIE-Motor_4", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "1c31c41b0f994cbfb98a9db6141d54a9", "jobIdParam": "625b66a91012495893e65632a1c01f6b"}], "jobErrMsg": "步骤Test_MindIE-Motor_4执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "99c36f2e0ce24c75a9677beddabf7939", "route": "test", "isBuild": false, "buildJobId": "625b66a91012495893e65632a1c01f6b"}, {"key": "MindSpeed|DrivingSDK_master", "pipeline": "DrivingSDK_master", "pipelineName": "Nightly-CI-Component-pipeline_DrivingSDK_master", "projectId": 300091, "pipelineId": "0260b812efd04b0ebf649f3a4c533996", "rid": "d0a3c7422b1349209aaee5d64f70aa53", "rn": 81, "st": "11-20 11:46", "jobId": "6d4e881a58af4c6c952d86619d8027be", "jobName": "Test_Pytest-smoke-DrivingSDK", "stepIds": ["ac447b884bef44b787126c08c606a68a"], "steps": [{"id": "ac447b884bef44b787126c08c606a68a", "name": "Test_Pytest-smoke-DrivingSDK", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "f90cd8c5d2694076912d313d691aec24", "jobIdParam": "fcc3e0c77752426d808df2c1925c1d07"}], "jobErrMsg": "步骤Test_Pytest-smoke-DrivingSDK执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "4a08ec84d4874d3ba836349e547cc5af", "route": "test", "isBuild": false, "buildJobId": "fcc3e0c77752426d808df2c1925c1d07"}, {"key": "Triton_Ascend|Ascend", "pipeline": "Ascend", "pipelineName": "Nightly-CI-Version-pipeline_Triton_Ascend", "projectId": 300130, "pipelineId": "9a4886d40e544cecb7da63c9597490a6", "rid": "ef5f434b29ea4a949069d5c68c51e281", "rn": 138, "st": "11-20 17:00", "jobId": "abe88b93e3584c999d1965495b208dc0", "jobName": "Test_Triton_Ascend", "stepIds": ["2213a861848e4d9ca0610f9ffb6b8746"], "steps": [{"id": "2213a861848e4d9ca0610f9ffb6b8746", "name": "Test_Triton_Ascend", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "79d12bf2920b4343be2a173f708af7be", "jobIdParam": "48c3b7763886441dafd7fdcb5550116f"}], "jobErrMsg": "步骤Test_Triton_Ascend执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "ba41c584440f4a3ba4c5524f130a5f0d", "route": "test", "isBuild": false, "buildJobId": "48c3b7763886441dafd7fdcb5550116f"}], "pageSize": 100, "delay": 250, "conc": 4, "maxTry": 3, "retryBackoffMs": [1000, 2000]};
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