(async () => {
const PARAMS = {"runs": [{"key": "MindStudio|msprobe", "rn": 265, "st": "11-13 00:00", "status": "FAILED", "cached": false, "track": "va", "dims": ["va"], "projectId": 300037, "pipelineId": "9de3361a26304f96a7ac8ebf571d0b57", "pipelineRunId": "bcee0cc2247645dca50aedc9f287211a"}, {"key": "MindStudio|msprobe", "rn": 266, "st": "11-13 14:48", "status": "CANCELED", "cached": false, "track": "va", "dims": ["va"], "projectId": 300037, "pipelineId": "9de3361a26304f96a7ac8ebf571d0b57", "pipelineRunId": "591f04b63f8b499b8a0c903f92f93e4c"}, {"key": "MindStudio|msserviceprofiler", "rn": 249, "st": "11-13 04:00", "status": "CANCELED", "cached": false, "track": "va", "dims": ["va"], "projectId": 300037, "pipelineId": "af61355154f54c85adac46449f506edc", "pipelineRunId": "5efc2b3253af4258bf1f65a5f0b99e20"}, {"key": "MindStudio|msot", "rn": 271, "st": "11-13 06:00", "status": "CANCELED", "cached": false, "track": "va", "dims": ["va"], "projectId": 300037, "pipelineId": "b67d335347fa4646acd3b96d1c55573e", "pipelineRunId": "3a6a297ccab244ca9024c17c0e65ea96"}, {"key": "Ascend-CANN|ops-cv", "rn": 177, "st": "11-13 01:05", "status": "FAILED", "cached": false, "track": "bs", "dims": ["bs"], "projectId": 300057, "pipelineId": "66b8958d6e0349ddb01143765c64afa5", "pipelineRunId": "2a25d50ec5fc4a1999a58d4e5bd13794"}, {"key": "Ascend-CANN|shmem", "rn": 152, "st": "11-13 17:00", "status": "FAILED", "cached": false, "track": "bs", "dims": ["bs"], "projectId": 300057, "pipelineId": "93831fdaa3234c8a9dd0b8a0c220f939", "pipelineRunId": "fda84ce8496847528d2bd240021175be"}, {"key": "Ascend-CANN|ops-math", "rn": 143, "st": "11-12 02:05", "status": "FAILED", "cached": false, "track": "va", "dims": ["va", "bs"], "projectId": 300057, "pipelineId": "aa3d520fe64f4071a09178d2d603278e", "pipelineRunId": "727649f778a44fbea40e080401a8245e"}, {"key": "Ascend-CANN|ops-math", "rn": 144, "st": "11-13 02:05", "status": "FAILED", "cached": false, "track": "va", "dims": ["va", "bs"], "projectId": 300057, "pipelineId": "aa3d520fe64f4071a09178d2d603278e", "pipelineRunId": "fc745eecf4934f7a85aad6e89ea252db"}, {"key": "Ascend-CANN|ops-math", "rn": 145, "st": "11-13 16:30", "status": "FAILED", "cached": false, "track": "va", "dims": ["va", "bs"], "projectId": 300057, "pipelineId": "aa3d520fe64f4071a09178d2d603278e", "pipelineRunId": "3afd5d1c652d489fbfb71996f75e09c0"}], "delay": 250, "conc": 4, "retry": 2, "backoffMs": 2000};
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