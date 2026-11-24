(async () => {
const PARAMS = {"runs": [{"key": "MindIE|MindIE-SD", "rn": 126, "st": "11-23 01:01", "status": "FAILED", "cached": false, "track": "va", "dims": ["va", "bs"], "projectId": 300036, "pipelineId": "921e6a7215ec4bf3972bbe13e9e41bb6", "pipelineRunId": "2c00dab76ae74116b79b7fa2353042b1"}, {"key": "MindStudio|msprof", "rn": 286, "st": "11-23 04:00", "status": "FAILED", "cached": false, "track": "va", "dims": ["va"], "projectId": 300037, "pipelineId": "6cf1bab4d4444a2b836c7b106901af49", "pipelineRunId": "4b840e62ed5b4c1cb4d077ff4a3aabda"}, {"key": "MindStudio|msprobe", "rn": 277, "st": "11-23 00:00", "status": "FAILED", "cached": false, "track": "va", "dims": ["va"], "projectId": 300037, "pipelineId": "9de3361a26304f96a7ac8ebf571d0b57", "pipelineRunId": "a6fe285ce1fb43fa8262ef1ba3e9fb6c"}, {"key": "MindStudio|msserviceprofiler", "rn": 259, "st": "11-23 04:00", "status": "CANCELED", "cached": false, "track": "va", "dims": ["va"], "projectId": 300037, "pipelineId": "af61355154f54c85adac46449f506edc", "pipelineRunId": "b8f860bfc0354751b8bcbf2d2a6bfeb0"}, {"key": "MindStudio|msmemscope", "rn": 275, "st": "11-23 00:00", "status": "FAILED", "cached": false, "track": "va", "dims": ["va"], "projectId": 300037, "pipelineId": "b4bf5a6de15549c59ce223fe03922413", "pipelineRunId": "5b7498855f8046bd9798a7a6f1181261"}, {"key": "MindStudio|msmodelslim", "rn": 280, "st": "11-23 06:00", "status": "FAILED", "cached": false, "track": "va", "dims": ["va"], "projectId": 300037, "pipelineId": "b9948b4f145e4063a094356af192513c", "pipelineRunId": "73dc7784a1fc4fa7bf9d0a7d94e74a37"}, {"key": "Triton_Ascend|Ascend", "rn": 144, "st": "11-23 17:00", "status": "FAILED", "cached": false, "track": "bs", "dims": ["bs"], "projectId": 300130, "pipelineId": "9a4886d40e544cecb7da63c9597490a6", "pipelineRunId": "fed7e370aa9e4b2ebf577049505b3aef"}], "delay": 250, "conc": 4, "retry": 2, "backoffMs": 2000};
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