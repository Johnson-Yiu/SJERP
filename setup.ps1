$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$Requirements = Join-Path $ProjectRoot "backend\requirements.txt"

if (-not (Get-Command python.exe -ErrorAction SilentlyContinue)) {
    throw "Python was not found. Install Python 3.10 or later, then run this file again."
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "Node.js was not found. Install Node.js LTS, then run this file again."
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "Creating Python environment..."
    & python.exe -m venv $VenvPath
}

Write-Host "Installing backend dependencies..."
& $VenvPython -m pip install -r $Requirements

Write-Host "Installing frontend dependencies..."
Push-Location (Join-Path $ProjectRoot "frontend")
try {
    & npm.cmd install
}
finally {
    Pop-Location
}

Write-Host "Preparing database..."
& $VenvPython (Join-Path $ProjectRoot "backend\manage.py") migrate
& $VenvPython (Join-Path $ProjectRoot "backend\manage.py") seed_demo

Write-Host "Setup complete. Starting the service..." -ForegroundColor Green
