# 局域网内测备份与恢复

运行实例沿用 [本地运行交接](LOCAL-RUNTIME.md) 的实例 `a`。交付时由运维将 [备份样例](pilot-backup.example.json) 和 [恢复样例](pilot-restore.example.json) 分别填入仓库外的 `/etc/sjerp/a/backup.json` 和 `/etc/sjerp/a/restore-drill.json`，核对以下项目。

| 项目 | 实例 `a` | 恢复演练 |
| --- | --- | --- |
| PostgreSQL 17 | 核验运行集群标识和 `sjerp_a` 库名 | 独立集群，核验标识与源不同。连接 `postgres` 管理库，工具生成新库 `sunjack_restore_…` |
| 私有媒体 | `/var/lib/sjerp/a/private-media` | 独立父目录 `/var/lib/sjerp-recovery/a/restored-media` |
| 归档 | `/srv/sjerp-backups/a/source-archives` | 只读归档输入、恢复媒体和回执分别存放 |
| 凭据 | 备份角色密码文件、加密密钥独立保管 | 隔离集群凭据及独立签名私钥单独保管。解密使用对应归档密钥 |
| 发布版本 | 备份配置填当时运行的完整 SHA | 恢复配置和维护代码使用归档中的源 SHA |

为运维保留受保护的 Git 检出及锁定依赖。命令会检查 Git HEAD 和 `backend`、`templates` 的工作区状态。在部署包外的干净检出执行以下命令。

## 首次导入前、升级前和日常备份

1. 约定维护窗口，停止仅属于此实例的应用服务及其他媒体写入者。数据库管理员按维护窗口记录现有登录角色的初始状态，暂停该专用集群的其他登录角色并结束源库其他会话，核对无未决两阶段事务。实际媒体卷必须是独立的 ext4、xfs 或 btrfs 只读文件系统且无子挂载。只读 bind mount 无法满足现有检测。
2. 核对源库、媒体卷及输出目录，运行 `python backend/operations_backup.py backup --config /etc/sjerp/a/backup.json`。确认退出 0 和 `VERIFIED`，记录归档路径、加密 SHA256 及原始 SHA256。仅在确认维护安全后恢复原来的角色、媒体挂载状态和服务。升级按 [运行交接](LOCAL-RUNTIME.md) 的顺序继续。
3. 有独立备份位置时，从维护检出执行 `python backend/operations_copy.py --source <归档> --destination <独立目标路径> --sha256 <加密归档SHA256>`。核对 `VERIFIED_COPY` 并记录位置。同一故障域内的副本只计本地副本。

## 恢复与复核

1. 在恢复样例填入经核实的隔离集群标识、归档路径与两个摘要，核对目标库和目录与运行实例分开。在归档对应版本的检出执行 `python backend/operations_backup.py restore-encrypted-verify --config /etc/sjerp/a/restore-drill.json`，核对退出 0、签名回执、新库和媒体路径。发生失败时保存退出信息并核对工具报告的目标状态，避免覆盖运行实例。
2. 启动连接新库和新媒体的私有演练实例。先按 [本地运行交接](LOCAL-RUNTIME.md) 验证运行身份、库和审计权限。对照停写前的数量、销售订单和收付款原币金额、库存数量及附件所属记录，经登录打开业务记录并下载两份不同附件，用 SHA256 核对实际下载字节。保留核对结果和验收时间。若要切换业务端，另行确认切换范围和权限。

| 私有交接待填写 | 值 |
| --- | --- |
| 运维执行人、替补、审批联系人 | 待团队指定 |
| 日常备份频率、维护窗口、保留期 | 待团队确认 |
| 独立备份位置、访问主体及最近复验时间 | 待运维确认 |
| 目标机源/恢复集群、媒体卷、签名回执与下载验收 | 待目标环境核实 |

本批准备阶段保留手动入口和上述待填写项。既有工具及 Linux 恢复依据见 [ISS-018](ISS-018-数据库与附件一致性备份恢复.md)，本轮演练见 [B 包结果](../uat-evidence/pilot-recovery-readiness-01/README.md)。
