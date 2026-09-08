$ErrorActionPreference = "Stop"

$jdk = $null
$roots = @(
  "C:\Program Files\Java",
  "C:\Program Files\Microsoft",
  "C:\Program Files\Eclipse Adoptium",
  "C:\Program Files\AdoptOpenJDK"
)
foreach ($root in $roots) {
  if (Test-Path $root) {
    $found = Get-ChildItem $root -Directory -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -like "jdk-17*" }
    if ($found) {
      $jdk = $found | Select-Object -First 1
      break
    }
  }
}
if (-not $jdk) { throw "JDK 17 folder not found." }

$env:JAVA_HOME = $jdk.FullName
$java = Join-Path $env:JAVA_HOME "bin\java.exe"
Write-Host "JAVA_HOME=$env:JAVA_HOME"
& $java -version

$jar = Get-ChildItem "D:\sonar-scanner\lib\sonar-scanner-cli-*.jar" -ErrorAction SilentlyContinue |
  Select-Object -First 1
if (-not $jar) {
  $jar = Get-ChildItem "D:\Sonar-scanner\lib\sonar-scanner-cli-*.jar" | Select-Object -First 1
}
if (-not $jar) { throw "sonar-scanner-cli jar not found under D:\sonar-scanner\lib" }

$t = [Environment]::GetEnvironmentVariable("SONAR_TOKEN", "Machine")
if (-not $t) { throw "missing SONAR_TOKEN system variable" }


$py = "C:/Users/X240/AppData/Local/Programs/Python/Python313/python.exe"
Write-Host "Generating Python coverage.xml"
& $py -m pip install -q -r requirements.txt pytest pytest-cov
& $py -m pytest -q --cov=app --cov-report=xml:coverage.xml
if (-not (Test-Path "coverage.xml")) { Write-Host "WARN: coverage.xml missing" }

Write-Host "Using jar $($jar.FullName)"
& $java -Xms64m -Xmx256m -XX:+UseSerialGC -jar $jar.FullName "-Dsonar.token=$t" "-Dsonar.qualitygate.wait=true"
$scanExit = $LASTEXITCODE

$env:GMAIL_USER = [Environment]::GetEnvironmentVariable("GMAIL_USER", "Machine")
$env:GMAIL_APP_PASSWORD = [Environment]::GetEnvironmentVariable("GMAIL_APP_PASSWORD", "Machine")
$env:GMAIL_TO = [Environment]::GetEnvironmentVariable("GMAIL_TO", "Machine")
$gate = if ($scanExit -eq 0) { "PASSED" } else { "FAILED" }
$subj = "[GoCD] sonar $gate  $($env:GO_PIPELINE_NAME)/$($env:GO_PIPELINE_COUNTER)"
$body = @"
pilot-ascode sonar quality gate: $gate
Pipeline: $($env:GO_PIPELINE_NAME) #$($env:GO_PIPELINE_COUNTER)
Job: $($env:GO_STAGE_NAME)/$($env:GO_JOB_NAME)
Dashboard: http://127.0.0.1:9000/dashboard?id=branch-rule-test
"@
try {
  & $py send-mail.py $subj $body
} catch {
  Write-Host "send-mail failed: $_"
}

if ($scanExit -ne 0) { exit $scanExit }
