# -*- coding: utf-8 -*-
"""临时探测（用完即删）：核对 openGauss/openEuler 构建的 epoch 与页面显示时间，判断时区口径。"""
import base64, json, re, ssl, urllib.request, urllib.error, datetime

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
H = {"User-Agent": "Mozilla/5.0"}
BJ = datetime.timezone(datetime.timedelta(hours=8))
UTC = datetime.timezone.utc

OG_BASE = "https://jenkins.opengauss.org"
OG_AUTH = {"Authorization": "Basic " + base64.b64encode(b"opengauss:11762b89da55bc7042ae96f533c4cda5a3").decode()}
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


def fmt(ms, tz):
    return datetime.datetime.fromtimestamp(ms / 1000.0, tz).strftime("%Y-%m-%d %H:%M:%S")


print("=" * 70)
print("A) openGauss buildHistory/ajax: time= 原始值 vs 页面显示文本")
job = "autobuild-opengauss-centos-x86"
r = get("%s/job/%s/buildHistory/ajax" % (OG_BASE, job), OG_AUTH)
if r.startswith(("HTTP", "ERR")):
    print("  取数失败:", r[:100])
else:
    items = re.split(r'<div page-entry-id="(-?\d+)" class="app-builds-container__item">', r)
    for i in range(2, min(len(items), 8), 2):
        body = items[i]
        mnum = re.search(r'href="/job/' + re.escape(job) + r'/(\d+)/console"', body)
        mts = re.search(r'time="(\d+)"', body)
        mdisp = re.findall(r'>([0-9]{4}-[0-9]{2}-[0-9]{2}[^<]{0,20})<', body)
        if not mnum:
            continue
        num = int(mnum.group(1))
        ms = int(mts.group(1)) if mts else None
        print("  #%-5s time=%s" % (num, ms))
        if ms:
            print("         epoch→北京 = %s" % fmt(ms, BJ))
            print("         epoch→UTC  = %s" % fmt(ms, UTC))
            print("         epoch秒?→北京 = %s" % fmt(ms * 1000 if ms < 10 ** 11 else ms, BJ))
        print("         页面文本候选:", mdisp[:3])

print("=" * 70)
print("B) openGauss 构建页 api/json timestamp（可能 418）")
r2 = get("%s/job/%s/2020/api/json?tree=number,result,timestamp,duration" % (OG_BASE, job), OG_AUTH)
print("  ", r2[:200] if r2.startswith(("HTTP", "ERR")) else r2[:300])

print("=" * 70)
print("C) openGauss consoleText 首几行（看服务端本地时间格式）")
rc = get("%s/job/%s/760/consoleText" % (OG_BASE, job), OG_AUTH)
if rc.startswith(("HTTP", "ERR")):
    print("  ", rc[:120])
else:
    for ln in rc.splitlines()[:12]:
        print("   |", ln[:160])

print("=" * 70)
print("D) openEuler api/json builds")
r3 = get("%s/job/%s/api/json?tree=builds[number,result,timestamp,duration]{0,10}" % (OE_BASE, OE_JOB))
if r3.startswith(("HTTP", "ERR")):
    print("  ", r3[:120])
else:
    d = json.loads(r3)
    for b in d.get("builds", [])[:6]:
        ts = b.get("timestamp")
        print("  #%-6s ts=%s  北京=%s  UTC=%s" % (b.get("number"), ts, fmt(ts, BJ) if ts else "-", fmt(ts, UTC) if ts else "-"))
