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
if (-not $jdk) {
  throw "JDK 17 folder not found under Program Files\Java or Microsoft. Install JDK 17 first."
}

$env:JAVA_HOME = $jdk.FullName
$env:Path = "$env:JAVA_HOME\bin;" + $env:Path
Write-Host "JAVA_HOME=$env:JAVA_HOME"
& "$env:JAVA_HOME\bin\java.exe" -version

$env:SONAR_SCANNER_OPTS = [Environment]::GetEnvironmentVariable("SONAR_SCANNER_OPTS", "Machine")
if (-not $env:SONAR_SCANNER_OPTS) {
  $env:SONAR_SCANNER_OPTS = "-Xms64m -Xmx256m -XX:+UseSerialGC"
}
$t = [Environment]::GetEnvironmentVariable("SONAR_TOKEN", "Machine")
if (-not $t) { throw "missing SONAR_TOKEN system variable" }

& "D:\sonar-scanner\bin\sonar-scanner.bat" "-Dsonar.token=$t" "-Dsonar.qualitygate.wait=true"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
