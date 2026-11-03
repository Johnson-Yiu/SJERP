$ErrorActionPreference = 'Continue'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
Set-Location (Join-Path $taskRoot 'backend')
$taskPython = Join-Path (Get-Location).Path '.venv/Scripts/python.exe'
$env:DATABASE_URL = 'sqlite:///:memory:'
$env:APP_STAGE = 'development'
$env:PYTHONUTF8 = '1'
$taskEnvLog = Join-Path $PSScriptRoot 'fix01-environment.log'
$taskTestLog = Join-Path $PSScriptRoot 'fix01-regression.log'
$taskFailure = 0

$taskChecks = @(
    @{ Name = 'python --version'; Arguments = @('--version') },
    @{ Name = 'python -m pip check'; Arguments = @('-m', 'pip', 'check') },
    @{ Name = 'python -m pip freeze'; Arguments = @('-m', 'pip', 'freeze') },
    @{ Name = 'python manage.py check'; Arguments = @('manage.py', 'check') },
    @{ Name = 'python manage.py makemigrations --check --dry-run'; Arguments = @('manage.py', 'makemigrations', '--check', '--dry-run') }
)
"DATABASE_URL=sqlite:///:memory:; APP_STAGE=development; PYTHONUTF8=1" | Tee-Object -FilePath $taskEnvLog
foreach ($taskCheck in $taskChecks) {
    "COMMAND: $($taskCheck.Name)" | Tee-Object -FilePath $taskEnvLog -Append
    $taskArgs = $taskCheck.Arguments
    & $taskPython @taskArgs 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath $taskEnvLog -Append
    $taskExit = $LASTEXITCODE
    "EXIT_CODE=$taskExit" | Tee-Object -FilePath $taskEnvLog -Append
    if ($taskExit -ne 0) { $taskFailure = 1 }
}

$taskArgs = @('manage.py', 'test', 'crm.tests.test_history_import_preflight', 'crm.tests.test_csv_upload_http_413', 'crm.tests.test_safe_csv_import', 'crm.tests.test_historical_orders', '--verbosity', '2')
'COMMAND: python manage.py test crm.tests.test_history_import_preflight crm.tests.test_csv_upload_http_413 crm.tests.test_safe_csv_import crm.tests.test_historical_orders --verbosity 2' | Tee-Object -FilePath $taskTestLog
'& configured Python from backend/.venv; DATABASE_URL=sqlite:///:memory:; APP_STAGE=development; PYTHONUTF8=1' | Tee-Object -FilePath $taskTestLog -Append
& $taskPython @taskArgs 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath $taskTestLog -Append
$taskExit = $LASTEXITCODE
"EXIT_CODE=$taskExit" | Tee-Object -FilePath $taskTestLog -Append
if ($taskExit -ne 0) { $taskFailure = 1 }
exit $taskFailure
