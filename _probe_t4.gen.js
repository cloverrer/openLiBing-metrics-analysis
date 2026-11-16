(async () => {
  const csrf = (document.cookie.split('; ').find(c => c.startsWith('csrf-token-open-li-bing=')) || '').split('=').slice(1).join('=');
  if (!csrf) return JSON.stringify({ ok: false, error: 'NOT_LOGGED_IN' });
  const out = [];
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  const P = {
    projectId: '300036', pipelineId: 'd05b26dfc2e5450e8fff23ddf4cd0eb6',
    pipelineRunId: 'c5a424f5e96646668648f056869831c1'
  };
  const base = '/gateway/openlibing-cicd/project/pipeline/pipeline-run/detail';

  async function tryCall(name, url, opts, tries) {
    for (let i = 0; i < (tries || 1); i++) {
      try {
        const res = await fetch(url, Object.assign({ headers: { 'Csrf-Token-Open-Li-Bing': csrf } }, opts));
        const text = await res.text();
        let j = null;
        try { j = JSON.parse(text); } catch (e) {}
        const hasStages = !!(j && j.data && j.data.stages);
        out.push({ name: name + '#' + (i + 1), status: res.status, len: text.length,
                   code: j && j.code, hasStages: hasStages,
                   stageN: hasStages ? j.data.stages.length : null,
                   head: hasStages ? '' : text.slice(0, 200) });
        if (hasStages) return;
        await sleep(1500);
      } catch (e) {
        out.push({ name: name + '#' + (i + 1), err: String(e && e.message || e) });
      }
    }
  }

  // 连续 4 次同参数 GET：看是不是间歇性空响应
  await tryCall('GET-retry', base + '?projectId=' + P.projectId + '&pipelineId=' + P.pipelineId + '&pipelineRunId=' + P.pipelineRunId, {}, 4);

  return JSON.stringify({ ok: true, probes: out });
})()
