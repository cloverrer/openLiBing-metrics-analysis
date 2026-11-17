# -*- coding: utf-8 -*-
"""临时探测 4（用完即删）：ajax 单个条目完整字段。"""
import base64, re, ssl, urllib.request, urllib.error
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
H={"User-Agent":"Mozilla/5.0"}
AUTH={"Authorization":"Basic "+base64.b64encode(b"opengauss:11762b89da55bc7042ae96f533c4cda5a3").decode()}
def get(u):
    hh=dict(H); hh.update(AUTH)
    return urllib.request.urlopen(urllib.request.Request(u,headers=hh),context=ctx,timeout=60).read().decode("utf-8",errors="replace")
r=get("https://jenkins.opengauss.org/job/autobuild-opengauss-openeuler24.03-arm/buildHistory/ajax")
parts=r.split('class="app-builds-container__item"')
print("items:",len(parts)-1)
print("=== item[1] ===")
print(parts[1][:2500])
