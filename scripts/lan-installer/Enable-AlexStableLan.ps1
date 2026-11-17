#Requires -Version 5.1
#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机执行。' }
$dir = Split-Path -Parent $PSCommandPath
$iso = Join-Path $dir 'sjerp-stable-lan.iso'
$cert = Join-Path $dir 'sjerp-acceptance-https.pem'
if ((Get-FileHash -LiteralPath $iso).Hash -ne '44973E848918C42DB5AF2B355CF62975566B68CEF1FDE92CBE76B23907584ECA' -or
    (Get-FileHash -LiteralPath $cert).Hash -ne '844D279C13B5E0522115B736265E480A1F0368C484B295CF9FDA52FE79F2AD4D') {
    throw '配置介质或验收证书的 SHA-256 不符。'
}
$switch = 'SJERP-HTTPS-Internal'
$mac = '02534A455201'
$vm = Get-VM -Name 'SJERP-Linux-CombinedTest'
$original = @(Get-VMNetworkAdapter -VM $vm | Where-Object MacAddress -eq '00155D012404')
$dvd = @(Get-VMDvdDrive -VM $vm)
if ($original.Count -ne 1 -or $original[0].SwitchName -ne 'Default Switch' -or $dvd.Count -ne 1) {
    throw '验收机与交接记录不一致。'
}
$proxy = netsh interface portproxy show v4tov4
if ($LASTEXITCODE -or !($proxy -match '^\s*192\.168\.1\.36\s+443\s+(172\.20\.\d+\.\d+|10\.253\.247\.2)\s+18443\s*$')) {
    throw '未找到原有验收 HTTPS 转发。'
}
$rule = Get-NetFirewallRule -Name 'SJERP-CombinedTest-HTTPS443-Temporary'
if (($rule | Get-NetFirewallAddressFilter).RemoteAddress -ne '192.168.1.79') {
    throw '现有防火墙规则与验收范围不符。'
}
$vs = Get-VMSwitch -Name $switch -ErrorAction SilentlyContinue
if (!$vs) {
    $route = Find-NetRoute -RemoteIPAddress 10.253.247.2 | Where-Object DestinationPrefix
    if ($route.DestinationPrefix -ne '0.0.0.0/0') { throw '专用子网与已有网络路由冲突。' }
    New-VMSwitch -Name $switch -SwitchType Internal | Out-Null
} elseif ($vs.SwitchType -ne 'Internal') { throw '同名交换机不是内部交换机。' }
$iface = Get-NetAdapter -Name "vEthernet ($switch)"
$existing = @(Get-NetIPAddress -InterfaceIndex $iface.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object IPAddress -notlike '169.254.*')
if (!$existing) {
    New-NetIPAddress -InterfaceIndex $iface.ifIndex -AddressFamily IPv4 -IPAddress 10.253.247.1 -PrefixLength 30 | Out-Null
} elseif ($existing.Count -ne 1 -or $existing[0].IPAddress -ne '10.253.247.1' -or $existing[0].PrefixLength -ne 30) {
    throw '专用交换机已有不同地址，未覆盖。'
}
$target = @(Get-VMNetworkAdapter -VM $vm | Where-Object Name -eq 'SJERP-HTTPS')
if ($target.Count -gt 1 -or ($target.Count -eq 1 -and
    ($target[0].MacAddress -ne $mac -or $target[0].SwitchName -ne $switch))) {
    throw '验收机的专用网卡与预期不符。'
}
if (!$target -or $dvd[0].Path -ne $iso) {
    if ($vm.State -ne 'Off') { Stop-VM -VM $vm }
    if ((Get-VM -Id $vm.Id).State -ne 'Off') { throw '验收机尚未关机。' }
    if (!$target) { Add-VMNetworkAdapter -VM $vm -Name 'SJERP-HTTPS' -SwitchName $switch -StaticMacAddress $mac }
    if ($dvd[0].Path -ne $iso) { Set-VMDvdDrive -VMDvdDrive $dvd[0] -Path $iso }
}
if ((Get-VM -Id $vm.Id).State -eq 'Off') { Start-VM -VM $vm | Out-Null }
$until = (Get-Date).AddMinutes(4)
do {
    curl.exe --noproxy '*' --cacert $cert --connect-timeout 2 --max-time 4 --silent --fail --connect-to '192.168.1.36:443:10.253.247.2:18443' 'https://192.168.1.36/api/session/csrf/' --output NUL
    $ready = $LASTEXITCODE -eq 0
    if (!$ready) { Start-Sleep -Seconds 3 }
} while (!$ready -and (Get-Date) -lt $until)
if (!$ready) { throw '固定地址 HTTPS 未就绪，原转发保持原值。' }
netsh interface portproxy set v4tov4 listenaddress=192.168.1.36 listenport=443 connectaddress=10.253.247.2 connectport=18443
if ($LASTEXITCODE) { throw 'HTTPS 转发更新失败。' }
$proxy = netsh interface portproxy show v4tov4
if ($LASTEXITCODE -or !($proxy -match '^\s*192\.168\.1\.36\s+443\s+10\.253\.247\.2\s+18443\s*$')) {
    throw '未能核实更新后的 HTTPS 转发。'
}
Write-Host '稳定 HTTPS 验收入口已配置：192.168.1.36:443 → 10.253.247.2:18443'
