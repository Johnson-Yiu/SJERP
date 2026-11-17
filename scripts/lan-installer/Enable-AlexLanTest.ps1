#Requires -Version 5.1
#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
$hostIp = '192.168.1.36'
$client = '192.168.1.79'
$port = 18443
$iso = Join-Path (Split-Path -Parent $PSCommandPath) 'sjerp-lan-https-test.iso'
$expected = '541CE6A559765B3689D40247DC54D5429399DDE188DC2DF361BAE27B26F617D6'
if ((Get-FileHash -LiteralPath $iso).Hash -ne $expected) { throw 'ISO SHA-256 不匹配。' }
$nic = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $hostIp
if ((Get-NetConnectionProfile -InterfaceIndex $nic.InterfaceIndex).NetworkCategory -ne 'Private') {
    throw 'ALEX 的目标网卡不是专用网络，未修改网络配置。'
}
$rule = 'SJERP-CombinedTest-HTTPS-Temporary'
$proxy = netsh interface portproxy show v4tov4
if ($LASTEXITCODE -or ($proxy -match "^\s*(\*|0\.0\.0\.0|192\.168\.1\.36)\s+$port\s") -or
    (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) -or
    (Get-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue)) {
    throw '目标端口或规则已存在，请先核对。'
}
$vm = Get-VM -Name 'SJERP-Linux-CombinedTest'
$adapter = @(Get-VMNetworkAdapter -VM $vm)
if ($adapter.Count -ne 1 -or $adapter[0].SwitchName -ne 'Default Switch' -or
    $adapter[0].MacAddress -ne '00155D012404') { throw '验收机网卡与预期不符。' }
$dvd = @(Get-VMDvdDrive -VM $vm)
if ($dvd.Count -ne 1) { throw '验收机 DVD 驱动器数量异常。' }
if ($dvd[0].Path -ne $iso) {
    if ($vm.State -ne 'Off') { Stop-VM -VM $vm }
    if ((Get-VM -Id $vm.Id).State -ne 'Off') { throw '验收机尚未关机。' }
    Set-VMDvdDrive -VMDvdDrive $dvd[0] -Path $iso
}
if ((Get-VM -Id $vm.Id).State -eq 'Off') { Start-VM -VM $vm | Out-Null }

$guest = $null
$until = (Get-Date).AddMinutes(4)
while (!$guest -and (Get-Date) -lt $until) {
    $reported = (Get-VMNetworkAdapter -VMName $vm.Name).IPAddresses
    $neighbors = Get-NetNeighbor -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.LinkLayerAddress -eq '00-15-5D-01-24-04' }
    $addresses = @($reported) + @($neighbors.IPAddress) + @('172.20.105.93')
    foreach ($address in ($addresses | Where-Object { $_ -match '^172\.20\.\d+\.\d+$' } | Select-Object -Unique)) {
        $tcp = [Net.Sockets.TcpClient]::new()
        try {
            if ($tcp.ConnectAsync([string]$address, $port).Wait(1200) -and $tcp.Connected) {
                $neighbor = Get-NetNeighbor -IPAddress $address -AddressFamily IPv4 -ErrorAction SilentlyContinue
                if ($neighbor.LinkLayerAddress -contains '00-15-5D-01-24-04') {
                    $guest = $address
                    break
                }
            }
        } catch {
            # The guest may still be configuring Nginx.
        } finally {
            $tcp.Dispose()
        }
    }
    if (!$guest) { Start-Sleep -Seconds 3 }
}
if (!$guest) { throw '还未确认验收机 HTTPS 已就绪，未添加转发或防火墙规则。' }

New-NetFirewallRule -Name $rule -DisplayName 'SJERP HTTPS 临时验收' -Direction Inbound -Action Allow `
    -Protocol TCP -Profile Private -LocalAddress $hostIp -LocalPort $port -RemoteAddress $client | Out-Null
netsh interface portproxy add v4tov4 "listenaddress=$hostIp" "listenport=$port" "connectaddress=$guest" "connectport=$port"
if ($LASTEXITCODE) {
    Remove-NetFirewallRule -Name $rule
    throw '添加临时转发失败，已移除本次的防火墙规则。'
}
Write-Host "LAN HTTPS 验收入口已配置：https://${hostIp}:$port/（仅允许 $client）"
