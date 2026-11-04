# 运维就绪工作包：阶段性结果

基线 `4388947d70d26bca66ca0bfc76b2383a2fc0d404`。**本工作包尚未完成，不具备生产部署或联合备份授权。** 不使用真实服务器、业务数据库或媒体，不改变正式 RBAC、财务、历史承接、打印模块及公共台账。

## 已完成：只读配置检查

命令：`python backend/operations_preflight.py --config <不含凭据的JSON文件>`。示例见 [operations-preflight.example.json](../../deployment/operations-preflight.example.json)，必须先在隔离环境中替换示例路径。检查 HTTPS origin 不含凭据、媒体/静态/备份目录存在且互不嵌套、目录及父路径不是符号链接、备份卷空闲空间；指定 inode 阈值而平台不支持时明确拒绝。命令不连接数据库、不创建目录、不读取媒体内容、不运行备份，任何结果都返回 `backup_authorized=false`。不要在配置中填写密码、令牌或数据库连接；未知字段直接拒绝且不回显。

CPython 3.12.16 / 锁定 Django 6.0.9，隔离内存 SQLite 和独立临时媒体，执行 `python manage.py test crm.tests.test_operations_preflight crm.tests.test_iss047_private_storage crm.tests.test_iss018_backup_recovery --verbosity 1`：32 项，28 通过、4 因平台条件跳过；没有将跳过项计为通过。含 HTTPS/凭据拒绝、路径重叠、容量不足、inode 不可核验时拒绝、现有私有媒体和 SQLite 备份恢复边界。结果不证明目标环境代理、ACL 或生产配置安全。

使用来源证据中的 PostgreSQL 17.11 程序二进制，既有 `crm.tests.test_iss018_drill_command` 在本次新建、任务所有的临时集群中重新执行：**8 项通过，806 秒**；成功案例核对 84 张表、923 行、121 项迁移及 2 个媒体文件（66 字节），恢复完成且源媒体不变。六项故障分别返回非零并报告清理完成；production stage 在创建集群前拒绝。原始输出为 [pg17-command-run.log](pg17-command-run.log)。该运行只验证现有隔离演练工具，不验证任意外部媒体写入者或生产运维入口；测试总时长不能作为生产 RTO。

锁定 Python 环境 16 个精确版本逐项匹配，`pip check`、Django check、迁移一致性检查通过；`npm ci` 和前端生产构建通过，保留既有大 chunk 警告。[npm 全依赖审计](npm-audit-all.json)报告 5 项中危开发依赖，[生产依赖审计](npm-audit-production.json)报告 0 项；未运行自动修复。GitHub 公告 API 对 Pillow 13.0.0 的限定查询没有返回记录，但 Python 全量审计工具安装受 TLS 连接错误影响，不能视为完整漏洞审计或证明无漏洞。

首次 [CI #41795791866](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41795791866) 的两个后端失败；Backend 原始日志明确为新增 inode 不可用测试错误地把全局 `os.statvfs` 设空，Linux 的 `shutil.disk_usage` 因此抛出 `TypeError`。测试已隔离磁盘容量 mock，保留原 fail-closed 断言；需以修正后的精确 SHA 重新运行 CI，不能把首次失败写成通过。PostgreSQL job 原始日志下载曾因 GitHub 存储连接失败，具体失败仍需复核。

## 尚未完成的门槛

### 持续实施补充

提交 `5d13f33c018b88f60878587770dc6dbf79fc0af9` 的 [CI #41797932846](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41797932846) 已核实 Backend、backend-postgres、Frontend 三项 SUCCESS；此结论不覆盖其后的新增代码。

新增 `operations_copy.py` 实际命令行入口与完整摘要核对、排他创建、仅清理本次目标及清理错误保留；新增 Nginx 私有媒体拒绝和 API 禁缓存模板。执行命令见 [RUNBOOK](RUNBOOK.md)。CPython 3.12.16 运行 `python -m unittest discover -s backend/crm/tests -p 'test_operations_*.py' -v`：15 项通过，原始日志 [operations-unit.log](operations-unit.log)。包括复制命令真实成功/重复目标拒绝、错误摘要、fsync/校验失败、清理失败保留原异常，以及本机可写目录无法满足只读栅栏的实际拒绝。停机状态与 PID 拒绝使用模拟工具输出，不能冒充真实 Linux 卷/竞争写入验收。

新增的离线源检查要求 Linux 文件系统与挂载都为只读，并检查 PG17 干净停机、系统标识及外部存储链接；尚未接入联合归档/恢复。当前 Windows 无可用 Linux 发行版，`wsl --list --quiet` 返回帮助和非零；未自动安装系统组件。Docker、Podman、Nginx、OpenSSL 命令均未发现。真实 Linux 只读卷、代理及加密演练仍待环境满足后执行，其余实施继续推进。

1. **BLOCKED / 未实施：生产用途 PostgreSQL 与媒体联合备份及恢复入口。** 现有 `isolated_postgres_drill.py` 和 `postgres_drill_backup.py` 只支持新建的隔离集群；不得将其改名或作为生产工具。必须先形成可证明覆盖 Web、worker、定时任务、外部数据库及媒体写入者的独立维护栅栏或同源原子快照机制，在竞争写入及中断下 fail closed，并经独立安全审查；单个 `quiesced` 标志、进程内锁、文件前后散列均不能证明全写入者一致性。
2. **未实施：恢复前身份和空目标验证、恢复后业务及媒体对账和故障回滚的生产入口。** 来源专项已完成一次性 PG17 合成演练，不能将其运行结果表述为本轮生产工具验收。审计保护不得关闭；数据库所有者与应用账户应分离。
3. **未实施：可安全执行的保留、加密副本、调度和告警工具。** 需要验证备份完整性、明确所有权且确认其他独立有效副本后才能删除；同机临时复制不是异地容灾。密钥交由独立保管者，不写入命令行、仓库、归档或日志。
4. **目标环境未验收：** 真实 HTTPS 代理、私有文件直链与缓存、外部对象存储、重启持久性、容量/inode 监控、DB/OS 最小权限、密钥交接及隔离镜像。历史 ISS-017/043/047 应用级证据不代替目标环境实测。
5. **依赖安全结论未完成：** 本轮外部公告检索收到 HTTP 429；不能据此判断当前 Pillow 或其他依赖安全。不得无证据升级或运行 `audit fix`。

此前独立演练运行环境、恢复核对、失败演练及限制见 [ISS-018 COMMAND-03](../r1-iss018-backup-restore-drill-20261103/COMMAND-03.md)。小规模演练耗时不能作为生产 RPO/RTO 承诺。后续应从上述缺口逐项完成实际实现、一次性 PG17/竞争写入及故障演练，再做同一精确 SHA 的三项 CI。当前不能报告该工作包完成。
