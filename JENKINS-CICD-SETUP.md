# Jenkins CI/CD — same Dev / Prod rules, Jenkins instead of Azure Pipelines

Jenkins **runs the pipeline**. GitHub is still the source. Azure App Service is still where the site lives. SonarQube stays on the **same AVD**.

Turn **Azure Pipelines off** after Jenkins works, or both will deploy.

---

## What stays the same

| | Dev | Prod |
|---|---|---|
| Git | `feat-*` → merge **`dev`** | `feat-*` → merge **`rc-*`** → later **`main`** |
| Sonar / gate | No | Yes, on the AVD (`http://127.0.0.1:9000`) |
| Zip | Always | **Only if gate PASS** |
| Approve | No | Yes (Jenkins **input**) |
| Email | No | Yes (start, Sonar, deploy, soak) |
| Soak | No | 6–7 hours, then PR `rc` → `main` |
| How many times | Unlimited merges to `dev` | One release path |

---

## Install Jenkins on the AVD (once)

You already have **Java 17** at `C:\Program Files\Java\jdk-17`.

1. Browser: [https://www.jenkins.io/download/](https://www.jenkins.io/download/) → **Windows** installer.
2. Install. Set `JAVA_HOME` = `C:\Program Files\Java\jdk-17`.
3. Open `http://localhost:8080` on the AVD.
4. Unlock with the password in:
   `C:\ProgramData\Jenkins\.jenkins\secrets\initialAdminPassword`
   (or `C:\Users\<you>\.jenkins\secrets\initialAdminPassword`)
5. **Install suggested plugins**.
6. Create the first admin user. Save.

### Extra plugins (Manage Jenkins → Plugins)

- **Pipeline**
- **GitHub Branch Source**
- **Credentials Binding**
- **PowerShell**
- **Timestamper**

Restart Jenkins if it asks.

---

## PATH for the Jenkins Windows service (same class of bug as GoCD)

Jenkins as a **service** often does **not** see `python` or `az`.

1. `Win + R` → `services.msc` → **Jenkins** → Log on as **your AVD user** (the one where `python` and Java work), **not** Local System.
2. Restart the Jenkins service.
3. Confirm in a job: `python --version` and `java -version` print 3.x and 17.

---

## Credentials (Manage Jenkins → Credentials → System → Global)

| ID (type this **exactly**) | Kind | Value |
|---|---|---|
| `sonar-token` | Secret text | Sonar user token |
| `gmail-smtp` | Username with password | Gmail + **App Password** (Prod mail only) |
| `azure-publish-dev` | Username with password | Dev Web App **publish profile** user + password |
| `azure-publish-prod` | Username with password | Prod Web App **publish profile** user + password |

**Publish profile:** Azure Portal → Web App → **Download publish profile**.  
User looks like `$test-webapp` or `$test-webapp-dev`. Password is the long `userPWD`.

| `gmail-to` | Secret text | Who receives Prod mail (comma-separated) |

Enable **SCM Basic Auth Publishing** on both Web Apps (Configuration → General) or zipdeploy returns 401.

Create Azure Web App **`test-webapp-dev`** if it does not exist (Python 3.11). Prod stays **`test-webapp`**.

---

## Connect GitHub

1. GitHub → Settings → Developer settings → **PAT** (classic): `repo`, `admin:repo_hook`.
2. Jenkins → New Item → **Multibranch Pipeline** → name: `branch-rule-test`.
3. Branch Sources → **GitHub** → Credentials = the PAT → Owner/repo = `vishal20034/branch-rule-test`.
4. Behaviours: discover branches. Include `dev`, `main`, `rc*`.
5. Build Configuration: **by Jenkinsfile**, script path `Jenkinsfile`.
6. Save. Jenkins scans the repo.

**Webhook (so a merge starts a build):**  
GitHub repo → Settings → Webhooks →  
Payload URL: `http://<AVD-public-or-ngrok>:8080/github-webhook/`  
Content type: `application/json`  
Events: **Just the push event**.

If the AVD has no public IP, run `ngrok http 8080` and use that URL (same idea as Sonar ngrok).

---

## First tests

1. Merge a `feat-*` into **`dev`**. Jenkins job **Dev — zip and deploy** runs. No mail. Open the Dev URL. If wrong, merge again.
2. Merge into **`rc-*`**. Mail Started → Sonar. **If FAIL:** zip is skipped. **If PASS:** zip → job waits on **Approve** → deploy `test-webapp` → soak 6–7 hours → mail “PR rc to main”.
3. **Rollback:** Run the job with `ACTION=rollback` and `ROLLBACK_BRANCH` = last good branch. Skip Sonar. Approve. Deploy old zip.

---

## Stop Azure Pipelines (avoid two deploys)

Azure DevOps → Pipelines → this pipeline → **Pause**  
or set in `azure-pipelines.yml`:

```yaml
trigger: none
```

Keep the YAML in git as backup until Jenkins is trusted.

---

## Keep SonarQube running

Jenkins Prod **fails** if SonarQube or JDK 17 is down (same as Azure agent).

```
net start SonarQube
```

Quality gate stays **release-gate** on **new code** (0 issues, hotspots reviewed, coverage ≥ 80%, dup ≤ 3%).

---

## File in the repo

`Jenkinsfile` at the repo root. That is the only extra file Jenkins needs.  
`sonar-scan.ps1`, `send_mail.py`, `sonar_mail.py` stay as they are.
