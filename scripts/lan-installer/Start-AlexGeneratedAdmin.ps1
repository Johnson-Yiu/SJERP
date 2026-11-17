#Requires -Version 5.1
#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
$iso = Join-Path (Split-Path -Parent $PSCommandPath) 'sjerp-johnson-admin.iso'
if ((Get-FileHash -LiteralPath $iso).Hash -ne '1136CE8E2EF0EA3B1EC7B53920FC0AF196ABC842727B75D816072B358BF0E2F4') {
    throw '开户 ISO SHA-256 不符。'
}
$vm = Get-VM -Name 'SJERP-Linux-CombinedTest'
$nic = @(Get-VMNetworkAdapter -VM $vm | Where-Object MacAddress -eq '00155D012404')
$dvd = @(Get-VMDvdDrive -VM $vm)
if ($nic.Count -ne 1 -or $dvd.Count -ne 1) { throw '验收机身份不符。' }
if ($dvd[0].Path -eq $iso) { throw '开户介质已挂载，请先确认上次执行结果。' }
if ($vm.State -ne 'Off') { Stop-VM -VM $vm }
if ((Get-VM -Id $vm.Id).State -ne 'Off') { throw '验收机尚未关机。' }
Set-VMDvdDrive -VMDvdDrive $dvd[0] -Path $iso
Start-VM -VM $vm | Out-Null
Get-VM -Name 'SJERP-Linux-CombinedTest','SJERP-Linux-Build' | Select-Object Name,State
Write-Host '自动开户已启动。请保留屏幕输出，无需输入密码。'
