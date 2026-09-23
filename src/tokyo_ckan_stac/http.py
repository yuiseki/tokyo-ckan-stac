"""The one way this project talks to the network.

A browser-like User-Agent is not needed and not sent. The one sent says who
is asking and where to complain, which is what an operator reading their logs
wants to know.
"""

import json
import urllib.parse
import urllib.request

UA = "tokyo-ckan-stac/0.1 (+https://github.com/yuiseki/tokyo-ckan-stac)"
API = "https://catalog.data.metro.tokyo.lg.jp/api/3/action"


def action(name: str, timeout: float = 120, **params):
    """Call a CKAN action and return `result`, raising on success=false."""
    q = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
         for k, v in params.items()}
    url = f"{API}/{name}?{urllib.parse.urlencode(q)}" if q else f"{API}/{name}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.load(r)
    if not body.get("success"):
        raise RuntimeError(f"{name}: {body.get('error')}")
    return body["result"]
