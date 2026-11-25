# Real-email test of forgot-password for one teacher and one parent on local_dev.db (see local_smtp_reset_test.py).
#   .\run_local_smtp_test.ps1                              uses staging.env (Gmail)
#   .\run_local_smtp_test.ps1 -EnvFile staging.hostinger.env   uses Hostinger
# The mailbox password is typed at the prompt and exists only in this window. Nothing is stored or printed.
param([string]$EnvFile = "staging.env")
Set-Location $PSScriptRoot
if (-not (Test-Path $EnvFile)) { Write-Host "$EnvFile was not found. Nothing was started."; exit 1 }
Get-Content $EnvFile | Where-Object { $_ -match '^\s*[A-Z_]+=' } | ForEach-Object { $k, $v = $_ -split '=', 2; Set-Item "env:$k" $v.Trim() }
$secure = Read-Host "Mailbox password for $env:SMTP_USERNAME" -AsSecureString
$env:SMTP_PASSWORD = [System.Net.NetworkCredential]::new("", $secure).Password
python local_smtp_reset_test.py
Remove-Item env:SMTP_PASSWORD -ErrorAction SilentlyContinue
