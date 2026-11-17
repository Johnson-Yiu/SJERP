#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 执行备份。' }
$base = Split-Path -Parent $PSCommandPath
$target = 'D:\ERP备份'
$scratch = Join-Path $target ('.sjerp-' + [Guid]::NewGuid().ToString('N') + '.partial')
$errors = Join-Path $base 'ssh-error.log'
$last = Join-Path $base 'last-run.json'
function Write-Status([hashtable]$State) {
    $State['updated_utc'] = [DateTime]::UtcNow.ToString('o')
    $json = $State | ConvertTo-Json -Compress
    $tmp = "$last.tmp"
    [IO.File]::WriteAllText($tmp,$json)
    Move-Item -LiteralPath $tmp -Destination $last -Force
}
Write-Status @{ status = 'RUNNING' }
try {
    $directory = Get-Item -LiteralPath $target -Force
    if (!$directory.PSIsContainer -or ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw '备份目录须为 D 盘上的普通目录。'
    }
    if ((Get-PSDrive -Name D).Free -lt 1GB) { throw 'D 盘可用空间不足 1 GB。' }
    $ssh = Join-Path $env:SystemRoot 'System32\OpenSSH\ssh.exe'
    $sshArgs = '-T -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=3'
    $sshArgs += (' -o UserKnownHostsFile="{0}" -i "{1}" sjerpbackup@10.253.247.2 backup' -f (Join-Path $base 'known_hosts'),(Join-Path $base 'collector'))
    $process = Start-Process -FilePath $ssh -ArgumentList $sshArgs -RedirectStandardOutput $scratch -RedirectStandardError $errors -WindowStyle Hidden -PassThru
    if (!$process.WaitForExit(1950000)) {
        $process.Kill()
        $process.WaitForExit()
        throw '备份连接已超时。'
    }
    if ($process.ExitCode -ne 0) { throw '来宾未完成联合备份。请检查受限目录内的 SSH 和来宾 systemd 日志。' }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $bundle = [IO.Compression.ZipFile]::OpenRead($scratch)
    try {
        $manifestEntry = $bundle.GetEntry('manifest.json')
        if ($bundle.Entries.Count -ne 3 -or !$manifestEntry -or $manifestEntry.Length -gt 4096) { throw '联合备份清单无效。' }
        $reader = [IO.StreamReader]::new($manifestEntry.Open())
        try { $manifest = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
        if ($manifest.format -ne 1 -or $manifest.commit -notmatch '^[a-f0-9]{40}$' -or
            $manifest.source_system_identifier -notmatch '^\d{10,32}$' -or
            $manifest.plaintext_sha256 -notmatch '^[a-f0-9]{64}$' -or
            $manifest.recovery_public_sha256 -ne (Get-Content -LiteralPath (Join-Path $base 'recovery-public.sha256') -Raw).Trim()) {
            throw '联合备份清单身份无效。'
        }
        $entries = @{
            'database-and-media.gpg' = $manifest.encrypted_sha256
            'recovery-key.bin' = $manifest.wrapped_key_sha256
        }
        foreach ($name in $entries.Keys) {
            $entry = $bundle.GetEntry($name)
            if (!$entry -or !$entry.Length -or $entries[$name] -notmatch '^[a-f0-9]{64}$') { throw "缺少联合备份校验项：$name" }
            $sha = [Security.Cryptography.SHA256]::Create()
            $stream = $entry.Open()
            try { $digest = [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '') }
            finally { $stream.Dispose(); $sha.Dispose() }
            if ($digest -ne $entries[$name]) { throw "联合备份 SHA-256 不符：$name" }
        }
    } finally { $bundle.Dispose() }
    $file = 'SJERP-auto-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '-' + $manifest.encrypted_sha256.Substring(0,12) + '.zip'
    $digest = (Get-FileHash -LiteralPath $scratch -Algorithm SHA256).Hash
    [IO.File]::Move($scratch,(Join-Path $target $file))
    Write-Status @{ status='VERIFIED'; archive=$file; sha256=$digest; commit=$manifest.commit }
} catch {
    Write-Status @{ status='FAILED'; reason=$_.Exception.Message }
    throw
} finally {
    if (Test-Path -LiteralPath $scratch) { Remove-Item -LiteralPath $scratch -Force }
}
