(async () => {
  const csrf = (document.cookie.split('; ').find(c => c.startsWith('csrf-token-open-li-bing=')) || '').split('=').slice(1).join('=');
  if (!csrf) return JSON.stringify({ ok: false, error: 'NOT_LOGGED_IN' });
  const H = { 'Content-Type': 'application/json', 'Csrf-Token-Open-Li-Bing': csrf };
  const out = {};
  try {
    const res = await fetch('/gateway/openlibing-ops/manage/common/detail', { method: 'POST', headers: H,
      body: JSON.stringify({ category: 'nightly-dashboard-detail', projectId: 300122,
        pipelineId: 'b51d159e1b9d4c6798dcda723e1876db', startDate: '2026-11-10', endDate: '2026-11-13', page: 1, pageSize: 100 }) });
    const j = JSON.parse((await res.text()) || '{}');
    const recs = (j.data && j.data.records) || [];
    out.n2keys = Object.keys(recs[0] || {});
    out.first = recs[0];
    out.total = j.data && j.data.total;
  } catch (e) { out.err = String(e); }
  try {
    const res = await fetch('/gateway/openlibing-ops/manage/common/detail', { method: 'POST', headers: H,
      body: JSON.stringify({ category: 'ops-nightly-detail', projectId: 300122, startDate: '2026-11-10', endDate: '2026-11-13', page: 1, pageSize: 100 }) });
    const j = JSON.parse((await res.text()) || '{}');
    out.opsKeys = Object.keys((j.data && j.data.records && j.data.records[0]) || {});
    out.opsSample = ((j.data && j.data.records) || []).slice(0, 3);
  } catch (e) { out.opsErr = String(e); }
  return JSON.stringify({ ok: true, out });
})()
