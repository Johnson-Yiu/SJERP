$ErrorActionPreference = 'Stop'
$evidencePath = $PSScriptRoot
$stagingPath = Join-Path $evidencePath '.archive-staging'
New-Item -ItemType Directory -Path $stagingPath -Force | Out-Null
$sources = @(Get-ChildItem -LiteralPath $evidencePath -Filter '*.log' -File)
foreach ($source in $sources) {
    # Ephemeral isolation identities are not needed in published test logs.
    # Preserve all other command output, including failures and whitespace.
    $content = [IO.File]::ReadAllText($source.FullName)
    $content = [regex]::Replace($content, '(?<![a-f0-9])[a-f0-9]{48}(?![a-f0-9])', '[ISOLATION_TOKEN_REDACTED]')
    [IO.File]::WriteAllText((Join-Path $stagingPath $source.Name), $content, [Text.UTF8Encoding]::new($false))
}
$artifactsPath = Join-Path $evidencePath 'artifacts'
if (Test-Path -LiteralPath $artifactsPath) {
    $contexts = @(Get-ChildItem -LiteralPath $artifactsPath -Recurse -File -Filter 'error-context.md')
    for ($index = 0; $index -lt $contexts.Count; $index++) {
        Copy-Item -LiteralPath $contexts[$index].FullName -Destination (Join-Path $stagingPath "failed-browser-context-$index.md")
    }
}
$files = @(Get-ChildItem -LiteralPath $stagingPath -File | ForEach-Object FullName)
Compress-Archive -LiteralPath $files -DestinationPath (Join-Path $evidencePath 'execution-logs.zip') -Force
Get-FileHash -LiteralPath (Join-Path $evidencePath 'execution-logs.zip') -Algorithm SHA256
