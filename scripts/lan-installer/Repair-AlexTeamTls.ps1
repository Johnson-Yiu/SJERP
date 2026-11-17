#Requires -Version 5.1
#Requires -RunAsAdministrator
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
$dir = Split-Path -Parent $PSCommandPath
$iso = Join-Path $dir 'sjerp-team-tls-aki.iso'
$oldCa = Join-Path $dir 'sjerp-alex-ca.pem'
$ca = Join-Path $dir 'sjerp-alex-ca-v3.pem'
$oldLeafHash = 'E57CF64C23C8F5587482237DC1E523052C0E431B0B621062FC33D446C6A6FA9D'
$leafHash = '08323823F84DAFC9CB24EDF9BFEB5F876B4F9159C0B0FF2414B37F179AD6E0E4'
$files = @{
    $iso = 'AB2CAFEB4096633FC997C98BD5A80A59F18883DA7A8695D3014C151D284C85A7'
    $oldCa = '7B89346A0E01D3AF55885BB5D12F8B6B6327BFBAC1AA71F267646BAAFC25C922'
    $ca = '9E03526B4A45ABC29531394C2EDC9D04AC6671ACD8C2B1EF0AE6329281EEAD6B'
}
foreach ($file in $files.Keys) {
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $files[$file]) {
        throw "证书修复交付文件摘要不匹配：$file"
    }
}
$proxy = netsh interface portproxy show v4tov4
if ($LASTEXITCODE -or !($proxy -match '^\s*192\.168\.1\.36\s+443\s+10\.253\.247\.2\s+18443\s*$')) {
    throw '现有固定 HTTPS 转发未通过核对。'
}
$curl = Join-Path $env:SystemRoot 'System32\curl.exe'
function Get-LiveCertificateHash([string]$CaPath) {
    $arguments = @(
        '--noproxy', '*', '--ssl-revoke-best-effort', '--cacert', $CaPath,
        '--connect-timeout', '2', '--max-time', '5', '--silent', '--fail',
        '--output', 'NUL', '--write-out', '%{certs}', '--connect-to',
        '192.168.1.36:443:10.253.247.2:18443', 'https://192.168.1.36/api/session/csrf/'
    )
    $result = & $curl @arguments
    if ($LASTEXITCODE -ne 0) { return }
    $pem = [regex]::Match(($result -join [Environment]::NewLine), '-----BEGIN CERTIFICATE-----(?<body>[A-Za-z0-9+/=\s]+)-----END CERTIFICATE-----')
    if (!$pem.Success) { return }
    $der = [Convert]::FromBase64String($pem.Groups['body'].Value)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { [BitConverter]::ToString($sha.ComputeHash($der)).Replace('-', '') }
    finally { $sha.Dispose() }
}

if ((Get-LiveCertificateHash $ca) -eq $leafHash) {
    Write-Host 'HTTPS 证书修复已验证。'
    return
}
if ((Get-LiveCertificateHash $oldCa) -ne $oldLeafHash) {
    throw '未能验证正在使用的原 ERP 证书。请保留当前配置并把此提示发给维护人员。'
}
$vm = Get-VM -Name 'SJERP-Linux-CombinedTest'
$nic = @(Get-VMNetworkAdapter -VM $vm | Where-Object MacAddress -eq '02534A455201')
$dvd = @(Get-VMDvdDrive -VM $vm)
if ($nic.Count -ne 1 -or $dvd.Count -ne 1) { throw 'ERP 虚拟机身份不符。' }
if ($dvd[0].Path -eq $iso) { throw '修复介质已挂载。请核对来宾控制台的 SJERP TEAM TLS AKI 状态。' }
if ((Read-Host '确认短暂重启 ERP 虚拟机以更新 HTTPS 证书，请输入 YES') -cne 'YES') { return }

$previousIso = $dvd[0].Path
if ($vm.State -ne 'Off') { Stop-VM -VM $vm }
if ((Get-VM -Id $vm.Id).State -ne 'Off') { throw 'ERP 来宾尚未关机。' }
try {
    Set-VMDvdDrive -VMDvdDrive $dvd[0] -Path $iso
    Start-VM -VM $vm | Out-Null
} catch {
    if ((Get-VM -Id $vm.Id).State -eq 'Off') {
        Set-VMDvdDrive -VMDvdDrive $dvd[0] -Path $previousIso
        Start-VM -VM $vm | Out-Null
    }
    throw
}
Write-Host '证书修复已启动，正在等待 HTTPS 验证。'
$until = (Get-Date).AddMinutes(5)
do {
    if ((Get-LiveCertificateHash $ca) -eq $leafHash) {
        Write-Host 'HTTPS 证书修复已验证。'
        return
    }
    Start-Sleep -Seconds 3
} while ((Get-Date) -lt $until)
throw '未能在期限内验证新证书。请查看来宾控制台的 SJERP TEAM TLS AKI 状态。'
