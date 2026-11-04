# Linux 运维验收

固定基线 `8087f2c68b19a302a25e814ec8ce6113d91d4750`；独立分支 `codex/linux-operations-acceptance-20261104`。本报告随验收进行更新，不代表生产环境已经通过。

## 已有真实 Linux 证据

专用 [Linux runner 运行 41850808334](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41850808334)，源码 `d233a1ef26bb6ad9c69a6d513446110c59f60965`：创建独立 ext4 loop 文件系统，实际可写状态被栅栏拒绝，重挂只读后被接受；独立 shell 写入返回 `Read-only file system`；重挂可写后再次拒绝。此运行没有执行数据库备份中途重挂或改变文件的测试，不声称已覆盖它们。同 SHA 的 [Backend、backend-postgres、Frontend CI](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41850808321) 均成功。

因 GitHub 要求手动触发的工作流存在于默认分支，首次 `workflow_dispatch` 返回 `HTTP 404: workflow linux-operations-acceptance.yml not found on the default branch`。专用工作流保留手动入口并仅对本任务分支增加推送触发；没有更改默认分支或现有 `ci.yml`。

## 真实复现与本地测试

[固定基线回执缺陷复现](receipt-baseline-repro.log)：仅用临时合成文件，未执行任何恢复，自填相同摘要仍使基线删除两个归档。修复改用独立恢复操作人私钥签名和固定公钥指纹验证；签名只在实际解密、恢复、附件及审计核验完成后产生。公钥及其 pin 必须由独立受信管理员配置并保护，保留执行者不能拥有签名私钥。持有签名私钥者能够签发任意回执，密钥必须由受信的独立恢复操作人保管。

[本地运维单元测试](local-unit.log)：合成文件、Windows、CPython 3.12.16；测试包括回执签名、错包、篡改、过期、陌生签名及保留拒绝。模拟恢复的单元测试不能作为真实 PostgreSQL 恢复证据；真正 PG17 和实际媒体验证以专用 runner 结果为准。

恢复签发入口为 `python backend/operations_backup.py restore-encrypted-verify --config <配置>`。配置在原恢复参数之外，需要密文摘要 `encrypted_sha256`、明文摘要 `expected_sha256`、独立加密密钥配置 `encryption`、仅恢复操作人可读的 `receipt_signing.private_key` 和明确的 OpenSSL `receipt_signing.executable`，以及不存在的绝对 `receipt_output`。回执绑定密文及明文摘要、备份来源和恢复目标数据库系统标识、源代码 SHA、恢复数据库、审计结果、签发时间和归档文件的观察到的修改时间；修改时间是文件系统观察值，不冒充历史业务发生时间。签名私钥不放入归档、命令行或日志。

保留入口 `python backend/operations_archive.py prune --config <配置>` 默认只预览；执行需另加 `--execute-prune`。每项需提供由恢复流程生成的 `restore_receipt`，以及独立受保护的 `receipt_verification` 配置：OpenSSL 可执行文件、验证公钥、该公钥 DER SHA-256 固定指纹及 `max_age_seconds`。旧 `restore_verified_sha256` 的自填声明不能授权删除；缺少签名回执、签名错误、错包、归档时间改变或超期都失败关闭。修改时间、归档及副本应由受控备份存储保护；持有私钥的恢复角色不应同时由保留执行账号使用。`python backend/operations_monitor.py --config <配置>` 在受信回执缺失、错误或备份超过频率门槛时返回非零，适合作为本地调度和告警入口；外部告警投递须目标环境另行测试。

## 本轮正在执行的验收

专用工作流增加三个互相独立的 runner job：原始媒体栅栏；新建 PG17 服务、真实只读媒体、非超级用户维护/运行角色、签名回执及故障测试；Nginx、自签测试证书、合成 SQLite、认证和越权附件及进程重启测试。所有系统资源仅属于一次性 runner；不使用生产 secret、数据库或媒体。

源码 `56d64848bed5dac0a507348c10313a566012b0be` 的 [专用运行 41857531961](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41857531961) 中，真实 Linux media-fence 与 Nginx 私有附件 job 成功，PG17 job 失败；[三个 job 的原始压缩日志](./)均保留。Nginx 用实际 `nginx -t` 及自签测试证书：SKU 下载授权 200、匿名 403、无权 404、公开直链 404；财务凭证授权 200、匿名 403、无权 403、公开直链 404；私有响应 no-store，Nginx 和 Django 重启后合成文件仍可访问，19.369 秒。该证书不代表正式证书通过。

PG17 首轮的维护/受限账号、真实媒体门禁及两类中途更改已执行到恢复阶段，但报 `RuntimeError: pg_restore failed; credential-bearing diagnostics withheld`，不得将该 job 写成成功。独立使用真实 PG17 客户端重现发现：`pg_restore --list -` 把 `-` 视为文件名，省略文件名才读 stdin；这是测试容器客户端传输器的调用错误。[原始失败日志](linux-pg-failure.raw.log.gz)及[真实客户端复现](pg-restore-stdin-repro.log)保留。已仅修正该测试传输器，后续运行结果须以对应精确 SHA 为准。

[本机真实 PG17/GPG 回执专项](local-real-pg-receipt.log)在 `56d64848bed5dac0a507348c10313a566012b0be`：99 表、1005 行，真实加密、恢复、签名回执和两份旧归档保留处理通过，源数据库未变，62.969 秒，cleanup complete；该运行的媒体只读栅栏是模拟，不能代替 Linux job。

本机 Windows 对 Linux mount 验收不能作为通过或阻塞的唯一理由；GitHub Linux runner 已证明支持初始 loop 文件系统操作。外部备份故障域、生产证书、目标服务器角色 ACL、真实调度告警投递及上线仍须单独验收，同机临时副本不是异地容灾。不修改业务模块、公共台账和现有 CI workflow。
