(async () => {
  // 把目标标签页导航到业务页。
  // 为什么需要它：实测 GitCode 单点登录成功后 cookie 已生效，但登录页自身**常常不跳转**，
  // 仍停在 ?loginFlag=true（标题还是 login），观感就是"点了没反应"。
  // 这里主动导航一次，既让页面真正进入业务页，也把"登录态确认"做实。
  // 导航会销毁本脚本的上下文，调用方需容忍这个异常（auto_login.py 已处理）。
  const p = (typeof PARAMS !== 'undefined' && PARAMS) || {};
  const url = p.url || 'https://www.openlibing.com/apps/eCDashboard';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  location.href = url;
  await sleep(p.waitMs || 4000);
  return { ok: true, navigatedTo: url, url: location.href, title: document.title };
})()
