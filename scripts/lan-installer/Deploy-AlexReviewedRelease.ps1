#Requires -Version 5.1
#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机执行。' }
$dir = Split-Path -Parent $PSCommandPath
$iso = Join-Path $dir 'SJERP-升级-3bb09701.iso'
if ((Get-FileHash -LiteralPath $iso).Hash -ne '9D952A7E171F030A62E4FD2BC68057FBBBCFF9C9FBB6FBAD5EB2A9F8FAD937DF') {
    throw '定位到的部署 ISO 摘要不匹配。'
}
$hostIp = '192.168.1.36'
$guest = '10.253.247.2'
$client = '192.168.1.79'
$port = 22223
$rule = 'SJERP-Deployment-Backup-Temporary'
$nic = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $hostIp
if ((Get-NetConnectionProfile -InterfaceIndex $nic.InterfaceIndex).NetworkCategory -ne 'Private') {
    throw 'ALEX 的局域网接口不是专用网络。'
}
$proxy = netsh interface portproxy show v4tov4
if ($LASTEXITCODE -or !($proxy -match '^\s*192\.168\.1\.36\s+443\s+10\.253\.247\.2\s+18443\s*$')) {
    throw '既有固定 HTTPS 转发不符。'
}
if (($proxy -match "^\s*\S+\s+$port\s") -or
    (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) -or
    (Get-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue)) {
    throw '临时备份转发端口或规则已存在。'
}
if (!(Test-Path -LiteralPath 'D:\ERP备份' -PathType Container)) { throw '未找到 D:\ERP备份。' }
$vm = Get-VM -Name 'SJERP-Linux-CombinedTest'
$nics = @(Get-VMNetworkAdapter -VM $vm | Where-Object MacAddress -eq '02534A455201')
$dvd = @(Get-VMDvdDrive -VM $vm)
if ($nics.Count -ne 1 -or $nics[0].SwitchName -ne 'SJERP-HTTPS-Internal' -or $dvd.Count -ne 1) {
    throw 'ERP 验收来宾身份不符。'
}
if ($dvd[0].Path -eq $iso) { throw '升级 ISO 已挂载，请先核查上次状态。' }
Write-Host '将先做加密备份，再切换 3b156502 → 3bb09701。本次按授权跳过 GitHub Actions。'
Write-Host '将启用临时 SSH 转发，仅允许开发机 192.168.1.79 导出加密归档和核验升级。'
if ((Read-Host '输入 YES 确认重启 ERP 验收来宾及新增临时转发') -cne 'YES') { return }
$firewall = @{
    Name = $rule
    DisplayName = 'SJERP 部署备份临时 SSH'
    Direction = 'Inbound'
    Action = 'Allow'
    Protocol = 'TCP'
    Profile = 'Private'
    LocalAddress = $hostIp
    LocalPort = $port
    RemoteAddress = $client
}
New-NetFirewallRule @firewall | Out-Null
netsh interface portproxy add v4tov4 "listenaddress=$hostIp" "listenport=$port" "connectaddress=$guest" connectport=22
if ($LASTEXITCODE) {
    Remove-NetFirewallRule -Name $rule
    throw '临时转发配置失败，已撤销本次新增规则。'
}
if ($vm.State -ne 'Off') { Stop-VM -VM $vm }
if ((Get-VM -Id $vm.Id).State -ne 'Off') { throw 'ERP 来宾尚未关机。' }
Set-VMDvdDrive -VMDvdDrive $dvd[0] -Path $iso
Start-VM -VM $vm | Out-Null
Write-Host '部署已启动，请保持 ERP 来宾运行。'
