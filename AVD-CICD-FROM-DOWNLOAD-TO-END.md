# GoCD + SonarQube + Azure — from download to first green deploy

Do these steps **in order** on the **AVD**. Do not skip. This is the path that worked on the pilot (`branch-rule-test` → `test-webapp`).

When you copy this to a **real** company repo, only the **names** change (git URL, app name, SCM URL, Python path, `sonar.projectKey`). The **order stays the same**.

---

# Part 0 — Before you start

You need:

- Windows AVD with **Admin** rights  
- GitHub repo (Python app)  
- Azure Web App (Linux, Python 3.11 is what we used)  
- A Gmail with **2-Step Verification** (for App password)  
- Browser on the AVD  

Pilot values (replace on the real AVD):

| Item | Pilot |
|---|---|
| GitHub | `https://github.com/vishal20034/branch-rule-test.git` |
| Azure app | `test-webapp` |
| Resource group | `rg-pilot-dev` |
| Unique site | `https://test-webapp-efepekhyfscpe4fk.westus3-01.azurewebsites.net` |
| SCM zip URL | `https://test-webapp-efepekhyfscpe4fk.scm.westus3-01.azurewebsites.net/api/zipdeploy` |
| GoCD | `http://127.0.0.1:8153` |
| Sonar | `http://127.0.0.1:9000` |

**Do not** start with Azure CLI / service principal. That failed (wrong tenant, no subscription). Deploy is **publish profile + curl**.

---

# Part 1 — Java 17

SonarQube 25 needs **Java 17**. Java 11 gives `UnsupportedClassVersionError` (class 61).

1. Browser: download **Windows x64 MSI** JDK 17 from Oracle or Microsoft.  
2. Install to `C:\Program Files\Java\jdk-17`.  
3. **New Administrator Command Prompt**:

```bat
"C:\Program Files\Java\jdk-17\bin\java.exe" -version
```

You must see `17`.

4. `Win+R` → `sysdm.cpl` → **Advanced** → **Environment Variables** → **System variables**:

   - **New** `JAVA_HOME` = `C:\Program Files\Java\jdk-17`  
   - Edit **Path** → **New** → `%JAVA_HOME%\bin`

5. Close all CMD windows. Open a **new** CMD:

```bat
java -version
echo %JAVA_HOME%
```

If `java -version` is still 11, a leftover `C:\Program Files\Common Files\Oracle\Java\javapath` is first on PATH. Move `JAVA_HOME\bin` **above** that, or always call the full `jdk-17\bin\java.exe` (the pipeline script does that).

---

# Part 2 — Python

1. Download Python 3.13 (or 3.11) Windows 64-bit from python.org.  
2. Install. **Tick “Add python.exe to PATH”**.  
3. After install, **new** CMD:

```bat
where python
python --version
```

Write down the **real** path, for example:

`C:\Users\X240\AppData\Local\Programs\Python\Python313\python.exe`

The **Go Agent service does not use your user PATH**. Every YAML/script must use this **full path**. If you see `'python' is not recognized` in GoCD, you used `python` instead of the full path.

```bat
"C:\Users\X240\AppData\Local\Programs\Python\Python313\python.exe" -m pip install pytest pytest-cov flask gunicorn flask-wtf
```

---

# Part 3 — SonarQube server (must run all the time)

## 3.1 Download and unzip

1. Download **SonarQube Community** zip (we used **25.9**).  
2. Unzip to **`D:\sonarqube`** (short path, no spaces if you can).  
3. Folder should contain `bin\windows-x86-64\StartSonar.bat`.

## 3.2 First start (to create admin)

**Administrator CMD:**

```bat
cd /d D:\sonarqube\bin\windows-x86-64
StartSonar.bat
```

Wait until the log says started. Browser: `http://127.0.0.1:9000`  
Default login **admin** / **admin**. Change the password. Keep it.

Leave this window until the **service** is installed. Then you can close it.

## 3.3 Windows service (survives reboot and logoff)

**Administrator CMD:**

```bat
cd /d D:\sonarqube\bin\windows-x86-64
dir *.bat
```

If `SonarService.bat` exists:

```bat
SonarService.bat install
sc config SonarQube start= auto
net start SonarQube
```

If it says **service already exists**:

```bat
sc config SonarQube start= auto
net start SonarQube
```

`sc config` **Access denied** = you are not in **Administrator** CMD.

If there is **no** `SonarService.bat`, use NSSM:

1. Download NSSM, unzip e.g. `C:\nssm`.  
2. Admin CMD:

```bat
C:\nssm\win64\nssm.exe install SonarQube "D:\sonarqube\bin\windows-x86-64\StartSonar.bat"
C:\nssm\win64\nssm.exe set SonarQube AppDirectory "D:\sonarqube\bin\windows-x86-64"
C:\nssm\win64\nssm.exe set SonarQube Start SERVICE_AUTO_START
C:\nssm\win64\nssm.exe start SonarQube
```

**Do not** run `StartSonar.bat` **and** the service together.

## 3.4 Check

```bat
netstat -an | find "9000"
```

Must show **LISTENING**. Browser `http://127.0.0.1:9000` works **without** a black console window.

`services.msc` → **SonarQube** → **Running**, **Automatic**.

## 3.5 Token and project

1. Sonar → user (top right) → **My Account** → **Security** → generate token. Copy once.  
2. This is **`SONAR_TOKEN`**. It is **not** the project key.  
3. Create project **Manually**.  
   - Project key / name: **same as the GitHub repo name** (pilot: `branch-rule-test`).  
   - **Never** paste the token as the project key.

## 3.6 Quality gate (or the pipeline stays red forever)

**Sonar way** fails this demo (coverage on HTML, CSRF hotspot).

1. Top → **Quality Gates** → **Create** → name `pilot-gate`.  
2. On **Conditions on New Code**, **trash**:  
   - Coverage  
   - Security Hotspots Reviewed  
   - Duplicated Lines (optional)  
3. You may keep **Issues is greater than 0**, or trash that too for a first pilot.  
4. **Projects** tab **Without** → search the project → **Add**.  
5. Tab **With** must list the project.  
6. Open the project → **Project Settings** → **Quality Gate** → **Always use a specific Quality Gate** → **pilot-gate** → Save.

The pipeline script `ensure_quality_gate.py` tries to do this via API. If the token cannot Administer, do the clicks above.

---

# Part 4 — SonarScanner CLI (the tool GoCD runs)

1. Download **SonarScanner CLI** zip. Unzip to **`D:\sonar-scanner`**.  
2. You should have `D:\sonar-scanner\bin\sonar-scanner.bat` and `D:\sonar-scanner\lib\sonar-scanner-cli-*.jar`.  
3. **Do not** trust `sonar-scanner.bat` if it prints **Java 11**. The pipeline uses:

```text
C:\Program Files\Java\jdk-17\bin\java.exe -jar D:\sonar-scanner\lib\sonar-scanner-cli-XXXX.jar
```

If AVD is low on RAM / paging file (error mapping 512MB):

```bat
setx SONAR_SCANNER_OPTS "-Xms64m -Xmx256m -XX:+UseSerialGC" /M
```

Then restart Go Agent.

---

# Part 5 — GoCD Server and Agent

1. Download **GoCD Server** and **GoCD Agent** Windows installers.  
2. Install Server first, then Agent, both as **Windows services**.  
3. Browser: `http://127.0.0.1:8153`  
4. **Admin** → **Agents**. The agent must be **idle/enabled** (not lost).  
5. If the agent never appears: `services.msc` → **Go Agent** → Running.

YAML config repo (after files exist on GitHub `main`):

1. **Admin** → **Config Repositories** → **Add**.  
2. Type: YAML.  
3. URL: your GitHub repo HTTPS.  
4. Branch: `main`.  
5. Plugin: yaml config.  
6. Save → **Check connection** / Refresh.  
7. Dashboard must show pipeline **`pilot-ascode`**.

If parse error `Expected a block end`: YAML indent is wrong (must be **2 spaces**; `arguments:` must be a list).

---

# Part 6 — Azure Web App (so deploy has a target)

## 6.1 App must be Running

Portal → App Service.

- Plan **F1 Free** + **Status: Quota exceeded** → app **stops**. **Start does not stick.** zipdeploy returns **403 This web app is stopped**.  
- **Fix:** App Service plan → **Scale up** → **B1** → Apply. Wait until **Status: Running**.

## 6.2 SCM Basic Auth

**Configuration** → **General settings**

- **SCM Basic Auth Publishing** = **On**  
- **FTP Basic Auth** = **On** if shown  
- **Save**

## 6.3 Publish profile

**Overview** → **Download publish profile**. Open the XML.

Use the **MSDeploy** entry (not FTP):

- `userName` → often `$YourAppName` (keep the `$`)  
- `userPWD` → long password  

Also copy the **publishUrl** / SCM host. If the site is `app-xxxx.region-01.azurewebsites.net`, zipdeploy is usually:

```text
https://app-xxxx.scm.region-01.azurewebsites.net/api/zipdeploy
```

**Wrong:** `https://app.scm.azurewebsites.net` (curl error 6 — host not found).

## 6.4 Startup Command (Python Linux)

**Configuration** → **General settings** → **Startup Command**:

```text
python -m pip install -r requirements.txt && gunicorn --bind=0.0.0.0:8000 app:app
```

**Save** → **Restart**.

If you skip this, Log stream shows:

- `App Command Line not configured`  
- `No module named 'flask_wtf'` (or any extra package)  
- Site **503**

zipdeploy **does not** install pip packages unless Oryx build runs. The startup line **does**.

Optional app settings:

| Name | Value |
|---|---|
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` |
| `ENABLE_ORYX_BUILD` | `true` |

## 6.5 Do not use (failed on this pilot)

- `az login` then SP on a **different** subscription  
- `az webapp deploy --username --password` (flags do not exist)  
- Mixing Vercel with this Azure zip  

---

# Part 7 — Gmail App password (pipeline mail)

GoCD **Email server → Send Test Email** returned **Not Acceptable**. **Do not use that screen** for CI mails.

1. Chrome, logged in as the mailbox that should receive mail.  
2. Open https://myaccount.google.com/apppasswords  
3. 2-Step Verification **must be On**.  
4. Create app password `gocd`. Copy **16 letters**.  

These go in **System** env vars in Part 8. Mail is sent by `send-mail.py` on the Agent.

---

# Part 8 — System environment variables

**Must be Machine (system), not User.** Go Agent runs as **Local System**.

`Win+R` → `sysdm.cpl` → **Advanced** → **Environment Variables** → **System variables** → **New** for each:

| Name | Value |
|---|---|
| `JAVA_HOME` | `C:\Program Files\Java\jdk-17` |
| `SONAR_TOKEN` | token from Part 3.5 |
| `AZURE_PUBLISH_USER` | publish profile `userName` |
| `AZURE_PUBLISH_PASS` | publish profile `userPWD` |
| `GMAIL_USER` | full Gmail |
| `GMAIL_APP_PASSWORD` | 16-letter App password, no spaces |
| `GMAIL_TO` | who receives the four pipeline mails |

Then **Administrator** `services.msc`:

- **Go Agent** → **Restart**  
- **SonarQube** → Running  

If Console later says `send-mail: skip`, these Gmail vars are missing or Agent was not restarted.

---

# Part 9 — Files on GitHub

For the **pilot**, they already exist on `main`. For a **new** repo, copy these and **edit names**.

## 9.1 `sonar-project.properties`

```
sonar.host.url=http://127.0.0.1:9000
sonar.projectKey=YOUR-REPO-NAME
sonar.projectName=YOUR-REPO-NAME
sonar.sources=.
sonar.tests=tests
sonar.python.version=3.11
sonar.exclusions=**/.git/**,**/venv/**,**/.venv/**,**/__pycache__/**,**/.github/**,**/package.zip,**/*.gocd.yaml,**/*.ps1,coverage.xml,send-mail.py
sonar.test.inclusions=tests/**
sonar.python.coverage.reportPaths=coverage.xml
sonar.sourceEncoding=UTF-8
sonar.coverage.exclusions=templates/**,static/**
```

## 9.2 `pilot-ascode.gocd.yaml`

- `git:` your repo HTTPS  
- `branch: main`  
- Python **full path** in the pytest task  
- Stages: **test** (notify-start + pytest) → **sonar** (`sonar-scan.ps1`) → **deploy** (`deploy.ps1`)  
- **2-space indent** only  

## 9.3 Scripts (copy from the pilot repo, then edit)

| File | Edit |
|---|---|
| `sonar-scan.ps1` | Python path, scanner jar folder `D:\sonar-scanner`, JDK 17 path |
| `deploy.ps1` | SCM zip URL, `tar` file list for **that** app |
| `send-mail.py` `mail.ps1` `notify-start.ps1` | Python path in `mail.ps1` |
| `ensure_quality_gate.py` | project key |
| `startup.sh` `.deployment` | include in the zip |

**Real company repo:** keep **their** `app.py` / packages. Do **not** overwrite with the demo Flask board. Only add the pipeline files. In `deploy.ps1`, zip **their** source (or the folders Azure needs).

Demo Flask (pilot only): `app.py`, `templates/`, `static/`, `requirements.txt`, `tests/`.

Push to **`main`**.

---

# Part 10 — First run (end to end)

1. Browser GoCD `http://127.0.0.1:8153` — pipeline visible.  
2. Browser Sonar `http://127.0.0.1:9000` — project + **pilot-gate** attached.  
3. Azure Overview **Running**.  
4. Push to `main` **or** GoCD **Play**.  

**Expected:**

| Stage | Success looks like |
|---|---|
| test | pytest passed; Console `send-mail: sent to …` (CI started) |
| sonar | Coverage xml, scanner Java 17, quality gate **OK**, mail STARTED then PASSED |
| deploy | `package.zip created`, `KUDU_HTTP=200` or `202` |

Then:

- Site loads (not 403, not 503).  
- Footer / `/health` shows the new version.  
- Inbox (and Spam): started, Sonar started, pass/fail, deploy OK.

---

# Part 11 — If a stage is red

Read the **last ERROR line** in the job Console.

| Error | What you do |
|---|---|
| `'python' is not recognized` | Full path to python.exe in YAML + scripts; restart Agent |
| `Connection refused` 127.0.0.1:9000 | `net start SonarQube` |
| Java class 61 / Java 11 in scanner log | Use jdk-17 `java.exe -jar` the scanner jar |
| `QUALITY GATE STATUS: FAILED` | Part 3.6. Open `http://127.0.0.1:9000/dashboard?id=PROJECT` |
| `send-mail: skip` | Part 8 GMAIL_* + restart Agent |
| curl **401** | New publish profile; SCM Basic Auth On; restart Agent |
| curl **403** + “web app is stopped” | Part 6.1 — Running / not F1 quota |
| curl **6** could not resolve host | Unique SCM hostname in `deploy.ps1` |
| gunicorn `No module named …` | Part 6.4 Startup Command + Restart + new deploy |
| YAML parse block end | 2-space indent; no tabs |
| PowerShell ExecutionPolicy | `-ExecutionPolicy Bypass -File` |

---

# Part 12 — What “done” means on the real AVD

You are done for that repo when **all** of these are true:

1. Push to `main` starts `pilot-ascode` by itself.  
2. pytest green.  
3. Sonar report on `:9000`. Gate green (or you accepted **pilot-gate**).  
4. Azure **Running**, site opens, Log stream has **no** worker boot error.  
5. Gmail received start + Sonar result.  
6. SonarQube and Go Agent are **Automatic** services.

---

# Part 13 — Company flow (after the pilot works)

This document’s pipeline **only watches `main`**. Later:

1. `feat-*` → PR → merge `rc-*`  
2. Tag on `rc-*`  
3. PR `rc-*` → `main` + manual check  
4. Merge to `main` runs **this** GoCD pipeline → Azure prod  

Do **not** add Vercel. Dev VS Code deploy to a **dev** slot stays **outside** this pipeline.

Zero-downtime later: **staging slot on the Production app** + swap. Without a slot, rollback = redeploy last good zip.

---

# Copy-paste checklist (print this page)

- [ ] JDK 17, `java -version` = 17  
- [ ] Python **full path** works in CMD  
- [ ] SonarQube **service** Running, `:9000`  
- [ ] Scanner jar under `D:\sonar-scanner\lib`  
- [ ] Go Server + Agent Running, pipeline listed  
- [ ] Azure app **Running**, not Quota exceeded  
- [ ] SCM Basic Auth On, publish profile in **System** vars  
- [ ] Startup Command = pip + gunicorn  
- [ ] `SONAR_TOKEN` System var (not used as projectKey)  
- [ ] GMAIL_* System vars, Agent restarted  
- [ ] `pilot-gate` attached to the project  
- [ ] YAML 2 spaces, Python full path, real SCM URL  
- [ ] First Play: test + sonar + deploy green  
- [ ] Site + mail + Sonar dashboard checked  
