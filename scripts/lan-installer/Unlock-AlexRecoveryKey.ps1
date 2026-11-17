#Requires -Version 7.4
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ProtectedKey,
    [Parameter(Mandatory)][string]$PublicKey,
    [Parameter(Mandatory)][string]$Envelope,
    [Parameter(Mandatory)][string]$Output
)
$ErrorActionPreference = 'Stop'
$credential = Import-Clixml -LiteralPath $ProtectedKey
if ($credential -isnot [pscredential]) { throw '恢复密钥保护格式无效。' }
$encoded = [Convert]::FromBase64String($credential.GetNetworkCredential().Password)
$rsa = [Security.Cryptography.RSA]::Create()
$public = [Security.Cryptography.RSA]::Create()
try {
    $read = 0
    $rsa.ImportPkcs8PrivateKey($encoded,[ref]$read)
    if ($read -ne $encoded.Length) { throw '恢复密钥编码无效。' }
    $public.ImportFromPem([IO.File]::ReadAllText((Resolve-Path -LiteralPath $PublicKey)))
    if ([Convert]::ToBase64String($rsa.ExportSubjectPublicKeyInfo()) -cne
        [Convert]::ToBase64String($public.ExportSubjectPublicKeyInfo())) { throw '恢复密钥与公开证书不匹配。' }
    $password = $rsa.Decrypt([IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $Envelope)),[Security.Cryptography.RSAEncryptionPadding]::OaepSHA256)
    try {
        $stream = [IO.FileStream]::new($Output,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try { $stream.Write($password,0,$password.Length) } finally { $stream.Dispose() }
    } finally { [Array]::Clear($password,0,$password.Length) }
} finally {
    [Array]::Clear($encoded,0,$encoded.Length)
    $public.Dispose()
    $rsa.Dispose()
}
