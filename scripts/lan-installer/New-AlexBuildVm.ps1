#Requires -Version 5.1
#Requires -RunAsAdministrator
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$IsoPath,
    [string]$IsoSha256 = '97f3d7ffb032c3eb3b23d2c8be9cc76e60c2c1f2c0146ba5ba9fe01cafae0fd8',
    [Parameter(Mandatory)][string]$SwitchName
)
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
Import-Module Hyper-V
if ((Get-Service vmms).Status -ne 'Running') { throw 'Hyper-V 管理服务未运行。' }
if (!$IsoPath) {
    $IsoPath = Join-Path (Split-Path -Parent $PSCommandPath) 'ubuntu-24.04.5-live-server-amd64.iso'
}
$iso = Get-Item -LiteralPath $IsoPath
if ($iso.PSIsContainer -or $iso.Extension -ne '.iso') { throw '请提供本地 Linux 安装 ISO。' }
if ((Get-FileHash -LiteralPath $iso.FullName -Algorithm SHA256).Hash -ne $IsoSha256) {
    throw 'ISO SHA-256 与指定摘要不一致。'
}
$switch = @(Get-VMSwitch | Where-Object Name -EQ $SwitchName)
if ($switch.Count -ne 1) { throw '找不到指定的现有 Hyper-V 虚拟交换机。' }
$name = 'SJERP-Linux-Build'
$root = 'D:\ERP\SJERP-Linux-Build'
$disk = Join-Path $root 'SJERP-Linux-Build.vhdx'
$existing = Get-CimInstance -Namespace 'root\virtualization\v2' -ClassName Msvm_ComputerSystem -Filter "ElementName = '$name'"
if ($existing -or (Test-Path -LiteralPath $root)) {
    throw '虚拟机或工作目录已存在。请先在 Hyper-V 管理器核对，不会覆盖。'
}
if ((Get-PSDrive D).Free -lt 64GB) { throw 'D 盘可用空间少于 64 GiB。' }
if (!$PSCmdlet.ShouldProcess($name, '在 D:\ERP 创建并启动专用安装虚拟机')) { return }
New-Item -ItemType Directory -Path $root | Out-Null
$vm = New-VM -Name $name -Path $root -Generation 2 -MemoryStartupBytes 3GB -NewVHDPath $disk -NewVHDSizeBytes 64GB -SwitchName $switch[0].Name
Set-VMProcessor -VM $vm -Count 2
Set-VM -VM $vm -AutomaticStartAction Nothing -AutomaticStopAction ShutDown
$dvd = Add-VMDvdDrive -VM $vm -Path $iso.FullName -Passthru
Set-VMFirmware -VM $vm -EnableSecureBoot On -SecureBootTemplate MicrosoftUEFICertificateAuthority -FirstBootDevice $dvd
Start-VM -VM $vm
Write-Host '已启动 Linux 安装虚拟机。请用 Hyper-V 管理器连接并完成来宾系统安装。'
