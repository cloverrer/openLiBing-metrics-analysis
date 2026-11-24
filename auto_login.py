# -*- coding: utf-8 -*-
"""openLiBing 登录态自检 / 自动 GitCode 登录（无人值守跑数前置步骤）。

背景: 第 1~5c 步都是通过 CDP 在真实 Chrome 里跑页面脚本取数，靠的是浏览器里
openLiBing 的登录态。登录态会过期；过期后取数会直接报 NOT_LOGGED_IN，凌晨定时
任务就会失败。openLiBing 用的是 GitCode 单点登录，而浏览器里 GitCode 的会话通常
仍然有效，所以只要在登录页点一下「登录」，就会静默完成鉴权，不需要账号密码。

判定口径（与第 1 步取数一致，不看页面长相）:
  POST /gateway/openlibing-ops/manage/ops-overview/main →
  {"code": 200, "data": {"records": [...]}} 视为已登录；其余（401/重定向到登录页/
  非 JSON）视为未登录。注意 csrf-token-open-li-bing cookie 在未登录时也可能存在，
  不能单独当登录依据。

流程（三处都是踩过的坑，改动前先看）:
  1) 自检 → 已登录就直接退出，不多开页、不点按钮。
  2) 未登录则开一个登录页标签页，**记下返回的标签页 id**，后续点击/导航都按 id 精确定位。
     原来用"URL 里带唯一标记"定位，但登录后 SPA 会把查询参数抹掉，标记随之消失 →
     node 侧找不到标签页就静默新开一个页，探针于是跑在新页上，判定看似成功实则碰巧。
  3) 点「登录」→ 探测（探测固定用 tab=openlibing：登录 cookie 按 profile 共享，
     任一 openlibing 页都能验证，所以不需要盯着某个特定页）。
  4) 仍未登录且这一页还在登录页 → **主动导航到业务页**再确认。实测鉴权成功后登录页
     自己常不跳转，只靠等是等不来的（用户观感就是"点了没反应"）。
  5) 若已跳到 GitCode 登录页/出现扫码密码框 → 说明 GitCode 会话也过期了，停下并
     保留页面提示人工处理，不空转重试。
  收尾：关掉本次自动打开的标签页（避免历史遗留的登录页越堆越多）；需要人工介入时保留。

用法:
  python auto_login.py                  # 自检；未登录则点「登录」自动补登录
  python auto_login.py --clicks 1       # 最多点几次登录（默认 2）
  python auto_login.py --keep           # 保留本次打开的标签页（排障用）
  python auto_login.py --port 9222      # 指定调试端口（默认取 config.chrome.debug_port）

退出码: 0=已登录（可直接跑 run_pipeline.py）；1=登录失败（需人工扫码/输密码）
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from lib.browser import ensure_browser  # noqa: E402
from lib.cdp_exec import load_config, run_page_js  # noqa: E402

LOGIN_PAGE = "https://www.openlibing.com/?loginFlag=true"
DEFAULT_DASHBOARD = "https://www.openlibing.com/apps/eCDashboard"
WAIT_TAB_S = 25            # 等新标签页出现
WAIT_AFTER_CLICK_S = 40    # 点完登录后等鉴权完成
WAIT_AFTER_GOTO_S = 25     # 主动导航到业务页后等加载 + 鉴权
POLL_S = 3


def log(msg):
    print("[登录] %s" % msg, flush=True)


def _http_json(url, method="GET", timeout=5):
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def _targets(port):
    try:
        return _http_json("http://127.0.0.1:%d/json/list" % port)
    except Exception:
        return []


def _open_tab(port, url):
    """开一个新标签页（Chrome 的 /json/new 必须用 PUT），返回含 id 的标签页信息。"""
    return _http_json("http://127.0.0.1:%d/json/new?%s"
                      % (port, urllib.parse.quote(url, safe="")), method="PUT")


def _tab_by_id(port, tid):
    for t in _targets(port):
        if str(t.get("id") or "") == tid and t.get("type") == "page":
            return t
    return None


def _close_tab(port, tid):
    try:
        return _http_json("http://127.0.0.1:%d/json/close/%s" % (port, tid))
    except Exception:
        return None


def _cfg_with(cfg, tab=None, target=None):
    """复制一份 cfg，覆盖标签页定位方式。

    走的是 run_page_js 既有的 config 读取路径（chrome.tab_url_substring / chrome.target_id），
    这样 lib/cdp_exec.py 的公开签名保持原样，不需要为自动登录改它的调用方。
    target 优先：按标签页 id 定位，页面跳转、改 URL 都不影响。
    """
    if not tab and not target:
        return cfg
    out = dict(cfg)
    out["chrome"] = dict(cfg.get("chrome") or {})
    if target:
        out["chrome"]["target_id"] = str(target)
    elif tab:
        out["chrome"]["tab_url_substring"] = str(tab)
    return out


def probe(cfg, tab=None, target=None):
    """登录态探测。都不给时用默认标签页（config.chrome.tab_url_substring）。

    注意: run_page_js 的落盘根目录是 out/work/，out_name 不能再带目录前缀。
    """
    return run_page_js("login_probe.js", {}, "auto_login_probe.json",
                       _cfg_with(cfg, tab, target), label="登录自检")


def probe_safe(cfg, tab=None, target=None):
    try:
        return probe(cfg, tab, target)
    except RuntimeError as exc:
        return {"loggedIn": False, "msg": str(exc)[:200]}


def click_login(cfg, target):
    """点登录页的「登录」按钮。整页跳转会销毁脚本上下文，这里的异常视为「已点击」。"""
    try:
        return run_page_js("login_click.js", {}, "auto_login_click.json",
                           _cfg_with(cfg, target=target), label="点击登录")
    except RuntimeError as exc:
        log("点击后页面已跳转（脚本上下文销毁，属正常）：%s" % str(exc)[:160])
        return {"clicked": True, "navigated": True}


def goto(cfg, target, url):
    """把登录页标签页导航到业务页。导航销毁上下文，异常视为「已发起导航」。"""
    try:
        return run_page_js("login_go.js", {"url": url}, "auto_login_go.json",
                           _cfg_with(cfg, target=target), label="导航到业务页")
    except RuntimeError as exc:
        log("导航中页面上下文销毁（属正常）：%s" % str(exc)[:140])
        return {"ok": True, "navigatedTo": url}


def wait_logged_in(cfg, seconds):
    """在 seconds 内轮询登录态，返回最后一个探测结果。

    探测固定用 tab="openlibing"：登录 cookie 按 profile 共享，任一 openlibing 页面
    （包括停在 ?loginFlag=true 的登录页）都能验证登录态，因此不依赖某个特定标签页。
    """
    deadline = time.time() + seconds
    last = {}
    while time.time() < deadline:
        last = probe_safe(cfg, tab="openlibing")
        if last.get("loggedIn"):
            return last
        time.sleep(POLL_S)
    return last


def main(argv=None):
    ap = argparse.ArgumentParser(description="openLiBing 登录态自检 / 自动 GitCode 登录")
    ap.add_argument("--clicks", type=int, default=2, help="最多点几次登录（默认 2）")
    ap.add_argument("--port", type=int, default=0, help="调试端口（默认取 config.chrome.debug_port）")
    ap.add_argument("--keep", action="store_true", help="保留本次自动打开的标签页（排障用）")
    args = ap.parse_args(argv)

    cfg = load_config()
    ch = cfg.get("chrome") or {}
    port = args.port or int(ch.get("debug_port", 9222))
    dashboard = str(ch.get("start_url") or DEFAULT_DASHBOARD)

    if not ensure_browser(cfg, start_url=LOGIN_PAGE, on_log=lambda m: log(m.replace("== 浏览器: ", ""))):
        log("浏览器调试端口不可用，无法自检登录态")
        return 1

    # 1) 先看现有标签页里的登录态：已登录就什么都不做（不额外开页、不点按钮）
    st = probe_safe(cfg)
    if st.get("loggedIn"):
        log("已登录（接口 code=200，%s）" % st.get("url", ""))
        return 0
    log("未登录：code=%s http=%s %s" % (st.get("code"), st.get("http"), st.get("msg") or ""))

    opened = []          # 本次自动打开的标签页 id
    keep_open = False    # 需要人工介入时保留页面，不清理

    try:
        # 2) 开一个登录页标签页，并记下它的 id（后续一律按 id 定位，不依赖 URL）
        try:
            res = _open_tab(port, LOGIN_PAGE)
        except Exception as exc:
            log("打开登录页失败：%s" % exc)
            return 1
        tid = str(res.get("id") or "")
        if not tid:
            log("打开登录页失败：%s" % json.dumps(res, ensure_ascii=False)[:200])
            return 1
        opened.append(tid)
        deadline = time.time() + WAIT_TAB_S
        while time.time() < deadline and not _tab_by_id(port, tid):
            time.sleep(1)
        if not _tab_by_id(port, tid):
            log("登录页标签页未就绪（id=%s）" % tid)
            return 1
        log("已打开登录页：%s（标签页 %s）" % (LOGIN_PAGE, tid))

        # 3) 点「登录」走 GitCode 单点登录
        for i in range(1, max(1, args.clicks) + 1):
            res = click_login(cfg, tid)
            if not res.get("clicked") and res.get("reason"):
                log("第 %d 次：%s" % (i, res["reason"]))
            else:
                log("第 %d 次：已点击「登录」（%s）" % (i, res.get("clickedEl") or res.get("button") or "页面跳转中"))
            st = wait_logged_in(cfg, WAIT_AFTER_CLICK_S)
            if st.get("loggedIn"):
                log("登录成功（接口 code=200，%s）" % st.get("url", ""))
                return 0
            log("第 %d 次后仍未登录：code=%s %s" % (i, st.get("code"), st.get("msg") or ""))

            # 诊断这一页现在在哪：若已跳到 GitCode 登录页，说明 GitCode 会话也过期，需人工
            here = probe_safe(cfg, target=tid)
            if here.get("onGitcode") or here.get("hasQr"):
                log("已跳转到 GitCode 登录页（GitCode 会话也过期），需要人工扫码/输密码。"
                    "已保留该标签页，登录后重跑本脚本即可")
                keep_open = True
                return 1

            # 4) 还停在登录页 → 主动导航到业务页再确认（鉴权成功后登录页常不自己跳转）
            if here.get("onLoginPage") or here.get("hasLoginBtn"):
                log("登录页未跳转，主动打开业务页确认登录态：%s" % dashboard)
                goto(cfg, tid, dashboard)
                st = wait_logged_in(cfg, WAIT_AFTER_GOTO_S)
                if st.get("loggedIn"):
                    log("登录成功（接口 code=200，%s）" % st.get("url", ""))
                    return 0
                log("导航到业务页后仍未登录：code=%s %s" % (st.get("code"), st.get("msg") or ""))

        log("自动登录失败：多半需要人工扫码/输密码。请在该 Chrome 窗口里登录一次后重跑。")
        keep_open = True     # 失败时保留页面，方便人工直接在这个窗口里登录
        return 1
    finally:
        # 收尾：关掉本次自动打开的标签页（避免历史遗留的登录页越堆越多）
        if not args.keep and not keep_open:
            for tid in opened:
                if _close_tab(port, tid) is not None:
                    log("已关闭本次打开的登录页标签页 %s" % tid)


if __name__ == "__main__":
    sys.exit(main())
