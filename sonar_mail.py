#!/usr/bin/env python3
"""Build a SonarQube summary and send it via send_mail.py."""
import base64
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
    auth = "Basic " + base64.b64encode((tok + ":").encode()).decode()
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": auth,
            "ngrok-skip-browser-warning": "true",
            "User-Agent": "Mozilla/5.0 (compatible; AzurePipeline/1.0)",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
        if raw.lstrip().startswith("<"):
            raise RuntimeError("Sonar returned HTML (ngrok warning page), not JSON")
        return json.loads(raw)


def build_body(status_word):
    task = report_task()
    tok, host = token_and_host(task)
    key = task.get("projectKey") or "branch-rule-test"
    lines = [
        "SONARQUBE REPORT (this email IS the report — no ngrok click needed)",
        "Pipeline status: " + status_word,
        "Project: " + key,
        "",
    ]
    if not host or not tok:
        lines.append("Could not load metrics (missing host or token).")
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
        lines.append("Summary")
        for m in ((meas.get("component") or {}).get("measures") or []):
            lines.append("  {0}: {1}".format(m.get("metric"), m.get("value")))
        lines.append("")
        issues = api_get(
            host
            + "/api/issues/search?componentKeys="
            + key
            + "&resolved=false&ps=15&s=SEVERITY",
            tok,
        )
        total = issues.get("total")
        lines.append("Open issues: " + str(total))
        for issue in issues.get("issues") or []:
            lines.append(
                "  [{severity}] {message} ({component}:{line})".format(
                    severity=issue.get("severity"),
                    message=issue.get("message"),
                    component=(issue.get("component") or "").split(":")[-1],
                    line=issue.get("line") or "-",
                )
            )
        if not (issues.get("issues") or []):
            lines.append("  none")
    except Exception as exc:
        lines.append("Live metrics could not be fetched: " + str(exc))
    lines.append("")
    lines.append("Recipients are GMAIL_TO (comma-separated) on the pipeline.")
    return "\n".join(lines)


def main():
    status_word = sys.argv[1] if len(sys.argv) > 1 else "REPORT"
    subject = sys.argv[2] if len(sys.argv) > 2 else "[CI/CD] SonarQube " + status_word
    body = build_body(status_word)
    print(body)
    subprocess.check_call([sys.executable, str(ROOT / "send_mail.py"), subject, body])


if __name__ == "__main__":
    main()
