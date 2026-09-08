$ErrorActionPreference = "Continue"
$py = "C:/Users/X240/AppData/Local/Programs/Python/Python313/python.exe"
$env:GMAIL_USER = [Environment]::GetEnvironmentVariable("GMAIL_USER", "Machine")
$env:GMAIL_APP_PASSWORD = [Environment]::GetEnvironmentVariable("GMAIL_APP_PASSWORD", "Machine")
$env:GMAIL_TO = [Environment]::GetEnvironmentVariable("GMAIL_TO", "Machine")
$subj = $args[0]
$body = $args[1]
if (-not $subj) { $subj = "GoCD" }
if (-not $body) { $body = "" }
& $py send-mail.py $subj $body
