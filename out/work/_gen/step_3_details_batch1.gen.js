(async () => {
const PARAMS = {"runs": [{"key": "MindStudio|msprof", "rn": 279, "st": "11-19 04:00", "status": "FAILED", "cached": false, "track": "va", "dims": ["va"], "projectId": 300037, "pipelineId": "6cf1bab4d4444a2b836c7b106901af49", "pipelineRunId": "6099f67d2d1f42548c33f8734618c711"}, {"key": "MindStudio|msprof", "rn": 280, "st": "11-19 11:50", "status": "FAILED", "cached": false, "track": "va", "dims": ["va"], "projectId": 300037, "pipelineId": "6cf1bab4d4444a2b836c7b106901af49", "pipelineRunId": "10d7c5c6736348949a656389dcbc8adf"}, {"key": "MindStudio|msprof", "rn": 281, "st": "11-19 14:11", "status": "CANCELED", "cached": false, "track": "va", "dims": ["va"], "projectId": 300037, "pipelineId": "6cf1bab4d4444a2b836c7b106901af49", "pipelineRunId": "f6a8025929fc49b9ab6afb2fc55e7ca7"}, {"key": "MindSpeed|DrivingSDK_master~089fff", "rn": 2, "st": "11-19 02:00", "status": "FAILED", "cached": false, "track": "va", "dims": ["va", "bs"], "projectId": 300091, "pipelineId": "6ae97566bb274346a7786b07268595ce", "pipelineRunId": "123c30bc598f4c4482a3126210a15970"}, {"key": "MindSpeed|DrivingSDK_master~089fff", "rn": 3, "st": "11-19 09:26", "status": "FAILED", "cached": false, "track": "va", "dims": ["va", "bs"], "projectId": 300091, "pipelineId": "6ae97566bb274346a7786b07268595ce", "pipelineRunId": "3480185e9405475caac4c80cd576d6ab"}, {"key": "MindSpeed|DrivingSDK_master~089fff", "rn": 4, "st": "11-19 15:02", "status": "FAILED", "cached": false, "track": "va", "dims": ["va", "bs"], "projectId": 300091, "pipelineId": "6ae97566bb274346a7786b07268595ce", "pipelineRunId": "88e4fa7f11ef4e3590184db98a9bd1da"}, {"key": "MindSpeed|MindSpeed-A3_master~49873f", "rn": 3, "st": "11-19 11:17", "status": "CANCELED", "cached": false, "track": "bs", "dims": ["bs"], "projectId": 300091, "pipelineId": "f9b23dc845054e8b913875f5dbc76427", "pipelineRunId": "f62392c52d384cc3a6336727c6ba3851"}], "delay": 250, "conc": 4, "retry": 2, "backoffMs": 2000};
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