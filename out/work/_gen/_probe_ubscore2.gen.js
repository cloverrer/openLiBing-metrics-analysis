(async () => {
  const csrf = (document.cookie.split('; ').find(c => c.startsWith('csrf-token-open-li-bing=')) || '').split('=').slice(1).join('=');
  if (!csrf) return JSON.stringify({ ok: false, error: 'NOT_LOGGED_IN' });
  const H = { 'Content-Type': 'application/json', 'Csrf-Token-Open-Li-Bing': csrf };
  const out = {};
  try {
    const res = await fetch('/gateway/openlibing-cicd/project/pipeline/pipeline-run/detail?projectId=300122&pipelineId=b51d159e1b9d4c6798dcda723e1876db&pipelineRunId=8afd6c81382a451aad1649f31cd8d47b');
    const j = JSON.parse((await res.text()) || '{}');
    const d = j.data || {};
    out.t4 = { code: j.code, msg: j.messageCn || j.msg,
      keys: Object.keys(d),
      stages: (d.stages || d.steps || []).map(s => ({ name: s.name || s.stepName || s.displayName, status: s.status,
        jobs: (s.jobs || s.tasks || []).length })),
      rawHead: JSON.stringify(d).slice(0, 1500) };
  } catch (e) { out.t4 = { error: String(e) }; }

  try {
    const res = await fetch('/gateway/openlibing-ops/manage/common/detail', { method: 'POST', headers: H,
      body: JSON.stringify({ category: 'nightly-dashboard-detail', projectId: 300122,
        pipelineId: 'b51d159e1b9d4c6798dcda723e1876db', startDate: '2026-11-10', endDate: '2026-11-13', page: 1, pageSize: 100 }) });
    const j = JSON.parse((await res.text()) || '{}');
    out.n2 = { code: j.code, total: j.data && j.data.total,
      rows: ((j.data && j.data.records) || []).map(r => ({ rn: r.pipelineRunNumber, id: r.pipelineRunId, st: r.pipelineStatus,
        end: r.pipelineRunEndtime, iva: r.isVersionAvailable, bc: r.buildCount, bpc: r.buildPassCount, ftt: r.failedTaskType, cpr: r.casePassRate })) };
  } catch (e) { out.n2 = { error: String(e) }; }

  return JSON.stringify({ ok: true, out });
})()
