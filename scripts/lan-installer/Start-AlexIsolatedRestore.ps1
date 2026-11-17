#Requires -Version 5.1
#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
$iso = Join-Path (Split-Path -Parent $PSCommandPath) 'sjerp-isolated-restore-v3.iso'
if ((Get-FileHash -LiteralPath $iso).Hash -ne '6CE040794040C43D3196CF27DFAEA89280B39B6FFF4AACA44C4CC8A59CC709F4') {
    throw '恢复演练 ISO 摘要不符。'
}
$vm = Get-VM -Name 'SJERP-Linux-CombinedTest'
$nic = @(Get-VMNetworkAdapter -VM $vm | Where-Object MacAddress -eq '02534A455201')
$dvd = @(Get-VMDvdDrive -VM $vm)
if ($nic.Count -ne 1 -or $dvd.Count -ne 1) { throw 'ERP 来宾身份与预期不一致。' }
if ($dvd[0].Path -eq $iso) { throw '恢复介质已挂载，请先核对结果。' }
if ((Read-Host '此操作会短暂重启 ERP 并在独立库中演练恢复。输入 YES 确认') -cne 'YES') { return }
if ($vm.State -ne 'Off') { Stop-VM -VM $vm }
if ((Get-VM -Id $vm.Id).State -ne 'Off') { throw 'ERP 来宾尚未关机。' }
Set-VMDvdDrive -VMDvdDrive $dvd[0] -Path $iso
Start-VM -VM $vm | Out-Null
Write-Host '恢复演练已启动。请在来宾控制台切换 Alt+F2 查看 SJERP ISOLATED RESTORE 状态。'
