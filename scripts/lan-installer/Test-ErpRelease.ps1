#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Bundle = $PSScriptRoot,
    [Parameter(Mandatory)][ValidatePattern('^[A-Fa-f0-9]{64}$')][string]$ManifestSha256
)
$ErrorActionPreference = 'Stop'
$root = (Get-Item -LiteralPath $Bundle).FullName
$manifestPath = Join-Path $root 'RELEASE.json'
if ((Get-FileHash -LiteralPath $manifestPath).Hash -ne $ManifestSha256) {
    throw '发布清单摘要不符。请从可信交付记录核对摘要。'
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.commit -notmatch '^[a-f0-9]{40}$' -or !$manifest.files) {
    throw '发布清单缺少提交或文件列表。'
}
$expected = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($entry in $manifest.files.PSObject.Properties) {
    $relative = [string]$entry.Name
    if ($relative -notmatch '^[^\\:/]+(/[^\\:/]+)*$' -or ($relative.Split('/') | Where-Object { $_ -in '.', '..' })) {
        throw "清单路径无效：$relative"
    }
    if (!$expected.Add($relative)) { throw "重复路径：$relative" }
}
$pending = [Collections.Generic.Stack[string]]::new()
$pending.Push($root)
while ($pending.Count) {
    foreach ($item in Get-ChildItem -LiteralPath $pending.Pop() -Force) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "发现重解析点：$($item.FullName)" }
        if ($item.PSIsContainer) { $pending.Push($item.FullName); continue }
        $relative = $item.FullName.Substring($root.Length + 1).Replace('\','/')
        if ($relative -ne 'RELEASE.json' -and !$expected.Contains($relative)) { throw "清单外文件：$relative" }
    }
}
foreach ($entry in $manifest.files.PSObject.Properties) {
    $path = Join-Path $root $entry.Name
    $file = Get-Item -LiteralPath $path
    if ($file.PSIsContainer -or $file.Length -ne $entry.Value.bytes -or (Get-FileHash -LiteralPath $path).Hash -ne $entry.Value.sha256) {
        throw "文件校验失败：$($entry.Name)"
    }
}
Write-Host "发布提交 $($manifest.commit)，已校验 $($expected.Count) 个文件。"
