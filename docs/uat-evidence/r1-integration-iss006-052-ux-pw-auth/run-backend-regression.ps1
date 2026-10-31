param([Parameter(Mandatory = $true)][string]$Python, [switch]$MigrationOnly, [switch]$TestsOnly)

$ErrorActionPreference = 'Stop'
$reportRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $reportRoot '../../..')).Path
$backendRoot = Join-Path $repoRoot 'backend'
$logsRoot = Join-Path $reportRoot 'logs'
New-Item -ItemType Directory -Path $logsRoot -Force | Out-Null
$tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$taskTempRoot = [IO.Path]::GetFullPath((Join-Path $tempBase ('sunjack-integration-' + [guid]::NewGuid().ToString('N'))))
if (-not $taskTempRoot.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase) -or -not (Split-Path -Leaf $taskTempRoot).StartsWith('sunjack-integration-')) {
  throw 'Refusing unsafe test temp path.'
}
New-Item -ItemType Directory -Path $taskTempRoot | Out-Null
$env:APP_STAGE = 'development'
$env:DJANGO_DEBUG = '1'
$env:DJANGO_SECRET_KEY = 'integration-test-only-secret-not-for-production'
$env:DJANGO_SETTINGS_MODULE = 'test_support.isolated_settings'
$env:DEVELOPMENT_SUPERADMIN = '1'
$env:RBAC_ENFORCEMENT = '0'
Remove-Item Env:AUDIT_LOG_ENABLED -ErrorAction SilentlyContinue
$env:MEDIA_STORAGE_BACKEND = 'django.core.files.storage.FileSystemStorage'
$env:MEDIA_ROOT = Join-Path $taskTempRoot 'media'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = $backendRoot
$script:results = @()

function Set-TestDatabase([string]$name) {
  $databasePath = Join-Path $taskTempRoot $name
  $env:DATABASE_URL = 'sqlite:///' + $databasePath.Replace('\', '/')
  Write-Host "Isolated database: $databasePath"
}

function Invoke-TestStage([string]$name, [string[]]$arguments) {
  Write-Host "Starting $name"
  $previousPreference = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & $Python @arguments 2>&1 | Tee-Object -FilePath (Join-Path $logsRoot ($name + '.log')) | Out-Host
  $code = $LASTEXITCODE
  $ErrorActionPreference = $previousPreference
  $script:results += [PSCustomObject]@{ stage = $name; exitCode = $code; arguments = $arguments }
  Write-Host "Finished ${name}: exit $code"
  return $code
}

Push-Location $backendRoot
try {
  if (-not $TestsOnly) {
  Set-TestDatabase 'fresh.sqlite3'
  $null = Invoke-TestStage 'backend-system-check' @('manage.py', 'check')
  $null = Invoke-TestStage 'backend-makemigrations-check' @('manage.py', 'makemigrations', '--check', '--dry-run')
  $freshCode = Invoke-TestStage 'backend-fresh-migrate' @('manage.py', 'migrate', '--noinput')
  if ($freshCode -eq 0) {
    $leafCode = 'import django; django.setup(); from django.db import connection; from django.db.migrations.loader import MigrationLoader; leaves=MigrationLoader(connection).graph.leaf_nodes("crm"); print("crm leaf nodes:", leaves); assert leaves == [("crm", "0092_merge_fulfillment_and_csv_audit")]'
    $null = Invoke-TestStage 'backend-migration-leaves' @('-c', $leafCode)
  }
  Set-TestDatabase 'upgrade.sqlite3'
  $oldCode = Invoke-TestStage 'backend-upgrade-to-0089' @('manage.py', 'migrate', 'crm', '0089_operationlog_operator_protect', '--noinput')
  if ($oldCode -eq 0) {
    $authCode = Invoke-TestStage 'backend-upgrade-auth' @('manage.py', 'migrate', 'auth', '--noinput')
    if ($authCode -ne 0) { throw 'Cannot seed an 0089 upgrade database without the current auth schema.' }
    $seedCode = 'import django; django.setup(); from django.contrib.auth import get_user_model; get_user_model().objects.create_user(username="r1_integration_0089_sentinel"); print("created pre-upgrade sentinel")'
    $seedResult = Invoke-TestStage 'backend-upgrade-seed' @('-c', $seedCode)
    if ($seedResult -eq 0) {
      $upgradeCode = Invoke-TestStage 'backend-upgrade-latest' @('manage.py', 'migrate', '--noinput')
      if ($upgradeCode -eq 0) {
        $verifyCode = 'import django; django.setup(); from django.contrib.auth import get_user_model; from crm.models import FulfillmentIdempotency, CSVImportBatch, CSVImportRowAudit; assert get_user_model().objects.filter(username="r1_integration_0089_sentinel").count() == 1; print("pre-upgrade sentinel retained; integrated models:", FulfillmentIdempotency._meta.db_table, CSVImportBatch._meta.db_table, CSVImportRowAudit._meta.db_table)'
        $null = Invoke-TestStage 'backend-upgrade-verify' @('-c', $verifyCode)
      }
    }
  }
  }
  if (-not $MigrationOnly) {
    Set-TestDatabase 'tests.sqlite3'
    $null = Invoke-TestStage 'backend-database-settings' @('manage.py', 'test', 'crm.tests.test_database_settings', '-v', '2')
    $null = Invoke-TestStage 'backend-iss006' @('manage.py', 'test', 'crm.tests.test_iss006_idempotency', '-v', '2')
    $null = Invoke-TestStage 'backend-iss052' @('manage.py', 'test', 'crm.tests.test_safe_csv_import', '-v', '2')
    $null = Invoke-TestStage 'backend-full' @('manage.py', 'test', '-v', '1')
  }
} finally {
  Pop-Location
  $summaryName = if ($MigrationOnly) { 'backend-migration-results.json' } elseif ($TestsOnly) { 'backend-test-results.json' } else { 'backend-results.json' }
  $script:results | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $reportRoot $summaryName) -Encoding utf8
  if (Test-Path -LiteralPath $taskTempRoot) { Remove-Item -LiteralPath $taskTempRoot -Recurse -Force }
  Write-Host "Removed only this run's temporary root: $taskTempRoot"
}
if (@($script:results | Where-Object { $_.exitCode -ne 0 }).Count -gt 0) { exit 1 }
