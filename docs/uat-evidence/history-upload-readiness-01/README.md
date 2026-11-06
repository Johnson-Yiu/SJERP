# HISTORY-UPLOAD-READINESS-01

验收候选 `b7ce265833320cc62a7b9aa57e08880f6013203f`。本分支只提交验收脚本和证据，部署仍以此产品候选为准。

## 开放结论

**暂不开放真实历史资料上传。** 本地可以使用合成数据复验。目标 HTTPS 服务、账号权限、私有存储和目标备份恢复尚待提供和实测。库存、应收应付、未结订单的接续执行留待独立验收。

候选没有历史 XLSX 只读预检页面。“导入”页提供通用 CSV 导入，“历史资料承接”页提交后会保存承接申请和源数据。只读预检使用 `POST /api/import/history-preflight/`，错误及警告清单使用同一路径的 `?report=csv`。该 CSV 包含通过、警告、人工核实和阻断记录。

预检与承接申请共用导入和数据范围权限。受控开放应在专用入口拦截其他导入和业务写入口，并确认应用监听端口不能绕过入口。工作簿通过 multipart 临时读取，预检无需保存工作簿。若另需长期保管原件，须单独明确存放权限、保留期限和删除流程。

## 已有证据及复用范围

- HISTORY-IMPORT-REHEARSAL-01 在 `25056fc4` 的 PostgreSQL 17.11 有 87/87 定向通过。已核对映射、重复预检、归档及接续差异、失败重试、CSV 和恢复日志。旧浏览器核验 CSV 保存且哈希一致，探针退出超时，旧结果保留。历史预检及接续核心模块在两个候选间无直接改动，候选有权限和会话集成变化。
- 候选已有 Chrome 受限登录 4/4、通用 CSV 浏览器定向 6/6。通用 CSV 浏览器使用模拟 API，与历史 XLSX 预检相分开。见 [候选定向证据](../int04/README.md)。
- 本轮在候选上使用 PostgreSQL 17.11 和普通实名权限模型的合成账号。密码登录、CSRF 轮换及权限分流通过。正常样本 3 行（通过 2、警告 1、阻断 0），重复样本 4 行阻断，其中两行标出重复来源。两次重复样本结果一致，4 行错误清单已保存。预检前后 102 张非会话表及私有媒体清单相同。
- 备份恢复到另一数据库后逐行核对 103 张表、1,025 行、134 条迁移和 1 份私有附件。恢复后的会话可按原权限访问文件，匿名及无权限会话被拒。实例已清理。见 [定向原始日志](rehearsal.log)、[正常样本](synthetic.xlsx)、[重复样本](synthetic-duplicates.xlsx)和[错误清单](history-preflight.csv)。仅用合成数据。无全量或 GitHub Actions。

## 目标环境还缺什么

| 缺项 | 用户或运维需要提供 | 合成验收通过条件 |
| --- | --- | --- |
| 目标实例 | 隔离 HTTPS 基础 URL、访问方式（VPN 或内网）、部署负责人及可核对的应用 SHA | 核对为指定候选，HTTPS 证书可信，代理 Cookie、CSRF 和请求限额生效，后端端口不直达 |
| 账号及范围 | 独立实名验收账号和一个无权限对照账号，使用受控渠道交付凭据 | 开发身份关闭。允许账号具备 `imports.import`、全数据范围和九个相关模块查看权限。未登录、无权限及缺 CSRF 请求被拒 |
| 数据和媒体隔离 | 专用 PostgreSQL、媒体与临时上传目录、访问边界和保管负责人 | 仅含获准的导入主档。私有样本只对授权账号可读，公开 `/media/` 和无权限账号无法获取，上传正文及 CSV 不进入代理日志或公共缓存 |
| 只读入口 | 可限制路径及方法的代理或等效入口配置，后端侧可读核对权限 | 允许实名会话及历史预检，验证承接提交、审批执行、普通 CSV 导入及其他业务写入口均被隔离边界拦截。用合成 XLSX 重复预检并下载 CSV，确认业务账和媒体无变化 |
| 恢复环境 | 备份工具、受控备份存储、独立恢复库和恢复窗口，提供运行或见证权限 | 实际恢复到独立目标，核验数据库、私有文件及访问控制，记录 SHA、耗时、权限和清理结果 |

权限所需查看模块为 `customers suppliers skus trade_units orders purchases transactions finance inventory`。代理限额需容纳 multipart 开销，应用当前默认文件上限为 10 MiB。目标应以配置实测值为准。

## 目标验收后如何操作

用 PowerShell 7，在受控终端对已批准的 HTTPS 入口运行。先用合成工作簿验证一轮。真实资料仅在上述目标验收签核后替换路径。保存的 JSON 和 CSV 含业务数据，输出路径应受控。

```powershell
$origin = 'https://替换为已批准的隔离域名'
$workbook = Get-Item -LiteralPath 'C:\受控目录\history.xlsx'
$account = Get-Credential -Message '输入导入预检实名账号'
$session = $null
$headers = $null
$sourceHash = (Get-FileHash -LiteralPath $workbook.FullName -Algorithm SHA256).Hash
try {
  $null = Invoke-WebRequest "$origin/api/session/csrf/" -SessionVariable session -MaximumRedirection 0
  $token = $session.Cookies.GetCookies([uri]$origin)['csrftoken'].Value
  $login = @{ username = $account.UserName; password = $account.GetNetworkCredential().Password } | ConvertTo-Json -Compress
  $null = Invoke-WebRequest "$origin/api/session/login/" -WebSession $session -Method Post -ContentType 'application/json' `
    -Body $login -Headers @{ 'X-CSRFToken' = $token; Referer = "$origin/" } -MaximumRedirection 0
  $token = $session.Cookies.GetCookies([uri]$origin)['csrftoken'].Value
  $headers = @{ 'X-CSRFToken' = $token; Referer = "$origin/" }
  $endpoint = "$origin/api/import/history-preflight/"
  $result = Invoke-RestMethod $endpoint -Method Post -WebSession $session -Headers $headers `
    -Form @{ file = $workbook } -MaximumRedirection 0
  if ($result.preflight_only -ne $true -or $result.business_write_performed -ne $false) { throw '预检响应不符合只读契约' }
  $result.summary
  if ((Get-FileHash -LiteralPath $workbook.FullName -Algorithm SHA256).Hash -ne $sourceHash) { throw '工作簿已变化，请重新预检' }
  Invoke-WebRequest "${endpoint}?report=csv" -Method Post -WebSession $session -Headers $headers `
    -Form @{ file = $workbook } -MaximumRedirection 0 -OutFile 'C:\受控目录\history-preflight.csv'
} finally {
  if ($session -and $headers) {
    $null = Invoke-WebRequest "$origin/api/session/logout/" -Method Post -WebSession $session -Headers $headers -MaximumRedirection 0
  }
  Remove-Variable login,account,session,token,headers -ErrorAction SilentlyContinue
}
```

修正源表后可重新预检。记录使用的文件哈希、目标部署 SHA、两次预检结果及导出 CSV 哈希。遇到阻断、异常响应或缺失结果时停在预检，交给对应负责人处理。

## 本地复执行

从本分支根目录运行。需要锁定 Python 依赖和完整的 PostgreSQL 17 二进制发行目录。使用新输出目录。Windows 沙箱遇到 `pg_ctl` 受限令牌错误时，按项目工具审批流程执行。

```powershell
$py = "$env:TEMP/sunjack-cpython312-verify-20261031-a37d/shared-venv/Scripts/python.exe"
$pg = "$env:TEMP/sunjack-iss018-pg17-d26bfa744cf54322af03ea964e90089f/pgsql/bin"
$env:APP_STAGE = 'development'
$env:DATABASE_URL = 'sqlite:///:memory:'
$env:PYTHONUTF8 = '1'
& $py docs/uat-evidence/history-upload-readiness-01/rehearse.py --postgres-bin $pg --output ".tmp/upload-readiness-$(Get-Date -Format yyyyMMdd-HHmmss)"
```

本地探针使用 Django HTTPS 请求模拟及真实 PostgreSQL，校验密码、CSRF、会话和私有文件应用层权限。目标真实 TLS、代理、文件 ACL、实名成员和恢复操作待独立验收。上述 PowerShell 操作说明也待在目标入口走通。
