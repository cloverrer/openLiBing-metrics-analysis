(async () => {
const PARAMS = {"runs": [{"key": "MindIE|MindIE-Motor", "rn": 140, "st": "11-20 07:04", "status": "FAILED", "cached": false, "track": "va", "dims": ["va", "bs"], "projectId": 300036, "pipelineId": "d05b26dfc2e5450e8fff23ddf4cd0eb6", "pipelineRunId": "1bb96b73e8214e53ae7b1420a47ec8d3"}, {"key": "boostkit|Ultrascan", "rn": 321, "st": "11-20 01:00", "status": "FAILED", "cached": false, "track": "bs", "dims": ["bs"], "projectId": 300059, "pipelineId": "b0040d6ccaae48b5b623931d34db5d24", "pipelineRunId": "f85457a771e8466f930bfaf2bcba21a9"}, {"key": "MindSpeed|DrivingSDK_master", "rn": 81, "st": "11-20 11:46", "status": "FAILED", "cached": false, "track": "va", "dims": ["va"], "projectId": 300091, "pipelineId": "0260b812efd04b0ebf649f3a4c533996", "pipelineRunId": "d0a3c7422b1349209aaee5d64f70aa53"}, {"key": "Triton_Ascend|Ascend", "rn": 138, "st": "11-20 17:00", "status": "FAILED", "cached": false, "track": "bs", "dims": ["bs"], "projectId": 300130, "pipelineId": "9a4886d40e544cecb7da63c9597490a6", "pipelineRunId": "ef5f434b29ea4a949069d5c68c51e281"}], "delay": 250, "conc": 4, "retry": 2, "backoffMs": 2000};
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