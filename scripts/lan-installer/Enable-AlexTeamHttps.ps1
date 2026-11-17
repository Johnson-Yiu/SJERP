#Requires -Version 5.1
#Requires -RunAsAdministrator
param([Parameter(Mandatory)][string[]]$ClientIPv4)
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
$clients = @($ClientIPv4 | Sort-Object -Unique)
if ($clients.Count -lt 1 -or $clients.Count -gt 5) { throw '请提供 1 至 5 台终端的 IPv4 地址。' }
foreach ($client in $clients) {
    if ($client -notmatch '^192\.168\.1\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4])$' -or $client -eq '192.168.1.36') {
        throw "终端地址不在本次验收网段或与 ALEX 冲突：$client"
    }
}
$local = Get-NetIPAddress -AddressFamily IPv4 -IPAddress 192.168.1.36
if ((Get-NetConnectionProfile -InterfaceIndex $local.InterfaceIndex).NetworkCategory -ne 'Private') {
    throw 'ALEX 的局域网网卡不在专用网络。'
}
$proxy = netsh interface portproxy show v4tov4
if ($LASTEXITCODE -or !($proxy -match '^\s*192\.168\.1\.36\s+443\s+10\.253\.247\.2\s+18443\s*$')) {
    throw '现有固定 HTTPS 转发未通过核对。'
}
$rule = 'SJERP-Team-HTTPS'
if (Get-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue) { throw '团队访问规则已存在，未覆盖。' }
$dir = Split-Path -Parent $PSCommandPath
$iso = Join-Path $dir 'sjerp-team-https.iso'
$ca = Join-Path $dir 'sjerp-alex-ca.pem'
if ((Get-FileHash -LiteralPath $iso).Hash -ne '2694D0A356079DF40BA83F8795AA86AD260010FCC7AAF38BA14B5D158804DB06') {
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
if ((Read-Host '确认重启 ERP 来宾、安装证书并开放上述终端，请输入 YES') -cne 'YES') { return }
if ($dvd[0].Path -ne $iso) {
    if ($vm.State -ne 'Off') { Stop-VM -VM $vm }
    if ((Get-VM -Id $vm.Id).State -ne 'Off') { throw 'ERP 来宾尚未关机。' }
    Set-VMDvdDrive -VMDvdDrive $dvd[0] -Path $iso
}
if ((Get-VM -Id $vm.Id).State -eq 'Off') { Start-VM -VM $vm | Out-Null }
$until = (Get-Date).AddMinutes(4)
do {
    curl.exe --noproxy '*' --cacert $ca --connect-timeout 2 --max-time 4 --silent --fail --connect-to '192.168.1.36:443:10.253.247.2:18443' 'https://192.168.1.36/api/session/csrf/' --output NUL
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
Write-Host '团队 HTTPS 已配置，客户端需信任交付的 CA 公共证书。'
