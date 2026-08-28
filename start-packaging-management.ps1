$ErrorActionPreference = "Stop"

# Temporary launcher for the isolated SKU-packaging worktree.
$PrimaryRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackagingRoot = "$PrimaryRoot-sku-packaging"
$VenvPython = Join-Path $PrimaryRoot ".venv\Scripts\python.exe"
$PythonExe = if (Test-Path -LiteralPath $VenvPython) { $VenvPython } else { "python.exe" }
$BackendDir = Join-Path $PackagingRoot "backend"
$FrontendDir = Join-Path $PackagingRoot "frontend"
$BackendPort = 8141
$FrontendPort = 5241

function Test-PortOpen([int] $Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $connection.AsyncWaitHandle.WaitOne(300)) { return $false }
        $client.EndConnect($connection)
        return $true
    } catch { return $false } finally { $client.Dispose() }
}

function Wait-ForPort([int] $Port, [int] $TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortOpen $Port) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

if (-not (Test-Path -LiteralPath $BackendDir)) { throw "Packaging worktree not found: $PackagingRoot" }
if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules"))) { throw "Frontend dependencies are missing. Run npm install in $FrontendDir first." }

$url = "http://127.0.0.1:$FrontendPort/sku-packaging"
if ((Test-PortOpen $BackendPort) -and (Test-PortOpen $FrontendPort)) { Start-Process $url; exit 0 }
if ((Test-PortOpen $BackendPort) -or (Test-PortOpen $FrontendPort)) { throw "Only one packaging service is running; stop it before restarting." }

Write-Host "Applying packaging worktree migrations..."
& $PythonExe (Join-Path $BackendDir "manage.py") migrate --noinput
if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }

Start-Process -FilePath $PythonExe -ArgumentList "manage.py runserver 127.0.0.1:$BackendPort --noreload" -WorkingDirectory $BackendDir -WindowStyle Hidden
$env:VITE_API_PROXY_PORT = $BackendPort
Start-Process -FilePath "npm.cmd" -ArgumentList "run dev -- --host 127.0.0.1 --port $FrontendPort --strictPort" -WorkingDirectory $FrontendDir -WindowStyle Hidden

if (-not (Wait-ForPort $BackendPort 20)) { throw "Backend failed to start on port $BackendPort." }
if (-not (Wait-ForPort $FrontendPort 20)) { throw "Frontend failed to start on port $FrontendPort." }
Write-Host "Packaging management is running: $url" -ForegroundColor Green
Start-Process $url
