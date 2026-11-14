param([string]$ReportPath=(Join-Path $env:TEMP "SJERP-预检-$env:COMPUTERNAME.txt"),[string]$ShareName='d',[int[]]$Ports=@(80,443))
$ErrorActionPreference='Stop'
function Read-Section($Title,[scriptblock]$Query) {
    ''
    "【$Title】"
    try { & $Query | Out-String -Width 200 }
    catch { "未知：$($_.Exception.Message)" }
}
$report = & {
    "SUNJACK ERP 局域网预检 · $env:COMPUTERNAME · $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
    Read-Section 'Windows 版本和类型' {
        Get-CimInstance Win32_OperatingSystem | Format-List Caption,Version,BuildNumber,OSArchitecture,OperatingSystemSKU
    }
    Read-Section 'CPU、内存、虚拟化' {
        Get-CimInstance Win32_ComputerSystem | Format-List TotalPhysicalMemory,HypervisorPresent
        Get-CimInstance Win32_Processor | Format-List Name,NumberOfCores,NumberOfLogicalProcessors,VirtualizationFirmwareEnabled,SecondLevelAddressTranslationExtensions,VMMonitorModeExtensions
    }
    Read-Section '磁盘空间（字节）' {
        Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Format-Table DeviceID,FileSystem,Size,FreeSpace
    }
    Read-Section 'Hyper-V、替代组件和部署路线' {
        foreach ($feature in @('Microsoft-Hyper-V-All','VirtualMachinePlatform','Microsoft-Windows-Subsystem-Linux')) {
            try {
                $item=Get-WindowsOptionalFeature -Online -FeatureName $feature
                "$feature = $($item.State)"
                if ($feature -eq 'Microsoft-Hyper-V-All') {
                    if ($item.State -eq 'Enabled') { '优先核实已有 Linux 虚拟机或专用 Hyper-V 虚拟机导入条件。' }
                    else { 'Hyper-V 当前未就绪。先核实已有获准 Linux 环境或启用条件。' }
                }
            } catch { "$feature 未知：$($_.Exception.Message)" }
        }
    }
    Read-Section '网卡、IP、网关和网络状态' {
        Get-NetIPConfiguration | Format-List InterfaceAlias,IPv4Address,IPv6Address,IPv4DefaultGateway
        Get-NetConnectionProfile | Format-Table InterfaceAlias,NetworkCategory,IPv4Connectivity,IPv6Connectivity
    }
    Read-Section 'TCP 监听' {
        "检查端口：$($Ports -join ', ')"
        $listeners=@(Get-NetTCPConnection -State Listen | Where-Object LocalPort -In $Ports)
        if (!$listeners.Count) { '未发现所查端口的监听。' }
        else { $listeners | Format-Table LocalAddress,LocalPort,OwningProcess }
    }
    Read-Section 'SMB 共享及 ERP 目录 ACL' {
        $share=Get-SmbShare -Name $ShareName
        $share | Format-List Name,Path
        Get-SmbShareAccess -Name $ShareName | Format-Table AccountName,AccessControlType,AccessRight
        $target=Join-Path $share.Path ERP
        "目录：$target"
        Get-Acl -LiteralPath $target | Format-List Owner,AccessToString
    }
    Read-Section '开机服务、休眠及防火墙状态' {
        Get-CimInstance Win32_Service -Filter "Name='vmms' OR Name='vmcompute' OR Name='LanmanServer'" | Format-Table Name,State,StartMode
        powercfg.exe /a
        powercfg.exe /getactivescheme
        powercfg.exe /query SCHEME_CURRENT SUB_SLEEP
        Get-NetFirewallProfile | Format-Table Name,Enabled,DefaultInboundAction
    }
    '现场待核对：固定局域网地址、证书信任、开机无登录运行、接电时不自动休眠、第二台终端可达性及独立备份位置。共享 ACL 仅作参考，未试写。'
}
$report | Set-Content -LiteralPath $ReportPath -Encoding UTF8
Write-Host "报告已保存：$ReportPath"
