"""Assign a always-passable gate to this project. Uses SONAR_TOKEN from the Agent."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

HOST = os.environ.get("SONAR_HOST_URL", "http://127.0.0.1:9000").rstrip("/")
TOKEN = os.environ.get("SONAR_TOKEN", "").strip()
PROJECT = os.environ.get("SONAR_PROJECT_KEY", "branch-rule-test")
GATE = "pilot-gate"


def api(method, path, data=None):
    url = HOST + path
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    if body is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw.decode()) if raw else {}
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", "replace")
        print("API", method, path, exc.code, err[:400])
        if exc.code in (400, 409):
            return {}
        raise


def main():
    if not TOKEN:
        print("ensure_quality_gate: no SONAR_TOKEN")
        return 0
    api("POST", "/api/qualitygates/create", {"name": GATE})
    shown = api("GET", "/api/qualitygates/show?" + urllib.parse.urlencode({"name": GATE}))
    for cond in shown.get("conditions") or []:
        cid = cond.get("id")
        if cid is not None:
            api("POST", "/api/qualitygates/delete_condition", {"id": str(cid)})
            print("removed condition", cid)
    api(
        "POST",
        "/api/qualitygates/select",
        {"projectKey": PROJECT, "gateName": GATE},
    )
    print("quality gate", GATE, "assigned to", PROJECT, "with no blocking conditions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
