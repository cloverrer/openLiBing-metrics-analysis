(async () => {
  const csrf = (document.cookie.split('; ').find(c => c.startsWith('csrf-token-open-li-bing=')) || '').split('=').slice(1).join('=');
  if (!csrf) return JSON.stringify({ ok: false, error: 'NOT_LOGGED_IN' });
  const H = { 'Content-Type': 'application/json', 'Csrf-Token-Open-Li-Bing': csrf };
  const G = '/gateway/openlibing-cicd';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const results = [], errors = [];
  const CONC = Math.max(1, PARAMS.conc || 1);
  // 重试口径与 step_2/step_4 一致：空响应体 / 解析失败 / code!=200 重试，最多 MAX_TRY 次。
  // T5 日志接口同样偶发空响应体，不重试会让失败任务整条无日志，根因只剩封装码。
  const MAX_TRY = Math.max(1, Number(PARAMS.maxTry) || 3);
  const BACKOFF = (Array.isArray(PARAMS.retryBackoffMs) && PARAMS.retryBackoffMs.length)
    ? PARAMS.retryBackoffMs : [1000, 2000];
  async function fetchOnce(it) {
    const res = await fetch(G + '/project/pipeline/logs', {
      method: 'POST', headers: H,
      body: JSON.stringify({
        projectId: it.projectId, pipelineId: it.pipelineId, pipelineRunId: it.rid,
        jobRunId: it.jobId, stepRunId: it.stepIds[0],
        sort: 'desc', limit: PARAMS.logLimit, startOffset: 0, endOffset: 0
      })
    });
    const text = (await res.text()) || '';
    if (!text.trim()) {
      if (res.status === 401 || res.status === 403) throw new Error('NOT_LOGGED_IN：登录态已失效（HTTP ' + res.status + '，空响应体），请在调试 Chrome 重新登录 openLiBing');
      throw new Error('EMPTY_BODY：响应体为空（http ' + res.status + '）');
    }
    let j;
    try { j = JSON.parse(text); } catch (e) {
      throw new Error('JSON_PARSE_FAIL: ' + String(e && e.message || e));
    }
    if (j.code !== 200) throw new Error(j.messageCn || j.msg || ('code=' + j.code));
    const d = j.data || {};
    const logText = d.log || '';
    const errLines = logText.split('\n').filter(l => /\[ERROR\]|\[FAIL|ERROR|FAIL|失败/i.test(l)).slice(0, PARAMS.maxErrLines);
    results.push({
      route: 'log', key: it.key, pipeline: it.pipeline, rn: it.rn, st: it.st,
      projectId: it.projectId, pipelineId: it.pipelineId, rid: it.rid,
      jobId: it.jobId, jobName: it.jobName, stepId: it.stepIds[0],
      fallback: !!it.fallback,
      code: j.code, has_more: d.has_more,
      logTail: logText.slice(-4000),
      errorLines: errLines
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
