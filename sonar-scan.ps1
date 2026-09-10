# Run SonarScanner with JDK 17 + the CLI jar. Never use sonar-scanner.bat (that embeds Java 11).
$ErrorActionPreference = "Stop"

if (-not $env:SONAR_TOKEN) {
    throw "SONAR_TOKEN is empty. Add it as a secret pipeline variable."
}

$env:SONAR_HOST_URL = "http://127.0.0.1:9000"
$env:JAVA_HOME = "C:\Program Files\Java\jdk-17"
$env:SONAR_SCANNER_OPTS = "-Xms64m -Xmx256m -XX:+UseSerialGC"
$java = "C:\Program Files\Java\jdk-17\bin\java.exe"
if (-not (Test-Path $java)) {
    throw "JDK 17 not found at $java"
}

$jar = $null
foreach ($p in @(
    "D:\sonar-scanner\lib\sonar-scanner-cli-4.3.0.2102.jar",
    "D:\Sonar-scanner\lib\sonar-scanner-cli-4.3.0.2102.jar",
    "C:\sonar-scanner\lib\sonar-scanner-cli-4.3.0.2102.jar"
)) {
    if (Test-Path $p) { $jar = $p; break }
}
if (-not $jar) {
    throw "sonar-scanner-cli jar not found"
}

Write-Host "JAVA_HOME=$env:JAVA_HOME"
Write-Host "java=$java"
Write-Host "jar=$jar"
$ver = & $java -version 2>&1 | Out-String
Write-Host $ver
if ($ver -notmatch 'version "17') {
    throw "Must use Java 17. Got: $ver"
}

# Do not put scanner\bin on PATH — its bundled JRE is Java 11.
$env:Path = "$env:JAVA_HOME\bin;" + (($env:Path -split ";" | Where-Object { $_ -notmatch "sonar-scanner" }) -join ";")

& $java -jar $jar `
    "-Dsonar.host.url=$env:SONAR_HOST_URL" `
    "-Dsonar.token=$env:SONAR_TOKEN" `
    "-Dsonar.projectKey=branch-rule-test" `
    "-Dsonar.python.version=3.11" `
    "-Dsonar.sources=." `
    "-Dsonar.tests=tests" `
    "-Dsonar.exclusions=**/antenv/**,**/.git/**,**/__pycache__/**,**/.scannerwork/**" `
    "-Dsonar.python.coverage.reportPaths=coverage.xml" `
    "-Dsonar.qualitygate.wait=true" `
    "-Dsonar.sourceEncoding=UTF-8"

exit $LASTEXITCODE
