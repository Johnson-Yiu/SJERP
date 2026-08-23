param(
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"

$WorktreeRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $WorktreeRoot "..\..")
$BackendDir = Join-Path $WorktreeRoot "backend"
$FrontendDir = Join-Path $WorktreeRoot "frontend"
$ManagePy = Join-Path $BackendDir "manage.py"

$PythonCandidates = @(
    (Join-Path $WorktreeRoot ".venv\Scripts\python.exe"),
    (Join-Path $ProjectRoot ".venv\Scripts\python.exe")
)
$PythonExe = $PythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $PythonExe) {
    $PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
}

if (-not $PythonExe) { throw "Python was not found. Run setup.ps1 in the project root first." }
if (-not (Test-Path -LiteralPath $ManagePy)) { throw "Backend entrypoint was not found: $ManagePy" }
if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules"))) {
    throw "Frontend dependencies were not found: $(Join-Path $FrontendDir 'node_modules'). Run npm install first."
}

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

$PortPairs = @(
    [pscustomobject]@{ Backend = 8139; Frontend = 5229 },
    [pscustomobject]@{ Backend = 8140; Frontend = 5230 },
    [pscustomobject]@{ Backend = 8141; Frontend = 5231 }
)

$RunningPair = $null
foreach ($pair in $PortPairs) {
    if ((Test-PortOpen $pair.Backend) -and (Test-PortOpen $pair.Frontend)) {
        $RunningPair = $pair
        break
    }
}
if ($RunningPair) {
    $url = "http://127.0.0.1:$($RunningPair.Frontend)/skus"
    if (-not $SkipBrowser) { Start-Process $url }
    Write-Host "Temporary SKU management is already running: $url" -ForegroundColor Green
    exit 0
}

$SelectedPair = $PortPairs | Where-Object {
    -not (Test-PortOpen $_.Backend) -and -not (Test-PortOpen $_.Frontend)
} | Select-Object -First 1
if (-not $SelectedPair) {
    throw "All temporary SKU management port pairs are in use."
}
$BackendPort = [int]$SelectedPair.Backend
$FrontendPort = [int]$SelectedPair.Frontend

Write-Host "Applying database migrations..."
& $PythonExe $ManagePy migrate --noinput
if ($LASTEXITCODE -ne 0) { throw "Database migration failed. Services were not started." }

$env:VITE_API_PROXY_PORT = $BackendPort
Start-Process -FilePath $PythonExe `
    -ArgumentList "manage.py runserver 127.0.0.1:$BackendPort --noreload" `
    -WorkingDirectory $BackendDir `
    -WindowStyle Hidden
Start-Process -FilePath "npm.cmd" `
    -ArgumentList "run dev -- --host 127.0.0.1 --port $FrontendPort --strictPort" `
    -WorkingDirectory $FrontendDir `
    -WindowStyle Hidden

$deadline = (Get-Date).AddSeconds(25)
while ((Get-Date) -lt $deadline) {
    if ((Test-PortOpen $BackendPort) -and (Test-PortOpen $FrontendPort)) {
        $url = "http://127.0.0.1:$FrontendPort/skus"
        if (-not $SkipBrowser) { Start-Process $url }
        Write-Host "Temporary SKU management is running: $url" -ForegroundColor Green
        exit 0
    }
    Start-Sleep -Milliseconds 500
}

throw "Temporary SKU management did not start within 25 seconds. Check the Python and npm service logs."
