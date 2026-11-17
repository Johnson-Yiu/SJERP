#Requires -Version 5.1
[CmdletBinding(SupportsShouldProcess, ConfirmImpact='High')]
param()
$ErrorActionPreference = 'Stop'
$path = Join-Path (Split-Path -Parent $PSCommandPath) 'sjerp-alex-ca-v3.cer'
$expected = '8F7C12615C449DF14F21D5BF7F9858FF09958A731EC05CCA2F990D742E82E7A9'
$bytes = [IO.File]::ReadAllBytes($path)
$sha = [Security.Cryptography.SHA256]::Create()
try { $actual = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '') }
finally { $sha.Dispose() }
if ($actual -ne $expected) { throw 'CA 证书 SHA-256 不匹配，未导入。' }
$cert = [Security.Cryptography.X509Certificates.X509Certificate2]::new($bytes)
try {
    if ($cert.Subject -ne 'CN=SJERP ALEX LAN CA' -or $cert.HasPrivateKey -or $cert.NotAfter -le (Get-Date)) {
        throw 'CA 证书身份或有效期不符。'
    }
    $store = [Security.Cryptography.X509Certificates.X509Store]::new('Root','CurrentUser')
    try {
        $store.Open([Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
        if ($store.Certificates.Find('FindByThumbprint',$cert.Thumbprint,$false).Count) {
            Write-Host '当前 Windows 用户已信任 SJERP ALEX CA。'
            return
        }
        $store.Close()
        if ($PSCmdlet.ShouldProcess('当前 Windows 用户的受信任根证书存储', '导入 SJERP ALEX 局域网 CA')) {
            $store.Open([Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
            $store.Add($cert)
            if (!$store.Certificates.Find('FindByThumbprint',$cert.Thumbprint,$false).Count) {
                throw '未能验证导入结果。'
            }
            Write-Host '证书已导入。服务器证书上线后访问 https://192.168.1.36/。'
        }
    } finally { $store.Dispose() }
} finally { $cert.Dispose() }
