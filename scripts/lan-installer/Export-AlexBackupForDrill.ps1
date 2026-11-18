#Requires -Version 5.1
#Requires -RunAsAdministrator
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
$record = Join-Path $env:ProgramData 'SJERP-AutoBackup\last-run.json'
$verifiedRecord = Join-Path (Split-Path -Parent $record) 'last-verified.json'
if (Test-Path -LiteralPath $verifiedRecord -PathType Leaf) { $record = $verifiedRecord }
$latest = Get-Content -LiteralPath $record -Raw -Encoding UTF8 | ConvertFrom-Json
if ($latest.status -eq 'FAILED') { throw ("最近一次自动任务失败。{0}" -f $latest.reason) }
if ($latest.status -ne 'VERIFIED' -or $latest.archive -cnotmatch '^SJERP-auto-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}\.zip$' -or
    $latest.sha256 -notmatch '^[a-f0-9]{64}$') {
    throw '最近一次自动任务未提供有效的已验证归档记录。'
}
$name = $latest.archive
$source = Get-Item -LiteralPath (Join-Path 'D:\ERP备份' $name) -Force
if ($source.PSIsContainer -or ($source.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw '本机归档路径不是普通文件。'
}
$directory = Split-Path -Parent $PSCommandPath
$target = Join-Path $directory $name
$sidecar = "$target.sha256"
$pending = Join-Path $directory ('.sjerp-export-' + [Guid]::NewGuid().ToString('N') + '.partial')
try {
    if (!(Test-Path -LiteralPath $target)) {
        $reader = [IO.File]::OpenRead($source.FullName)
        try {
            $writer = [IO.File]::Open($pending,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            try { $reader.CopyTo($writer) } finally { $writer.Dispose() }
        } finally { $reader.Dispose() }
        if ((Get-FileHash -LiteralPath $pending -Algorithm SHA256).Hash -ne $latest.sha256) {
            throw '归档与 ALEX 自动任务记录的 SHA-256 不符。'
        }
        [IO.File]::Move($pending,$target)
    }
    $staged = Get-Item -LiteralPath $target -Force
    if ($staged.PSIsContainer -or ($staged.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
        (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $latest.sha256) {
        throw '已存在的传输文件与 ALEX 自动任务记录不符。'
    }
    $line = $latest.sha256.ToLowerInvariant() + '  ' + $name
    if (Test-Path -LiteralPath $sidecar) {
        if ((Get-Content -LiteralPath $sidecar -Raw).Trim() -cne $line) { throw '已存在的传输校验清单不符。' }
    } else {
        [IO.File]::WriteAllText($pending,$line + [Environment]::NewLine,[Text.Encoding]::ASCII)
        [IO.File]::Move($pending,$sidecar)
    }
    $schedule = Get-ScheduledTaskInfo -TaskName 'SJERP-AutomaticJointBackup'
    Write-Host "恢复验收归档已导出。$name"
    Write-Host "SHA-256  $($latest.sha256)"
    Write-Host "计划任务下次运行  $($schedule.NextRunTime.ToString('yyyy-MM-dd HH:mm:ss'))"
} finally {
    if (Test-Path -LiteralPath $pending) { Remove-Item -LiteralPath $pending -Force }
}
