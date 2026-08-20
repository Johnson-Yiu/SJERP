$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$PythonExe = if (Test-Path -LiteralPath $VenvPython) { $VenvPython } else { "python.exe" }
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$ManagePy = Join-Path $BackendDir "manage.py"

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

Write-Host "Applying database migrations..."
& $PythonExe $ManagePy migrate --noinput
if ($LASTEXITCODE -ne 0) {
    throw "Database migration failed. The services were not started."
}

if (-not (Test-PortOpen 8100)) {
    Start-Process -FilePath $PythonExe -ArgumentList "manage.py runserver 127.0.0.1:8100 --noreload" -WorkingDirectory $BackendDir -WindowStyle Hidden
}

if (-not (Test-PortOpen 5191)) {
    Start-Process -FilePath "npm.cmd" -ArgumentList "run dev -- --host 127.0.0.1 --port 5191 --strictPort" -WorkingDirectory $FrontendDir -WindowStyle Hidden
}

if (-not (Wait-ForPort 8100 20)) { throw "Backend failed to start on port 8100." }
if (-not (Wait-ForPort 5191 20)) { throw "Frontend failed to start on port 5191." }

Write-Host "Service is running:" -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:5191"
Write-Host "API:      http://127.0.0.1:8100/api/"
Start-Process "http://127.0.0.1:5191"
