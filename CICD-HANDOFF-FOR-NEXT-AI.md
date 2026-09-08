# CI/CD handoff — continue from here

This file is a full brief of the work done in Grok chat (Aug–Sep 2026) so another AI or engineer can resume **without** the old thread. Do **not** ask the user to re-explain architecture unless something below is wrong.

**Date of this snapshot:** 8 Sep 2026 ~15:10 IST  
**User / operator:** Vishal (AVD user `X240`). Chat also involved Shounak. Company repos are many; this pilot is one test repo.

**Never store or reuse secrets from old chat.** A GitHub PAT and a Gmail App password were pasted in chat and must be treated as **burned**. Rotate if still active.

---

## 1. What they are trying to build

Company CI/CD for Python apps on **Azure App Service** (and later Function App), quality with **SonarQube**, orchestration with **GoCD on an AVD**, source on **GitHub**.

**Intended prod flow (company):**

```
feat-*  →  PR  →  rc-*   (merge, then tag on rc)
rc-*    →  PR  →  main   (manual verification, then CI/CD → Azure prod)
```

- No direct push to `main` / `rc` in the *company* story (branch rules exist on some repos).
- **SonarQube only on the prod/rc path**, not on a “dev VS Code deploy”.
- **Dev** in the original story: developers deploy from **VS Code → Azure** (there is already a **dev deployment slot**). Not GitHub Actions for that path.
- **Prod:** tag after merge to `rc`, PR `rc → main`, manual approval, then deploy.
- **Rollback:** no staging slot required if they use **redeploy last good zip from GitHub Release / GoCD artifact**. Zero-downtime **swap** needs a **staging slot on the Production app** (they discussed this; pilot did **not** implement slots).
- They compared GitHub Actions, Azure DevOps, Vercel, Octopus, GoCD. **Pilot they actually ran = GoCD on AVD + GitHub + Azure App Service + local SonarQube.** Vercel was a side experiment; **do not mix Vercel into Azure**.

**Pilot they implemented (test, not company prod yet):**

```
push to GitHub main
    → GoCD pipeline `pilot-ascode`
        → test (pytest)
        → sonar (scanner + qualitygate.wait)
        → deploy (zip → Kudu zipdeploy on Azure Web App)
```

Auto-trigger is **`main` only**. feat→rc→main was demonstrated in GitHub; the **live GoCD material branch is `main`**.

---

## 2. Repos, Azure, machines

| Item | Value |
|---|---|
| GitHub test repo | https://github.com/vishal20034/branch-rule-test.git |
| Org / real apps | `aperturexi/guardians-process` and others on AVD; **do not assume this AI still has push rights** |
| Azure Web App | `test-webapp` |
| Resource group | `rg-pilot-dev` |
| Unique hostname | `test-webapp-efepekhyfscpe4fk.westus3-01.azurewebsites.net` |
| SCM / zipdeploy | `https://test-webapp-efepekhyfscpe4fk.scm.westus3-01.azurewebsites.net/api/zipdeploy` |
| Azure startup | `gunicorn --bind=0.0.0.0:8000 app:app` (Linux Python 3.11) |
| Subscription they **logged into with CLI** | `0e19cbdf-57d2-4dcb-bc02-01560019432d` (EB Industries) — **not** the app’s subscription |
| Subscription of `test-webapp` (Overview) | `aa7e7e16-5d9d-4c45-88c9-c94a268644a4` — **service principal could not see this** (wrong tenant / security defaults) |
| GoCD | Windows AVD, pipeline **`pilot-ascode`**, group `defaultGroup`, config-as-code YAML |
| Go Agent workspace | `C:\Program Files (x86)\Go Agent\pipelines\pilot-ascode` |
| Python on Agent | `C:\Users\X240\AppData\Local\Programs\Python\Python313\python.exe` |
| JDK 17 | `C:\Program Files\Java\jdk-17` |
| SonarQube **server** | `http://127.0.0.1:9000` — **SonarQube 25.9.0.112764**, project key **`branch-rule-test`** |
| SonarScanner | `D:\sonar-scanner` (CLI **4.3.0.2102** — old; they invoke **jar + java 17** because `.bat` used Java 11) |
| SonarQube install | `D:\sonarqube\bin\windows-x86-64\` — **Windows service `SonarQube`**, start=auto |
| Gmail they want | `nagbishal07@gmail.com` (From/To). GoCD **Email server UI does not work** (HTTP 406 / Not Acceptable). |

**Live site (if last deploy succeeded):**  
https://test-webapp-efepekhyfscpe4fk.westus3-01.azurewebsites.net

---

## 3. Why Azure CLI / service principal failed (do not repeat)

- `az login` landed on a **different tenant/subscription** than `test-webapp`.
- Security defaults blocked some tenants (`AADSTS530035`).
- `az webapp deploy` with SP: **No subscriptions found** / subscription ID not recognized.
- **Working deploy:** **publish profile** (Basic Auth / SCM) + `curl.exe` **Kudu zipdeploy**.  
  System vars: `AZURE_PUBLISH_USER`, `AZURE_PUBLISH_PASS`.  
  User name looks like `$test-webapp` (keep the `$`).  
  Basic auth on SCM had to be **enabled** in Azure (was disabled at first).
- `az webapp deploy --username/--password` is **not valid** on their CLI. Do not use that.

---

## 4. Files that matter (GitHub `main`)

All of these live at repo root unless noted.

| File | Role |
|---|---|
| `pilot-ascode.gocd.yaml` | GoCD config-as-code. Material: this git, **branch `main`**. Stages: **test → sonar → deploy**. Test job first task: `notify-start.ps1`, then pytest. |
| `app.py` | Flask operator board (notes, checklist, health, export). CSRFProtect. Version string `APP_VERSION`. |
| `templates/` `static/` | HTML/CSS. POST forms include `csrf_token`. |
| `tests/test_app.py` | pytest; CSRF disabled in test client. |
| `requirements.txt` | flask, gunicorn, pytest, flask-wtf |
| `deploy.ps1` | `tar` zip of `app.py`, `requirements.txt`, `templates`, `static` → curl zipdeploy. Then optional mail. |
| `sonar-scan.ps1` | JDK17, coverage pytest, `ensure_quality_gate.py`, scanner jar + `qualitygate.wait=true`, mails start + pass/fail. |
| `sonar-project.properties` | `sonar.host.url=http://127.0.0.1:9000`, `sonar.projectKey=branch-rule-test`, exclusions, coverage.xml, coverage.exclusions templates/static. |
| `sonar-scan.ps1` jar | `java.exe -jar D:\sonar-scanner\lib\sonar-scanner-cli-*.jar` — **do not** use `sonar-scanner.bat` (Java 11). |
| `send-mail.py` | smtplib Gmail 587 STARTTLS. Env: `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `GMAIL_TO`. |
| `mail.ps1` | Loads **Machine** env vars, calls `send-mail.py`. |
| `notify-start.ps1` | Mail: CI/CD STARTED. |
| `ensure_quality_gate.py` | Sonar API: create/select **`pilot-gate`**, strip conditions, assign project. Token = `SONAR_TOKEN`. |
| `sonar_demo_issues.py` | **Deleted** (was intentional red gate). |

**Do not commit:** tokens, publish password, Gmail app password.

---

## 5. Windows **System** environment variables (Agent = Local System)

Must be **Machine** level (`sysdm.cpl`), then **Restart Go Agent** service. User-level vars are **invisible** to the Agent.

| Name | Purpose |
|---|---|
| `SONAR_TOKEN` | Sonar user token (never `squ_…` as **projectKey**) |
| `AZURE_PUBLISH_USER` | From publish profile XML `userName` |
| `AZURE_PUBLISH_PASS` | From publish profile `userPWD` |
| `GMAIL_USER` | `nagbishal07@gmail.com` |
| `GMAIL_APP_PASSWORD` | 16-letter App password (**not** Gmail login) |
| `GMAIL_TO` | Same or sir’s mail |
| Optional `FLASK_SECRET_KEY` | Else `os.urandom` at process start |

**Still true at last run:** Console printed `send-mail: skip (set GMAIL_USER and GMAIL_APP_PASSWORD)` — **those three Gmail vars were not set / Agent not restarted.** That is why no mail.

GoCD **Admin → Server configuration → Email** **Send Test Email** = `Not Acceptable`. **Do not debug that UI.** Mail path is Python on the Agent.

Gmail App password URL: https://myaccount.google.com/apppasswords (2FA on).

---

## 6. Sonar quality gate (why GoCD was red for days)

- Scanner **works**. Report **uploads**. Fail is **`QUALITY GATE STATUS: FAILED`** then GoCD exits 2 → **deploy skipped**.
- Default **Sonar way** needs coverage ≥ 80% on new code, 100% hotspots reviewed, 0 issues. HTML/templates and a **CSRF hotspot** (`Flask(__name__)` without CSRF) kept it red.
- CSRF **fixed in code** (`CSRFProtect` + flask-wtf).
- User created **`pilot-gate`**. Last instruction: trash Coverage / Hotspots / Duplication; keep Issues or none; **Projects → Without → add `branch-rule-test`**.
- There were **two** projects named `branch-rule-test`. **Use the one with ~400 LOC Python, recent analysis, ~90% coverage.** Ignore the old 188-LOC HTML card.
- Last code also runs `ensure_quality_gate.py` so the pipeline can assign **pilot-gate** via API.

**If sonar is red:** open `http://127.0.0.1:9000/dashboard?id=branch-rule-test` and read the **Quality Gate** condition list. Do not “fix Java” or “fix pytest” — those already passed.

**Sonar must stay up:** Windows service **SonarQube**. If log is `Failed to connect to /127.0.0.1:9000` → `net start SonarQube`. Do not run a second `StartSonar.bat`.

**Java:** `UnsupportedClassVersionError` class 61 = need JDK **17**. Scanner `.bat` was Java 11; **jar + JAVA_HOME=jdk-17** is the workaround. Paging-file / G1 512MB errors on AVD were earlier; they use `-Xms64m -Xmx256m -XX:+UseSerialGC`.

---

## 7. Emails that should exist (after Gmail vars work)

| Event | How |
|---|---|
| CI/CD started | `notify-start.ps1` first task of **test** |
| Sonar started | start of `sonar-scan.ps1` |
| Sonar PASSED / FAILED | after scanner; body includes dashboard URL |
| Deploy OK | end of `deploy.ps1` |

Subjects like `[GoCD] CI/CD STARTED …`, `[GoCD] SonarQube FAILED …`.

Dashboard link `http://127.0.0.1:9000/...` only works **on the AVD**, not on a phone unless they tunnel.

**SonarCloud GitHub emails** (quality gate on PRs) are a **different product**. Do not confuse with this local Sonar.

---

## 8. App behaviour (Flask)

- `/` operator board: checklist (test/sonar/deploy), notes CRUD, search, persist `data/store.json` (gitignored).
- `/pipeline` `/health` JSON `/health/ui` `/export.json`
- Footer version `APP_VERSION` (last bump `2026.09.08-qg` then mail commit `ac67b0e` did not bump again).
- In-process + JSON file; Azure restart may lose notes if wwwroot is replaced by zipdeploy.

---

## 9. Git / PRs already done

- Direct pushes to `main` were **allowed** for this login (company rules are stricter elsewhere).
- `feat/full-website` was merged to **main** (#104) **skipping rc** once; later `rc/full-website` + `feat/website-rc` existed for feat→rc demo.
- Last **main** commit at handoff: **`ac67b0e`** — *Mail at CI start, Sonar start, and Sonar pass or fail*.

---

## 10. Known pitfalls (copy these; they cost hours)

1. GoCD YAML: **2-space indent**. `cmd /c "%VAR%"` often **does not expand** for the service → use **PowerShell + `[Environment]::GetEnvironmentVariable(..., "Machine")`**.
2. `sonar.projectKey` must **not** be a token (`squ_…`).
3. `python` not on Agent PATH → **full path** to Python313.
4. `sonar-scanner` not on PATH for the service; use **full path / jar**.
5. zipdeploy **401** = wrong SCM user/pass or Basic auth off; **curl 6** = wrong hostname (`test-webapp.scm.azurewebsites.net` is wrong; use **unique** scm host).
6. PowerShell `Send-MailMessage` with `$cred` **before** `$pass` is defined → 5.7.0. GoCD mailhost 406. Use **`send-mail.py`**.
7. Execution policy: `powershell -ExecutionPolicy Bypass -File …`
8. Config repo parse error “Expected a block end” = YAML indent/list under `arguments`.
9. Quality gate **Blocks deploy by design** while `qualitygate.wait=true`.

---

## 11. What is DONE vs PENDING

**Done (pilot):**

- GoCD pipeline-as-code from GitHub `main`
- pytest on Agent
- Sonar scan + wait + local server as Windows service
- Azure zipdeploy via publish profile
- Flask demo site with CSRF, tests
- Mail **code** for start / sonar start / pass / fail / deploy
- `pilot-gate` + API helper
- Branch-rule experiments on GitHub (separate from GoCD)

**Pending / next work (start here):**

1. **Set GMAIL_* Machine vars + restart Go Agent.** Prove Console `send-mail: sent to …` and inbox (Spam). This was **not** finished.
2. Confirm last runs: **sonar green** after `pilot-gate` + project attached; **deploy green**; site footer updates.
3. If `ensure_quality_gate.py` logs **403**, Sonar token needs Administer on project/gates.
4. **Company AVD / real Python repos:** copy this pattern (YAML, `sonar-project.properties`, `deploy.ps1` with **that** app’s SCM host, Machine vars). Do not copy `test-webapp` URL blindly.
5. Prod story still missing vs original design: feat→rc merge, **tag on rc**, PR rc→main, **manual approval** in GoCD, GitHub Release notes, rollback workflow, Function App + App Service together, zero-downtime slot (optional).
6. Upgrade SonarScanner CLI (4.3 is old); keep Java 17.
7. Rotate leaked GitHub PAT / Gmail app password.
8. Do not use GoCD Email server UI.

---

## 12. How to run / verify (AVD)

```text
Browser  http://127.0.0.1:8153     GoCD
         http://127.0.0.1:9000     Sonar  (project branch-rule-test)
services.msc  Go Agent, SonarQube  both Running, Automatic
GoCD dashboard  pipeline pilot-ascode  History
```

Trigger: `git push origin main` or Play.  
Azure: Deployment Center / Kudu or browse the unique hostname.

---

## 13. Commands that work on that AVD (reference)

```bat
cd /d D:\sonarqube\bin\windows-x86-64
net start SonarQube
```

```powershell
# Machine env (example names only — do not put secrets in git)
# sysdm.cpl → System variables
```

Deploy zip (already in `deploy.ps1`):

```text
tar -a -c -f package.zip app.py requirements.txt templates static
curl.exe -f -S -X POST -u USER:PASS --data-binary @package.zip https://test-webapp-efepekhyfscpe4fk.scm.westus3-01.azurewebsites.net/api/zipdeploy
```

---

## 14. Instructions for the next AI

- Prefer **small pushes to `main`** on `branch-rule-test` only if the user still wants the same test repo and still has a token that can push (the one in old chat is **invalid/leaked**).
- Do **not** mix Vercel + Azure in one pipeline.
- Do **not** re-debug service principal unless they have a SP that can **see subscription `aa7e7e16-…`**.
- First user-visible check: **Gmail vars + last GoCD console** (`sent` vs `skip`, sonar gate OK vs FAILED).
- If they say “same issue”: paste-match the **last ERROR line** (`Connection refused` vs `QUALITY GATE FAILED` vs `send-mail: skip` vs curl 401). Those are four different bugs.

**Resume sentence:**  
*Pilot GoCD `pilot-ascode` is on GitHub `main`; Azure zipdeploy and Sonar wait work; last commit `ac67b0e` adds pipeline Gmail; Gmail Machine vars were still missing so mail skipped; quality gate depends on `pilot-gate` attached to `branch-rule-test`.*
