$ErrorActionPreference = "Continue"
$subj = "[GoCD] CI/CD STARTED  $($env:GO_PIPELINE_NAME)/$($env:GO_PIPELINE_COUNTER)"
$body = @"
CI/CD started.
Pipeline: $($env:GO_PIPELINE_NAME) #$($env:GO_PIPELINE_COUNTER)
Triggered by a push to main.
Next: pytest, then SonarQube, then Azure deploy.
"@
& powershell -NoProfile -ExecutionPolicy Bypass -File mail.ps1 $subj $body
