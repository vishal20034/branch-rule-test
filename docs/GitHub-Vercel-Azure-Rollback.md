# GitHub → Vercel and Azure (with rollback)

Vercel does **not** deploy into Azure Function App or Azure App Service.
GitHub is the hub. One merge can update **both** targets. Rollback is per target.

```
feat → PR → merge to dev (or later: rc → main for prod)
                │
                ▼
         GitHub Actions
          (test + build once)
                │
     ┌──────────┴──────────┐
     ▼                     ▼
  Vercel                Azure
  website / preview     Function App  and/or  App Service
     │                     │
     ▼                     ▼
  Instant Rollback      Rollback workflow
  (previous Vercel      (previous zip artifact
   deployment)           from GitHub Actions)
```

## What goes where

| Target | Use it for | How it deploys today |
|---|---|---|
| Vercel | Public HTML + `/api/*` Python functions (preview site) | Git integration on branch `dev` (already live) |
| Azure Function App | Company API / jobs | GitHub Actions (real when `AZURE_CREDENTIALS_*` exist; simulated until then) |
| Azure App Service | Company web app | Same Actions run, second package |

You choose Function App, App Service, or both. Same git commit. Same artifacts.

## Rollback

### Azure (Function App / App Service)

1. GitHub → **Actions** → **Rollback**
2. Run workflow
3. Pick:
   - environment: `dev` or `production`
   - target: Function App, App Service, or both
   - `artifact_run_id`: the **green** Dev CI/CD (or Prod) run that has the last good packages. Find it on Actions → Dev CI/CD → run number in the URL.
4. The workflow **does not rebuild**. It downloads that zip and deploys it again.

Until Azure secrets exist, the job still downloads the old package and prints it (proves the path). After secrets are added, the same workflow calls Azure.

### Vercel

- Dashboard → Deployments → previous deployment → **Instant Rollback**
- Or Actions → Rollback → target `vercel` and paste the previous deployment URL (`vercel promote`)

Vercel rollback does **not** change Azure. Azure rollback does **not** change Vercel. If both went bad, run **target = all**.

## Secrets (per project — values change, key names stay)

| Secret / var | Used by |
|---|---|
| Vercel project env (`APP_NAME`, `APP_ENV`, `APP_SECRET`) | Vercel only |
| `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` | Actions rollback / optional CLI deploy |
| `AZURE_CREDENTIALS_DEV` / `_PROD` | Actions → Azure |
| `AZURE_FUNCTIONAPP_NAME_DEV` / `_PROD` | Which Function App |
| `AZURE_APPSERVICE_NAME_DEV` / `_PROD` | Which App Service |

Do not put Azure credentials in Vercel. Do not put Vercel tokens in Azure.

## Prod later

Same hub. Different branch (`main` after `rc-*`), different Azure names, GitHub Environment `production` with a reviewer. Rollback workflow already has a `production` choice.
