# Linux 运维验收

固定基线 `8087f2c68b19a302a25e814ec8ce6113d91d4750`；独立分支 `codex/linux-operations-acceptance-20261104`。本报告随验收进行更新，不代表生产环境已经通过。

## 已有真实 Linux 证据

专用 [Linux runner 运行 41850808334](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41850808334)，源码 `d233a1ef26bb6ad9c69a6d513446110c59f60965`：创建独立 ext4 loop 文件系统，实际可写状态被栅栏拒绝，重挂只读后被接受；独立 shell 写入返回 `Read-only file system`；重挂可写后再次拒绝。此运行没有执行数据库备份中途重挂或改变文件的测试，不声称已覆盖它们。同 SHA 的 [Backend、backend-postgres、Frontend CI](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41850808321) 均成功。

因 GitHub 要求手动触发的工作流存在于默认分支，首次 `workflow_dispatch` 返回 `HTTP 404: workflow linux-operations-acceptance.yml not found on the default branch`。专用工作流保留手动入口并仅对本任务分支增加推送触发；没有更改默认分支或现有 `ci.yml`。

## 真实复现与本地测试

[固定基线回执缺陷复现](receipt-baseline-repro.log)：仅用临时合成文件，未执行任何恢复，自填相同摘要仍使基线删除两个归档。修复改用独立恢复操作人私钥签名和固定公钥指纹验证；签名只在实际解密、恢复、附件及审计核验完成后产生。公钥及其 pin 必须由独立受信管理员配置并保护，保留执行者不能拥有签名私钥。持有签名私钥者能够签发任意回执，密钥必须由受信的独立恢复操作人保管。

[本地运维单元测试](local-unit.log)：合成文件、Windows、CPython 3.12.16；测试包括回执签名、错包、篡改、过期、陌生签名及保留拒绝。模拟恢复的单元测试不能作为真实 PostgreSQL 恢复证据；真正 PG17 和实际媒体验证以专用 runner 结果为准。

恢复签发入口为 `python backend/operations_backup.py restore-encrypted-verify --config <配置>`。配置在原恢复参数之外，需要密文摘要 `encrypted_sha256`、明文摘要 `expected_sha256`、独立加密密钥配置 `encryption`、仅恢复操作人可读的 `receipt_signing.private_key` 和明确的 OpenSSL `receipt_signing.executable`，以及不存在的绝对 `receipt_output`。回执绑定密文及明文摘要、备份来源和恢复目标数据库系统标识、源代码 SHA、恢复数据库、审计结果、签发时间和归档文件的观察到的修改时间；修改时间是文件系统观察值，不冒充历史业务发生时间。签名私钥不放入归档、命令行或日志。

保留入口 `python backend/operations_archive.py prune --config <配置>` 默认只预览；执行需另加 `--execute-prune`。每项需提供由恢复流程生成的 `restore_receipt`，配置以 `receipt_trust_file` 指向独立信任文件。该 JSON 包含 `executable`、`public_key`、公钥 DER SHA-256 的 `pinned_fingerprint` 和 `max_age_seconds`；信任文件、公钥、OpenSSL 可执行文件及其各级目录必须由 root 拥有且不可由其他用户写入，保留和监控入口必须由非 root 账号运行。此限制目前仅支持 Linux，不能验证时拒绝运行。恢复签名私钥由独立恢复角色保护，不交给保留账号。旧 `restore_verified_sha256` 自填声明不能授权删除；缺少签名回执、签名错误、错包、归档时间改变或超期都失败关闭。修改时间、归档及副本应由受控备份存储保护；拥有文件系统直接删除权限的账号仍可绕过该工具，目标环境须另设存储和账号权限。`python backend/operations_monitor.py --config <配置>` 使用相同 `receipt_trust_file`，在受信回执缺失、错误或备份超过频率门槛时返回非零；外部告警投递须目标环境另行测试。

## 本轮正在执行的验收

专用工作流增加三个互相独立的 runner job：原始媒体栅栏；新建 PG17 服务、真实只读媒体、非超级用户维护/运行角色、签名回执及故障测试；Nginx、自签测试证书、合成 SQLite、认证和越权附件及进程重启测试。所有系统资源仅属于一次性 runner；不使用生产 secret、数据库或媒体。

源码 `56d64848bed5dac0a507348c10313a566012b0be` 的 [专用运行 41857531961](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41857531961) 中，真实 Linux media-fence 与 Nginx 私有附件 job 成功，PG17 job 失败；[三个 job 的原始压缩日志](./)均保留。Nginx 用实际 `nginx -t` 及自签测试证书：SKU 下载授权 200、匿名 403、无权 404、公开直链 404；财务凭证授权 200、匿名 403、无权 403、公开直链 404；私有响应 no-store，Nginx 和 Django 重启后合成文件仍可访问，19.369 秒。该证书不代表正式证书通过。

PG17 首轮的维护/受限账号、真实媒体门禁及两类中途更改已执行到恢复阶段，但报 `RuntimeError: pg_restore failed; credential-bearing diagnostics withheld`，不得将该 job 写成成功。独立使用真实 PG17 客户端重现发现：`pg_restore --list -` 把 `-` 视为文件名，省略文件名才读 stdin；这是测试容器客户端传输器的调用错误。[原始失败日志](linux-pg-failure.raw.log.gz)及[真实客户端复现](pg-restore-stdin-repro.log)保留。已仅修正该测试传输器，后续运行结果须以对应精确 SHA 为准。

[本机真实 PG17/GPG 回执专项](local-real-pg-receipt.log)在 `56d64848bed5dac0a507348c10313a566012b0be`：99 表、1005 行，真实加密、恢复、签名回执和两份旧归档保留处理通过，源数据库未变，62.969 秒，cleanup complete；该运行的媒体只读栅栏是模拟，不能代替 Linux job。

修正传输器后的 `b48e92084f3645a2ec0cc0c5918f0dcc53455e1b` [真实 Linux 运行 41858410673](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41858410673) 三个 job 均成功：[媒体原始日志](linux-media-pass-b48e920.raw.log.gz)、[PG17 原始日志](linux-pg-pass-b48e920.raw.log.gz)、[Nginx 原始日志](linux-nginx-pass-b48e920.raw.log.gz)。所有压缩文件保留 GitHub 返回的原始字节，解压后可直接检索。

PG17 使用该 job 自建的 PostgreSQL 17 service，维护角色和应用角色均明确验证非 superuser。应用角色实际 SELECT/INSERT 允许、UPDATE/DELETE/TRUNCATE 因权限被拒；启用的其他登录角色、仍活动的竞争连接被分别拒绝。备份在真实 ext4 只读卷上执行；用独立 mount 进程在备份过程中解除保护、以及解除后修改文件再重置只读，均被真实检查拒绝，最终成功归档未被发布。这里仅对故障注入时机加测试钩子，没有模拟文件系统栅栏。

受限维护角色实际恢复 99 表、975 行和合成 FinanceVoucher，校验完整行/序列、私有凭证摘要及审计触发器。三份实际 GPG 解密及数据库恢复分别生成独立签名回执；自填、伪造签名、错包、篡改、真实过期和组可写保留目录均拒绝，保留最新备份、删除两份已核验旧备份，三个本机副本不删除。实际 Linux ENOSPC、备份进程中断、清理权限错误及错误密钥均触发预期保护；源数据库和凭证未变。监控命令健康返回 0、漏执行返回 1；本地 syslog 与任务自建 loopback 告警入口均实际接收。整个 PG17 专项 30.171 秒；副本仍位于同一 runner，不能算异地容灾。

Nginx job 重新在独立合成 SQLite、真实 Nginx 及本地自签测试证书上通过：SKU 文件授权/匿名/越权/公开直链分别为 200/403/404/404，财务凭证为 200/403/403/404；私有响应 no-store，两个服务重启后文件仍可访问，14.068 秒。此实验不替代真实证书、目标主机 ACL、部署代理或生产数据验证。

`bcac0ec503e0e48064e20907b5de97c8da7f89ef` 的 [Linux 运行 41859454586](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41859454586) 三个 job 均成功，原始日志：[PG17 与 systemd](linux-pg-pass-bcac0ec.raw.log.gz)、[Nginx](linux-nginx-pass-bcac0ec.raw.log.gz)、[媒体栅栏](linux-media-pass-bcac0ec.raw.log.gz)。PG17 专项实际创建独立 systemd timer，使已过期的备份监控退出码为 1；`OnFailure` 触发唯一临时告警 unit，并由任务独占的本地 UDP 接收器收到合成告警；唯一临时 unit 已清理。该实验只证明本机入口与传递，不代表外部值班通知或生产调度已验收。PG17、受限角色、真实媒体竞争、加密恢复、回执及故障路径同时通过，99 表、975 行，29.639 秒。

新增 [回执清理边界单元测试](local-unit-after-cleanup.log)：49 项全通过。对模拟的临时明文清理错误，保留原恢复错误及清理错误；如果真实恢复已完成但回执签发或清理失败，则不返回成功回执，并在错误附注中标明需要核查的本次恢复目标。这些模拟注入仅验证错误传播，不替代上面的真实 Linux 清理权限失败演练。

本机 Windows 对 Linux mount 验收不能作为通过或阻塞的唯一理由；GitHub Linux runner 已证明支持初始 loop 文件系统操作。外部备份故障域、生产证书、目标服务器角色 ACL、真实调度告警投递及上线仍须单独验收，同机临时副本不是异地容灾。不修改业务模块、公共台账和现有 CI workflow。

## 独立信任根复验

源码 `81d37ddb78748f61d58e24ace023fe7fc16a1379` 的 [Linux 专项运行 41862017884](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41862017884) 三项均成功，保留真实原始日志：[媒体栅栏](81d37dd-media-fence.raw.log.gz)、[PG17 与回执](81d37dd-postgres-role-receipts.raw.log.gz)、[Nginx 与私有附件](81d37dd-nginx-private-media.raw.log.gz)。实际恢复角色的私钥由 root 持有且运行保留的普通账号不能读取；可由普通账号修改的信任配置被拒绝，root 管理的公钥和信任文件可供普通账号验证。实际解密并恢复三次，确认伪造、错包、过期输入拒绝；99 表、975 行，源数据库及合成凭证不变，专项耗时 29.406 秒。真实临时 systemd timer 和 OnFailure 到本机接收器通过；外部告警及独立故障域仍需在目标环境验证。

同轮本地 CPython 3.12 相关单元测试 27 项通过；Django system check 与迁移差异检查通过。该 Linux 测试使用临时 CI 环境和合成密钥，不代表生产密钥交接完成。
