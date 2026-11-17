# -*- coding: utf-8 -*-
"""临时探测 2（用完即删）：openGauss 带认证 api/json、失败构建控制台日志、开放时间字段。"""
import base64, json, ssl, urllib.request, urllib.error, datetime
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
H = {"User-Agent":"Mozilla/5.0"}
BJ = datetime.timezone(datetime.timedelta(hours=8))
OG_BASE="https://jenkins.opengauss.org"
OG_AUTH={"Authorization":"Basic "+base64.b64encode(b"opengauss:11762b89da55bc7042ae96f533c4cda5a3").decode()}
def get(u,h=None,t=60):
    hh=dict(H); hh.update(h or {})
    try:
        return urllib.request.urlopen(urllib.request.Request(u,headers=hh),context=ctx,timeout=t).read().decode("utf-8",errors="replace")
    except urllib.error.HTTPError as e: return "HTTP %s"%e.code
    except Exception as e: return "ERR %s %s"%(type(e).__name__,e)
def bj(ts): return datetime.datetime.fromtimestamp(ts/1000.0,BJ).strftime("%Y-%m-%d %H:%M:%S")

print("--- openGauss api/json (auth) ---")
j = get(OG_BASE+"/job/autobuild-opengauss-openeuler24.03-arm/api/json?tree=builds[number,result,timestamp,duration]{0,10}", OG_AUTH)
print(j[:500] if j.startswith(("HTTP","ERR")) else "OK len=%d"%len(j))
if not j.startswith(("HTTP","ERR")):
    for b in json.loads(j)["builds"]:
        st=b.get("timestamp"); du=b.get("duration") or 0
        print("  #%s %s start=%s end=%s dur=%ss"%(b["number"],b.get("result"),bj(st),bj(st+du),du//1000))

print("--- openEuler api/json build detail 42 / 41 ---")
for n in (42,41,40):
    j = get("https://ci.openeuler.openatom.cn/job/EBS-OS-build/job/Main-openEuler-24.03-LTS-SP5-EBS-dailybuild/%d/api/json?tree=number,result,timestamp,duration,displayName"%n)
    if j.startswith(("HTTP","ERR")): print("  #%s -> %s"%(n,j[:60])); continue
    d=json.loads(j); st=d["timestamp"]; du=d.get("duration") or 0
    print("  #%s %s %s start=%s end=%s dur=%.1fh"%(d["number"],d.get("result"),d.get("displayName"),bj(st),bj(st+du),du/3600000.0))

print("--- openGauss failed consoleText (#760 24.03-arm) ---")
r = get(OG_BASE+"/job/autobuild-opengauss-openeuler24.03-arm/760/consoleText", OG_AUTH)
if r.startswith(("HTTP","ERR")): print("  ",r[:80])
else:
    lines=r.splitlines(); print("  len=%d lines=%d"%(len(r),len(lines)))
    for ln in lines[-40:]: print("   |",ln[:200])
