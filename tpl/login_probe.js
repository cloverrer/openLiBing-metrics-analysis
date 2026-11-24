(async () => {
  // openLiBing 登录态自检：不看页面长相，只看受保护接口的真实返回。
  // 判定口径与第 1 步取数完全一致（同一接口 / 同一 csrf 头），所以「自检通过」=「第 1 步能取到数」。
  // 注意: csrf-token-open-li-bing cookie 在未登录时也可能存在，不能单独作为登录依据。
  const csrf = (document.cookie.split('; ').find(c => c.startsWith('csrf-token-open-li-bing=')) || '').split('=').slice(1).join('=');
  const H = { 'Content-Type': 'application/json' };
  if (csrf) H['Csrf-Token-Open-Li-Bing'] = csrf;

  const d = new Date(); d.setDate(d.getDate() - 1);
  const p2 = n => String(n).padStart(2, '0');
  const day = d.getFullYear() + '-' + p2(d.getMonth() + 1) + '-' + p2(d.getDate());

  let http = null, code = null, msg = '', sample = '';
  try {
    const res = await fetch('/gateway/openlibing-ops/manage/ops-overview/main', {
      method: 'POST', headers: H, credentials: 'include',
      body: JSON.stringify({ startDate: day, endDate: day, page: 1, pageSize: 1 })
    });
    http = res.status;
    const body = await res.text();
    sample = String(body).slice(0, 200);
    try { const j = JSON.parse(body); code = j.code; msg = j.msg || j.message || ''; } catch (e) { msg = 'body 非 JSON（多半被重定向到登录页）'; }
  } catch (e) {
    msg = String(e);
  }

  const txt = el => ((el && (el.innerText || el.textContent)) || '').trim();
  const hasLoginBtn = [...document.querySelectorAll('button')]
    .some(b => /^登\s*录$|^立即登录$/.test(txt(b)) && b.getBoundingClientRect().width > 0);
  let clickedAt = null;
  try { clickedAt = sessionStorage.getItem('rcaAutoLoginClicked'); } catch (e) {}

  // 供登录引导判断下一步：还在登录页就主动导航到业务页；跳到 GitCode 登录页就得人工介入。
  const title = document.title || '';
  const onGitcode = /(^|\.)gitcode\.(com|s2\.udesk\.cn)/i.test(location.hostname);
  const bodyText = txt(document.body).slice(0, 3000);
  const hasQr = /扫码|二维码|手机.*(验证码|登录)|请输入密码|password/i.test(bodyText);
  const onLoginPage = hasLoginBtn || /login|登录/i.test(title) && !/eCDashboard/i.test(location.href);

  return {
    ok: true,
    loggedIn: code === 200,
    http: http, code: code, msg: msg,
    csrf: !!csrf, hasLoginBtn: hasLoginBtn, clickedAt: clickedAt,
    title: title, onGitcode: onGitcode, hasQr: hasQr, onLoginPage: onLoginPage,
    url: location.href, sample: sample
  };
})()
