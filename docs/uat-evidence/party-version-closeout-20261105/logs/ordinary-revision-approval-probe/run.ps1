$ErrorActionPreference = 'Stop'
$env:APP_STAGE = 'development'
$env:DATABASE_URL = 'sqlite:///:memory:'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
$env:MEDIA_ROOT = Join-Path $env:TEMP ('party-revision-probe-' + [guid]::NewGuid().ToString('N'))
$env:PYTHONPATH = $PSScriptRoot
$backend = (Resolve-Path (Join-Path $PSScriptRoot '../../../../../backend')).Path
$python = 'C:/Users/Johnson/AppData/Local/Temp/sunjack-cpython312-verify-20261031-a37d/shared-venv/Scripts/python.exe'
Set-Location $backend
& $python -u manage.py test probe_revision.OrdinaryRevisionApprovalProbe.test_sent_quote_party_revision --verbosity 2 --noinput *> (Join-Path $PSScriptRoot 'api-client-raw.log')
exit $LASTEXITCODE
