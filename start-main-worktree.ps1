$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$ManagePy = Join-Path $BackendDir "manage.py"
$Requirements = Join-Path $BackendDir "requirements.txt"
$DatabasePath = Join-Path $BackendDir "db.sqlite3"
$BackendPort = 8100
$FrontendPort = 5191

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

function Wait-ForPortClosed([int] $Port, [int] $TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (-not (Test-PortOpen $Port)) { return $true }
        Start-Sleep -Milliseconds 250
    }
    return $false
}

function Stop-BackendServer([int] $Port) {
    $listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    foreach ($listener in $listeners) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)" -ErrorAction SilentlyContinue
        $command = [string]$process.CommandLine
        if (-not $process -or $command -notmatch "manage\.py\s+runserver") {
            throw "Port $Port is occupied by a process that is not this project's Django server. Close that process first, then run the launcher again."
        }
        $targetProcessId = $process.ProcessId
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId = $($process.ParentProcessId)" -ErrorAction SilentlyContinue
        if ($parent -and [string]$parent.CommandLine -match "manage\.py\s+runserver") {
            $targetProcessId = $parent.ProcessId
        }
        Write-Host "Restarting the existing backend service..."
        # /T stops the Django autoreloader parent and child together.
        & taskkill.exe /PID $targetProcessId /T /F | Out-Null
    }
}

function Wait-ForBackendHealth([int] $Port, [int] $TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $url = "http://127.0.0.1:$Port/api/suppliers/?page_size=1"
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return $true }
        }
        catch { }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

if (-not (Get-Command python.exe -ErrorAction SilentlyContinue)) {
    throw "Python was not found. Install Python 3.10 or later, then run this launcher again."
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "Node.js was not found. Install Node.js LTS, then run this launcher again."
}

$createdVenv = $false
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "Creating Python environment..."
    & python.exe -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { throw "Python environment creation failed." }
    $createdVenv = $true
}

if ($createdVenv) {
    Write-Host "Installing backend dependencies..."
    & $VenvPython -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }
}

if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    & npm.cmd install --prefix $FrontendDir
    if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." }
}

$databaseMissing = -not (Test-Path -LiteralPath $DatabasePath)
Write-Host "Applying database migrations..."
& $VenvPython $ManagePy migrate --noinput
if ($LASTEXITCODE -ne 0) { throw "Database migration failed. The services were not started." }

if ($databaseMissing) {
    Write-Host "Seeding demo data for the new database..."
    & $VenvPython $ManagePy seed_demo
    if ($LASTEXITCODE -ne 0) { throw "Demo data initialization failed." }
}

# Always replace an existing Django development server. A live port alone is not
# sufficient: it may be an old process whose in-memory models no longer match
# the database after migrations have run.
if (Test-PortOpen $BackendPort) {
    Stop-BackendServer $BackendPort
    if (-not (Wait-ForPortClosed $BackendPort 10)) { throw "The previous backend process did not stop." }
}
Start-Process -FilePath $VenvPython -ArgumentList "manage.py runserver 127.0.0.1:$BackendPort" -WorkingDirectory $BackendDir -WindowStyle Hidden

if (-not (Test-PortOpen $FrontendPort)) {
    $env:VITE_API_PROXY_PORT = $BackendPort
    Start-Process -FilePath "npm.cmd" -ArgumentList "run dev -- --host 127.0.0.1 --port $FrontendPort --strictPort" -WorkingDirectory $FrontendDir -WindowStyle Hidden
}

if (-not (Wait-ForPort $BackendPort 30)) { throw "Backend failed to start on port $BackendPort." }
if (-not (Wait-ForBackendHealth $BackendPort 30)) { throw "Backend started but the API health check failed. Review the backend startup log." }
if (-not (Wait-ForPort $FrontendPort 30)) { throw "Frontend failed to start on port $FrontendPort." }

$url = "http://127.0.0.1:$FrontendPort"
Write-Host "Service is running: $url" -ForegroundColor Green
Write-Host "API:              http://127.0.0.1:$BackendPort/api/"
Start-Process $url
