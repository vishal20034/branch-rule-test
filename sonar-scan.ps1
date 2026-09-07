$env:SONAR_SCANNER_OPTS = [Environment]::GetEnvironmentVariable("SONAR_SCANNER_OPTS", "Machine")
if (-not $env:SONAR_SCANNER_OPTS) {
  $env:SONAR_SCANNER_OPTS = "-Xms64m -Xmx256m -XX:+UseSerialGC"
}
$t = [Environment]::GetEnvironmentVariable("SONAR_TOKEN", "Machine")
if (-not $t) { throw "missing SONAR_TOKEN system variable" }
& "D:\sonar-scanner\bin\sonar-scanner.bat" "-Dsonar.token=$t" "-Dsonar.qualitygate.wait=true"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
