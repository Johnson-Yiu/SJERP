#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$BackupDirectory = '\\ALEX\d\ERP备份',
    [ValidatePattern('^[0-9]{4}-[0-9]{2}-[0-9]{2}$')][string]$ScheduledDate
)

$ErrorActionPreference = 'Stop'
$pattern = '^SJERP-auto-(?<utc>[0-9]{8}T[0-9]{6}Z)-(?<digest>[a-f0-9]{12})\.zip$'
$china = [TimeZoneInfo]::FindSystemTimeZoneById('China Standard Time')
$culture = [Globalization.CultureInfo]::InvariantCulture
$format = "yyyyMMdd'T'HHmmss'Z'"
$archives = @(Get-ChildItem -LiteralPath $BackupDirectory -File -Filter '*.zip' |
    Where-Object { $_.Name -cmatch $pattern } | Sort-Object Name -Descending)
$window = 'LatestArchive'

if ($PSBoundParameters.ContainsKey('ScheduledDate')) {
    $date = [DateTime]::ParseExact($ScheduledDate,'yyyy-MM-dd',$culture).AddHours(3)
    $start = [TimeZoneInfo]::ConvertTimeToUtc($date,$china)
    $end = $start.AddMinutes(35)
    if ([DateTime]::UtcNow -lt $end) {
        return [pscustomobject]@{Status='WaitingForScheduleWindow'; ScheduledDate=$ScheduledDate; WindowEndChina=$date.AddMinutes(35).ToString('yyyy-MM-dd HH:mm:ss',$culture)}
    }
    $archives = @($archives | Where-Object {
        $issued = [DateTimeOffset]::ParseExact([regex]::Match($_.Name,$pattern).Groups['utc'].Value,$format,$culture,
            [Globalization.DateTimeStyles]::AssumeUniversal).UtcDateTime
        $issued -ge $start -and $issued -le $end
    })
    $window = 'ScheduleWindowMatch'
}
if (!$archives.Count) { return [pscustomobject]@{Status='NoArchive'; ScheduledDate=$ScheduledDate} }

$file = $archives[0]
$parts = [regex]::Match($file.Name,$pattern)
$expectedPublic = '287B870EAE654532E95EE80C8542E6AFBA45AB78B2DDD3985C8C4E9CEAA98BDE'
Add-Type -AssemblyName System.IO.Compression
$stream = [IO.File]::Open($file.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
try {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $archiveHash = [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-','').ToLowerInvariant()
        $stream.Position = 0
        $zip = [IO.Compression.ZipArchive]::new($stream,[IO.Compression.ZipArchiveMode]::Read,$true)
        try {
            $entries = @($zip.Entries | ForEach-Object FullName | Sort-Object)
            if (($entries -join '|') -cne 'database-and-media.gpg|manifest.json|recovery-key.bin') { throw '联合归档文件清单不符。' }
            $entry = $zip.GetEntry('manifest.json')
            if ($entry.Length -gt 4096 -or $zip.GetEntry('recovery-key.bin').Length -ne 384) { throw '清单或恢复密钥信封长度无效。' }
            $reader = [IO.StreamReader]::new($entry.Open())
            try { $manifest = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
            if ($manifest.format -ne 1 -or $manifest.commit -cnotmatch '^[a-f0-9]{40}$' -or
                $manifest.source_system_identifier -notmatch '^[0-9]{10,32}$' -or
                $manifest.plaintext_sha256 -cnotmatch '^[a-f0-9]{64}$' -or
                $manifest.encrypted_sha256 -cnotmatch ('^' + $parts.Groups['digest'].Value + '[a-f0-9]{52}$') -or
                $manifest.recovery_public_sha256 -ne $expectedPublic) {
                throw '归档名称、发布或恢复接收者身份与清单不符。'
            }
            $digests = @{ 'database-and-media.gpg'=$manifest.encrypted_sha256; 'recovery-key.bin'=$manifest.wrapped_key_sha256 }
            foreach ($name in $digests.Keys) {
                $item = $zip.GetEntry($name).Open()
                try { $digest = [BitConverter]::ToString($sha.ComputeHash($item)).Replace('-','') } finally { $item.Dispose() }
                if ($digest -ne $digests[$name]) { throw "归档内部 SHA-256 不符 $name" }
            }
        } finally { $zip.Dispose() }
    } finally { $sha.Dispose() }
} finally { $stream.Dispose() }
$issued = [DateTimeOffset]::ParseExact($parts.Groups['utc'].Value,$format,$culture,[Globalization.DateTimeStyles]::AssumeUniversal)
[pscustomobject]@{
    Status='Verified'; Evidence=$window; Archive=$file.Name; CreatedChina=[TimeZoneInfo]::ConvertTime($issued,$china).ToString('yyyy-MM-dd HH:mm:ss',$culture)
    SHA256=$archiveHash; Release=$manifest.commit
}
