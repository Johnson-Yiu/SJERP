#Requires -Version 5.1
#Requires -RunAsAdministrator
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)][string]$BaseDisk,
    [Parameter(Mandatory)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$BaseDiskSha256,
    [Parameter(Mandatory)][string]$SeedIso,
    [Parameter(Mandatory)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$SeedIsoSha256,
    [Parameter(Mandatory)][string]$SwitchName,
    [switch]$OfflineInstall,
    [switch]$CombinedTest
)
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
Import-Module Hyper-V
$source = Get-Item -LiteralPath $BaseDisk
$seed = Get-Item -LiteralPath $SeedIso
foreach ($entry in @(
    @{ File = $source; Extension = '.vhdx'; Hash = $BaseDiskSha256 },
    @{ File = $seed; Extension = '.iso'; Hash = $SeedIsoSha256 }
)) {
    if ($entry.File.PSIsContainer -or $entry.File.Extension -ne $entry.Extension -or
        (Get-FileHash -LiteralPath $entry.File.FullName).Hash -ne $entry.Hash) {
        throw "输入文件格式或 SHA-256 不符：$($entry.File.Name)"
    }
}
$name = 'SJERP-Linux-ImageTest'
if ($OfflineInstall) { $name = 'SJERP-Linux-OfflineTest' }
if ($CombinedTest) { $name = 'SJERP-Linux-CombinedTest' }
$root = Join-Path 'D:\ERP' $name
$existing = Get-CimInstance -Namespace 'root\virtualization\v2' -ClassName Msvm_ComputerSystem -Filter "ElementName = '$name'"
if ($existing -or (Test-Path -LiteralPath $root)) { throw '镜像验收虚拟机或目录已存在。' }
$switch = @(Get-VMSwitch | Where-Object Name -eq $SwitchName)
if ($switch.Count -ne 1) { throw '找不到指定的现有虚拟交换机。' }
if (!$PSCmdlet.ShouldProcess($name, '创建并启动隔离的基础镜像验收虚拟机')) { return }
New-Item -ItemType Directory -Path $root | Out-Null
$disk = Join-Path $root 'system.vhdx'
$localSeed = Join-Path $root 'seed.iso'
Copy-Item -LiteralPath $source.FullName -Destination $disk
Copy-Item -LiteralPath $seed.FullName -Destination $localSeed
if ((Get-FileHash -LiteralPath $disk).Hash -ne $BaseDiskSha256 -or
    (Get-FileHash -LiteralPath $localSeed).Hash -ne $SeedIsoSha256) {
    throw '验收目录副本摘要校验失败，尚未创建虚拟机。'
}
if ($OfflineInstall -or $CombinedTest) { Resize-VHD -Path $disk -SizeBytes 24GB }
$vm = New-VM -Name $name -Path $root -Generation 2 -MemoryStartupBytes 2GB -VHDPath $disk -SwitchName $switch[0].Name
Set-VMProcessor -VM $vm -Count 2
Set-VM -VM $vm -AutomaticStartAction Nothing -AutomaticStopAction ShutDown
Add-VMDvdDrive -VM $vm -Path $localSeed
$boot = Get-VMHardDiskDrive -VM $vm
Set-VMFirmware -VM $vm -EnableSecureBoot On -SecureBootTemplate MicrosoftUEFICertificateAuthority -FirstBootDevice $boot
Start-VM -VM $vm
Write-Host '基础镜像验收虚拟机已启动。请在 Hyper-V 控制台检查 cloud-init 和来宾系统状态。'
