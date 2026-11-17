#Requires -Version 5.1
[CmdletBinding(SupportsShouldProcess)]
param()
$ErrorActionPreference = 'Stop'
$dir = Split-Path -Parent $PSCommandPath
$ca = Join-Path $dir 'sjerp-alex-ca-v3.pem'
$der = Join-Path $dir 'sjerp-alex-ca-v3.cer'
$url = 'https://192.168.1.36/'
function Get-CertificateFileDigest($file) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { [BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($file))).Replace('-', '') }
    finally { $sha.Dispose() }
}
if ((Get-CertificateFileDigest $ca) -ne '9E03526B4A45ABC29531394C2EDC9D04AC6671ACD8C2B1EF0AE6329281EEAD6B' -or
    (Get-CertificateFileDigest $der) -ne '8F7C12615C449DF14F21D5BF7F9858FF09958A731EC05CCA2F990D742E82E7A9') {
    throw '交付证书摘要不匹配。'
}
if ($WhatIfPreference) {
    & (Join-Path $dir 'Install-SjerpClientTrust.ps1') -WhatIf
    return
}
curl.exe --noproxy '*' --ssl-revoke-best-effort --cacert $ca --connect-timeout 5 --max-time 10 --silent --fail --output NUL $url
if ($LASTEXITCODE) {
    throw 'ERP 未通过团队证书连接验证。请确认服务器已经启用团队证书且本机已获准访问。'
}
$cert = [Security.Cryptography.X509Certificates.X509Certificate2]::new($der)
try {
    if (!(Test-Path -LiteralPath "Cert:\CurrentUser\Root\$($cert.Thumbprint)")) {
        & (Join-Path $dir 'Install-SjerpClientTrust.ps1') -Confirm
    }
    if (!(Test-Path -LiteralPath "Cert:\CurrentUser\Root\$($cert.Thumbprint)")) {
        Write-Host '证书未导入。请在信任证书后重新打开。'
        return
    }
    if ($PSCmdlet.ShouldProcess($url, '打开 ERP')) { Start-Process $url }
} finally { $cert.Dispose() }
