# Production implementation steps

**GoCD + GitHub + Azure only.** No GitHub Actions. No Vercel.

Do these **in this order**. Do not start Azure prod until step 8. Do not tag until Sonar is green on `rc`.

Pilot today: push `main` → test → sonar → one App Service.  
Target: feat → `rc` → Sonar → **manual tag** → release note → **approval** → one zip → Function App + App Service → soak 6–7h → PR `rc` → `main` → rollback from previous tag.

---

## Step 1 — Freeze the rule on paper

Agree with the team (one page):

1. Nobody pushes to `rc` or `main` except via PR.  
2. feat → `rc` can merge without a reviewer (if that is still the rule).  
3. Sonar runs **only after merge to `rc`**. Fail = no tag.  
4. A person creates tag `vX.Y.Z` on `rc` **by hand**.  
5. Production deploy is **GoCD Play** (manual), from **that tag**.  
6. Soak **6–7 hours**. No `rc` → `main` during soak.  
7. After soak, PR `rc` → `main`. **`main` does not deploy.**  
8. Rollback = GoCD Play `prod-rollback` with the **previous tag**.

Use **one** branch named **`rc`** (GoCD material = one branch). If the company insists on `rc-1.4`, change the GoCD material each release, or keep a single `rc`.

---

## Step 2 — GitHub: branches and protection

On the **real** repo:

1. Create `rc` from current `main` if it does not exist.  
   `git checkout main && git pull && git checkout -b rc && git push -u origin rc`  
2. **Settings → Branches → Add rule** for `rc`:  
   - Require a pull request  
   - Do **not** allow force push  
   - Do **not** allow deletions  
   - Reviewers: **0** if feat→rc may merge without review  
3. Same for `main`:  
   - Require PR  
   - No force push  
   - Reviewers: at least **1** (release after soak)  
4. Optional: restrict who can create tags `v*`.  
5. Confirm a feat branch **cannot** push to `rc`/`main` directly.

Do **not** add GitHub Actions.

---

## Step 3 — Azure production apps

1. Create (or reuse) **two** Linux apps in the **prod** resource group:  
   - Function App  
   - App Service (Python)  
2. Plan **not F1** (B1 or higher). F1 quota **stops** the app → zipdeploy 403.  
3. Each app:  
   - **SCM Basic Auth Publishing = On**  
   - **Download publish profile** → MSDeploy `userName` / `userPWD`  
   - Copy the **unique** SCM host  
     `https://<app>-<hash>.scm.<region>-01.azurewebsites.net/api/zipdeploy`  
4. App Service **Startup Command**:

```text
python -m pip install -r requirements.txt && gunicorn --bind=0.0.0.0:8000 app:app
```

   (Function App: its own runtime / `functionapp` deploy zip as that project requires.)

5. Optional: Application Insights on both (for soak).

Write down four values: FA user, FA pass, FA URL, Web user, Web pass, Web URL.

---

## Step 4 — AVD: keep what already works

On the AVD, confirm:

- JDK 17  
- Python **full path**  
- SonarQube **Windows service** Running (`http://127.0.0.1:9000`)  
- SonarScanner jar + Java 17  
- Go Server + Go Agent **Automatic**  
- Machine env vars (then **Restart Go Agent**):

| Name | Use |
|---|---|
| `SONAR_TOKEN` | Scanner (never as projectKey) |
| `GMAIL_USER` `GMAIL_APP_PASSWORD` `GMAIL_TO` | Pipeline mail |
| `AZURE_FA_USER` `AZURE_FA_PASS` | Function App publish |
| `AZURE_FA_URL` | Function zipdeploy URL |
| `AZURE_WEB_USER` `AZURE_WEB_PASS` | App Service publish |
| `AZURE_WEB_URL` | App Service zipdeploy URL |

Copy `send-mail.py`, `mail.ps1`, `notify-start.ps1`, `sonar-scan.ps1`, `ensure_quality_gate.py` from the pilot. Point Python path and `sonar.projectKey` at **this** repo.

Sonar: project key = repo name. Quality gate **`pilot-gate`** (no coverage/hotspot wall) **or** a real gate the team accepts. Attach it to this project.

---

## Step 5 — GoCD pipeline `quality` (rc only, no Azure)

1. In YAML, pipeline **`quality`**:  
   - Material: git URL, **`branch: rc`**  
   - Stage **notify** → `notify-start.ps1`  
   - Stage **test** → pytest (full Python path)  
   - Stage **sonar** → `sonar-scan.ps1` (`qualitygate.wait=true`)  
   - **No deploy stage**  
2. Remove or **disable** auto-deploy from `main` (`pilot-ascode` deploy).  
3. Config repo refresh.  
4. **Prove:** open PR `feat-*` → `rc`, merge, GoCD runs, Sonar mail pass or fail.  
5. If Sonar **fails**, do **not** tag. Fix code, PR again.

This is table steps **1–3**.

---

## Step 6 — Tagging rule (people, not GoCD)

After **`quality` is green** on that commit:

```bat
git checkout rc
git pull
git tag v1.0.0
git push origin v1.0.0
```

Tag the **merge commit** that passed Sonar, not a random commit.

This is table step **4**.

---

## Step 7 — GitHub Release note (people)

On GitHub → **Releases** → **Draft** from tag `v1.0.0`:

- What changed  
- What to watch in soak  
- Rollback: Play GoCD pipeline `prod-rollback`, tag `v0.x` (previous)

This is table step **5**. GoCD does not have to write the note. Do this **before** Play `prod`.

---

## Step 8 — GoCD pipeline `prod` (manual, from tag)

New YAML pipeline **`prod`**:

1. **Do not** auto-trigger from git.  
   `timer` off. Start = **Play** only (or first stage manual).  
2. Parameter / env: `GIT_TAG` (example `v1.0.0`).  
3. Stages, in order:

**A. approve** (table step 6)

```yaml
approval: type: manual
```

Only named roles in GoCD **Authorization** can pass this. It waits forever until they click.

**B. build** (table step 7 — once)

- `git fetch --tags`  
- `git checkout %GIT_TAG%`  
- Create **one** `package.zip` (or two zips if Function and Web need different layouts — still **one** stage, **same tag**)  
- `artifacts:` save the zip(s) on the job  

**C. deploy**

- Mail “CI/CD started”  
- `curl` zip to **Function App** SCM URL  
- `curl` zip to **App Service** SCM URL  
- Mail success or failure  

**D. soak** (table step 9)

```yaml
approval: type: manual
```

Nobody clicks this until **6–7 hours** of watching prod (logs, Insights, errors). This click **is** the soak sign-off.

4. Authorization: who may Play `prod` and who may pass **approve** / **soak**.

---

## Step 9 — First production Play

1. Sonar green on `rc`.  
2. Tag `v1.0.0` pushed.  
3. Release note published.  
4. GoCD → `prod` → **Play** → enter `GIT_TAG=v1.0.0`.  
5. Approver passes **approve**.  
6. Wait until Function + App Service are **Running**, health URLs OK.  
7. Wait **6–7 hours**. Do **not** merge to `main`.  
8. Approver passes **soak**.

This is table steps **6–9**.

---

## Step 10 — PR `rc` → `main` (table step 10)

1. GitHub: PR `rc` → `main`.  
2. Reviewer approves. Merge.  
3. Confirm **no** GoCD pipeline deploys on `main`.  
4. `main` is now the **record** of the soaked release.

---

## Step 11 — Pipeline `prod-rollback`

New YAML pipeline **`prod-rollback`**:

- Play only, parameter `GIT_TAG` = **previous** good tag  
- Manual approval  
- Fetch zip from that pipeline run’s **artifacts**, **or** `git checkout` that tag and rebuild the **same** zip script  
- Deploy **same** two Azure URLs  
- Mail “rollback started / succeeded / failed”

**Prove once** on a test tag before you need it in an incident.

---

## Step 12 — Definition of done (all requirements)

You are finished when you have **walked one fake release** like this:

1. feat PR → `rc` → merge  
2. `quality` green + mail  
3. Tag `v1.0.0`  
4. GitHub Release text  
5. `prod` waits on **approve** until a person clicks  
6. One zip → **both** Azure apps  
7. Artifact visible in GoCD  
8. `soak` waits; after 6–7h (or a short test wait) click  
9. PR `rc` → `main`  
10. `prod-rollback` to previous tag restores the old site  

If any of those ten fail, that requirement is **not** implemented yet.

---

## Do not

- Deploy from `main`  
- Put Sonar on feat branches  
- Use GitHub Actions for Azure  
- Skip manual approve  
- Merge to `main` during soak  
- Use F1 for prod  
- Put secrets in git (System env vars only)

---

## Order reminder (one line)

**Protect branches → quality on `rc` → tag by hand → Release note → Play `prod` (approve → zip → two apps) → soak click → PR to `main` → keep `prod-rollback`.**
