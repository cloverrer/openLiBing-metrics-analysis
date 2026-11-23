(async () => {
const PARAMS = {"runs": [{"key": "UBS Core|Nightly-CI-Version-pipeline_BeiMing", "rn": 270, "st": "2026-11-20 00:00:19", "status": "FAILED", "track": "va", "dims": ["bs"], "projectId": "300122", "pipelineId": "b51d159e1b9d4c6798dcda723e1876db", "pipelineRunId": "d0dd1ada45d643488a9e0af2d613fc02"}], "delay": 250, "conc": 4, "retry": 2, "backoffMs": 2000};
return (async () => {
  const csrf = (document.cookie.split('; ').find(c => c.startsWith('csrf-token-open-li-bing=')) || '').split('=').slice(1).join('=');
  if (!csrf) return JSON.stringify({ ok: false, error: 'NOT_LOGGED_IN' });
  const G = '/gateway/openlibing-cicd';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const out = [];
  const CONC = Math.max(1, PARAMS.conc || 1);
  const RETRY = Math.max(0, PARAMS.retry || 0);
  // T4 详情响应偶发被网关截断（Unexpected end of JSON input）：
  // 失败原样重试整个请求，最多 RETRY 次，每次间隔 backoffMs
  async function fetchOnce(r) {
    const res = await fetch(G + '/project/pipeline/pipeline-run/detail?projectId=' + r.projectId + '&pipelineId=' + r.pipelineId + '&pipelineRunId=' + r.pipelineRunId, {
      headers: { 'Csrf-Token-Open-Li-Bing': csrf }
    });
    const txt = await res.text();
    try {
      const j = JSON.parse(txt);
      if (j.code !== 200 || !j.data) throw new Error('code=' + j.code + ' len=' + txt.length);
      // 任务图谱为空 = 没拿到失败任务（截断/未生成），对下游同样不可用，按失败处理走重试
      if (!(j.data.stages || []).length) throw new Error('stages 空 len=' + txt.length);
      out.push({ key: r.key, rn: r.rn, st: r.st, rstatus: r.status, rid: r.pipelineRunId, track: r.track, dims: r.dims, code: j.code, data: j.data });
      return true;
    } catch (e) {
      out.push({ key: r.key, rn: r.rn, st: r.st, rstatus: r.status, rid: r.pipelineRunId, err: String(e && e.message || e), body: txt.slice(0, 200) });
      return false;
    }
  }
  async function fetchOne(r) {
    for (let attempt = 0; attempt <= RETRY; attempt++) {
      if (await fetchOnce(r)) return;
      // 只重试真正失败的那条：把刚 push 的错误项弹出来重抓，成功即终止
      const bad = out[out.length - 1];
      if (bad && bad.rid === r.pipelineRunId && bad.err) out.pop();
      if (attempt < RETRY) await sleep(PARAMS.backoffMs || 1500);
    }
    out.push({ key: r.key, rn: r.rn, st: r.st, rstatus: r.status, rid: r.pipelineRunId, err: 'T4 重试 ' + RETRY + ' 次后仍失败' });
  }
  for (let i = 0; i < PARAMS.runs.length; i += CONC) {
    await Promise.all(PARAMS.runs.slice(i, i + CONC).map(fetchOne));
    if (i + CONC < PARAMS.runs.length) await sleep(PARAMS.delay);
  }
  return JSON.stringify({ ok: true, details: out });
})()


})()