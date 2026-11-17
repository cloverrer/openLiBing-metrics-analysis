(async () => {
  const csrf = (document.cookie.split('; ').find(c => c.startsWith('csrf-token-open-li-bing=')) || '').split('=').slice(1).join('=');
  if (!csrf) return JSON.stringify({ ok: false, error: 'NOT_LOGGED_IN' });
  const H = { 'Content-Type': 'application/json', 'Csrf-Token-Open-Li-Bing': csrf };
  async function post(url, body) {
    const res = await fetch(url, { method: 'POST', headers: H, body: JSON.stringify(body) });
    const text = (await res.text()) || '';
    let json = null;
    try { json = JSON.parse(text); } catch (e) { return { code: -2, error: 'PARSE_FAIL', raw: text.slice(0, 400) }; }
    return json;
  }
  const out = {};
  try {
    const t1 = await post('/gateway/openlibing-ops/manage/ops-overview/main', { startDate: '2026-11-10', endDate: '2026-11-13', page: 1, pageSize: 100 });
    out.t1 = { code: t1.code, count: ((t1.data && t1.data.records) || []).length,
      names: ((t1.data && t1.data.records) || []).map(r => ({ n: r.projectName, id: r.projectId })) };
  } catch (e) { out.t1 = { error: String(e) }; }

  try {
    const n1 = await post('/gateway/openlibing-ops/manage/common/detail', { category: 'ops-nightly-detail', projectId: 300122, startDate: '2026-11-10', endDate: '2026-11-13', page: 1, pageSize: 100 });
    out.n1 = { code: n1.code, msg: n1.messageCn || n1.msg, total: n1.data && n1.data.total,
      rows: ((n1.data && n1.data.records) || []).map(r => ({ pid: r.pipelineId, name: r.pipelineName, va: r.versionAvail, bs: r.buildSuccess, pl: r.platform })) };
  } catch (e) { out.n1 = { error: String(e) }; }

  try {
    const n2 = await post('/gateway/openlibing-ops/manage/common/detail', { category: 'nightly-dashboard-detail', projectId: 300122, pipelineId: 'b51d159e1b9d4c6798dcda723e1876db', startDate: '2026-11-10', endDate: '2026-11-13', page: 1, pageSize: 100 });
    out.n2 = { code: n2.code, msg: n2.messageCn || n2.msg, total: n2.data && n2.data.total,
      rows: ((n2.data && n2.data.records) || []).map(r => ({ rn: r.pipelineRunNumber, id: r.pipelineRunId, st: r.pipelineRunStatus,
        start: r.pipelineRunStarttime, end: r.pipelineRunEndtime, iva: r.isVersionAvailable, bc: r.buildCount, bpc: r.buildPassCount,
        ftt: r.failedTaskType, cpr: r.casePassRate, title: r.displayTitle })) };
  } catch (e) { out.n2 = { error: String(e) }; }

  return JSON.stringify({ ok: true, out });
})()
