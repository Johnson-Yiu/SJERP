$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Worktree = Join-Path $ProjectRoot ".worktrees\quotation-template-revamp"
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$BackendDir = Join-Path $Worktree "backend"
$FrontendDir = Join-Path $Worktree "frontend"

if (-not (Test-Path -LiteralPath $Worktree)) {
    throw "Feature worktree not found: $Worktree"
}
if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python environment not found: $PythonExe. Run setup.ps1 in the project root first."
}
if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules"))) {
    throw "Feature frontend dependencies are missing. Run npm install in $FrontendDir first."
}

$occupied = foreach ($port in 8100, 5191) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { $port }
}
if ($occupied) {
    Write-Host "Ports $($occupied -join ', ') are occupied by an existing service." -ForegroundColor Yellow
    Write-Host "Stop the existing service (or press Ctrl+C in its terminal), then run this launcher again."
    exit 1
}

Start-Process -FilePath $PythonExe -ArgumentList "manage.py runserver 127.0.0.1:8100 --noreload" -WorkingDirectory $BackendDir -WindowStyle Hidden
Start-Process -FilePath "npm.cmd" -ArgumentList "run dev -- --host 127.0.0.1 --port 5191 --strictPort" -WorkingDirectory $FrontendDir -WindowStyle Hidden

for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    if ((Get-NetTCPConnection -LocalPort 8100 -State Listen -ErrorAction SilentlyContinue) -and (Get-NetTCPConnection -LocalPort 5191 -State Listen -ErrorAction SilentlyContinue)) {
        Start-Process "http://127.0.0.1:5191/quotes"
        Write-Host "Quotation feature branch is running: http://127.0.0.1:5191/quotes" -ForegroundColor Green
        exit 0
    }
}

throw "Feature service did not start within 20 seconds. Check Python and npm dependencies."
