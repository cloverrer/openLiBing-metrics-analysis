# -*- coding: utf-8 -*-
"""临时探测（用完即删）：openGauss buildHistory/ajax 分页与条目字段完整性。"""
import base64, re, ssl, urllib.request, urllib.error, datetime

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
H = {"User-Agent": "Mozilla/5.0",
     "Authorization": "Basic " + base64.b64encode(b"opengauss:11762b89da55bc7042ae96f533c4cda5a3").decode()}
BJ = datetime.timezone(datetime.timedelta(hours=8))


def get(u):
    try:
        return urllib.request.urlopen(urllib.request.Request(u, headers=H), context=ctx, timeout=40).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return "HTTP %s" % e.code


job = "autobuild-opengauss-openeuler-x86"
base = "https://jenkins.opengauss.org/job/" + job
r = get(base + "/buildHistory/ajax")
print("page1 len", len(r), "has after:", "after=" in r)
print("after params:", re.findall(r"after=(\d+)", r)[:8])
nums = re.findall(r'href="/job/' + re.escape(job) + r'/(\d+)/console"', r)
print("page1 nums:", nums)
r2 = get(base + "/buildHistory/ajax?after=1860")
print("page2:", r2[:60] if r2.startswith("HTTP") else "len=%d" % len(r2))
if not r2.startswith("HTTP"):
    print("page2 nums:", re.findall(r'href="/job/' + re.escape(job) + r'/(\d+)/console"', r2)[:10])
# 看单条目原始结构
seg = re.split(r'<div page-entry-id="(-?\d+)" class="app-builds-container__item">', r)
print("entries:", (len(seg) - 1) // 2)
if len(seg) >= 3:
    print(seg[2][:1200])
