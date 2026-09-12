// Jenkins on the AVD (same PC as SonarQube). GitHub = source. Azure = host.
//
//   branch "dev"  → zip + deploy test-webapp-dev. No email. No Sonar. No Approve.
//   branch rc / rc-* / rc/* → Sonar first. Zip ONLY if gate PASS. Approve. Prod. Soak.
//   branch "main" → Sonar only. No Azure.
//   ACTION=rollback → skip Sonar, zip ROLLBACK_BRANCH, Approve, prod.

pipeline {
  agent any

  parameters {
    choice(name: 'ACTION', choices: ['ci', 'rollback'], description: 'ci = normal. rollback = old zip to prod.')
    string(name: 'ROLLBACK_BRANCH', defaultValue: 'main', description: 'Branch to zip for rollback')
  }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
    timeout(time: 10, unit: 'HOURS')
  }

  environment {
    WEBAPP_DEV     = 'test-webapp-dev'
    WEBAPP_PROD    = 'test-webapp'
    SONAR_HOST_URL = 'http://127.0.0.1:9000'
    PYTHON         = 'python'
    GMAIL_TO       = credentials('gmail-to')
  }

  stages {
    stage('Dev — zip and deploy') {
      when {
        allOf {
          branch 'dev'
          not { equals expected: 'rollback', actual: params.ACTION }
        }
      }
      steps {
        bat '''
          %PYTHON% -m pip install -q setuptools wheel
          %PYTHON% -m pip install -q -r requirements.txt pytest pytest-cov
          set PYTHONPATH=%CD%
          %PYTHON% -m pytest -q tests --tb=short
        '''
        bat '''
          if exist app.zip del /f app.zip
          tar -a -c -f app.zip app.py requirements.txt startup.sh templates static
        '''
        withCredentials([usernamePassword(credentialsId: 'azure-publish-dev', usernameVariable: 'AZ_USER', passwordVariable: 'AZ_PASS')]) {
          bat 'curl.exe -f -X POST -u "%AZ_USER%:%AZ_PASS%" --data-binary @app.zip https://%WEBAPP_DEV%.scm.azurewebsites.net/api/zipdeploy'
        }
        echo "DEV done. No email. Open the Dev URL and check right or wrong. Merge feat to dev again as needed."
      }
    }

    stage('Prod — CI/CD started mail') {
      when {
        anyOf {
          branch 'main'
          branch 'rc'
          branch pattern: 'rc/.*', comparator: 'REGEXP'
          branch pattern: 'rc-.*', comparator: 'REGEXP'
        }
      }
      steps {
        withCredentials([usernamePassword(credentialsId: 'gmail-smtp', usernameVariable: 'GMAIL_USER', passwordVariable: 'GMAIL_APP_PASSWORD')]) {
          bat '%PYTHON% send_mail.py "[CI/CD] Started" "Jenkins CI/CD started. Branch %BRANCH_NAME% build %BUILD_NUMBER%. Next: SonarQube. Zip only if gate passes."'
        }
      }
    }

    stage('Prod — SonarQube') {
      when {
        allOf {
          not { equals expected: 'rollback', actual: params.ACTION }
          anyOf {
            branch 'main'
            branch 'rc'
            branch pattern: 'rc/.*', comparator: 'REGEXP'
            branch pattern: 'rc-.*', comparator: 'REGEXP'
          }
        }
      }
      steps {
        withCredentials([
          string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN'),
          usernamePassword(credentialsId: 'gmail-smtp', usernameVariable: 'GMAIL_USER', passwordVariable: 'GMAIL_APP_PASSWORD')
        ]) {
          bat '''
            %PYTHON% send_mail.py "[CI/CD] SonarQube started" "SonarQube started for %BRANCH_NAME% build %BUILD_NUMBER%. Zip is NOT built until the quality gate passes."
            %PYTHON% -m pip install -q pytest pytest-cov fpdf2 matplotlib pypdf
            set PYTHONPATH=%CD%
            %PYTHON% -m pytest -q tests --cov=app --cov-report=xml:coverage.xml --tb=short
            powershell -NoProfile -ExecutionPolicy Bypass -File sonar-scan.ps1
          '''
        }
      }
      post {
        success {
          withCredentials([
            string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN'),
            usernamePassword(credentialsId: 'gmail-smtp', usernameVariable: 'GMAIL_USER', passwordVariable: 'GMAIL_APP_PASSWORD')
          ]) {
            bat '%PYTHON% -m pip install -q fpdf2 matplotlib pypdf && %PYTHON% sonar_mail.py PASSED "[CI/CD] SonarQube PASSED - CI/CD passed"'
          }
        }
        failure {
          withCredentials([
            string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN'),
            usernamePassword(credentialsId: 'gmail-smtp', usernameVariable: 'GMAIL_USER', passwordVariable: 'GMAIL_APP_PASSWORD')
          ]) {
            bat '''
              %PYTHON% send_mail.py "[CI/CD] FAILED because SonarQube failed" "CI/CD FAILED because SonarQube failed. Zip was NOT built. Deploy will not start. Build %BUILD_NUMBER%"
              %PYTHON% -m pip install -q fpdf2 matplotlib pypdf
              %PYTHON% sonar_mail.py FAILED "[CI/CD] FAILED because SonarQube failed"
            '''
          }
        }
      }
    }

    stage('Prod — zip (only after Sonar PASS)') {
      when {
        anyOf {
          equals expected: 'rollback', actual: params.ACTION
          branch 'rc'
          branch pattern: 'rc/.*', comparator: 'REGEXP'
          branch pattern: 'rc-.*', comparator: 'REGEXP'
        }
      }
      steps {
        script {
          if (params.ACTION == 'rollback') {
            bat "git fetch origin && git checkout -f ${params.ROLLBACK_BRANCH} || git checkout -f origin/${params.ROLLBACK_BRANCH}"
          }
        }
        bat '''
          if exist app.zip del /f app.zip
          tar -a -c -f app.zip app.py requirements.txt startup.sh templates static
        '''
        archiveArtifacts artifacts: 'app.zip', fingerprint: true
      }
    }

    stage('Prod — manual Approve') {
      when {
        anyOf {
          equals expected: 'rollback', actual: params.ACTION
          branch 'rc'
          branch pattern: 'rc/.*', comparator: 'REGEXP'
          branch pattern: 'rc-.*', comparator: 'REGEXP'
        }
      }
      steps {
        timeout(time: 72, unit: 'HOURS') {
          input message: 'Deploy this zip to PRODUCTION Azure?', ok: 'Approve'
        }
      }
    }

    stage('Prod — deploy Azure') {
      when {
        anyOf {
          equals expected: 'rollback', actual: params.ACTION
          branch 'rc'
          branch pattern: 'rc/.*', comparator: 'REGEXP'
          branch pattern: 'rc-.*', comparator: 'REGEXP'
        }
      }
      steps {
        withCredentials([
          usernamePassword(credentialsId: 'azure-publish-prod', usernameVariable: 'AZ_USER', passwordVariable: 'AZ_PASS'),
          usernamePassword(credentialsId: 'gmail-smtp', usernameVariable: 'GMAIL_USER', passwordVariable: 'GMAIL_APP_PASSWORD')
        ]) {
          bat '''
            %PYTHON% send_mail.py "[CI/CD] Deploy started" "Deploying %WEBAPP_PROD% build %BUILD_NUMBER%"
            curl.exe -f -X POST -u "%AZ_USER%:%AZ_PASS%" --data-binary @app.zip https://%WEBAPP_PROD%.scm.azurewebsites.net/api/zipdeploy
            %PYTHON% send_mail.py "[CI/CD] Implementation done" "Production is live. Do NOT merge rc into main for 6-7 hours. Soak is waiting. Build %BUILD_NUMBER%"
          '''
        }
      }
      post {
        failure {
          withCredentials([usernamePassword(credentialsId: 'gmail-smtp', usernameVariable: 'GMAIL_USER', passwordVariable: 'GMAIL_APP_PASSWORD')]) {
            bat '%PYTHON% send_mail.py "[CI/CD] Deploy FAILED" "test-webapp deploy failed build %BUILD_NUMBER%"'
          }
        }
      }
    }

    stage('Prod — soak 6-7 hours') {
      when {
        allOf {
          not { equals expected: 'rollback', actual: params.ACTION }
          anyOf {
            branch 'rc'
            branch pattern: 'rc/.*', comparator: 'REGEXP'
            branch pattern: 'rc-.*', comparator: 'REGEXP'
          }
        }
      }
      steps {
        timeout(time: 7, unit: 'HOURS') {
          input message: 'Soak: watch production 6-7 hours. Do NOT merge rc to main. Resume when healthy (or wait for timeout).', ok: 'Resume'
        }
      }
      post {
        success {
          withCredentials([usernamePassword(credentialsId: 'gmail-smtp', usernameVariable: 'GMAIL_USER', passwordVariable: 'GMAIL_APP_PASSWORD')]) {
            bat '%PYTHON% send_mail.py "[CI/CD] Soak done - PR rc to main" "6-7 hour production soak is complete. Open a pull request from rc into main. Build %BUILD_NUMBER%"'
          }
        }
      }
    }
  }
}
