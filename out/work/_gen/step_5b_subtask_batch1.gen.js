(async () => {
const PARAMS = {"items": [{"key": "MindStudio|msprobe", "pipeline": "msprobe", "pipelineName": "Nightly-CI-Component-pipeline_msprobe", "projectId": 300037, "pipelineId": "9de3361a26304f96a7ac8ebf571d0b57", "rid": "bcee0cc2247645dca50aedc9f287211a", "rn": 265, "st": "11-13 00:00", "jobId": "b3f93f623f4743f2b7d4de018cad0308", "jobName": "docker-mindstudio-msprobe-a2-aarch64-nightly", "stepIds": ["da25478c8024481384e2f442421a39da"], "steps": [{"id": "da25478c8024481384e2f442421a39da", "name": "docker-mindstudio-msprobe-a2-aarch64-nightly", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "e92f92889a0a4d82851034aa9f9ff660", "jobIdParam": "fba9a61669b34b36be7cdab4b0df3fdb"}], "jobErrMsg": "步骤docker-mindstudio-msprobe-a2-aarch64-nightly执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "c9cf9d871f1741649a4113df8e2f06b1", "route": "log", "isBuild": false, "buildJobId": "fba9a61669b34b36be7cdab4b0df3fdb"}, {"key": "MindStudio|msprobe", "pipeline": "msprobe", "pipelineName": "Nightly-CI-Component-pipeline_msprobe", "projectId": 300037, "pipelineId": "9de3361a26304f96a7ac8ebf571d0b57", "rid": "bcee0cc2247645dca50aedc9f287211a", "rn": 265, "st": "11-13 00:00", "jobId": "504628fad3d34ea493b77b688300b63f", "jobName": " docker-mindstudio-msprobe-a3-aarch64-nightly", "stepIds": ["d5128252259346f3b2ba861457b2ae07"], "steps": [{"id": "d5128252259346f3b2ba861457b2ae07", "name": " docker-mindstudio-msprobe-a3-aarch64-nightly", "status": "FAILED", "errMsg": "{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "lastDispatchId": "32c408bb165e49b581f13246555a5c62", "jobIdParam": "2d97861093b14de196eea09b0ddd9980"}], "jobErrMsg": "步骤 docker-mindstudio-msprobe-a3-aarch64-nightly执行失败，错误信息：{\"errorMessage\":\" 构建任务执行失败!\",\"errorCode\":\"DEV-CODECI-35002\"}", "jobLastDispatchId": "dafccb557825410d8a2320e49a6514b2", "route": "log", "isBuild": false, "buildJobId": "2d97861093b14de196eea09b0ddd9980"}], "delay": 250, "conc": 4, "pollTimeoutMs": 180000, "maxTry": 3, "retryBackoffMs": [1000, 2000]};
return (async () => {
  const csrf = (document.cookie.split('; ').find(c => c.startsWith('csrf-token-open-li-bing=')) || '').split('=').slice(1).join('=');
  if (!csrf) return JSON.stringify({ ok: false, error: 'NOT_LOGGED_IN' });
  const H = { 'Content-Type': 'application/json', 'Csrf-Token-Open-Li-Bing': csrf };
  const G = { 'Csrf-Token-Open-Li-Bing': csrf };
  const CICD = '/gateway/openlibing-cicd';
  const FW = '/gateway/openlibing-framework';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const results = [];
  const drill = [];
  const CONC = Math.max(1, PARAMS.conc || 1);
  // 重试口径与其余模板一致：空响应体 / 解析失败 / code!=200 重试，最多 MAX_TRY 次。
  // T7 flow/子任务日志接口同样偶发空响应体，不重试会让 Build 子任务证据整块缺失。
  const MAX_TRY = Math.max(1, Number(PARAMS.maxTry) || 3);
  const BACKOFF = (Array.isArray(PARAMS.retryBackoffMs) && PARAMS.retryBackoffMs.length)
    ? PARAMS.retryBackoffMs : [1000, 2000];
  async function pAll(arr, fn) {
    for (let i = 0; i < arr.length; i += CONC) {
      await Promise.all(arr.slice(i, i + CONC).map(fn));
      if (i + CONC < arr.length) await sleep(PARAMS.delay);
    }
  }
  async function fetchJson(url, opts) {
    // 统一带重试的 JSON 请求：空响应体/解析失败/code!=200 都抛错由调用方重试
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

  // 阶段 1：逐 log 任务调 flow 接口拉构建子任务列表（buildflow 任务才有 builds；普通流水线返回空列表）
  async function flowOne(it) {
    const qs = 'projectId=' + it.projectId + '&pipelineId=' + it.pipelineId
      + '&pipelineRunId=' + it.rid + '&stepRunIds=' + it.stepIds.join(',');
    const row = { key: it.key, pipeline: it.pipeline, rn: it.rn, rid: it.rid,
                  jobId: it.jobId, jobName: it.jobName,
                  flow: 'failed', reason: '', builds: [] };
    try {
      const j = await fetchJson(CICD + '/project/pipeline/flow?' + qs, { headers: G });
      if (Array.isArray(j.data)) {
        row.flow = 'ok';
        for (const ent of j.data) {
          for (const b of ent.builds || []) {
            row.builds.push({ buildJobId: b.id, name: b.display_name, buildNo: String(b.build_no),
                              status: b.status, durationMs: b.build_duration,
                              startTime: b.start_time, finishTime: b.finish_time,
                              stepRunId: ent.step_run_id });
          }
        }
      } else {
        row.reason = 'flow: data 非数组 ' + JSON.stringify(j).slice(0, 120);
      }
    } catch (e) { row.reason = 'flow: ' + String(e && e.message || e) + '（已重试 ' + MAX_TRY + ' 次）'; }
    if (row.flow === 'ok' && row.builds.some(b => b.status === 'FAILURE')) {
      drill.push({ it, failed: row.builds.filter(b => b.status === 'FAILURE') });
    }
    results.push(row);
  }
  await pAll(PARAMS.items, flowOne);

  // 阶段 2：失败子任务逐个创建 build-log/export 导出任务
  // jobId 用 T4 失败步骤 inputs 里 key=jobId 的构建 jobId（buildflow 调度任务专属），
  // buildNo 来自 flow builds[]；flow 的 builds[].id 仅用于 obs-product，此处不可用
  const pending = [];
  async function createOne(d) {
    for (const b of d.failed) {
      const sp = (d.it.steps || []).find(s => s.id === b.stepRunId);
      const jid = (sp && sp.jobIdParam) || d.it.buildJobId || null;
      if (!jid) {
        pending.push({ it: d.it, b, state: 'failed',
                       reason: '缺 buildJobId（T4 step inputs.key=jobId），无法下钻子任务日志' });
        continue;
      }
      const body = { projectId: d.it.projectId, jobId: jid, buildNo: b.buildNo,
                     stepRunId: b.stepRunId, pipelineId: d.it.pipelineId,
                     pipelineRunId: d.it.rid, taskName: d.it.jobName };
      try {
        const j = await fetchJson(CICD + '/project/pipeline/build-log/export', {
          method: 'POST', headers: H, body: JSON.stringify(body) });
        if (j.data) {
          pending.push({ it: d.it, b, state: 'pending', exportId: String(j.data) });
        } else {
          pending.push({ it: d.it, b, state: 'failed', reason: 'create: ' + JSON.stringify(j).slice(0, 160) });
        }
      } catch (e) {
        pending.push({ it: d.it, b, state: 'failed', reason: 'create: ' + String(e && e.message || e) + '（已重试 ' + MAX_TRY + ' 次）' });
      }
    }
  }
  await pAll(drill, createOne);

  // 阶段 3：轮询导出任务（「导出成功」取 OBS 直链；「生成中」继续；其它判失败）；
  // 每轮对所有未完成项并发查询
  async function checkOne(p) {
    if (p.state !== 'pending') return;
    let j = null;
    try {
      j = await fetchJson(FW + '/export/detail?id=' + encodeURIComponent(p.exportId), { headers: G });
    } catch (e) { /* 网络抖动，下一轮再查 */ }
    if (!j) return;
    const d = j.data || {};
    const msg = String(d.message || d.msg || '');
    if (msg.indexOf('导出成功') >= 0) {
      try {
        const j2 = await fetchJson(FW + '/export/download-url?id=' + encodeURIComponent(p.exportId), { headers: G });
        if (j2 && j2.data) { p.state = 'ok'; p.url = String(j2.data); }
        else { p.state = 'failed'; p.reason = 'download-url 空: ' + JSON.stringify(j2).slice(0, 120); }
      } catch (e) { p.state = 'failed'; p.reason = 'download-url: ' + String(e && e.message || e); }
    } else if (msg && msg.indexOf('生成中') < 0) {
      p.state = 'failed'; p.reason = 'detail: ' + msg.slice(0, 120);
    }
  }
  const deadline = Date.now() + PARAMS.pollTimeoutMs;
  while (pending.some(p => p.state === 'pending') && Date.now() < deadline) {
    await Promise.all(pending.filter(p => p.state === 'pending').map(checkOne));
    if (pending.some(p => p.state === 'pending')) await sleep(2000);
  }
  for (const p of pending) if (p.state === 'pending') { p.state = 'timeout'; p.reason = '轮询超时'; }

  // 阶段 4：导出失败/超时的子任务走 build/log 分页兜底（sort=DESC 取尾部窗口，标记 truncated）
  async function pageOne(p) {
    if (p.state === 'ok') return;
    const sp = (p.it.steps || []).find(s => s.id === p.b.stepRunId);
    const jid = (sp && sp.jobIdParam) || p.it.buildJobId || null;
    if (!jid) {
      p.paging = 'failed';
      p.reason = (p.reason ? p.reason + '；' : '') + 'build/log: 缺 buildJobId';
      return;
    }
    try {
      const qs = 'projectId=' + p.it.projectId + '&jobId=' + jid + '&buildNo=' + p.b.buildNo
        + '&stepRunId=' + p.b.stepRunId + '&startOffset=0&endOffset=0&sort=DESC'
        + '&pipelineId=' + p.it.pipelineId + '&pipelineRunId=' + p.it.rid;
      const j = await fetchJson(CICD + '/project/pipeline/build/log?' + qs, { headers: G });
      const d = j.data || {};
      let tail = '';
      for (const k of ['log', 'logs', 'logContent', 'content', 'lines', 'result']) {
        if (typeof d[k] === 'string' && d[k]) { tail = d[k]; break; }
      }
      p.paging = tail ? 'ok' : 'failed';
      if (!tail) tail = JSON.stringify(d).slice(0, 400000);
      p.logTail = tail;
      p.hasMore = d.has_more === undefined ? null : !!d.has_more;
      if (p.paging !== 'ok') {
        p.reason = (p.reason ? p.reason + '；' : '') + 'build/log: data 无日志正文';
      }
    } catch (e) {
      p.paging = 'failed';
      p.reason = (p.reason ? p.reason + '；' : '') + 'build/log: ' + String(e && e.message || e) + '（已重试 ' + MAX_TRY + ' 次）';
    }
  }
  await pAll(pending, pageOne);

  const subLogs = pending.map(p => ({
    key: p.it.key, pipeline: p.it.pipeline, rn: p.it.rn, rid: p.it.rid,
    jobId: p.it.jobId, jobName: p.it.jobName,
    subName: p.b.name, buildJobId: p.b.buildJobId, buildNo: p.b.buildNo, stepRunId: p.b.stepRunId,
    export: p.state, exportId: p.exportId || null, url: p.url || null,
    reason: p.reason || null, paging: p.paging || null,
    logTail: p.logTail || null, hasMore: p.hasMore === undefined ? null : p.hasMore,
  }));
  return JSON.stringify({ ok: true, results, subLogs });
})()

})()