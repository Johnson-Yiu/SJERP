# 运维就绪工作包：阶段性结果

基线 `4388947d70d26bca66ca0bfc76b2383a2fc0d404`。**本工作包尚未完成，不具备生产部署或联合备份授权。** 不使用真实服务器、业务数据库或媒体，不改变正式 RBAC、财务、历史承接、打印模块及公共台账。

## 已完成：只读配置检查

命令：`python backend/operations_preflight.py --config <不含凭据的JSON文件>`。示例见 [operations-preflight.example.json](../../deployment/operations-preflight.example.json)，必须先在隔离环境中替换示例路径。检查 HTTPS origin 不含凭据、媒体/静态/备份目录存在且互不嵌套、目录及父路径不是符号链接、备份卷空闲空间；指定 inode 阈值而平台不支持时明确拒绝。命令不连接数据库、不创建目录、不读取媒体内容、不运行备份，任何结果都返回 `backup_authorized=false`。不要在配置中填写密码、令牌或数据库连接；未知字段直接拒绝且不回显。

CPython 3.12.16 / 锁定 Django 6.0.9，隔离内存 SQLite 和独立临时媒体，执行 `python manage.py test crm.tests.test_operations_preflight crm.tests.test_iss047_private_storage crm.tests.test_iss018_backup_recovery --verbosity 1`：32 项，28 通过、4 因平台条件跳过；没有将跳过项计为通过。含 HTTPS/凭据拒绝、路径重叠、容量不足、inode 不可核验时拒绝、现有私有媒体和 SQLite 备份恢复边界。结果不证明目标环境代理、ACL 或生产配置安全。

## 尚未完成的门槛

1. **BLOCKED / 未实施：生产用途 PostgreSQL 与媒体联合备份及恢复入口。** 现有 `isolated_postgres_drill.py` 和 `postgres_drill_backup.py` 只支持新建的隔离集群；不得将其改名或作为生产工具。必须先形成可证明覆盖 Web、worker、定时任务、外部数据库及媒体写入者的独立维护栅栏或同源原子快照机制，在竞争写入及中断下 fail closed，并经独立安全审查；单个 `quiesced` 标志、进程内锁、文件前后散列均不能证明全写入者一致性。
2. **未实施：恢复前身份和空目标验证、恢复后业务及媒体对账和故障回滚的生产入口。** 来源专项已完成一次性 PG17 合成演练，不能将其运行结果表述为本轮生产工具验收。审计保护不得关闭；数据库所有者与应用账户应分离。
3. **未实施：可安全执行的保留、加密副本、调度和告警工具。** 需要验证备份完整性、明确所有权且确认其他独立有效副本后才能删除；同机临时复制不是异地容灾。密钥交由独立保管者，不写入命令行、仓库、归档或日志。
4. **目标环境未验收：** 真实 HTTPS 代理、私有文件直链与缓存、外部对象存储、重启持久性、容量/inode 监控、DB/OS 最小权限、密钥交接及隔离镜像。历史 ISS-017/043/047 应用级证据不代替目标环境实测。
5. **依赖安全结论未完成：** 本轮外部公告检索收到 HTTP 429；不能据此判断当前 Pillow 或其他依赖安全。不得无证据升级或运行 `audit fix`。

此前独立演练运行环境、恢复核对、失败演练及限制见 [ISS-018 COMMAND-03](../r1-iss018-backup-restore-drill-20261103/COMMAND-03.md)。小规模演练耗时不能作为生产 RPO/RTO 承诺。后续应从上述缺口逐项完成实际实现、一次性 PG17/竞争写入及故障演练，再做同一精确 SHA 的三项 CI。当前不能报告该工作包完成。
