#Requires -Version 7.4
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$OriginalCa,
    [Parameter(Mandatory)][string]$OriginalServer,
    [Parameter(Mandatory)][string]$ProtectedCaKey,
    [Parameter(Mandatory)][string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
if ((Get-FileHash -LiteralPath $OriginalCa).Hash -ne '7B89346A0E01D3AF55885BB5D12F8B6B6327BFBAC1AA71F267646BAAFC25C922' -or
    (Get-FileHash -LiteralPath $OriginalServer).Hash -ne '822F79BF42D8053B15EFC2A8939C254F15503BA12015BE595BD365F06781B103') {
    throw '原 CA 或服务器证书摘要不符。'
}
if (Test-Path -LiteralPath $OutputDirectory) { throw '请指定尚不存在的输出目录。' }

$originalRoot = [Security.Cryptography.X509Certificates.X509Certificate2]::CreateFromPem(
    [IO.File]::ReadAllText((Resolve-Path -LiteralPath $OriginalCa)))
$originalLeaf = [Security.Cryptography.X509Certificates.X509Certificate2]::CreateFromPem(
    [IO.File]::ReadAllText((Resolve-Path -LiteralPath $OriginalServer)))
$key = [Security.Cryptography.RSA]::Create()
try {
    $credential = Import-Clixml -LiteralPath $ProtectedCaKey
    if ($credential -isnot [pscredential]) { throw 'CA 密钥保护格式无效。' }
    $bytes = [Convert]::FromBase64String($credential.GetNetworkCredential().Password)
    try {
        $read = 0
        try { $key.ImportPkcs8PrivateKey($bytes, [ref]$read) }
        catch [Security.Cryptography.CryptographicException] {
            $key.ImportRSAPrivateKey($bytes, [ref]$read)
        }
        if ($read -ne $bytes.Length) { throw 'CA 密钥编码异常。' }
    } finally { [Array]::Clear($bytes, 0, $bytes.Length) }

    $expectedKey = [Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPublicKey($originalRoot)
    try {
        if ([Convert]::ToBase64String($key.ExportSubjectPublicKeyInfo()) -cne
            [Convert]::ToBase64String($expectedKey.ExportSubjectPublicKeyInfo())) {
            throw '解封的密钥与原 CA 公钥不匹配。'
        }
    } finally { $expectedKey.Dispose() }

    $hash = [Security.Cryptography.HashAlgorithmName]::SHA256
    $padding = [Security.Cryptography.RSASignaturePadding]::Pkcs1
    $signer = [Security.Cryptography.X509Certificates.X509SignatureGenerator]::CreateForRSA($key, $padding)
    $rootRequest = [Security.Cryptography.X509Certificates.CertificateRequest]::new(
        $originalRoot.SubjectName, $originalRoot.PublicKey, $hash, $padding)
    foreach ($extension in $originalRoot.Extensions) { $rootRequest.CertificateExtensions.Add($extension) }
    $rootRequest.CertificateExtensions.Add(
        [Security.Cryptography.X509Certificates.X509SubjectKeyIdentifierExtension]::new($originalRoot.PublicKey, $false))
    $root = $rootRequest.Create($originalRoot.SubjectName, $signer, $originalRoot.NotBefore, $originalRoot.NotAfter,
        [Security.Cryptography.RandomNumberGenerator]::GetBytes(16))
    try {
        $leafRequest = [Security.Cryptography.X509Certificates.CertificateRequest]::new(
            $originalLeaf.SubjectName, $originalLeaf.PublicKey, $hash, $padding)
        foreach ($extension in $originalLeaf.Extensions) { $leafRequest.CertificateExtensions.Add($extension) }
        $leafRequest.CertificateExtensions.Add(
            [Security.Cryptography.X509Certificates.X509SubjectKeyIdentifierExtension]::new($originalLeaf.PublicKey, $false))
        # A key identifier without an issuer serial allows existing clients to recognize the original CA key.
        $leafRequest.CertificateExtensions.Add(
            [Security.Cryptography.X509Certificates.X509AuthorityKeyIdentifierExtension]::CreateFromCertificate($root, $true, $false))
        $leaf = $leafRequest.Create($root.SubjectName, $signer, $originalLeaf.NotBefore, $originalLeaf.NotAfter,
            [Security.Cryptography.RandomNumberGenerator]::GetBytes(16))
        try {
            $out = New-Item -ItemType Directory -Path $OutputDirectory
            [IO.File]::WriteAllText((Join-Path $out.FullName 'sjerp-alex-ca-v3.pem'), $root.ExportCertificatePem() + [Environment]::NewLine)
            [IO.File]::WriteAllBytes((Join-Path $out.FullName 'sjerp-alex-ca-v3.cer'), $root.RawData)
            [IO.File]::WriteAllText((Join-Path $out.FullName 'sjerp-alex-server-v3.pem'), $leaf.ExportCertificatePem() + [Environment]::NewLine)
        } finally { $leaf.Dispose() }
    } finally { $root.Dispose() }
} finally {
    $key.Dispose()
    $originalLeaf.Dispose()
    $originalRoot.Dispose()
}
