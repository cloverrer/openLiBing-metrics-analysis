(async () => {
  // 点登录页的主「登录」按钮 = 走 GitCode 单点登录。
  // 浏览器里 GitCode 会话通常仍然有效，所以点完会自动鉴权，无需输入账号密码。
  // 注意：鉴权成功是「cookie 生效」，登录页本身**不一定**会跳转（实测它常停在登录页），
  // 所以这里只负责点击；点完由 auto_login.py 主动导航到业务页再确认登录态。
  // 点击可能立刻触发整页跳转，导致本脚本的返回值丢失（CDP 上下文被销毁），
  // 因此点之前先写一个「已点击」标记，由 login_probe.js 在跳转后读出来做证据。
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const txt = el => ((el && (el.innerText || el.textContent)) || '').trim();
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const hit = () => [...document.querySelectorAll('button,a,[role="button"],div,span')]
    .filter(el => /^登\s*录$|^立即登录$/.test(txt(el)) && vis(el));
  // 优先级：Element Plus 主按钮（真正的提交按钮）> 原生 button > 其它带「登录」文案的可点元素。
  // 页面换实现时按钮可能不再是 <button>，所以选择器不写死标签。
  const pick = () => {
    const cs = hit();
    return cs.find(el => /el-button--primary/.test(String(el.className || '')))
        || cs.find(el => el.tagName === 'BUTTON') || cs[0] || null;
  };

  let b = null;
  for (let i = 0; i < 60 && !b; i++) { b = pick(); if (!b) await sleep(250); }
  if (!b) {
    return { ok: true, clicked: false, reason: '页面上没有可点的「登录」按钮（可能已是登录态，或页面尚未加载完）', url: location.href };
  }
  try { sessionStorage.setItem('rcaAutoLoginClicked', new Date().toISOString()); } catch (e) {}
  const label = txt(b);
  const desc = b.tagName + '.' + String(b.className || '').split(' ')[0];
  b.click();
  await sleep(300);
  return { ok: true, clicked: true, button: label, clickedEl: desc, url: location.href };
})()
