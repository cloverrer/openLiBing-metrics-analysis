(async () => {
const PARAMS = {"items": [{"key": "MindIE|MindIE-SD", "pipeline": "MindIE-SD", "pipelineName": "Nightly-CI-Component-pipeline_MindIE-SD", "projectId": 300036, "pipelineId": "921e6a7215ec4bf3972bbe13e9e41bb6", "rid": "5a5a6716983b4f84b5488031000653d7", "rn": 116, "st": "11-18 01:01", "jobId": "43aca12a05ca47a787692cf5c15d169c", "jobName": "Build_MindIE-SD", "stepIds": ["8271aa6d296a467cadbd9b1dd135313f"], "steps": [{"id": "8271aa6d296a467cadbd9b1dd135313f", "name": "Build_MindIE-SD", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "6ca41dfa6b7d4c64b40bc47b5c904bd3", "jobIdParam": "3e2e6a4a47294a80b35e8118eb10423d"}], "jobErrMsg": "步骤Build_MindIE-SD执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "71b9ce23d7de48a3ba31a563ecb8258f", "route": "log", "isBuild": true, "buildJobId": "3e2e6a4a47294a80b35e8118eb10423d"}, {"key": "MindIE|MindIE-Motor", "pipeline": "MindIE-Motor", "pipelineName": "Nightly-CI-Component-pipeline_MindIE-Motor", "projectId": 300036, "pipelineId": "d05b26dfc2e5450e8fff23ddf4cd0eb6", "rid": "9f3772fb2963417d9b1c5b1e36e4d1c0", "rn": 137, "st": "11-18 14:43", "jobId": "0eb5b598b63a42b7859bb8c7b94c149e", "jobName": "Build_MindIE-Motor", "stepIds": ["1bb0e9e8dcd14004a61bc7318e9c31e6"], "steps": [{"id": "1bb0e9e8dcd14004a61bc7318e9c31e6", "name": "Build_MindIE-Motor", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "98155b4d6c7f49a09150d0f519c67a2e", "jobIdParam": "9aaead01b1e94a998e5f0edd788ea1a7"}], "jobErrMsg": "步骤Build_MindIE-Motor执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "0fe0c284a52549c1bb71530b5d4ec654", "route": "log", "isBuild": true, "buildJobId": "9aaead01b1e94a998e5f0edd788ea1a7"}], "delay": 250, "conc": 4, "pollTimeoutMs": 180000, "maxTry": 3, "retryBackoffMs": [1000, 2000]};
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