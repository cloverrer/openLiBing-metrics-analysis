import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from lib.cdp_exec import load_config

cfg = load_config()
gh = cfg["github"]
headers = {"Authorization": "Bearer %s" % gh["token"],
           "Accept": "application/vnd.github+json",
           "User-Agent": "rca-probe"}

for rid in sys.argv[1:]:
    url = "https://api.github.com/repos/sgl-project/sglang/actions/runs/%s/jobs?per_page=100" % rid
    req = urllib.request.Request(url, headers=headers)
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    print("run %s: %d jobs" % (rid, len(d.get("jobs") or [])))
    for j in d.get("jobs") or []:
        if j.get("conclusion") not in ("success", "skipped", None):
            print("  -", j.get("name"), "|", j.get("status"), j.get("conclusion"))
