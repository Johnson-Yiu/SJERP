#Requires -Version 5.1
#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
$hostIp = '192.168.1.36'
$guest = '10.253.247.2'
$client = '192.168.1.79'
$port = 22223
$rule = 'SJERP-Restore-Diagnostics-Temporary'
$nic = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $hostIp
if ((Get-NetConnectionProfile -InterfaceIndex $nic.InterfaceIndex).NetworkCategory -ne 'Private') {
    throw '目标网卡须为 Windows 专用网络。'
}
$configured = netsh interface portproxy show v4tov4
if ($LASTEXITCODE -or !($configured -match '^\s*192\.168\.1\.36\s+443\s+10\.253\.247\.2\s+18443\s*$')) {
    throw '固定 ERP 转发与交接记录不一致。'
}
if (($configured -match '^\s*\S+\s+22223\s') -or
    (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) -or
    (Get-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue)) {
    throw '诊断端口或规则已存在。'
}
if ((Read-Host '仅允许 192.168.1.79 读取恢复状态，临时开放 22223 至多 15 分钟。输入 YES 继续') -cne 'YES') {
    return
}
$allow = @{
    Name = $rule
    DisplayName = 'SJERP 隔离恢复临时诊断'
    Direction = 'Inbound'
    Action = 'Allow'
    Protocol = 'TCP'
    Profile = 'Private'
    LocalAddress = $hostIp
    LocalPort = $port
    RemoteAddress = $client
}
New-NetFirewallRule @allow | Out-Null
$forwarding = $false
try {
    netsh interface portproxy add v4tov4 "listenaddress=$hostIp" "listenport=$port" "connectaddress=$guest" connectport=22
    if ($LASTEXITCODE) { throw '无法启用临时诊断转发。' }
    $forwarding = $true
    Write-Host '临时诊断已开启。请通知 Codex，并保留此窗口。收到完成通知后按 Enter 可提前关闭。'
    $end = (Get-Date).AddMinutes(15)
    while ((Get-Date) -lt $end) {
        if ([Console]::KeyAvailable -and [Console]::ReadKey($true).Key -eq 'Enter') { break }
        Start-Sleep -Seconds 1
    }
} finally {
    try {
        if ($forwarding) {
            netsh interface portproxy delete v4tov4 "listenaddress=$hostIp" "listenport=$port"
            if ($LASTEXITCODE) { Write-Warning '临时转发表项移除失败，请联系管理员。' }
        }
    } finally { Remove-NetFirewallRule -Name $rule }
}
Write-Host '临时诊断已关闭。'
