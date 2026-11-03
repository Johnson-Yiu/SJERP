$ErrorActionPreference = 'Continue'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:DATABASE_URL = 'sqlite:///:memory:'
$env:APP_STAGE = 'development'
$env:MEDIA_ROOT = Join-Path $env:TEMP ('iss039-audit-' + [guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $env:MEDIA_ROOT | Out-Null
$reportDir = $PSScriptRoot
Push-Location (Join-Path $PSScriptRoot '../../../backend')
try {
  $log = Join-Path $reportDir 'existing-tests.raw.log'
  & python --version 2>&1 | Tee-Object -FilePath $log
  & python -c "import sys,django; from django.conf import settings; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); print('executable=',sys.executable); print('django=',django.get_version()); print('database=',settings.DATABASES); print('APP_STAGE=',settings.APP_STAGE); print('MEDIA_ROOT=',settings.MEDIA_ROOT)" 2>&1 | Tee-Object -FilePath $log -Append
  & python manage.py test crm.tests.test_iss039_shared_purchase_costs crm.tests.test_purchase_costs crm.tests.test_procurement_data_scope crm.tests.test_supplier_allocation crm.tests.test_integration_039_037_040 crm.tests.test_audit crm.tests.test_functional_rbac --verbosity 2 --noinput 2>&1 | Tee-Object -FilePath $log -Append
  $testExit = $LASTEXITCODE
  "EXIT=$testExit" | Tee-Object -FilePath $log -Append
  Compress-Archive -LiteralPath $log -DestinationPath (Join-Path $reportDir 'existing-tests.raw.zip') -Force
  Remove-Item -LiteralPath $log
  exit $testExit
} finally { Pop-Location }
