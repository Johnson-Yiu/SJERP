# R1-ISS018-BACKUP-RESTORE-DRILL-01

日期：2026-11-03
仓库：`Johnson-Yiu/SUNJACK-ERP`
分支：`codex/r1-iss018-backup-restore-drill-20261103`
统一基线 / 本轮代码核验 SHA：`a55469c1b07e4f13037c6644c69d8a35ef0496a0`

## 结论：BLOCKED，未完成 PostgreSQL 联合备份恢复演练

本轮没有可用且获准的一次性 PostgreSQL 17 环境。没有连接任何数据库，没有创建 PostgreSQL 源库或恢复目标，没有生成联合备份包，也没有启动恢复后的应用。不能把 SQLite 测试当作 PostgreSQL 备份恢复验收；本报告不宣称数据库/私有附件在 PostgreSQL 下恢复成功。

仅完成了当前实现、安全边界及隔离 SQLite 回归的核对。没有修改备份恢复生产代码、模型、迁移、认证/RBAC 或 CI 配置。ISS-018 仍为 `BLOCKED` / `DEPLOYMENT_VERIFICATION_PENDING`。

## 工作区与环境核验

- 从远端 `codex/r1-rule-gap-fix-integration-20261103` fetch 后确认 `FETCH_HEAD` 精确等于指定基线 `a55469c1b07e4f13037c6644c69d8a35ef0496a0`，并在新建独立 worktree 创建本分支；没有改动 `master` 或其他工作树。
- 主机：Windows；Python `3.14.5`；Django `6.0.6`。本轮未能取得 PostgreSQL server version。
- 查找 `psql`、`pg_ctl`、`initdb`、`pg_dump`、`pg_restore`、`pg_isready`、`docker` 均不可用；常见 PostgreSQL 16/17 安装目录不存在；没有 PostgreSQL Windows 服务；本机 TCP `5432`、`5433`、`55432` 无监听进程。
- 没有从配置的工具中发现其他获准的临时 PostgreSQL 环境。为避免误连共享/生产系统，没有尝试连接任意数据库，也未启动付费服务、服务器、容器或 GitHub Actions。

## 现有实现审查

已读取 `AGENTS.md`、项目台账/阶段文档、`REVIEW_PROTOCOL.md`，ISS-018/017/043/052 部署与验收报告，以及备份恢复服务、管理命令和测试。

当前代码明确是 SQLite 专用实现：

- `backend/crm/services/backup_recovery.py::_assert_sqlite()` 在接触数据库路径、媒体目录及输出目录之前拒绝 PostgreSQL；归档成员是 `database.sqlite3`，恢复用 SQLite `PRAGMA integrity_check`。
- `create_consistent_backup` 的文档和命令帮助均限定 SQLite。测试中的 PostgreSQL 边界仅通过临时设置 PostgreSQL engine 验证拒绝路径，不会连接 PostgreSQL。
- 当前归档清单包含备份 schema、时间、数据库 engine/SHA、私有媒体逐文件路径/大小/SHA 和恢复配置 allowlist；恢复配置声明不含密钥。清单没有应用 commit/version 和数据库迁移状态字段，无法据当前实现核验用户要求的版本/迁移兼容性。
- `--quiesced` 是调用方布尔确认；代码没有协调暂停 Web、后台任务、调度器及文件写入者的机制。SQLite 的媒体复制前后清单比较能发现媒体树变化，但不能证明数据库与媒体跨时点一致，也不能证明所有后台写入均已暂停。
- ISS-043 的审计触发器为 PostgreSQL 迁移层保护；ISS-052 的 CSV 导入审计追加保护依赖 PostgreSQL 0091/0093/0094。SQLite 结果不能证明触发器、运行账号权限或审计保护在恢复后的 PostgreSQL 中仍有效。
- ISS-017 报告证明的是应用文件 API 的既有权限规则；本轮没有恢复后的数据库/媒体及运行应用，因此没有实测授权读取、匿名/越权拒绝、缓存策略或旧公开路径。

上述均为静态实现核对，不是本轮 PostgreSQL 运行结果。没有尝试通过放宽安全检查来“完成”测试。

## 本轮实际执行的隔离验证

测试数据库由进程显式配置为 `sqlite:///:memory:`；媒体配置指向本轮新建的临时空目录：
`C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-iss018-restore-drill-599692d23ed84d6e8dad536958894759-media`。

```powershell
$env:DATABASE_URL = 'sqlite:///:memory:'
$env:MEDIA_ROOT = 'C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-iss018-restore-drill-599692d23ed84d6e8dad536958894759-media'
python manage.py test crm.tests.test_iss018_backup_recovery --verbosity 2
```

原始结果：`Ran 22 tests in 3.155s — OK (skipped=3)`。其中 19 项通过；3 项按平台条件跳过（POSIX mode 检查 1 项、Windows 当前无符号链接创建权限 2 项）。PostgreSQL fail-closed 用例通过，但它只是 Django setting override 下的拒绝逻辑测试，不是真实 PostgreSQL 测试。该套件内部在 `TemporaryDirectory` 创建简单 SQLite 表/媒体测试夹具，执行结束后自动清理；夹具不是本轮综合业务演练数据。

同样在该隔离配置下执行：

```powershell
python manage.py check
# System check identified no issues (0 silenced).

python manage.py makemigrations crm --check --dry-run
# No changes detected in app 'crm'
```

`git diff --check` 通过。没有运行 `migrate` 到 PostgreSQL，也没有将任何跳过项计作通过。

现有 SQLite 测试中实际覆盖的失败边界包括：未确认静默时拒绝、媒体复制期间清单变化后不留最终归档、篡改媒体后拒绝恢复、解包/磁盘失败不创建正式目标或残留 staging、已有目标不变、路径穿越拒绝。它们只说明既有 SQLite 代码路径。当前套件没有分别证明“缺少归档媒体成员”“只改 manifest”“损坏数据库成员恢复失败”的完整 PostgreSQL 失败演练；这些也未在本轮人工执行。

## 演练资产与核对矩阵

| 验收项 | 本轮状态 | 证据/原因 |
|---|---|---|
| PostgreSQL 17 源数据库及恢复目标为两个全新隔离库 | BLOCKED | 本机没有 PostgreSQL 17 或获准隔离服务；两个库均未创建。 |
| 独立源媒体和恢复媒体目录 | BLOCKED | 只创建了测试用临时空 `MEDIA_ROOT`；未执行 PG 联合恢复，不能将它称为恢复目标。 |
| 合成客户、供应商、SKU、报价/销售订单/采购及交易快照 | NOT RUN | 没有在 PostgreSQL fixture 中创建业务对象。既有简单 SQLite 单测不包含这些完整业务实体。 |
| 资金、库存、成本归属、附件和历史图片关联 | NOT RUN | 无 PostgreSQL 业务数据集；无行数、金额/数量或外键对账结果。 |
| OperationLog 与 CSV 批次/行级审计、触发器及 append-only 保护 | BLOCKED | 没有 PostgreSQL 迁移或 SQL 运行证据；未更改/关闭审计保护。 |
| 联合备份、版本/迁移清单及包 SHA256 | NOT RUN | 没有生成本轮归档；归档 manifest、包摘要与耗时均 N/A。当前 SQLite manifest 不含代码版本/迁移状态。 |
| 恢复后数据库行数、关键金额/数量、外键、主键序列及历史快照 | NOT RUN | 没有 PostgreSQL 恢复目标。 |
| 恢复后附件文件、媒体 SHA256 与数据库引用逐项匹配 | NOT RUN | 没有 PostgreSQL 备份包或恢复媒体。 |
| 恢复后的 Django 应用及真实 HTTP 文件权限 | BLOCKED | 应用未连接恢复后的 PostgreSQL/媒体；授权、匿名、越权、旧公开路径均未重新实测。 |
| PostgreSQL 失败演练（缺失媒体、manifest 改动、DB 恢复失败、错误目标、联合备份中途失败） | BLOCKED | 没有可运行 PostgreSQL 的环境；SQLite 单测的部分故障注入不替代这些演练。 |

本轮没有本地 PG 备份源、恢复目标、归档 manifest 或逐文件 SHA 清单。因此没有可提供的 PG 数据源/目标标识、记录数量/业务金额对账、备份 SHA、恢复 SHA 或 PG 演练时长。定向测试套件总耗时 `3.155s` 不是备份/恢复时间，不得用于生产 RTO/RPO 推断。旧测试 fixture 仅有 3 张原生 SQL 表各 1 行、2 个媒体文件（合计 44 字节），不包含所需的业务规模，且在测试临时目录中自动清理。

## 外部配置与敏感信息

归档不得包含明文密码、令牌或完整环境变量。下一次获准演练应只记录所需配置名称和取值保管责任，不记录取值：至少由目标部署配置确认数据库连接、应用密钥、stage、媒体根路径和存储后端；若使用独立加密副本，age 私钥须由既有密钥保管方在恢复时提供。当前代码 allowlist 未写入密钥值，但本轮没有生成归档来验证实际包内容。

## 运维执行建议与失败处理

1. 先由环境负责人提供一次性、可销毁的 PostgreSQL 17 服务和专用数据库/账号；通过服务端身份查询记录版本、数据库名和隔离属性，确认不属于共享或生产系统。准备两个不同的专属媒体目录及受控备份目录。
2. 先定义并验证一致性边界：要么在整个操作窗口阻断所有 Web、后台 worker、scheduler、导入和直接文件写入，并用数据库/文件写入探针证明静默；要么由 DBA/存储层提供可核对的共享快照标识。只停止 Web 或传 `--quiesced` 不构成证据。
3. 对 PG17 实施/选择与媒体快照绑定的备份适配器，清单记录应用版本、迁移状态、PG 版本、快照 ID、时间、数据库与每个媒体对象的大小/SHA；恢复目标必须与源库和源媒体目录明确不同。目标身份、兼容性或任何摘要校验失败时停止，不创建 PASS 标记。
4. 恢复到新数据库和新媒体目录，核对迁移与审计触发器、表所有者/运行角色、记录计数、代表金额/数量、外键、序列、快照和每个附件引用。只从受控密钥管理渠道注入恢复配置，不把秘密放入归档、命令行或报告。
5. 用恢复后的应用访问合成私有附件/历史图片，记录授权响应、匿名/无权拒绝、缓存头和旧公开 URL 保护；该结果只覆盖本地应用入口，不扩大为生产代理/CDN/对象存储 ACL 验收。
6. 对媒体缺失、manifest/包篡改、数据库恢复失败、目标身份不符和联合备份中途故障分别故障注入。失败时检查退出码、错误/诊断日志、目标与 staging 状态，并确认没有成功状态或可误用的完整成功标记；不得禁用审计触发器。修复/清理仅针对本轮创建的明确隔离目标。

## 解除阻塞条件及台账建议

需要在另一个获准、可访问且有清晰隔离证明的环境重新执行本任务。至少要有 PostgreSQL 17 服务、销毁策略、专用数据库及最小权限账号、可隔离的源/目标媒体卷和经验证的全写入者暂停或同一快照机制。随后实现/复核 PG 备份恢复适配器、版本/迁移元数据，并完成正向恢复、恢复后 HTTP 权限以及全部失败演练。若保持现有实现不变，它会继续拒绝 PostgreSQL 备份，这是安全 fail-closed 行为。

建议后续统一台账继续保留 ISS-018 `BLOCKED` / `DEPLOYMENT_VERIFICATION_PENDING`，记录本报告及最终提交 SHA；不因 SQLite 回归或此次预检改变 Issue 状态。ISS-043/052 的真实 PostgreSQL 审计保护待验与 ISS-017 的代理/CDN/对象存储 ACL 边界继续分别保留。

本轮未触发 CI、未连接真实业务数据库/媒体、未使用真实服务器或付费服务、未创建 PR、未合并 `master`、未部署、未关闭 Issue。
