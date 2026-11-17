# -*- coding: utf-8 -*-
"""临时连通性探测（用完即删）：确认两社区 nightly 构建历史与控制台日志可采。"""
import base64, json, re, ssl, urllib.request, urllib.error, datetime

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
H = {"User-Agent":"Mozilla/5.0"}
BJ = datetime.timezone(datetime.timedelta(hours=8))

OG_BASE = "https://jenkins.opengauss.org"
OG_AUTH = {"Authorization": "Basic " + base64.b64encode(b"opengauss:11762b89da55bc7042ae96f533c4cda5a3").decode()}
OG_JOBS = [
 "autobuild-opengauss-centos-x86",
 "autobuild-opengauss-openeuler-arm",
 "autobuild-opengauss-openeuler-x86",
 "autobuild-opengauss-openeuler2203-arm",
 "autobuild-opengauss-openeuler2203-x86",
 "autobuild-opengauss-openeuler24.03-arm",
 "autobuild-opengauss-openeuler24.03-x86",
]
OE_BASE = "https://ci.openeuler.openatom.cn"
OE_JOB = "EBS-OS-build/job/Main-openEuler-24.03-LTS-SP5-EBS-dailybuild"

def get(url, headers=None, timeout=40):
    h = dict(H); h.update(headers or {})
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=h), context=ctx, timeout=timeout)
        return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return "HTTP %s" % e.code
    except Exception as e:
        return "ERR %s %s" % (type(e).__name__, e)

def bj(ts_ms):
    return datetime.datetime.fromtimestamp(ts_ms/1000.0, BJ).strftime("%Y-%m-%d %H:%M:%S")

print("="*70); print("openGauss ajax probe")
for job in OG_JOBS:
    url = "%s/job/%s/buildHistory/ajax" % (OG_BASE, job)
    r = get(url, OG_AUTH)
    if r.startswith("HTTP") or r.startswith("ERR"):
        print(" ", job, "->", r[:80]); continue
    items = re.split(r'<div page-entry-id="(-?\d+)" class="app-builds-container__item">', r)
    rows = []
    for i in range(2, len(items), 2):
        body = items[i]
        mnum = re.search(r'href="/job/' + re.escape(job) + r'/(\d+)/console"', body)
        mres = re.search(r'tooltip="([^"]+)" href="/job/' + re.escape(job) + r'/(\d+)/console"', body)
        mts = re.search(r'time="(\d+)"', body)
        if not mnum: continue
        rows.append((int(mnum.group(1)), mres.group(1) if mres else "?", bj(int(mts.group(1))) if mts else None))
    print(" ", job, "rows=%d" % len(rows), rows[:3])
    inwin = [x for x in rows if x[2] and "2026-11-10" <= x[2][:10] <= "2026-11-13"]
    print("      in 11-10..11-13:", [(x[0], x[1], x[2]) for x in inwin])

print("="*70); print("openEuler api probe")
r = get("%s/job/%s/api/json?tree=builds[number,result,timestamp,duration]{0,40}" % (OE_BASE, OE_JOB))
print(r[:400] if r.startswith(("HTTP","ERR")) else "OK json len=%d" % len(r))
if not r.startswith(("HTTP","ERR")):
    d = json.loads(r)
    rows = [(b["number"], b.get("result"), bj(b["timestamp"]) if b.get("timestamp") else None) for b in d.get("builds",[])]
    print("  total builds:", len(rows))
    print("  first5:", rows[:5]); print("  last5:", rows[-5:])
    inwin = [x for x in rows if x[2] and "2026-11-10" <= x[2][:10] <= "2026-11-13"]
    print("  in 11-10..11-13:", inwin)

print("="*70); print("consoleText probe")
rc = get("%s/job/%s/1/consoleText" % (OE_BASE, OE_JOB))
print("  openEuler console:", (rc[:200] if rc.startswith(("HTTP","ERR")) else "OK len=%d" % len(rc)))
rg = get("%s/job/%s/lastSuccessfulBuild/consoleText" % (OG_BASE, OG_JOBS[0]), OG_AUTH)
print("  openGauss console:", (rg[:200] if rg.startswith(("HTTP","ERR")) else "OK len=%d" % len(rg)))
