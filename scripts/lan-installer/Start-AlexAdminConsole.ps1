#Requires -Version 5.1
#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
$iso = Join-Path (Split-Path -Parent $PSCommandPath) 'sjerp-admin-console.iso'
if ((Get-FileHash -LiteralPath $iso).Hash -ne 'B32AA22F8653DD0C8EBCE9EC2786FFFE99271C2C51CDF677C231A714C2BF58F9') {
    throw '开户 ISO SHA-256 不符。'
}
$vm = Get-VM -Name 'SJERP-Linux-CombinedTest'
$nic = @(Get-VMNetworkAdapter -VM $vm | Where-Object MacAddress -eq '00155D012404')
$dvd = @(Get-VMDvdDrive -VM $vm)
if ($nic.Count -ne 1 -or $dvd.Count -ne 1) { throw '验收虚拟机身份不符。' }
if ((Read-Host '将重启 ERP 验收机并打开本机开户终端。输入 YES 继续') -cne 'YES') { return }
if ($vm.State -ne 'Off') { Stop-VM -VM $vm }
if ((Get-VM -Id $vm.Id).State -ne 'Off') { throw '验收机尚未关机。' }
Set-VMDvdDrive -VMDvdDrive $dvd[0] -Path $iso
Start-VM -VM $vm | Out-Null
Write-Host '请在 Hyper-V 管理器连接验收机，启动后按 Alt+F2，按提示输入密码。'
