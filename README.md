# branch-rule-test

Python Flask app on Azure App Service.

**CI/CD:** GitHub + Azure Pipelines + SonarQube. GoCD is not used.

## GitHub rules
- `feat-*` → `rc` / `rc-*` / `rc/*` (PR)
- Only those **rc** branches may PR into **main**
- Invalid PRs into `main` are closed automatically

## Azure Pipelines (`azure-pipelines.yml`)
- Push to **rc**: Build + Sonar (no deploy)
- **Run pipeline** → Action **deploy**: deploy `test-webapp`
- **Run pipeline** → Action **rollback** + **Branch to deploy**: redeploy that branch

## App
- Board `/` · Pipeline `/pipeline` · Health `/health` · About `/about`

```
python -m pip install -r requirements.txt
python -m pytest -q
python -m flask --app app run
```

Azure Startup Command:

```
python -m pip install -r requirements.txt && gunicorn --bind=0.0.0.0:8000 app:app
```
