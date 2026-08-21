$ErrorActionPreference = "Stop"

$BranchRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent $BranchRoot)
$VenvPython = Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"
$PythonExe = if (Test-Path -LiteralPath $VenvPython) { $VenvPython } else { "python.exe" }
$BackendDir = Join-Path $BranchRoot "backend"
$FrontendDir = Join-Path $BranchRoot "frontend"
$BackendPort = 8138
$FrontendPort = 5228

function Test-PortOpen([int] $Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $connection.AsyncWaitHandle.WaitOne(300)) { return $false }
        $client.EndConnect($connection)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Wait-ForPort([int] $Port, [int] $TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortOpen $Port) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

if (-not (Test-Path -LiteralPath $BackendDir)) { throw "Backend directory not found: $BackendDir" }
if (-not (Test-Path -LiteralPath $FrontendDir)) { throw "Frontend directory not found: $FrontendDir" }
if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules"))) {
    throw "Frontend dependencies are missing. Run npm install in $FrontendDir first."
}

$url = "http://127.0.0.1:$FrontendPort/inventory"
$backendAlreadyRunning = Test-PortOpen $BackendPort
$frontendAlreadyRunning = Test-PortOpen $FrontendPort
if ($backendAlreadyRunning -and $frontendAlreadyRunning) {
    Write-Host "Inventory fulfillment branch is already running: $url" -ForegroundColor Green
    Start-Process $url
    exit 0
}
if ($backendAlreadyRunning -or $frontendAlreadyRunning) {
    throw "Only one branch service is running. Stop the service using port(s) $(@($BackendPort, $FrontendPort | Where-Object { Test-PortOpen $_ }) -join ', ') before restarting."
}

Write-Host "Applying inventory fulfillment branch migrations..."
& $PythonExe (Join-Path $BackendDir "manage.py") migrate --noinput
if ($LASTEXITCODE -ne 0) { throw "Database migration failed. Services were not started." }

Start-Process -FilePath $PythonExe -ArgumentList "manage.py runserver 127.0.0.1:$BackendPort --noreload" -WorkingDirectory $BackendDir -WindowStyle Hidden
$env:VITE_API_PROXY_PORT = $BackendPort
Start-Process -FilePath "npm.cmd" -ArgumentList "run dev -- --host 127.0.0.1 --port $FrontendPort --strictPort" -WorkingDirectory $FrontendDir -WindowStyle Hidden

if (-not (Wait-ForPort $BackendPort 20)) { throw "Backend failed to start on port $BackendPort." }
if (-not (Wait-ForPort $FrontendPort 20)) { throw "Frontend failed to start on port $FrontendPort." }

Write-Host "Inventory fulfillment branch is running: $url" -ForegroundColor Green
Start-Process $url
