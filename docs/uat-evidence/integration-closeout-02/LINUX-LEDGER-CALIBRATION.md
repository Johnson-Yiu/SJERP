# Linux 运维稳定来源：Issue 台账证据校准

日期：2026-11-05
性质：开发侧只读校准；不是 ChatGPT 独立复审，也不变更 Issue 状态。

## 范围与来源

- Linux 稳定来源：`codex/linux-operations-acceptance-20261104`，完整 SHA `4a4f338b09e9a464f1e66c24a905c35c970729bf`。
- 集成验收回执：`stable-source-ci-receipt.json`。来源 CI `41866028447` 的 Backend、Frontend、Backend-Postgres 三项成功；Linux 专项 `41866028480` 的 `nginx-private-media`、`media-fence`、`postgres-role-receipts` 三项成功。这些是来源证据，不代表集成版重新运行，也不覆盖生产环境验收。
- 本文仅据稳定来源报告、上述回执、集成树中的只读来源审查和现有台账校准归属及缺项；本轮未运行测试，未扫描扩展其他源码范围。

## 逐项校准

| Issue | 台账状态（保留） | Linux 来源实际覆盖 | 仍缺的关闭证据 |
|---|---|---|---|
| ISS-018 | BLOCKED | 主要归属。真实临时 PostgreSQL、受限角色、实际数据库恢复和签名恢复回执；拒绝伪造、错误及过期回执；验证归档保留/清理；ext4 媒体围栏和清理。来源实际恢复 99 张表、975 行；同一 runner 临时副本不等于异地灾备。 | 在目标环境验证实际 PostgreSQL 角色、持久媒体卷、加密异地副本、数据库与媒体共同恢复点、POSIX/NTFS 权限、调度器及外部告警、RPO/RTO 和真实业务数据恢复。每项须有目标配置、运行日志及恢复结果。**0600 回执跨账号交接：**协调主审已启动最小修复并归入 ISS-018 子项，尚未提交或完成真实跨 UID 验收；该稳定来源 4a4 的代码/测试仍未证明不同 UID 可读取正式生成的回执，精确补修 SHA、测试路径及补修后跨 UID 结果均为 **UNKNOWN**。需补交补修提交和真实不同 UID 的成功/拒绝路径日志后才能校准此子项；不得用 4a4 CI 代替。 |
| ISS-043 | BLOCKED | 仅覆盖运维角色权限的一个子面：Linux PostgreSQL 专项验证 `crm_operationlog` 运行角色可 SELECT/INSERT、不可 UPDATE/DELETE/TRUNCATE。 | 全部目标运行角色及实际表级授权清单、真实部署权限验证和拒绝证据；此单表结果不能证明 ERP 全库最小权限。 |
| ISS-017 | BLOCKED | 与私有附件运维边界有交叉证据：合成 Nginx 环境验证附件/财务凭证的授权、匿名、越权和直链访问结果，并检查私有响应 `no-store`。 | 目标环境反向代理/CDN、私有存储 ACL、真实身份及实际部署路径验收；当前合成 TLS/服务不能证明生产配置。 |
| ISS-047 | BLOCKED | 与媒体及运维有交叉证据：合成私有媒体访问、ext4 围栏及恢复测试。 | 生产持久媒体卷、磁盘/ inode 容量告警、数据库与媒体联合恢复、独立故障域及目标环境恢复演练。来源报告明确同 runner 临时副本不是异地灾备。 |
| ISS-051 | BLOCKED | 无真实员工认证结论。Linux 合成服务/角色身份不代表 ERP 员工身份或正式认证接入。 | 按权限设计完成业务认证、真实员工身份及目标部署配置的验收；Linux 运维回归不构成该项证据。 |
| ISS-025 | FIXED_PENDING_REVIEW | 不属于本 Linux 运维来源；该 Issue 是客户状态文案/业务范围。 | 依其自身复审记录补齐独立复审凭证；本来源不增加关闭证据。 |
| ISS-036 | FIXED_PENDING_REVIEW | 不属于本 Linux 运维来源；该 Issue 是采购包装业务范围。 | 依其自身复审记录补齐独立复审凭证；本来源不增加关闭证据。 |

以上仅列已核实的运维交叉项；不根据旧分支名称将 ISS-025、ISS-036 或其他业务 Issue 强行归入运维工作。

## 可复用的来源证据与限制

- Linux 验收报告：`docs/uat-evidence/linux-operations-acceptance-20261104/README.md`
- 稳定来源 CI 回执：`docs/uat-evidence/integration-closeout-02/stable-source-ci-receipt.json`
- 只读来源审查及 0600 交接缺口记录：`docs/uat-evidence/integration-closeout-02/REVIEW-LINUX-STABLE-SOURCE.md`
- PostgreSQL 运维专项入口：`backend/crm/tests/linux_operations_pg_acceptance.py`
- Nginx/私有媒体专项入口：`backend/crm/tests/linux_nginx_acceptance.py`

来源专项还验证了 systemd 定时器及 `OnFailure` 将合成告警送达 job-local UDP 接收端；这不证明外部值班告警链路。早期 PostgreSQL 运行曾因 `pg_restore --list -` 的 stdin 用法失败，来源随后修复传输并由上述精确来源 CI/专项成功；不得把早期失败算作当前通过，也不得把来源通过外推为集成版或生产环境通过。

本次只新增本报告；未修改公共台账、产品代码、测试、Git 分支或提交，也未关闭 Issue。台账状态均按现有记录保留。
