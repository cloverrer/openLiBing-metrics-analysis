# -*- coding: utf-8 -*-
"""临时探测 3（用完即删）：openGauss 构建级 api/json 与 ajax 条目原始字段。"""
import base64, json, re, ssl, urllib.request, urllib.error
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
H = {"User-Agent":"Mozilla/5.0"}
OG="https://jenkins.opengauss.org"
AUTH={"Authorization":"Basic "+base64.b64encode(b"opengauss:11762b89da55bc7042ae96f533c4cda5a3").decode()}
def get(u,h=None,t=60):
    hh=dict(H); hh.update(h or {})
    try:
        return urllib.request.urlopen(urllib.request.Request(u,headers=hh),context=ctx,timeout=t).read().decode("utf-8",errors="replace")
    except urllib.error.HTTPError as e: return "HTTP %s"%e.code
    except Exception as e: return "ERR %s %s"%(type(e).__name__,e)

print("--- build-level api/json ---")
for u in ["/job/autobuild-opengauss-openeuler24.03-arm/760/api/json",
          "/job/autobuild-opengauss-openeuler24.03-arm/760/api/json?tree=number,result,timestamp,duration,building,displayName,description"]:
    r=get(OG+u,AUTH); print(" ",u,"->",(r[:200] if r.startswith(("HTTP","ERR")) else r[:300]))

print("--- raw ajax entry snippet ---")
r=get(OG+"/job/autobuild-opengauss-openeuler24.03-arm/buildHistory/ajax",AUTH)
i=r.find('page-entry-id="761"')
print(r[i-50:i+1400] if i>0 else "not found; head:"+r[:800])
