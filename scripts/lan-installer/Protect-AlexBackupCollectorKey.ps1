#Requires -Version 5.1
#Requires -RunAsAdministrator
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
$path = Join-Path $env:ProgramData 'SJERP-AutoBackup\collector'
$key = Get-Item -LiteralPath $path -Force
if ($key.PSIsContainer -or ($key.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw '备份连接私钥不是普通文件。'
}
$system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$admins = [Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')
$sidType = [Security.Principal.SecurityIdentifier]
if ((Get-Acl -LiteralPath $path).GetOwner($sidType) -ne $system) {
    & icacls.exe $path '/setowner' '*S-1-5-18' | Out-Null
    if ($LASTEXITCODE) { throw '无法将备份连接私钥所有者设为 SYSTEM。' }
}

# Replace the entire DACL. Disabling inheritance alone retains explicit ACEs
# created by ssh-keygen for the interactive installer.
$policy = [Security.AccessControl.FileSecurity]::new()
$policy.SetAccessRuleProtection($true,$false)
$full = [Security.AccessControl.FileSystemAccessRule]::new($system,'FullControl','Allow')
$metadata = [Security.AccessControl.FileSystemRights]::ReadPermissions -bor [Security.AccessControl.FileSystemRights]::ChangePermissions
$adminRule = [Security.AccessControl.FileSystemAccessRule]::new($admins,$metadata,'Allow')
$policy.AddAccessRule($full)
$policy.AddAccessRule($adminRule)
[IO.File]::SetAccessControl($path,$policy)

$actual = Get-Acl -LiteralPath $path
$rules = @($actual.GetAccessRules($true,$true,$sidType))
$systemRule = @($rules | Where-Object { $_.IdentityReference -eq $system })
$adminActual = @($rules | Where-Object { $_.IdentityReference -eq $admins })
if ($actual.GetOwner($sidType) -ne $system -or !$actual.AreAccessRulesProtected -or
    $rules.Count -ne 2 -or @($rules | Where-Object { $_.IsInherited -or $_.AccessControlType -ne 'Allow' }).Count -ne 0 -or
    $systemRule.Count -ne 1 -or $systemRule[0].FileSystemRights -ne $full.FileSystemRights -or
    $adminActual.Count -ne 1 -or $adminActual[0].FileSystemRights -ne $adminRule.FileSystemRights) {
    throw '私钥权限核对失败，自动备份任务未启动。'
}
Write-Host '备份连接私钥权限已核对。'
