#!/usr/bin/env python3
"""Fetch SonarQube metrics, write a PDF report, email it as an attachment."""
import base64
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PDF_PATH = ROOT / "SonarQube-Report.pdf"


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
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read().decode()
        if raw.lstrip().startswith("<"):
            raise RuntimeError("Sonar returned HTML (ngrok warning), not JSON")
        return json.loads(raw)


def collect(status_word):
    task = report_task()
    tok, host = token_and_host(task)
    key = task.get("projectKey") or "branch-rule-test"
    data = {
        "status": status_word,
        "project": key,
        "when": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "gate": "UNKNOWN",
        "conditions": [],
        "measures": [],
        "issues": [],
        "issue_total": 0,
        "error": "",
    }
    if not host or not tok:
        data["error"] = "Missing Sonar host or token"
        return data
    try:
        qg = api_get(host + "/api/qualitygates/project_status?projectKey=" + key, tok)
        ps = qg.get("projectStatus") or {}
        data["gate"] = str(ps.get("status") or "UNKNOWN")
        data["conditions"] = ps.get("conditions") or []
        meas = api_get(
            host
            + "/api/measures/component?component="
            + key
            + "&metricKeys=bugs,vulnerabilities,security_hotspots,code_smells,coverage,duplicated_lines_density,ncloc,reliability_rating,security_rating,sqale_rating,alert_status",
            tok,
        )
        data["measures"] = (meas.get("component") or {}).get("measures") or []
        issues = api_get(
            host
            + "/api/issues/search?componentKeys="
            + key
            + "&resolved=false&ps=50&s=SEVERITY",
            tok,
        )
        data["issue_total"] = issues.get("total") or 0
        data["issues"] = issues.get("issues") or []
    except Exception as exc:
        data["error"] = str(exc)
    return data


def ascii(text):
    return ("" if text is None else str(text)).encode("latin-1", "replace").decode("latin-1")


def write_pdf(data):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "SonarQube Analysis Report", ln=1)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, ascii("Project: " + data["project"]), ln=1)
    pdf.cell(0, 7, ascii("Generated: " + data["when"]), ln=1)
    pdf.cell(0, 7, ascii("Pipeline: " + data["status"]), ln=1)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, ascii("Quality gate: " + data["gate"]), ln=1)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Quality gate conditions", ln=1)
    pdf.set_font("Helvetica", "", 10)
    if not data["conditions"]:
        pdf.cell(0, 6, "None", ln=1)
    for c in data["conditions"]:
        line = "{metricKey}: {actualValue} (threshold {errorThreshold}) -> {status}".format(
            metricKey=c.get("metricKey"),
            actualValue=c.get("actualValue"),
            errorThreshold=c.get("errorThreshold"),
            status=c.get("status"),
        )
        pdf.multi_cell(0, 6, ascii(line))

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Metrics", ln=1)
    pdf.set_font("Helvetica", "", 10)
    if not data["measures"]:
        pdf.cell(0, 6, "None", ln=1)
    for m in data["measures"]:
        pdf.cell(0, 6, ascii("{0}: {1}".format(m.get("metric"), m.get("value"))), ln=1)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, ascii("Open issues: " + str(data["issue_total"])), ln=1)
    pdf.set_font("Helvetica", "", 9)
    if not data["issues"]:
        pdf.cell(0, 6, "None", ln=1)
    for issue in data["issues"]:
        line = "[{severity}] {type} {message}  ({file}:{line})".format(
            severity=issue.get("severity"),
            type=issue.get("type"),
            message=issue.get("message"),
            file=(issue.get("component") or "").split(":")[-1],
            line=issue.get("line") or "-",
        )
        pdf.multi_cell(0, 5, ascii(line))

    if data["error"]:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Notes", ln=1)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, ascii(data["error"]))

    pdf.output(str(PDF_PATH))
    return PDF_PATH


def main():
    status_word = sys.argv[1] if len(sys.argv) > 1 else "REPORT"
    subject = sys.argv[2] if len(sys.argv) > 2 else "[CI/CD] SonarQube " + status_word
    data = collect(status_word)
    write_pdf(data)
    body = (
        "SonarQube PDF report is attached (SonarQube-Report.pdf).\n"
        "Quality gate: {gate}\n"
        "Open issues: {total}\n"
        "This mail goes only to GMAIL_TO."
    ).format(gate=data["gate"], total=data["issue_total"])
    print(body)
    subprocess.check_call(
        [sys.executable, str(ROOT / "send_mail.py"), subject, body, str(PDF_PATH)]
    )


if __name__ == "__main__":
    main()
