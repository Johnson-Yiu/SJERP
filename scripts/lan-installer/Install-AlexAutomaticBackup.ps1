#Requires -Version 5.1
#Requires -RunAsAdministrator
[CmdletBinding()]
param()

$ErrorActionPreference='Stop'
if ($env:COMPUTERNAME -ne 'ALEX') { throw '请在 ALEX 本机运行。' }
$dir = Split-Path -Parent $PSCommandPath
$iso = Join-Path $dir 'sjerp-automatic-backup-template.iso'
$receive = Join-Path $dir 'Receive-AlexAutomaticBackup.ps1'
$pins = @{
    $iso = '022CBC29B9B009C112C3998B90CAC9186BC12555A72DACBE0EEE93AE2546D579'
    $receive = '2B875328DAFC9246852300AA910400A19C0E38575A5924C1D4276CF0F75B16F8'
}
foreach ($file in $pins.Keys) {
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $pins[$file]) { throw "交付文件校验失败：$file" }
}
$task = 'SJERP-AutomaticJointBackup'
$base = Join-Path $env:ProgramData 'SJERP-AutoBackup'
if ((Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue) -or (Test-Path -LiteralPath $base)) {
    throw '已存在备份任务或本地安装目录，请先检查现有安装状态。'
}
$destination = Get-Item -LiteralPath 'D:\ERP备份' -Force
if (!$destination.PSIsContainer -or ($destination.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw '未找到有效的 D:\ERP备份 目录。'
}
$guest = Get-VM -Name 'SJERP-Linux-CombinedTest'
$nics = @(Get-VMNetworkAdapter -VM $guest | Where-Object MacAddress -eq '02534A455201')
$dvd = @(Get-VMDvdDrive -VM $guest)
$internal = @(Get-NetIPAddress -IPAddress '10.253.247.1' -AddressFamily IPv4)
if ($nics.Count -ne 1 -or $nics[0].SwitchName -ne 'SJERP-HTTPS-Internal' -or
    $dvd.Count -ne 1 -or $internal.Count -ne 1 -or $internal[0].PrefixLength -ne 30) {
    throw 'ERP 来宾身份或固定专用网络不符。'
}
$known = '10.253.247.2 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPgM6a65T0QV00qS7EJcT/wPFkks+tqOnd/vC1fOVRnp'
$keygen = Join-Path $env:SystemRoot 'System32\OpenSSH\ssh-keygen.exe'
$ssh = Join-Path $env:SystemRoot 'System32\OpenSSH\ssh.exe'
if (!(Test-Path -LiteralPath $keygen) -or !(Test-Path -LiteralPath $ssh)) { throw '缺少 Windows OpenSSH 客户端。' }
Write-Host '计划每天 03:00 执行。每次备份期间暂停 ERP 写入，完成后自动恢复服务。'
if ((Read-Host '确认现在短暂重启 ERP 虚拟机并执行首份备份，请输入 YES') -cne 'YES') { return }

New-Item -ItemType Directory -Path $base | Out-Null
& icacls.exe $base '/inheritance:r' '/grant:r' '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE) { throw '无法限制 ALEX 本地备份配置目录权限。' }
$identity = Join-Path $base 'collector'
$arguments = '-q -t ed25519 -N "" -C sjerp-backup -f "{0}"' -f $identity
$keygenResult = Start-Process -FilePath $keygen -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
if ($keygenResult.ExitCode -ne 0) { throw '无法生成备份连接密钥。' }
& icacls.exe $identity '/inheritance:r' '/grant:r' '*S-1-5-18:F' | Out-Null
if ($LASTEXITCODE) { throw '无法限制备份连接私钥权限。' }
& icacls.exe $identity '/setowner' '*S-1-5-18' | Out-Null
if ($LASTEXITCODE) { throw '无法将备份连接私钥交给系统任务。' }

$public = (Get-Content -LiteralPath "$identity.pub" -Raw).Trim()
if ($public -cnotmatch '^ssh-ed25519 [A-Za-z0-9+/]{68} sjerp-backup$') { throw '不支持的备份连接公钥。' }
$marker = 'ssh-ed25519 ' + (('Z' * 68) -join '') + ' sjerp-backup'
$binary = [Text.Encoding]::GetEncoding(28591)
$contents = $binary.GetString([IO.File]::ReadAllBytes($iso))
$position = $contents.IndexOf($marker,[StringComparison]::Ordinal)
if ($position -lt 0 -or $position -ne $contents.LastIndexOf($marker,[StringComparison]::Ordinal)) {
    throw '自动备份镜像中的公钥占位无效。'
}
$seed = Join-Path $base 'sjerp-automatic-backup.iso'
[IO.File]::WriteAllBytes($seed,$binary.GetBytes($contents.Substring(0,$position) + $public + $contents.Substring($position + $marker.Length)))
[IO.File]::WriteAllText((Join-Path $base 'known_hosts'),$known + [char]10)
[IO.File]::WriteAllText((Join-Path $base 'recovery-public.sha256'),'287B870EAE654532E95EE80C8542E6AFBA45AB78B2DDD3985C8C4E9CEAA98BDE')
$installed = Join-Path $base 'Receive-AlexAutomaticBackup.ps1'
Copy-Item -LiteralPath $receive -Destination $installed

$old = $dvd[0].Path
if ($guest.State -ne 'Off') { Stop-VM -VM $guest }
if ((Get-VM -Id $guest.Id).State -ne 'Off') { throw 'ERP 来宾尚未关机。' }
try {
    Set-VMDvdDrive -VMDvdDrive $dvd[0] -Path $seed
    Start-VM -VM $guest | Out-Null
} catch {
    if ((Get-VM -Id $guest.Id).State -eq 'Off') {
        Set-VMDvdDrive -VMDvdDrive $dvd[0] -Path $old
        Start-VM -VM $guest | Out-Null
    }
    throw
}
Write-Host '自动备份配置已启动，等待 ERP 和来宾设置完成。'
Start-Sleep -Seconds 90

$action = New-ScheduledTaskAction -Execute (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $installed)
$trigger = New-ScheduledTaskTrigger -Daily -At 03:00
$principal = New-ScheduledTaskPrincipal -UserId 'NT AUTHORITY\SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 35)
Register-ScheduledTask -TaskName $task -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'SJERP 每日加密数据库和附件联合备份' | Out-Null
Start-ScheduledTask -TaskName $task
$last = Join-Path $base 'last-run.json'
$deadline = (Get-Date).AddMinutes(35)
do {
    if (Test-Path -LiteralPath $last) {
        $status = Get-Content -LiteralPath $last -Raw | ConvertFrom-Json
        if ($status.status -eq 'VERIFIED') {
            Write-Host "自动联合备份已验证。归档：$($status.archive)"
            return
        }
        if ($status.status -eq 'FAILED') {
            throw "自动任务已登记，首份备份失败。$($status.reason) 查看 $last"
        }
    }
    Start-Sleep -Seconds 5
} while ((Get-Date) -lt $deadline)
throw "首份备份未在期限内完成。请查看 $last 和任务 $task。"
