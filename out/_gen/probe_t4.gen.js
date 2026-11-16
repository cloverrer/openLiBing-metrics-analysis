(async () => {
  const csrf = (document.cookie.split('; ').find(c => c.startsWith('csrf-token-open-li-bing=')) || '').split('=').slice(1).join('=');
  if (!csrf) return JSON.stringify({ ok: false, error: 'NOT_LOGGED_IN' });
  const G = '/gateway/openlibing-cicd';
  async function probe(pid) {
    try {
      const res = await fetch(G + '/project/pipeline/pipeline-run/detail?projectId=' + pid + '&pipelineId=d05b26dfc2e5450e8fff23ddf4cd0eb6&pipelineRunId=c5a424f5e96646668648f056869831c1', {
        headers: { 'Csrf-Token-Open-Li-Bing': csrf }
      });
      const txt = await res.text();
      let j = null;
      try { j = JSON.parse(txt); } catch (e) {}
      const stages = (j && j.data && j.data.stages) || [];
      const jobs = [];
      stages.forEach(st => (st.jobs || []).forEach(jb => {
        if (jb.status && jb.status !== 'COMPLETED') jobs.push(jb.name + ':' + jb.status);
      }));
      return 'pid=' + pid + ' http=' + res.status + ' len=' + txt.length + ' code=' + (j && j.code) + ' stages=' + stages.length + ' badJobs=[' + jobs.join(', ') + ']';
    } catch (e) { return 'pid=' + pid + ' ERR ' + String(e && e.message || e); }
  }
  const r1 = await probe(300036);
  const r2 = await probe(300037);
  return JSON.stringify({ ok: true, p300036: r1, p300037: r2 });
})()
