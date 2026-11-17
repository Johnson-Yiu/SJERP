#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
$admin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
try {
    if (!$admin) {
        $adminArgs = '-NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '"'
        Start-Process powershell.exe -Verb RunAs -ArgumentList $adminArgs
        exit 0
    }
    if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
    $iso = Join-Path (Split-Path -Parent $PSCommandPath) 'sjerp-offline-upgrade-test.iso'
    $expected = '100C13C1D68E3AC299FC2C6A1D4E4133BB2D667FC9044A4B715F1393F5ADA341'
    if ((Get-FileHash -LiteralPath $iso).Hash -ne $expected) { throw '升级 ISO SHA-256 不匹配。' }
    $vm = Get-VM -Name 'SJERP-Linux-CombinedTest'
    $adapter = @(Get-VMNetworkAdapter -VM $vm)
    $dvd = @(Get-VMDvdDrive -VM $vm)
    if ($adapter.Count -ne 1 -or $adapter[0].MacAddress -ne '00155D012404' -or $dvd.Count -ne 1) {
        throw '验收虚拟机与交接记录不符。'
    }
    if ($dvd[0].Path -eq $iso) { throw '本次升级 ISO 已挂载，请先核查升级状态。' }
    Write-Host '将对 SJERP-Linux-CombinedTest 执行真实加密联合备份，再升级 96276dff → 3b156502。'
    if ((Read-Host '输入 YES 确认重启这台验收机') -cne 'YES') { return }
    if ($vm.State -ne 'Off') { Stop-VM -VM $vm }
    if ((Get-VM -Id $vm.Id).State -ne 'Off') { throw '验收机尚未关机。' }
    Set-VMDvdDrive -VMDvdDrive $dvd[0] -Path $iso
    Start-VM -VM $vm | Out-Null
    Write-Host '升级演练已启动，请保持验收机运行。'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    if ($admin) { [void](Read-Host '按 Enter 关闭窗口') }
}
