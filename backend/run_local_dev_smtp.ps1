# Starts the LOCAL backend (local_dev.db, http://localhost:8000) with REAL email delivery.
#   .\run_local_dev_smtp.ps1 -EnvFile staging.hostinger.env   Hostinger mailbox (mailbox password)
#   .\run_local_dev_smtp.ps1                                  Gmail from staging.env (16-letter App Password)
# The password is typed at the prompt and lives only in this window's environment. It never uses school.db.
param([string]$EnvFile = "staging.env")
Set-Location $PSScriptRoot
if (-not (Test-Path "local_dev.db")) { Write-Host "local_dev.db was not found. Nothing was started."; exit 1 }
if (-not (Test-Path $EnvFile)) { Write-Host "$EnvFile was not found. Nothing was started."; exit 1 }

Get-Content $EnvFile | Where-Object { $_ -match '^\s*[A-Z_]+=' } | ForEach-Object { $k, $v = $_ -split '=', 2; Set-Item "env:$k" $v.Trim() }
$secure = Read-Host "Mailbox password for $env:SMTP_USERNAME" -AsSecureString
$password = [System.Net.NetworkCredential]::new("", $secure).Password
if ($env:SMTP_HOST -match 'gmail\.com$') {
    $password = $password -replace '[\s ​-‏⁠﻿"''`]', ''
    if ($password -notmatch '^[A-Za-z]{16}$') { Write-Host "That is $($password.Length) characters (a Gmail App Password is exactly 16 letters). Nothing was started."; exit 1 }
}
if (-not $password) { Write-Host "No password entered. Nothing was started."; exit 1 }

$env:SMTP_PASSWORD = $password
$env:DATABASE_URL = "sqlite:///local_dev.db"
$env:APP_ENV = "development"
Write-Host "Starting on local_dev.db with REAL email via $env:SMTP_HOST (credentials not shown). Ctrl+C stops it."
python -m uvicorn main:app --host 127.0.0.1 --port 8000
