#!/usr/bin/env python3
"""Build a SonarQube summary and send it via send_mail.py."""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def report_task():
    for p in (ROOT / ".scannerwork" / "report-task.txt", Path(".scannerwork/report-task.txt")):
        if p.exists():
            data = {}
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()
            return data
    return {}


def token_and_host(task):
    raw = os.environ.get("SONARQUBE_SCANNER_PARAMS") or "{}"
    try:
        params = json.loads(raw)
    except json.JSONDecodeError:
        params = {}
    tok = (
        params.get("sonar.token")
        or params.get("sonar.login")
        or os.environ.get("SONAR_TOKEN")
        or ""
    )
    host = (
        params.get("sonar.host.url")
        or task.get("serverUrl")
        or os.environ.get("SONAR_HOST_URL")
        or ""
    ).rstrip("/")
    return tok, host


def api_get(url, tok):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + tok,
            "ngrok-skip-browser-warning": "1",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def build_body(status_word):
    task = report_task()
    tok, host = token_and_host(task)
    key = task.get("projectKey") or "branch-rule-test"
    dash = task.get("dashboardUrl") or (host + "/dashboard?id=" + key if host else "")
    lines = [
        "SonarQube report",
        "Status: " + status_word,
        "Project: " + key,
        "Dashboard: " + dash,
        "",
    ]
    if not host or not tok:
        lines.append("Could not call Sonar API (missing host or token). Open the dashboard link.")
        return "\n".join(lines)
    try:
        qg = api_get(host + "/api/qualitygates/project_status?projectKey=" + key, tok)
        ps = qg.get("projectStatus") or {}
        lines.append("Quality gate: " + str(ps.get("status")))
        for c in ps.get("conditions") or []:
            lines.append(
                "  - {metricKey}: {actualValue} (vs {errorThreshold}) -> {status}".format(
                    metricKey=c.get("metricKey"),
                    actualValue=c.get("actualValue"),
                    errorThreshold=c.get("errorThreshold"),
                    status=c.get("status"),
                )
            )
        lines.append("")
        meas = api_get(
            host
            + "/api/measures/component?component="
            + key
            + "&metricKeys=bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density,ncloc,alert_status",
            tok,
        )
        for m in ((meas.get("component") or {}).get("measures") or []):
            lines.append("{0}: {1}".format(m.get("metric"), m.get("value")))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        lines.append("API extra details failed: " + str(exc))
        lines.append("Use the dashboard link above.")
    return "\n".join(lines)


def main():
    status_word = sys.argv[1] if len(sys.argv) > 1 else "REPORT"
    subject = sys.argv[2] if len(sys.argv) > 2 else "[CI/CD] SonarQube " + status_word
    body = build_body(status_word)
    print(body)
    subprocess.check_call([sys.executable, str(ROOT / "send_mail.py"), subject, body])


if __name__ == "__main__":
    main()
