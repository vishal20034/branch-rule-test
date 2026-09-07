# branch-rule-test

Flask site used to prove GitHub → GoCD → SonarQube → Azure App Service.

- Local: `python -m flask --app app run`
- Azure startup: `gunicorn --bind=0.0.0.0:8000 app:app`
- Pipeline: `pilot-ascode` (test, sonar, deploy). Push to `main` auto-starts GoCD.
