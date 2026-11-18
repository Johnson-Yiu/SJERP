#Requires -Version 5.1
[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateSet('Menu','Status','Start','Stop','Restart','Backup','BackupLogs','Console','CloseDiagnostics')]
    [string]$Action = 'Menu'
)

$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $PSCommandPath
$url = 'https://192.168.1.36'
$backupName = 'SJERP-AutomaticJointBackup'
$backupState = Join-Path $env:ProgramData 'SJERP-AutoBackup'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$localAdmin = $env:COMPUTERNAME -eq 'ALEX' -and
    [Security.Principal.WindowsPrincipal]::new($identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

function Get-ErpVm {
    $vm = Get-VM -Name 'SJERP-Linux-CombinedTest'
    $nic = @(Get-VMNetworkAdapter -VM $vm | Where-Object {
        $_.MacAddress -eq '02534A455201' -and $_.SwitchName -eq 'SJERP-HTTPS-Internal'
    })
    if ($nic.Count -ne 1) { throw 'ERP 虚拟机身份与交接记录不符。' }
    $vm
}
function Get-ErpHealth {
    $ca = Join-Path $base 'sjerp-alex-ca-v3.pem'
    if ((Get-FileHash -LiteralPath $ca).Hash -ne '9E03526B4A45ABC29531394C2EDC9D04AC6671ACD8C2B1EF0AE6329281EEAD6B') {
        throw '团队 CA 证书摘要不符。'
    }
    $curl = Join-Path $env:SystemRoot 'System32\curl.exe'
    $flags = @('--noproxy','*','--ssl-revoke-best-effort','--cacert',$ca,
        '--connect-timeout','3','--max-time','7','--silent','--show-error','--fail')
    $release = & $curl @flags "$url/release-info.json"
    if ($LASTEXITCODE) { throw '无法读取 ERP HTTPS 发布信息。' }
    $release = ($release -join [Environment]::NewLine | ConvertFrom-Json).commit
    if ($release -cnotmatch '^[0-9a-f]{40}$') { throw 'ERP 发布信息无效。' }
    $http = & $curl @flags --output NUL --write-out '%{http_code}' "$url/api/session/csrf/"
    if ($LASTEXITCODE -or $http -ne '200') { throw 'ERP 会话接口健康检查失败。' }
    Write-Host "ERP HTTPS 正常，发布提交 $release"
}
function Get-DiagnosticChannel {
    $rows = @(netsh interface portproxy show v4tov4)
    if ($LASTEXITCODE -or !($rows -match '^\s*192\.168\.1\.36\s+443\s+10\.253\.247\.2\s+18443\s*$')) {
        throw '无法核对 ERP 的固定 HTTPS 转发。'
    }
    $proxy = @($rows -match '^\s*\S+\s+22223\s')
    $rules = @(Get-NetFirewallRule -Name 'SJERP-Restore-Diagnostics-Temporary','SJERP-Deployment-Backup-Temporary' -ErrorAction SilentlyContinue)
    if (!$proxy.Count -and !$rules.Count) {
        if (Get-NetTCPConnection -LocalPort 22223 -State Listen -ErrorAction SilentlyContinue) { throw '22223 仍有监听，无法确认归属。' }
        return
    }
    if ($proxy.Count -gt 1 -or ($proxy.Count -eq 1 -and
        $proxy[0] -notmatch '^\s*192\.168\.1\.36\s+22223\s+10\.253\.247\.2\s+22\s*$') -or $rules.Count -ne 1) {
        throw '22223 的转发或规则归属无法确认。'
    }
    $address = $rules[0] | Get-NetFirewallAddressFilter
    $port = $rules[0] | Get-NetFirewallPortFilter
    if (($address.LocalAddress -join ',') -ne '192.168.1.36' -or ($address.RemoteAddress -join ',') -ne '192.168.1.79' -or
        ($port.LocalPort -join ',') -ne '22223' -or $port.Protocol -notin 'TCP','6' -or
        $rules[0].Direction -ne 'Inbound' -or $rules[0].Action -ne 'Allow') {
        throw '22223 的防火墙筛选条件与交付记录不符。'
    }
    [pscustomobject]@{Proxy=($proxy.Count -eq 1); Rule=$rules[0]}
}
function Invoke-ErpAction([string]$Name) {
    if ($Name -eq 'Status') {
        if ($localAdmin) {
            Get-ErpVm | Select-Object Name,State,Status | Format-List
            Get-ScheduledTaskInfo -TaskName $backupName | Select-Object LastRunTime,LastTaskResult,NextRunTime | Format-List
        }
        Get-ErpHealth
        $probe = Join-Path $base 'SJERP-AutomaticBackup-Recovery\Test-AlexBackupArchive.ps1'
        & $probe | Format-List
        return
    }
    if (!$localAdmin) { throw '该操作须在 ALEX 的管理员 PowerShell 执行。' }
    switch ($Name) {
        'CloseDiagnostics' {
            $channel = Get-DiagnosticChannel
            if (!$channel) { Write-Host '临时恢复诊断入口已关闭。'; return }
            if (!$PSCmdlet.ShouldProcess('ALEX 22223', '关闭 SJERP 临时恢复诊断')) { return }
            if ($channel.Proxy) {
                netsh interface portproxy delete v4tov4 listenaddress=192.168.1.36 listenport=22223 | Out-Null
                if ($LASTEXITCODE) { throw '删除临时诊断转发失败。' }
            }
            Remove-NetFirewallRule -InputObject $channel.Rule
            if (Get-DiagnosticChannel) { throw '临时诊断入口仍存在。' }
            Get-ErpHealth
            Write-Host '临时恢复诊断入口已关闭。'
        }
        'Backup' {
            $task = Get-ScheduledTask -TaskName $backupName
            if ($task.State -ne 'Ready') { throw '现有备份任务未就绪。' }
            if ($PSCmdlet.ShouldProcess($backupName, '开始联合备份，ERP 将短暂停止')) {
                Start-ScheduledTask -TaskName $backupName
                Write-Host '已提交联合备份。请用「查看备份日志」检查结果。'
            }
        }
        'BackupLogs' {
            Get-ScheduledTaskInfo -TaskName $backupName | Select-Object LastRunTime,LastTaskResult,NextRunTime | Format-List
            $record = Join-Path $backupState 'last-run.json'
            $log = Join-Path $backupState 'ssh-error.log'
            if (Test-Path -LiteralPath $record -PathType Leaf) { Get-Content -LiteralPath $record -Encoding UTF8 -Raw | ConvertFrom-Json | Format-List }
            if (Test-Path -LiteralPath $log -PathType Leaf) { Get-Content -LiteralPath $log -Encoding UTF8 -Tail 20 }
        }
        'Console' {
            $vm = Get-ErpVm
            Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\vmconnect.exe') -ArgumentList @('localhost',$vm.Name)
        }
        default {
            $vm = Get-ErpVm
            if ($vm.State -notin 'Off','Running') { throw '虚拟机正在转换状态，或需要在 Hyper-V 中检查。' }
            if ((Get-ScheduledTask -TaskName $backupName).State -eq 'Running') { throw '联合备份正在执行。' }
            if (!$PSCmdlet.ShouldProcess($vm.Name,$Name)) { return }
            if ($Name -in 'Stop','Restart' -and $vm.State -eq 'Running') {
                Stop-VM -VM $vm -Confirm:$false
                if ((Get-VM -Id $vm.Id).State -ne 'Off') { throw '未能正常关闭 ERP 虚拟机。' }
            }
            if ($Name -in 'Start','Restart' -and (Get-VM -Id $vm.Id).State -eq 'Off') { Start-VM -VM $vm | Out-Null }
            Get-VM -Id $vm.Id | Select-Object Name,State,Status | Format-List
        }
    }
}
if ($Action -ne 'Menu') { Invoke-ErpAction $Action; return }
$choices = @{ '1'='Status'; '2'='Start'; '3'='Stop'; '4'='Restart'; '5'='Backup'; '6'='BackupLogs'; '7'='Console'; '8'='CloseDiagnostics' }
do {
    Write-Host '1 状态与健康检查    2 启动 ERP      3 停止 ERP       4 重启 ERP'
    Write-Host '5 执行联合备份      6 查看备份日志  7 打开来宾控制台  8 关闭临时诊断'
    Write-Host '0 退出'
    $choice = Read-Host '请输入编号'
    if (!$choices.ContainsKey($choice)) { continue }
    if ($choice -in '2','3','4','5','8' -and (Read-Host '输入 YES 确认执行') -cne 'YES') { continue }
    try { Invoke-ErpAction $choices[$choice] } catch { Write-Host $_.Exception.Message -ForegroundColor Red }
} while ($choice -ne '0')
