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
& tar -a -c -f package.zip app.py requirements.txt
if (-not (Test-Path "package.zip")) { throw "package.zip was not created" }
Write-Host "package.zip created"
Get-Item "package.zip" | Format-List Name, Length

& curl.exe -f -S -X POST -u ($u + ":" + $p) --data-binary "@package.zip" "https://test-webapp-efepekhyfscpe4fk.scm.westus3-01.azurewebsites.net/api/zipdeploy"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
