(async () => {
const PARAMS = {"items": [{"key": "MindStudio|msprof", "pipeline": "msprof", "pipelineName": "Nightly-CI-Component-pipeline_msprof", "projectId": 300037, "pipelineId": "6cf1bab4d4444a2b836c7b106901af49", "rid": "10d7c5c6736348949a656389dcbc8adf", "rn": 280, "st": "11-19 11:50", "jobId": "e31f29a24e1b4b5a8de3587796c0b464", "jobName": " docker-mindstudio-msprof-a2-aarch64-nightly", "stepIds": ["3f0a84cb397248d0b0612a27696093c3"], "steps": [{"id": "3f0a84cb397248d0b0612a27696093c3", "name": " docker-mindstudio-msprof-a2-aarch64-nightly", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "4d000c76d280453788f135ec7abeb52f", "jobIdParam": "1c5e0d3ec0d94b288d12ef08fa68b089"}], "jobErrMsg": "步骤 docker-mindstudio-msprof-a2-aarch64-nightly执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "fc373f8a80684a96b191803e41adcadb", "route": "log", "isBuild": false, "buildJobId": "1c5e0d3ec0d94b288d12ef08fa68b089"}, {"key": "MindStudio|msprof", "pipeline": "msprof", "pipelineName": "Nightly-CI-Component-pipeline_msprof", "projectId": 300037, "pipelineId": "6cf1bab4d4444a2b836c7b106901af49", "rid": "10d7c5c6736348949a656389dcbc8adf", "rn": 280, "st": "11-19 11:50", "jobId": "ecb84d2ba4464a2b9ee4af8e8dc5c5af", "jobName": " docker-mindstudio-msprof-a3-aarch64-nightly", "stepIds": ["8717355b913148b9a369882989e01737"], "steps": [{"id": "8717355b913148b9a369882989e01737", "name": " docker-mindstudio-msprof-a3-aarch64-nightly", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "96438a6e1dc74c5e8ce13299c29236bf", "jobIdParam": "95b3d17e0d17423f87a6c66f825e0217"}], "jobErrMsg": "步骤 docker-mindstudio-msprof-a3-aarch64-nightly执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "fe02a367969847d599f34544584883fc", "route": "log", "isBuild": false, "buildJobId": "95b3d17e0d17423f87a6c66f825e0217"}, {"key": "MindStudio|msprof", "pipeline": "msprof", "pipelineName": "Nightly-CI-Component-pipeline_msprof", "projectId": 300037, "pipelineId": "6cf1bab4d4444a2b836c7b106901af49", "rid": "10d7c5c6736348949a656389dcbc8adf", "rn": 280, "st": "11-19 11:50", "jobId": "8ea73094f20a4ccab7c2b1ea04101c41", "jobName": "Test_msprof_smoke_large_model", "stepIds": ["49589afac3804d0a89a4c7492ed4e82d"], "steps": [{"id": "49589afac3804d0a89a4c7492ed4e82d", "name": "Test_msprof_smoke_large_model", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "ec768cf94625464baa6ef342e6d572ed", "jobIdParam": "d1808247dd8844799de2e3c74beb7455"}], "jobErrMsg": "步骤Test_msprof_smoke_large_model执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "5f3d08acf98b496f906aebcc74406710", "route": "log", "fallback": true, "fallbackReason": "empty"}, {"key": "MindStudio|msprof", "pipeline": "msprof", "pipelineName": "Nightly-CI-Component-pipeline_msprof", "projectId": 300037, "pipelineId": "6cf1bab4d4444a2b836c7b106901af49", "rid": "6099f67d2d1f42548c33f8734618c711", "rn": 279, "st": "11-19 04:00", "jobId": "ca957e1bfa664f76abd059d99ca2c3ab", "jobName": "Test_msprof_smoke", "stepIds": ["4cbba7a328af486a919e762944a688cc"], "steps": [{"id": "4cbba7a328af486a919e762944a688cc", "name": "Test_msprof_smoke", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "1c0c2c905c48473abe8fe0d8e6f1c158", "jobIdParam": "d1808247dd8844799de2e3c74beb7455"}], "jobErrMsg": "步骤Test_msprof_smoke执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "91230b9ae31442059b4e1c80dc63523f", "route": "log", "fallback": true, "fallbackReason": "empty"}], "delay": 250, "conc": 4, "pollTimeoutMs": 180000, "maxTry": 3, "retryBackoffMs": [1000, 2000]};
return (async () => {
  const csrf = (document.cookie.split('; ').find(c => c.startsWith('csrf-token-open-li-bing=')) || '').split('=').slice(1).join('=');
  if (!csrf) return JSON.stringify({ ok: false, error: 'NOT_LOGGED_IN' });
  const H = { 'Content-Type': 'application/json', 'Csrf-Token-Open-Li-Bing': csrf };
  const CICD = '/gateway/openlibing-cicd';
  const FW = '/gateway/openlibing-framework';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const results = [];
  const pending = [];
  const CONC = Math.max(1, PARAMS.conc || 1);
  // 重试口径与其余模板一致：空响应体 / 解析失败 / code!=200 重试，最多 MAX_TRY 次。
  const MAX_TRY = Math.max(1, Number(PARAMS.maxTry) || 3);
  const BACKOFF = (Array.isArray(PARAMS.retryBackoffMs) && PARAMS.retryBackoffMs.length)
    ? PARAMS.retryBackoffMs : [1000, 2000];
  async function fetchJson(url, opts) {
    let lastErr = null;
    for (let t = 1; t <= MAX_TRY; t++) {
      try {
        const res = await fetch(url, opts);
        const text = (await res.text()) || '';
        if (!text.trim()) throw new Error('EMPTY_BODY（http ' + res.status + '）');
        let j;
        try { j = JSON.parse(text); } catch (e) {
          throw new Error('JSON_PARSE_FAIL: ' + String(e && e.message || e));
        }
        if (j.code !== undefined && j.code !== 200) {
          throw new Error(j.messageCn || j.msg || ('code=' + j.code));
        }
        return j;
      } catch (e) {
        lastErr = e;
        if (t < MAX_TRY) {
          await sleep(Number(BACKOFF[Math.min(t - 1, BACKOFF.length - 1)]) || 1000);
        }
      }
    }
    throw lastErr;
  }

  // 阶段 1：创建导出任务（整 job 全量日志，同一 job 多个失败 step 共用一份）；按 CONC 分组并发
  async function createOne(it) {
    const body = {
      projectId: it.projectId, pipelineId: it.pipelineId, pipelineRunId: it.rid,
      jobRunId: it.jobId, stepRunId: it.stepIds[0], taskName: it.jobName
    };
    const ldi = (it.steps && it.steps[0] && it.steps[0].lastDispatchId) || it.jobLastDispatchId;
    if (ldi) body.lastDispatchId = ldi;
    try {
      const j = await fetchJson(CICD + '/project/pipeline/exec-log/export', {
        method: 'POST', headers: H, body: JSON.stringify(body)
      });
      if (j.data) {
        pending.push({ it, exportId: String(j.data) });
      } else {
        results.push({ ...it, export: 'failed', reason: 'create: ' + JSON.stringify(j).slice(0, 200) });
      }
    } catch (e) {
      results.push({ ...it, export: 'failed', reason: 'create: ' + String(e && e.message || e) + '（已重试 ' + MAX_TRY + ' 次）' });
    }
  }
  for (let i = 0; i < PARAMS.items.length; i += CONC) {
    await Promise.all(PARAMS.items.slice(i, i + CONC).map(createOne));
    if (i + CONC < PARAMS.items.length) await sleep(PARAMS.delay);
  }

  // 阶段 2：轮询导出任务状态（data.message「导出文件生成中」继续 /「导出成功」取直链 / 其它判失败）；
  // 每轮对所有未完成项并发查询
  async function checkOne(p) {
    let j = null;
    try {
      j = await fetchJson(FW + '/export/detail?id=' + encodeURIComponent(p.exportId),
                          { headers: { 'Csrf-Token-Open-Li-Bing': csrf } });
    } catch (e) { /* 网络抖动，下一轮再查 */ }
    if (!j) return;
    const d = j.data || {};
    const msg = String(d.message || d.msg || '');
    if (msg.indexOf('导出成功') >= 0) {
      p.done = true;
      try {
        const j2 = await fetchJson(FW + '/export/download-url?id=' + encodeURIComponent(p.exportId),
                                  { headers: { 'Csrf-Token-Open-Li-Bing': csrf } });
        if (j2 && j2.data) {
          results.push({ ...p.it, export: 'ok', exportId: p.exportId, url: String(j2.data) });
        } else {
          results.push({ ...p.it, export: 'failed', reason: 'download-url 空: ' + JSON.stringify(j2).slice(0, 150) });
        }
      } catch (e) {
        results.push({ ...p.it, export: 'failed', reason: 'download-url: ' + String(e && e.message || e) });
      }
    } else if (msg && msg.indexOf('生成中') < 0) {
      p.done = true;
      results.push({ ...p.it, export: 'failed', reason: 'detail: ' + msg.slice(0, 150) });
    }
  }
  const deadline = Date.now() + PARAMS.pollTimeoutMs;
  while (pending.some(p => !p.done) && Date.now() < deadline) {
    await Promise.all(pending.filter(p => !p.done).map(checkOne));
    if (pending.some(p => !p.done)) await sleep(2000);
  }
  for (const p of pending) if (!p.done) results.push({ ...p.it, export: 'timeout', reason: '轮询超时' });

  return JSON.stringify({ ok: true, created: results.filter(r => r.export === 'ok').length, results });
})()

})()