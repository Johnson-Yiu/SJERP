#Requires -Version 5.1
#Requires -RunAsAdministrator
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
$base = Join-Path $env:ProgramData 'SJERP-AutoBackup'
$taskName = 'SJERP-AutomaticJointBackup'
$task = Get-ScheduledTask -TaskName $taskName
$installed = Join-Path $base 'Receive-AlexAutomaticBackup.ps1'
if ($task.State -ne 'Ready' -or $task.Actions.Count -ne 1 -or
    $task.Principal.UserId -notin @('SYSTEM','NT AUTHORITY\SYSTEM','S-1-5-18') -or
    $task.Actions[0].Arguments -cnotlike "*`"$installed`"*" -or !(Test-Path -LiteralPath $installed -PathType Leaf)) {
    throw '现有自动备份任务未就绪或任务入口与交付记录不符。'
}
$source = Join-Path (Split-Path -Parent $PSScriptRoot) 'Receive-AlexAutomaticBackup.ps1'
$sha = '1BC465DC67490462E431BF2F7B50E20DEE6EBFA5EA86A1DAF5F694CDBA5BB646'
if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $sha) { throw '修复版接收脚本摘要不符。' }
$log = Join-Path $base 'ssh-error.log'
$record = Join-Path $base 'last-run.json'

function Write-SshDiagnostic {
    if (Test-Path -LiteralPath $log -PathType Leaf) {
        $lines = @(Get-Content -LiteralPath $log -Encoding UTF8 -Tail 12 | Where-Object { $_.Trim() })
        if ($lines.Count) {
            Write-Host 'OpenSSH 诊断'
            $lines | ForEach-Object { Write-Host $_ }
        }
    }
}

Write-SshDiagnostic
if ((Get-FileHash -LiteralPath $installed -Algorithm SHA256).Hash -ne $sha) {
    $temp = Join-Path $base ('receiver-' + [Guid]::NewGuid().ToString('N') + '.tmp')
    try {
        Copy-Item -LiteralPath $source -Destination $temp
        if ((Get-FileHash -LiteralPath $temp -Algorithm SHA256).Hash -ne $sha) { throw '本机更新副本摘要不符。' }
        [IO.File]::Replace($temp,$installed,[System.Management.Automation.Language.NullString]::Value)
    } finally {
        if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Force }
    }
}
$protect = Join-Path (Split-Path -Parent $PSScriptRoot) 'Protect-AlexBackupCollectorKey.ps1'
if ((Get-FileHash -LiteralPath $protect -Algorithm SHA256).Hash -ne '6957A27ADE54FB8EB12C0C986521C40706E7EF37657A63F1E7F89D6904579165') {
    throw '私钥权限修复脚本摘要不符。'
}
& $protect
if ((Read-Host '接收脚本已修复。选择 ERP 无人使用时输入 YES，重试一次联合备份') -cne 'YES') { return }

$start = [DateTimeOffset]::UtcNow.AddSeconds(-1)
Start-ScheduledTask -TaskName $taskName
$deadline = (Get-Date).AddMinutes(35)
do {
    if (Test-Path -LiteralPath $record -PathType Leaf) {
        $state = Get-Content -LiteralPath $record -Raw -Encoding UTF8 | ConvertFrom-Json
        if ([DateTimeOffset]::Parse($state.updated_utc) -ge $start) {
            if ($state.status -eq 'VERIFIED') {
                & (Join-Path $PSScriptRoot 'Export-AlexBackupForDrill.ps1')
                return
            }
            if ($state.status -eq 'FAILED') {
                Write-SshDiagnostic
                throw $state.reason
            }
        }
    }
    Start-Sleep -Seconds 5
} while ((Get-Date) -lt $deadline)
Write-SshDiagnostic
throw '重试未在期限内完成，请核对本机任务状态。'
