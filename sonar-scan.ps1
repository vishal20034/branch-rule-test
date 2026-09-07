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

Write-Host "Using jar $($jar.FullName)"
& $java -Xms64m -Xmx256m -XX:+UseSerialGC -jar $jar.FullName "-Dsonar.token=$t" "-Dsonar.qualitygate.wait=true"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
