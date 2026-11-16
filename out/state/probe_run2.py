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

rid = sys.argv[1]
url = "https://api.github.com/repos/sgl-project/sglang/actions/runs/%s" % rid
req = urllib.request.Request(url, headers=headers)
d = json.loads(urllib.request.urlopen(req, timeout=30).read())
print("run:", d.get("status"), d.get("conclusion"), "| attempt:", d.get("run_attempt"),
      "| event:", d.get("event"), "| created:", d.get("created_at"),
      "| updated:", d.get("updated_at"))
print("title:", d.get("display_title"))
