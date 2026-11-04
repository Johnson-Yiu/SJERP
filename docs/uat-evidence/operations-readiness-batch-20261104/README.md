# OPERATIONS-READINESS-BATCH-01 运维工具验收

固定基线：`4388947d70d26bca66ca0bfc76b2383a2fc0d404`。独立分支：`codex/operations-readiness-batch-20261104`。实现源码检查点：`a3a6f634b377876d0bf686a2ebe8a02b1cfbf896`；最终证据提交及其精确 CI 结果以交付消息为准。

本轮交付可执行运维入口及隔离验证，等待独立复审。**不授权生产使用；真实 Linux 全写入者静默、目标代理、外部副本和实际运行账号验收仍 BLOCKED/待验收。** 不把受控 PostgreSQL 演练或模拟媒体栅栏当作全写入者一致性证明。

## 实现清单

|要求|实现及结果|边界|
|---|---|---|
|联合备份|`operations_backup.py`、`operations_postgres.py`：实例系统标识/库名/PG17/工具主版本/干净源码 SHA/迁移检查；导出快照与逐表 SHARE 锁；私有媒体清单、摘要及附件引用；可选 AES256 加密后实际解密复核|真实 PG17 备份恢复已验证；媒体只读卷的真实 Linux 专项未完成|
|全写入者|拒绝其他可登录 DB 角色、其他活动会话和 prepared transaction；媒体要求专用本地 ext4/xfs/btrfs 文件系统与挂载都只读且无子挂载；不接受 quiesced 参数，不仅信任文件前后散列|实际独立连接锁竞争及登录/会话拒绝通过；真实 Linux 媒体竞争 BLOCKED，Windows 默认拒绝成功|
|恢复回滚|仅创建随机新库/新媒体，不覆盖既有目标；先查身份/摘要/路径/链接/容量/版本，再恢复；全部行摘要、序列、关联、附件及快照一致；触发器实际拒绝；失败清理仅针对本次资源|真实 pg_restore 失败、错误摘要、审计拒绝和源库不变已验证；ACL/应用角色必须由目标 DBA 另行重建验证|
|副本/保留|`operations_copy.py`、`operations_retention.py`：有界复制、摘要双核对、排他创建；恢复凭据+独立路径副本摘要；默认 dry-run，至少留一份，未知文件不删；失败清理保留错误|实际文件故障与真实加密 PG 归档保留专项通过；同机副本明确不是异地容灾|
|加密/密钥|`operations_crypto.py`、`operations_archive.py`：GnuPG AES256，密钥标准输入、独立临时 home/agent，失败输出不接受；运行密钥与归档分离|1,114,112 字节真实加解密、错误密钥、截断密文均通过；OS 密钥托管/轮换/交接仍目标验收|
|调度/监控|systemd service/timer/OnFailure syslog 模板；明确退出状态、唯一归档名、无成功标志的失败路径|未安装、未启用，真实告警投递及漏调度监控待目标验收|
|配置/私有附件|HTTPS/目录隔离/容量/inode只读检查；Nginx拒绝媒体直链、API禁缓存模板；私有存储现有回归保留|目标 HTTPS/Nginx、持久卷重启、缓存、ACL和容量告警未实测|
|运行权限|维护连接与应用连接分离；其他登录角色未静默即拒绝；不关闭任何审计触发器|应用超级管理员不等于 DB/OS 管理员；应用非 owner/非 superuser 及最小权限仍须目标实际账号验证|
|可复现部署|CPython 3.12.16、Django 6.0.9，16项 Python 精确锁全部匹配；npm ci/生产构建通过|Python锁无发行包哈希；无本机容器运行时，未冒充镜像启动通过|

命令、配置字段、维护前置条件、恢复权限和密钥交接见 [RUNBOOK](RUNBOOK.md)。没有更改业务模块、数据库迁移、工作流或共享台账，没有触碰 master、真实服务器/数据库/媒体或正式 RBAC。

## 已执行验证与原始日志

- [锁定环境实测](runtime-versions.log)：CPython 3.12.16；16项精确锁全部匹配。
- [pip check](pip-check.log)、[Django check](django-check.log)、[迁移一致性](migrations-check.log)：通过。
- [定向 Django 回归](django-targeted.log)：55项，51通过、4跳过。4项是既有 Windows 不支持的 POSIX权限或符号链接检查；原因逐项在日志中，没有算作通过。
- [运维单元测试](operations-unit.log)：覆盖有界副本、错误摘要、清理失败、归属与保留、错误密钥/工具路径及数据库预执行拒绝；29项通过，最终数量见原始输出。
- [真实 PG17 新入口专项](maintenance-pg17-final.log)：84表、923行、全部数据/序列与附件引用一致；真实锁竞争、活动连接、其他登录角色拒绝；8次审计 UPDATE/DELETE拒绝、CSV审计TRUNCATE拒绝；损坏转储触发真实恢复失败且新建库已清理；源库不变；45.672秒。**媒体只读栅栏明确模拟。**
- [真实 PG17 加密/副本/保留联合专项](maintenance-pg17-encrypted-final.log)：对实际数据库归档加密、解密到相同摘要、校验本机独立路径副本、保留最新一份并删除两份旧归档；最终状态/耗时见日志；不宣称异地或真实 Linux 媒体栅栏通过。
- [真实 GnuPG 故障专项](crypto-real.log)：1,114,112字节，2.765秒；正常往返、错误密钥/截断密文拒绝，源文件不变，独立agent与临时目录清理完成。实际 GnuPG 2.4.9，OpenSSL 3.5.6；没有更改系统安装。
- [npm锁定安装](npm-ci.log)、[生产构建](frontend-build.log)：通过；主JS约1,136.16 kB，gzip396.79 kB，保留既有超过500kB警告，不据此声称体验改善。
- [Python审计工具独立安装](pip-audit-tool-install.log)、[pip-audit](pip-audit-final.log)：公开PyPI直连恢复后完成，16项锁定依赖（含Pillow13.0.0）无已知漏洞返回；只代表本次公开库覆盖，不等于绝对安全。工具单独安装在任务临时目录，未改项目依赖。
- [npm全依赖审计](npm-audit-all.json)：5项中危开发依赖；[生产依赖](npm-audit-production.json)：0项。未运行audit fix或无关升级。
- [既有隔离PG17演练](pg17-command-run.log)：8项通过，806秒；仅作为来源演练回归，未改名成生产工具。
- [真实清理失败留档](maintenance-pg17-cleanup-failure.log)：早期测试在业务核对通过后，Windows占用任务复制的postgres.exe导致清理失败，进程非零退出；后续已修正为清理完成后才输出成功，并经路径/PID/进程核对清理了该任务遗留目录。失败记录不计为通过。

先前 `5d13f33c018b88f60878587770dc6dbf79fc0af9` 的 [三项CI](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41797932846) 均成功，只代表该历史提交。首次 CI 的 inode 测试跨平台 mock 错误已修正，没有降低实际 fail-closed 断言。最终提交必须重新核实 Backend、backend-postgres、Frontend；不能沿用历史绿色状态。

## 剩余目标环境门槛及下一步

1. **BLOCKED：真实 Linux 媒体全写入者证明。** 本机 Windows 无可用 Linux 发行版（[实际环境拒绝日志](environment-boundaries.log)），wsl列举命令非零/帮助输出；无Docker/Podman。需在获准一次性 Linux 环境建立专用文件系统，停全部服务/任务、限制全部非维护DB登录，实施真正只读文件系统后，用独立OS进程与DB连接竞争验证拒绝。工具当前在不能提供证据时拒绝备份。
2. **待验收：HTTPS代理/持久卷/缓存/容量/inode/真实角色。** 提供模板并保留应用级私有附件回归；下一步在目标隔离环境运行nginx -t和未登录/越权/直链请求、重启及真实运行账号DML拒绝。当前未发现Nginx，未安装真实代理。
3. **待验收：独立故障域、密钥托管及告警。** 本次仅本机临时副本。下一步由获准外部存储/监控环境验证加密副本下载恢复、密钥分离、告警投递、漏调度及唯一有效副本保护；不调用付费资源，不把本地复制算异地容灾。
4. **待验收：部署镜像。** 仓库及本机未提供可运行容器环境，已做锁定依赖和构建；下一步在目标环境固定镜像摘要，复验实际安装、启动与健康检查，不猜测镜像已通过。
5. **保留风险：** Python锁只有精确版本无发行包哈希；npm中危开发依赖仍存在；外部网页公告检索返回HTTP429，但pip-audit公开漏洞库已成功，不再把Python完整审计误写为无法执行。GnuPG/OS工具安全维护归目标部署包管理流程。

所有耗时均是一次性小规模合成演练，不提供生产 RPO/RTO 承诺。ISS-002/017/018/043/047/052及部署议题整体均未关闭，等待集中独立复审。
