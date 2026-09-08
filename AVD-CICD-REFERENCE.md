# AVD CI/CD — what actually works (keep this)

Use this on the **real AVD**. Only steps that we proved. Skip the failed experiments.

**Pilot repo:** https://github.com/vishal20034/branch-rule-test  
**Pilot Azure app:** `test-webapp` in `rg-pilot-dev` (Linux Python 3.11)

---

## What the pipeline does

```
git push origin main
    → GoCD pipeline  pilot-ascode
        1. test     pytest
        2. sonar    SonarScanner + quality gate
        3. deploy   zip → Azure Kudu zipdeploy
```

Mail (from the **Agent**, not GoCD Email server):

- CI/CD started  
- Sonar started  
- Sonar PASSED or FAILED (link to local Sonar dashboard)  
- Deploy OK  

---

## Install on the AVD (once)

| Piece | Notes |
|---|---|
| **Go Server + Go Agent** | Windows services, Automatic |
| **Python** | Full path, e.g. `C:\Users\<user>\AppData\Local\Programs\Python\Python313\python.exe`. Agent **does not** see `python` on PATH. |
| **JDK 17** | `C:\Program Files\Java\jdk-17`. Scanner `.bat` used Java 11 and failed. Call **`java.exe -jar sonar-scanner-cli-*.jar`**. |
| **SonarQube** | `D:\sonarqube`. Install **Windows service** `SonarQube`, start=auto. URL `http://127.0.0.1:9000`. Do not rely on `StartSonar.bat` (dies on logoff). |
| **SonarScanner** | e.g. `D:\sonar-scanner`. Old CLI 4.3 is OK **if** you use JDK 17 + jar. |
| **Azure CLI** | **Not required** for this deploy method. |
| **curl.exe** | Built into Windows. Used for zipdeploy. |

Memory: set `SONAR_SCANNER_OPTS=-Xms64m -Xmx256m -XX:+UseSerialGC` if AVD paging file is small.

---

## Azure (what worked)

**Do not** use service principal + `az webapp deploy` unless the SP can **see the same subscription as the Web App**. We logged into the **wrong tenant**; SP had **no subscriptions**.

**Do this instead:**

1. Portal → Web App → **Configuration → General settings**  
   - **SCM Basic Auth Publishing = On**  
2. **Download publish profile** → use **MSDeploy** `userName` / `userPWD` (name looks like `$appname`).  
3. Put them in **System** env vars (below).  
4. Deploy URL is the **unique SCM host**, not `app.scm.azurewebsites.net`:  
   `https://<app>-<hash>.scm.<region>-01.azurewebsites.net/api/zipdeploy`  
5. **Startup Command** (Python Linux):

```text
python -m pip install -r requirements.txt && gunicorn --bind=0.0.0.0:8000 app:app
```

Zipdeploy **does not** run pip by itself. Without that command you get **503** and `ModuleNotFoundError` (we hit `flask_wtf`).

**F1 Free:** **Quota exceeded** → app **Stopped** → zipdeploy **403 “This web app is stopped”**. **Start will not stick.** Scale plan **F1 → B1** (or wait for quota reset).

---

## System environment variables (Machine)

`Win+R` → `sysdm.cpl` → **Advanced** → **Environment Variables** → **System variables** (bottom).

Then **Restart Go Agent** (Local System **cannot** see User vars).

| Name | What |
|---|---|
| `SONAR_TOKEN` | Sonar user token. **Never** use the token as `sonar.projectKey`. |
| `AZURE_PUBLISH_USER` | From publish profile `userName` |
| `AZURE_PUBLISH_PASS` | From publish profile `userPWD` |
| `GMAIL_USER` | Full Gmail |
| `GMAIL_APP_PASSWORD` | 16-letter App password (not Gmail login) |
| `GMAIL_TO` | Who receives pipeline mail |

App passwords: https://myaccount.google.com/apppasswords (2FA on).

**GoCD Admin → Email server → Send Test Email** failed for us (**Not Acceptable**). **Ignore that screen.** Mail is `send-mail.py` on the Agent. Console must say `send-mail: sent to …` not `skip`.

If SMTP port **587**: **do not** tick Use SMTPS. Port **465**: tick Use SMTPS. Only if you insist on the GoCD UI.

---

## GitHub files to copy onto a real Python repo

| File | Why |
|---|---|
| `pilot-ascode.gocd.yaml` | GoCD stages. Change git URL, Python path, pipeline name. **2-space YAML.** |
| `sonar-project.properties` | `sonar.host.url`, `sonar.projectKey` = repo name, exclusions, `coverage.xml` |
| `sonar-scan.ps1` | JDK 17, pytest-cov, scanner jar, `qualitygate.wait=true`, mails |
| `ensure_quality_gate.py` | Assigns **pilot-gate** so Sonar way coverage/hotspots do not always fail |
| `deploy.ps1` | tar zip + curl zipdeploy. **Change SCM URL and zip file list** for that app. |
| `send-mail.py` `mail.ps1` `notify-start.ps1` | Pipeline Gmail |
| `startup.sh` `.deployment` | Help Azure pip install |
| `app.py` `templates/` `static/` `requirements.txt` `tests/` | Only for this **demo site**. Real repos already have their own code. |

On a **real** repo: **do not** copy `app.py`. Add the **pipeline files** only. Zip in `deploy.ps1` must list **that** app’s files (or the whole tree you need on Azure).

---

## Sonar (no UI guessing)

- Service **Running** on `:9000` or scanner: `Connection refused`.  
- Quality gate **FAILED** → GoCD **stops**, **no Azure**. That is intended.  
- **Sonar way** fails on **Coverage on new code** and **Hotspots reviewed** (HTML = 0% coverage; Flask CSRF hotspot).  
- Create gate **`pilot-gate`**, remove Coverage + Hotspots rows, **Projects → Without → add this project**.  
- Or let `ensure_quality_gate.py` do that (token needs permission).  
- Project key = `branch-rule-test` (or the new repo name). Two cards with the same name: use the **recent, Python, ~90% coverage** one.

---

## GoCD YAML rules (this broke us)

- Indent **2 spaces**. `arguments:` is a **list**.  
- Prefer **PowerShell `-File script.ps1`** over `cmd /c "%VAR%"` (service often does not expand `%VAR%`).  
- Read secrets with `[Environment]::GetEnvironmentVariable("NAME", "Machine")`.  
- `powershell -NoProfile -ExecutionPolicy Bypass -File script.ps1` (ExecutionPolicy blocked `.ps1`).  
- After YAML change: Config repos → **Refresh**, or wait; Play if it does not auto-run.

---

## Order on a **new** AVD / **new** repo

1. Install JDK 17, Python, SonarQube **service**, Scanner, Go Server+Agent.  
2. Set **Machine** env vars. Restart **Go Agent** and **SonarQube**.  
3. Copy pipeline files; fix Python path, git URL, SCM URL, zip contents, `sonar.projectKey`.  
4. Push **`main`**.  
5. Azure: SCM Basic Auth On, Startup Command (pip + gunicorn), plan **not F1** if you need it always on.  
6. First run: pytest green → Sonar (gate) → zipdeploy **200/202**.  
7. Site: not 403 (stopped/quota), not 503 (`pip` missing). Footer/version proves the new zip.

---

## Do not do (wasted time)

- Service principal on the **wrong subscription**  
- `az webapp deploy --username --password` (CLI does not take those flags)  
- SCM host `app.scm.azurewebsites.net` when the app has a **unique** `*.scm.*-01.azurewebsites.net`  
- GoCD Email server for pipeline start/fail mail  
- `sonar.projectKey` = token `squ_…`  
- Leaving Sonar as a console window  
- Mixing **Vercel** into this Azure deploy  
- Expecting F1 to stay **Running** after quota  

---

## Quick “which error is this?”

| You see | Meaning |
|---|---|
| `python` is not recognized | Use **full path** to python.exe |
| `Connection refused` `:9000` | Start **SonarQube** service |
| Java class file 61 vs 55 | JDK **17**, not 11 |
| `QUALITY GATE STATUS: FAILED` | Gate (coverage/hotspots/issues), not scanner crash |
| `send-mail: skip` | GMAIL_* Machine vars + restart Agent |
| curl **401** | Publish user/pass or Basic Auth off |
| curl **403** + “web app is stopped” | App **Stopped** / **Quota exceeded** / F1 |
| curl **6** host not found | Wrong SCM hostname |
| gunicorn `No module named …` | Startup Command must `pip install -r requirements.txt` |
| Site **503** | Worker crash (see Log stream) or still starting |

---

## Company prod flow (not fully built on this pilot)

Pilot only watches **`main`**. Later, on the real AVD:

`feat-*` → PR → `rc-*` (then tag) → PR → `main` (manual check) → this pipeline → Azure prod.

Sonar on **prod/rc path**. Dev VS Code → Azure is **separate**. Rollback = redeploy last good zip (or a **staging slot** if you need swap / zero downtime).
