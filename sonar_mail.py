#!/usr/bin/env python3
"""Build a multi-page Sonar executive PDF (dashboard, issues, hotspots, rule detail) and email it."""
import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PDF_PATH = ROOT / "SonarQube-Report.pdf"

TEAL = (15, 108, 189)
DARK = (35, 45, 55)
MUTED = (90, 100, 110)
GREEN = (34, 160, 90)
RED = (200, 55, 55)
ORANGE = (230, 140, 30)
CARD = (248, 250, 252)
RATING_RGB = {
    "A": (34, 160, 90),
    "B": (120, 180, 50),
    "C": (230, 180, 30),
    "D": (230, 120, 30),
    "E": (200, 55, 55),
}


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


def download_bytes(url, tok, timeout=180):
    auth = "Basic " + base64.b64encode((tok + ":").encode()).decode()
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": auth,
            "ngrok-skip-browser-warning": "true",
            "User-Agent": "Mozilla/5.0 (compatible; AzurePipeline/1.0)",
            "Accept": "application/pdf,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download_bitegarden(host, tok, key):
    """Pull the official bitegarden Full Issues PDF (trial may watermark)."""
    q = urllib.parse.quote(key)
    urls = [
        host + "/api/bitegarden/report/pdf?resource=" + q + "&type=2",
        host + "/api/bitegarden/report/pdf?resource=" + q + "&type=FULL",
        host + "/api/bitegarden/report/pdf?resource=" + q,
        host + "/api/bitegarden/report/pdf?component=" + q + "&type=2",
        host + "/api/bitegarden/report/pdf?componentKey=" + q + "&type=2",
    ]
    last = ""
    for url in urls:
        try:
            print("bitegarden GET", url)
            raw = download_bytes(url, tok)
            if raw[:4] == b"%PDF":
                PDF_PATH.write_bytes(raw)
                print("bitegarden PDF saved", len(raw), "bytes")
                return True
            last = "not PDF (%s bytes) %r" % (len(raw), raw[:60])
            print(last)
        except Exception as exc:
            last = str(exc)
            print("bitegarden miss:", last)
    print("bitegarden unavailable:", last)
    return False


def letter(rating):
    try:
        n = int(float(rating))
    except (TypeError, ValueError):
        return str(rating or "-")
    return {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}.get(n, str(rating))


def size_rating(ncloc):
    try:
        n = int(float(ncloc))
    except (TypeError, ValueError):
        return "XS"
    if n < 1000:
        return "XS"
    if n < 10000:
        return "S"
    if n < 100000:
        return "M"
    if n < 500000:
        return "L"
    return "XL"


def measure_map(measures):
    out = {}
    for m in measures or []:
        out[m.get("metric")] = m.get("value") or m.get("period", {}).get("value") or "0"
    return out


def collect(status_word):
    task = report_task()
    tok, host = token_and_host(task)
    key = task.get("projectKey") or "branch-rule-test"
    data = {
        "status": status_word,
        "project": key,
        "branch": os.environ.get("BUILD_SOURCEBRANCHNAME") or "main",
        "when": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "version": "1.0",
        "gate": "UNKNOWN",
        "conditions": [],
        "measures": {},
        "issues": [],
        "hotspots": [],
        "error": "",
    }
    if not host or not tok:
        data["error"] = "Missing Sonar host or token"
        return data
    metrics = (
        "bugs,vulnerabilities,security_hotspots,code_smells,coverage,"
        "duplicated_lines_density,duplicated_blocks,ncloc,reliability_rating,"
        "security_rating,sqale_rating,sqale_debt_ratio,alert_status,"
        "new_bugs,new_vulnerabilities,new_security_hotspots,new_code_smells,"
        "new_coverage,new_duplicated_lines_density,new_sqale_debt_ratio,"
        "tests,security_hotspots_reviewed"
    )
    try:
        qg = api_get(host + "/api/qualitygates/project_status?projectKey=" + urllib.parse.quote(key), tok)
        ps = qg.get("projectStatus") or {}
        data["gate"] = str(ps.get("status") or "UNKNOWN")
        data["conditions"] = ps.get("conditions") or []
        meas = api_get(
            host
            + "/api/measures/component?component="
            + urllib.parse.quote(key)
            + "&metricKeys="
            + metrics,
            tok,
        )
        data["measures"] = measure_map((meas.get("component") or {}).get("measures"))
        issues = api_get(
            host
            + "/api/issues/search?componentKeys="
            + urllib.parse.quote(key)
            + "&resolved=false&ps=100&s=SEVERITY&additionalFields=rules",
            tok,
        )
        data["issues"] = issues.get("issues") or []
        data["rules"] = {r.get("key"): r for r in (issues.get("rules") or [])}
        try:
            hs = api_get(
                host
                + "/api/hotspots/search?projectKey="
                + urllib.parse.quote(key)
                + "&ps=50",
                tok,
            )
            data["hotspots"] = hs.get("hotspots") or []
        except Exception:
            data["hotspots"] = []
    except Exception as exc:
        data["error"] = str(exc)
    return data


def ascii(text):
    return ("" if text is None else str(text)).encode("latin-1", "replace").decode("latin-1")


def donut_png(folder, value, color_hex, filename):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        v = max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        v = 0.0
    fig, ax = plt.subplots(figsize=(2.4, 2.4))
    ax.pie(
        [v, 100.0 - v],
        colors=[color_hex, "#E8EEF2"],
        startangle=90,
        counterclock=False,
        wedgeprops=dict(width=0.42, edgecolor="white"),
    )
    ax.text(0, 0, "%.1f%%" % v, ha="center", va="center", fontsize=13, fontweight="bold", color="#233")
    ax.set_aspect("equal")
    plt.axis("off")
    path = os.path.join(folder, filename)
    fig.savefig(path, bbox_inches="tight", transparent=True, dpi=140)
    plt.close(fig)
    return path


def header(pdf, title):
    pdf.set_fill_color(*TEAL)
    pdf.rect(0, 0, 210, 18, "F")
    pdf.set_xy(12, 5)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(100, 8, "SonarQube  |  branch-rule-test", align="L")
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(86, 8, ascii(title), align="R")
    pdf.set_text_color(*DARK)
    pdf.set_xy(12, 22)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED)


def footer(pdf, page, total):
    pdf.set_xy(12, 285)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 5, ascii("Confidential quality report  |  page %s" % page), align="C")


def group_issues(issues):
    by_rule = defaultdict(list)
    for issue in issues:
        by_rule[issue.get("rule") or "unknown"].append(issue)
    return by_rule


def write_pdf(data):
    from fpdf import FPDF

    mm = data["measures"]
    tmp = tempfile.mkdtemp()
    cov = mm.get("coverage") or "0"
    dup = mm.get("duplicated_lines_density") or "0"
    cov_png = donut_png(tmp, cov, "#2AA05A" if float(cov or 0) >= 80 else "#E08C1E", "cov.png")
    dup_png = donut_png(tmp, dup, "#2AA05A" if float(dup or 0) < 3 else "#C83737", "dup.png")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=16)

    # ----- Page 1 Executive -----
    pdf.add_page()
    header(pdf, "Executive Report")
    pdf.set_xy(12, 24)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(60, 6, ascii("Project  " + data["project"]))
    pdf.cell(60, 6, ascii("Branch  " + data["branch"]))
    pdf.cell(60, 6, ascii("Analysis  " + data["when"]), ln=1)
    pdf.set_x(12)
    pdf.cell(60, 6, ascii("Size  " + size_rating(mm.get("ncloc"))))
    pdf.cell(60, 6, ascii("Lines of code  " + str(mm.get("ncloc") or "0")))
    pdf.cell(40, 6, ascii("Version  " + data["version"]))
    gate = (data["gate"] or "").upper()
    if gate in ("OK", "PASSED"):
        pdf.set_fill_color(*GREEN)
        gtxt = "PASSED"
    else:
        pdf.set_fill_color(*RED)
        gtxt = gate or "FAILED"
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(22, 6, gtxt, align="C", fill=True, ln=1)

    def rating_card(x, title, letter_v, metric, value, extra):
        pdf.set_fill_color(*CARD)
        pdf.rect(x, 44, 60, 52, "F")
        pdf.set_xy(x + 2, 46)
        pdf.set_text_color(*MUTED)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(56, 6, title, align="C")
        rgb = RATING_RGB.get(letter_v, MUTED)
        pdf.set_fill_color(*rgb)
        pdf.ellipse(x + 20, 54, 20, 20, "F")
        pdf.set_xy(x + 20, 58)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(20, 10, letter_v, align="C")
        pdf.set_xy(x + 2, 76)
        pdf.set_text_color(*DARK)
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(56, 8, ascii(str(value)), align="C")
        pdf.set_xy(x + 2, 84)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*MUTED)
        pdf.cell(56, 6, extra, align="C")

    rating_card(
        12,
        "Reliability",
        letter(mm.get("reliability_rating")),
        "bugs",
        mm.get("bugs") or "0",
        "Bugs",
    )
    rating_card(
        75,
        "Security",
        letter(mm.get("security_rating")),
        "vuln",
        mm.get("vulnerabilities") or "0",
        "Vulnerabilities / hotspots %s" % (mm.get("security_hotspots") or "0"),
    )
    rating_card(
        138,
        "Maintainability",
        letter(mm.get("sqale_rating")),
        "smells",
        mm.get("code_smells") or "0",
        "Code smells  |  debt %s%%" % (mm.get("sqale_debt_ratio") or "0"),
    )

    pdf.image(cov_png, x=22, y=104, w=42)
    pdf.image(dup_png, x=118, y=104, w=42)
    pdf.set_xy(22, 148)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*DARK)
    pdf.cell(70, 6, "Coverage", align="C")
    pdf.set_xy(118, 148)
    pdf.cell(70, 6, "Duplications", align="C")
    pdf.set_xy(22, 154)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(70, 5, ascii("Unit tests  " + str(mm.get("tests") or "0")), align="C")
    pdf.set_xy(118, 154)
    pdf.cell(70, 5, ascii("Duplicated blocks  " + str(mm.get("duplicated_blocks") or "0")), align="C")

    pdf.set_xy(12, 168)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, "Quality gate conditions", ln=1)
    pdf.set_font("Helvetica", "", 9)
    if not data["conditions"]:
        pdf.set_x(12)
        pdf.cell(0, 6, "No extra conditions (or gate uses overall ratings).", ln=1)
    for c in data["conditions"]:
        pdf.set_x(12)
        line = "{metricKey}: actual {actualValue}  threshold {errorThreshold}  -> {status}".format(
            metricKey=c.get("metricKey"),
            actualValue=c.get("actualValue"),
            errorThreshold=c.get("errorThreshold"),
            status=c.get("status"),
        )
        pdf.multi_cell(186, 5, ascii(line))

    if data["error"]:
        pdf.set_x(12)
        pdf.set_text_color(*RED)
        pdf.multi_cell(186, 5, ascii("Note: " + data["error"]))

    footer(pdf, 1, 1)

    # ----- Page 2 Issues -----
    pdf.add_page()
    header(pdf, "Issues Breakdown")
    pdf.set_xy(12, 26)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, "Top issues by rule", ln=1)

    grouped = group_issues(data["issues"])
    ranked = sorted(grouped.items(), key=lambda kv: -len(kv[1]))
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(12)
    pdf.cell(18, 7, "Sev")
    pdf.cell(140, 7, "Rule")
    pdf.cell(28, 7, "# issues", ln=1)
    pdf.set_font("Helvetica", "", 9)
    if not ranked:
        pdf.set_x(12)
        pdf.cell(0, 7, "No open issues.", ln=1)
    for rule, items in ranked[:20]:
        sev = items[0].get("severity") or ""
        msg = items[0].get("message") or rule
        pdf.set_x(12)
        pdf.cell(18, 6, ascii(sev[:8]))
        pdf.cell(140, 6, ascii(msg[:78]))
        pdf.cell(28, 6, str(len(items)), ln=1)

    pdf.set_xy(12, 200)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Counts", ln=1)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_x(12)
    pdf.cell(0, 6, ascii(
        "Bugs %s   Vulnerabilities %s   Hotspots %s   Code smells %s"
        % (
            mm.get("bugs") or "0",
            mm.get("vulnerabilities") or "0",
            mm.get("security_hotspots") or "0",
            mm.get("code_smells") or "0",
        )
    ), ln=1)
    footer(pdf, 2, 1)

    # ----- Page 3 Hotspots -----
    pdf.add_page()
    header(pdf, "Security Hotspots")
    pdf.set_xy(12, 26)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, "Top security hotspots to review", ln=1)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(12)
    pdf.cell(28, 7, "Status")
    pdf.cell(148, 7, "Message")
    pdf.cell(12, 7, "#", ln=1)
    pdf.set_font("Helvetica", "", 9)
    hs_group = defaultdict(list)
    for h in data["hotspots"]:
        hs_group[h.get("message") or h.get("ruleKey") or "hotspot"].append(h)
    if not hs_group:
        pdf.set_x(12)
        pdf.cell(0, 7, "No security hotspots.", ln=1)
    for msg, items in list(hs_group.items())[:15]:
        pdf.set_x(12)
        pdf.cell(28, 6, ascii((items[0].get("status") or "TO_REVIEW")[:12]))
        pdf.cell(148, 6, ascii(msg[:80]))
        pdf.cell(12, 6, str(len(items)), ln=1)
    pdf.set_xy(12, 200)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        186,
        5,
        ascii(
            "Reviewed: %s of %s hotspots."
            % (mm.get("security_hotspots_reviewed") or "0", mm.get("security_hotspots") or "0")
        ),
    )
    footer(pdf, 3, 1)

    # ----- Rule detail pages -----
    for rule, items in ranked[:8]:
        pdf.add_page()
        header(pdf, ascii((items[0].get("type") or "Issue") + "  " + (rule.split(":")[-1] if ":" in rule else rule)[:18]))
        pdf.set_xy(12, 26)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(186, 6, ascii(items[0].get("message") or rule))
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.set_x(12)
        pdf.cell(0, 6, ascii("Language  Python    Issues  %s    Severity  %s" % (len(items), items[0].get("severity"))), ln=1)
        pdf.set_xy(12, 50)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 7, "Issues breakdown", ln=1)
        pdf.set_font("Helvetica", "", 9)
        for issue in items[:12]:
            loc = (issue.get("component") or "").split(":")[-1]
            line = issue.get("line") or "-"
            pdf.set_x(12)
            pdf.multi_cell(186, 5, ascii("%s  L%s   %s" % (loc, line, issue.get("message") or "")))
        footer(pdf, pdf.page_no(), 1)

    for msg, items in list(hs_group.items())[:6]:
        pdf.add_page()
        header(pdf, "Security Hotspot")
        pdf.set_xy(12, 26)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(186, 6, ascii(msg))
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.set_x(12)
        h0 = items[0]
        pdf.cell(0, 6, ascii("Status  %s    Rule  %s" % (h0.get("status"), h0.get("ruleKey"))), ln=1)
        pdf.set_xy(12, 50)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 7, "Occurrences", ln=1)
        pdf.set_font("Helvetica", "", 9)
        for h in items[:12]:
            loc = (h.get("component") or "").split(":")[-1]
            line = (h.get("textRange") or {}).get("startLine") or h.get("line") or "-"
            pdf.set_x(12)
            pdf.multi_cell(186, 5, ascii("%s  L%s" % (loc, line)))
        footer(pdf, pdf.page_no(), 1)

    pdf.output(str(PDF_PATH))
    return PDF_PATH


def main():
    status_word = sys.argv[1] if len(sys.argv) > 1 else "REPORT"
    subject = sys.argv[2] if len(sys.argv) > 2 else "[CI/CD] SonarQube " + status_word
    data = collect(status_word)
    task = report_task()
    tok, host = token_and_host(task)
    source = "generated"
    if host and tok and download_bitegarden(host, tok, data["project"]):
        source = "bitegarden"
    else:
        write_pdf(data)
    body = (
        "SonarQube report attached (SonarQube-Report.pdf).\n"
        "Source: {source} (bitegarden trial PDF has evaluation watermark until license is paid).\n"
        "Quality gate: {gate}\n"
        "Bugs {bugs} | Vulnerabilities {vuln} | Hotspots {hs} | Smells {smells} | Coverage {cov}%\n"
        "Sent only to GMAIL_TO."
    ).format(
        source=source,
        gate=data["gate"],
        bugs=(data["measures"].get("bugs") or "0"),
        vuln=(data["measures"].get("vulnerabilities") or "0"),
        hs=(data["measures"].get("security_hotspots") or "0"),
        smells=(data["measures"].get("code_smells") or "0"),
        cov=(data["measures"].get("coverage") or "0"),
    )
    print(body)
    subprocess.check_call(
        [sys.executable, str(ROOT / "send_mail.py"), subject, body, str(PDF_PATH)]
    )


if __name__ == "__main__":
    main()
