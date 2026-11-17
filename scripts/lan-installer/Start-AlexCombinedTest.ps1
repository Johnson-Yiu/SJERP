#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        $argsForAdmin = '-NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '"'
        Start-Process powershell.exe -Verb RunAs -ArgumentList $argsForAdmin
        exit 0
    }
    if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
    $dir = Split-Path -Parent $PSCommandPath
    $creator = Join-Path $dir 'New-AlexImageTestVm.ps1'
    if ((Get-FileHash -LiteralPath $creator).Hash -ne 'A56B68B0893767AEBE3F7BD8226F1F79B2FCB64C1546DBC746C489F241061C1B') {
        throw '创建脚本 SHA-256 不匹配。'
    }
    $inputs = @{
        CombinedTest = $true
        BaseDisk = Join-Path $dir 'sjerp-noble-base.vhdx'
        BaseDiskSha256 = '3A5E4C8B5C1509260483ACA285202AE597E9DCB322A24E1588BFDA7A9F4E38A9'
        SeedIso = Join-Path $dir 'sjerp-combined-first-install.iso'
        SeedIsoSha256 = '8892A1E968F0E532E96D1D4C755ECD2A9ECF3337A85640DE699443A5069020BA'
        SwitchName = 'Default Switch'
    }
    & $creator @inputs -WhatIf
    $old = @(Get-VM -Name 'SJERP-Linux-OfflineTest' -ErrorAction SilentlyContinue)
    if ($old.Count -eq 1 -and $old[0].State -ne 'Off') {
        if ((Read-Host '为腾出内存，允许正常关闭旧验收机吗？输入 YES 确认') -cne 'YES') { return }
        Stop-VM -VM $old[0]
        if ((Get-VM -Id $old[0].Id).State -ne 'Off') { throw '旧验收机尚未关机。' }
    }
    & $creator @inputs
    Write-Host '合并首装已启动。请保持新验收机运行。'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        [void](Read-Host '按 Enter 关闭窗口')
    }
}
