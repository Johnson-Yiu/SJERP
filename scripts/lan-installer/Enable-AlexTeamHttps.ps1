#Requires -Version 5.1
#Requires -RunAsAdministrator
[CmdletBinding(DefaultParameterSetName='Devices')]
param(
    [Parameter(Mandatory, ParameterSetName='Devices')][string[]]$ClientIPv4,
    [Parameter(Mandatory, ParameterSetName='Subnet')][switch]$WholeLan
)
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
if ($WholeLan) {
    $clients = @('192.168.1.1-192.168.1.254')
} else {
    $clients = @($ClientIPv4 | Sort-Object -Unique)
    if ($clients.Count -lt 1 -or $clients.Count -gt 5) { throw '请提供 1 至 5 台终端的 IPv4 地址。' }
    foreach ($client in $clients) {
        if ($client -notmatch '^192\.168\.1\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4])$' -or $client -eq '192.168.1.36') {
            throw "终端地址不在本次验收网段或与 ALEX 冲突：$client"
        }
    }
}
$local = @(Get-NetIPAddress -AddressFamily IPv4 -IPAddress 192.168.1.36)
if ($local.Count -ne 1) { throw '无法唯一定位 ALEX 的 192.168.1.36 网卡。' }
$profile = @(Get-NetConnectionProfile -InterfaceIndex $local[0].InterfaceIndex)
if ($profile.Count -ne 1 -or $profile[0].NetworkCategory -ne 'Private') {
    $category = if ($profile.Count -eq 1) { $profile[0].NetworkCategory } else { '无法唯一识别' }
    throw "ALEX 网卡 $($local[0].InterfaceAlias)，地址 192.168.1.36/$($local[0].PrefixLength)，网络类型 $category。启用需要专用网络。"
}
$proxy = netsh interface portproxy show v4tov4
if ($LASTEXITCODE -or !($proxy -match '^\s*192\.168\.1\.36\s+443\s+10\.253\.247\.2\s+18443\s*$')) {
    throw '现有固定 HTTPS 转发未通过核对。'
}
$rule = 'SJERP-Team-HTTPS'
if (Get-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue) { throw '团队访问规则已存在，未覆盖。' }
$dir = Split-Path -Parent $PSCommandPath
$iso = Join-Path $dir 'sjerp-team-https-v2.iso'
$ca = Join-Path $dir 'sjerp-alex-ca.pem'
if ((Get-FileHash -LiteralPath $iso).Hash -ne '28DFBDE8F78B1CC9D0846F4EB45A5A9E794BCEDF6A94AFF48B7912FA96F32491') {
    throw '团队 HTTPS 配置 ISO 摘要不匹配。'
}
if ((Get-FileHash -LiteralPath $ca).Hash -ne '7B89346A0E01D3AF55885BB5D12F8B6B6327BFBAC1AA71F267646BAAFC25C922') {
    throw '团队 CA 公共证书摘要不匹配。'
}
$vm = Get-VM -Name 'SJERP-Linux-CombinedTest'
$serviceNic = @(Get-VMNetworkAdapter -VM $vm | Where-Object MacAddress -eq '02534A455201')
$dvd = @(Get-VMDvdDrive -VM $vm)
if ($serviceNic.Count -ne 1 -or $dvd.Count -ne 1) { throw 'ERP 虚拟机身份不符。' }
Write-Host ('本次只启用以下终端：' + ($clients -join ', '))
if ((Read-Host '确认重启 ERP 来宾、安装证书、开放上述地址，并清理部署备份临时转发，请输入 YES') -cne 'YES') { return }
if ($dvd[0].Path -ne $iso) {
    if ($vm.State -ne 'Off') { Stop-VM -VM $vm }
    if ((Get-VM -Id $vm.Id).State -ne 'Off') { throw 'ERP 来宾尚未关机。' }
    Set-VMDvdDrive -VMDvdDrive $dvd[0] -Path $iso
}
if ((Get-VM -Id $vm.Id).State -eq 'Off') { Start-VM -VM $vm | Out-Null }
$until = (Get-Date).AddMinutes(4)
do {
    curl.exe --noproxy '*' --ssl-revoke-best-effort --cacert $ca --connect-timeout 2 --max-time 4 --silent --fail --connect-to '192.168.1.36:443:10.253.247.2:18443' 'https://192.168.1.36/api/session/csrf/' --output NUL
    $ready = $LASTEXITCODE -eq 0
    if (!$ready) { Start-Sleep -Seconds 3 }
} while (!$ready -and (Get-Date) -lt $until)
if (!$ready) { throw '新证书的 HTTPS 验证未通过，未开放团队终端。' }
$firewall = @{
    Name = $rule
    DisplayName = 'SJERP 局域网团队 HTTPS'
    Direction = 'Inbound'
    Action = 'Allow'
    Protocol = 'TCP'
    Profile = 'Private'
    LocalAddress = '192.168.1.36'
    LocalPort = 443
    RemoteAddress = $clients
}
New-NetFirewallRule @firewall | Out-Null
# Only remove the exact, deployment-owned temporary forwarding and firewall rule.
$backupRuleName = 'SJERP-Deployment-Backup-Temporary'
$backupRule = Get-NetFirewallRule -Name $backupRuleName -ErrorAction SilentlyContinue
$backupProxy = netsh interface portproxy show v4tov4
if ($LASTEXITCODE) { throw '团队 HTTPS 已启用，但无法核对临时备份转发。' }
$backupRows = @($backupProxy -match '^\s*192\.168\.1\.36\s+22223\s')
if ($backupRule -or $backupRows.Count) {
    $backupAddresses = if ($backupRule) { $backupRule | Get-NetFirewallAddressFilter }
    $backupPorts = if ($backupRule) { $backupRule | Get-NetFirewallPortFilter }
    if (!$backupRule -or $backupRows.Count -ne 1 -or
        $backupRows[0] -notmatch '^\s*192\.168\.1\.36\s+22223\s+10\.253\.247\.2\s+22\s*$' -or
        $backupAddresses.LocalAddress -ne '192.168.1.36' -or
        $backupAddresses.RemoteAddress -ne '192.168.1.79' -or $backupPorts.LocalPort -ne '22223') {
        Write-Warning '团队 HTTPS 已启用。临时备份转发与部署记录不符，保留原配置供核查。'
    } elseif (!(Test-Path -LiteralPath 'D:\ERP备份\backup-9bbea3f05507489dbe4cb98c8be48f56.gpg' -PathType Leaf) -or
        (Get-FileHash -LiteralPath 'D:\ERP备份\backup-9bbea3f05507489dbe4cb98c8be48f56.gpg').Hash -ne '0AE73EEC385C1015297FBFB40BA83AB2ECF66B837DEF85EDEB32FCE63F4097A9') {
        Write-Warning '团队 HTTPS 已启用。部署备份未通过本机核对，保留临时备份转发。'
    } else {
        netsh interface portproxy delete v4tov4 listenaddress=192.168.1.36 listenport=22223
        if ($LASTEXITCODE) { throw '团队 HTTPS 已启用，但移除临时备份转发失败。' }
        Remove-NetFirewallRule -Name $backupRuleName
        Write-Host '部署备份临时转发已移除。'
    }
}
Write-Host '团队 HTTPS 已配置，客户端需信任交付的 CA 公共证书。'
