# branch-rule-test

Flask operator board used to prove GitHub → GoCD → SonarQube → Azure App Service.

## App
- Board: checklist + release notes (saved in `data/store.json`)
- Health JSON: `/health`
- Export: `/export.json`

## Run locally
```
python -m pip install -r requirements.txt
python -m pytest -q
python -m flask --app app run
```

## Azure
Startup command: `gunicorn --bind=0.0.0.0:8000 app:app`

## Pipeline
`pilot-ascode` on branch `main`: test → sonar → deploy.
Gmail is sent from `send-mail.py` on the Agent (not GoCD Email server).
