(async () => {
  const csrf = (document.cookie.split('; ').find(c => c.startsWith('csrf-token-open-li-bing=')) || '').split('=').slice(1).join('=');
  if (!csrf) return JSON.stringify({ ok: false, error: 'NOT_LOGGED_IN' });
  const out = [];
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const base = '/gateway/openlibing-cicd/project/pipeline/pipeline-run/detail';

  async function tryCall(name, P) {
    try {
      const res = await fetch(base + '?projectId=' + P.projectId + '&pipelineId=' + P.pipelineId + '&pipelineRunId=' + P.pipelineRunId,
        { headers: { 'Csrf-Token-Open-Li-Bing': csrf } });
      const text = await res.text();
      let j = null;
      try { j = JSON.parse(text); } catch (e) {}
      const hasStages = !!(j && j.data && j.data.stages);
      // 收集失败 job 的关键信息
      let jobs = [];
      if (hasStages) {
        j.data.stages.forEach(st => {
          (st.jobs || []).forEach(job => {
            if (job.status && job.status !== 'COMPLETED' && job.status !== 'UNSELECTED' && job.status !== 'INIT' && job.status !== 'IGNORED') {
              jobs.push({ name: job.name, status: job.status, id: job.id, msg: (job.message || '').slice(0, 120) });
            }
          });
        });
      }
      out.push({ name: name, status: res.status, len: text.length, code: j && j.code,
                 hasStages: hasStages, badJobs: jobs });
    } catch (e) {
      out.push({ name: name, err: String(e && e.message || e) });
    }
  }

  // 抽样不同流水线的失败运行
  await tryCall('MindIE-Motor#117', { projectId: '300036', pipelineId: 'd05b26dfc2e5450e8fff23ddf4cd0eb6', pipelineRunId: 'c5a424f5e96646668648f056869831c1' });
  await sleep(800);
  await tryCall('MindStudio-msot#261', { projectId: '300037', pipelineId: 'b67d335347fa4646acd3b96d1c55573e', pipelineRunId: 'e509275186da4ee38affa7c15dfb2ecc' });

  return JSON.stringify({ ok: true, probes: out });
})()
