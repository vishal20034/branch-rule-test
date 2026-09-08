$ErrorActionPreference = "Stop"

$u = [Environment]::GetEnvironmentVariable("AZURE_PUBLISH_USER", "Machine")
$p = [Environment]::GetEnvironmentVariable("AZURE_PUBLISH_PASS", "Machine")
Write-Host ("USER=[" + $u + "] len_pass=" + $(if ($p) { $p.Length } else { 0 }))
if (-not $u -or -not $p) {
  throw "missing AZURE_PUBLISH_USER or AZURE_PUBLISH_PASS in System environment variables"
}

if (-not (Test-Path "app.py")) { throw "app.py not found in workspace" }
if (-not (Test-Path "requirements.txt")) { throw "requirements.txt not found in workspace" }

if (Test-Path "package.zip") { Remove-Item "package.zip" -Force }
& tar -a -c -f package.zip app.py requirements.txt templates static startup.sh .deployment
if (-not (Test-Path "package.zip")) { throw "package.zip was not created" }
Write-Host "package.zip created"
Get-Item "package.zip" | Format-List Name, Length

$url = "https://test-webapp-efepekhyfscpe4fk.scm.westus3-01.azurewebsites.net/api/zipdeploy"
$resp = "kudu-response.txt"
if (Test-Path $resp) { Remove-Item $resp -Force }

# Do not use curl -f; print Azure body on 403/401
$code = & curl.exe -sS -o $resp -w "%{http_code}" -X POST `
  -H "Content-Type: application/octet-stream" `
  -H "Cache-Control: no-cache" `
  -u ($u + ":" + $p) `
  --data-binary "@package.zip" `
  $url

Write-Host "KUDU_HTTP=$code"
if (Test-Path $resp) {
  Write-Host "----- kudu body -----"
  Get-Content $resp -Raw
  Write-Host "----- end body -----"
}

if ($code -ne "200" -and $code -ne "202") {
  Write-Host "zipdeploy failed. Enable SCM Basic Auth Publishing on the Web App, download a new publish profile, update AZURE_PUBLISH_USER / AZURE_PUBLISH_PASS, restart Go Agent."
  exit 22
}

$env:GMAIL_USER = [Environment]::GetEnvironmentVariable("GMAIL_USER", "Machine")
$env:GMAIL_APP_PASSWORD = [Environment]::GetEnvironmentVariable("GMAIL_APP_PASSWORD", "Machine")
$env:GMAIL_TO = [Environment]::GetEnvironmentVariable("GMAIL_TO", "Machine")
$py = "C:/Users/X240/AppData/Local/Programs/Python/Python313/python.exe"
$subj = "[GoCD] deploy OK  $($env:GO_PIPELINE_NAME)/$($env:GO_PIPELINE_COUNTER)"
$body = "Azure zipdeploy finished for $($env:GO_PIPELINE_NAME) #$($env:GO_PIPELINE_COUNTER)."
try { & $py send-mail.py $subj $body } catch { Write-Host "send-mail failed: $_" }
