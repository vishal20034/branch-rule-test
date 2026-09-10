# Run SonarScanner with JDK 17 + the CLI jar. Never use sonar-scanner.bat (that embeds Java 11).
# java.exe writes -version to stderr; do not use ErrorAction Stop around that.
$ErrorActionPreference = "Continue"

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
$ver = cmd /c "`"$java`" -version 2>&1"
Write-Host $ver


$env:Path = "$env:JAVA_HOME\bin;" + (($env:Path -split ";" | Where-Object { $_ -notmatch "sonar-scanner" }) -join ";")

$argsList = @(
    "-jar", $jar,
    "-Dsonar.host.url=$env:SONAR_HOST_URL",
    "-Dsonar.token=$env:SONAR_TOKEN",
    "-Dsonar.projectKey=branch-rule-test",
    "-Dsonar.python.version=3.11",
    "-Dsonar.sources=.",
    "-Dsonar.tests=tests",
    "-Dsonar.exclusions=**/antenv/**,**/.git/**,**/__pycache__/**,**/.scannerwork/**,**/sonar_mail.py,**/send_mail.py,**/*.ps1,**/azure-pipelines.yml",
    "-Dsonar.coverage.exclusions=templates/**,static/**,**/sonar_mail.py,**/send_mail.py",
    "-Dsonar.python.coverage.reportPaths=coverage.xml",
    "-Dsonar.qualitygate.wait=true",
    "-Dsonar.sourceEncoding=UTF-8"
)
& $java @argsList
exit $LASTEXITCODE
