# How to check FINAL Dev CI/CD

File: `docs/FINAL-dev-cicd.yml`

This is the **review** copy of the Dev pipeline (Node + Azure Function App + Graph mail placeholders).

- It is **not** under `.github/workflows/`, so GitHub Actions will **not** run it on this test repo.
- This test repo has no `package.json` and no Azure. Running this YAML as a live workflow would fail on `npm ci`.
- Live workflow on `dev` stays: `.github/workflows/dev-cicd.yml` (simulated deploy).

## Job order

1. Email 1 Started (echo / Graph later)
2. `npm ci` + `npm test`
3. `npm run build` → artifact `dev-package` from `dist/`
4. Azure login + deploy Dev Function App
5. Email 3 Succeeded (if deploy green)
6. Email 2 Failed (only if something failed)

App Service deploy is in the file as a **commented** extra step.

## Secrets this YAML needs (when you use it on a real app repo)

- `AZURE_CREDENTIALS_DEV`
- `AZURE_FUNCTIONAPP_NAME_DEV`
- `AZURE_APPSERVICE_NAME_DEV` (when you uncomment App Service)
- Graph mail secrets (when you replace the `echo` lines)
