# 集成来源只读审查：447d

审查对象：冻结检出 HEAD 447d7816ead2e971e249cb2e762b1a6f7009b9c0。
审查性质：Codex 开发侧预审，不是 ChatGPT 独立接受或上线批准。
结论：指定的财务自动合并、权限动作映射、历史来源隔离/幂等及 0104–0108 迁移/测试清理边界中，未发现确定的集成缺陷。完整 447d 综合套件及 PostgreSQL 套件未在本轮重跑；来源结果不等于 447d 本次测试。

## 来源与冻结状态

- 财务完整稳定交付来源为 e301a86044ffe56b72172a94dc3b00ae09401b05，已由合并提交 087fe34d54e1f34b5e55a59795bf5cfcad9a0d89 完整合入。3a07e7ef1a9e63c98077d45492ba23b798c7fcdd 是该稳定来源的较早祖先提交，不是最终交付 SHA。90683506f5d9447974302d83c89ba27351d5dfd4 也是 e301 的祖先。
- Linux 运维稳定来源 4a4f338b09e9a464f1e66c24a905c35c970729bf 已合入，合并提交 536789f6dbafb2874b1abfd33ade2b30faa123a4。
- 历史承接稳定来源 ba4274742727a6794608dc8581a49b3692d865a6 已合入，作为 447d 第二父提交。
- 权限修复 9af2a32fa81df3aa975424b70a887057e40b6b22 和历史实现 438bc5b8526bb43b48445b4646e82ead0b2caaa6 都是 447d 祖先。447d 父提交为 ea140fd18ac9a4b5c0a64eed4c8f4b400674578e、ba4274742727a6794608dc8581a49b3692d865a6。

读取时 HEAD 与指定 SHA 相符。冻结工作树中存在无关文档脚本修改：run-postgres-regression.py、seed_history_backup.py 两项修改及 seed_history_operational_backup.py 未跟踪文件；后续状态还出现未跟踪 final-447d-frontend 目录。均未编辑，未观察到冻结产品代码被修改。该目录的并发生成归属 UNKNOWN，保留原样。

## 关键审查结果

### finance_closeout.py 自动合并

路径：backend/crm/services/finance_closeout.py。

- effective_nature() 读取追加式分类最新记录并回退到原始 nature；match_transfer()、match_historical_transfer() 以此判断 internal_principal。账户锁后重新读取并复验分类及更正状态，避免锁等待期间变更被旧快照绕过。
- balance() 对有转账匹配的账户将匹配编号纳入指纹；无匹配账户沿用原指纹输入。
- post() 在行锁后要求 HISTORY_TAKEOVER_V1 指令为 approved，再校验请求指纹、verified 真值、凭证及适用的双人复核。已 posted 重试返回原 FinanceFact，不新建事实。
- 9068350 的分类、指纹、锁内复验逻辑及历史来源 approved 门槛均保留；未发现自动合并覆盖。

### 权限动作映射

审阅 backend/crm/finance_closeout_api.py、backend/crm/permissions.py、backend/crm/tests/test_finance_integration_permissions.py。

- 导出查询/路径优先判为 export。普通 POST 动作只读取可信 ViewSet 声明的 action map，且动作须属于 ACTION_FIELDS；请求正文不能指定权限动作。
- preview 映射为 view；accounts、vouchers、instructions 映射为 create；未映射写操作沿用 update。
- CSV facts 仅在 reports.export 有权且 finance.export 缺失时选择 reports 模块；业务读取仍经 ledger.access()，保留 finance.view、transactions.view 和既有全局数据范围。
- 定向测试覆盖只读、创建/记账分权、finance/reports 导出，以及 finance/transactions、受限范围、停用员工拒绝。未发现改变导出优先级或开发超级管理员语义。

### 历史真实性、来源编号与幂等

审阅 backend/crm/history_takeover.py、backend/crm/history_takeover_models.py、backend/crm/history_operational_finance.py。

- execute_group() 在事务内锁关联组，只允许 approved 组执行；执行前复验组与每行真实性、完整覆盖、预检结果及批准指纹。指纹变化会转为 needs_reapproval。
- 历史承接本身只生成历史单据、来源登记和 handoff，不直接记正式 FinanceFact、库存或履约流水；execution_result 将这些 posted 数量设为 0。
- 来源记录对 source_system + record_type + source_record_id 有数据库唯一约束；执行前查重，业务记录与来源登记同事务提交，数据库约束兜底并发冲突。execution_key 唯一且绑定来源系统、组编号及源文件 SHA。
- 财务承接走显式来源服务。测试覆盖待确认/来源变更/金额不匹配拒绝、不同人员审批、同源重复提交与重复 post 只产生一条指令/事实和一条事件。未发现模拟或待核实资料进入正式记账的代码路径。

### 迁移 0104–0108、不可变性与 test_cleanup

MigrationLoader 检查无冲突；CRM 链为 0103 → 0104 → 0105 → 0106 → 0107 → 0108，唯一叶节点为 0108。五个迁移文件在 ba427474 与 447d 的 Git blob ID 逐一相同。来源旧数据升级证据可复用于这些迁移文件，但不是 447d 的 PostgreSQL 重跑。

- 0104/0105 对历史盘点、冲销、接续合同安装 UPDATE/DELETE 保护，并在有历史数据时拒绝危险回退；0106/0107 保护历史采购口径和库存位置。
- 0108 对历史盘点、盘点冲销、接续合同增加 PostgreSQL TRUNCATE 保护，并在有记录时拒绝移除保护。
- backend/crm/postgres_test_cleanup.py 仅接管新建随机 PostgreSQL 测试库的 TransactionTestCase fixture teardown。先校验连接身份、迁移状态和指定触发器，取得 ACCESS EXCLUSIVE 锁后在单一 atomic 内暂时停用明确 guard，执行原生 flush，重新启用并核验后提交；失败时依事务回滚恢复数据与 DDL，不在 finally 中执行宽泛恢复 SQL。
- backend/crm/test_runner.py 拒绝 keepdb、并行、自定义测试库名、远程主机、非空 OPTIONS 和 PG* 环境变量；只销毁 CREATE 已成功登记的随机测试库，并二次校验目标身份。hook 限定在 teardown 且由 ExitStack 恢复。
- 测试覆盖错误 guard、迁移状态不一致、hook 范围、清理失败回滚与重试、其他连接锁阻挡和数据库销毁限制。来源 PostgreSQL 90 项专测通过。数据库超级用户/对象所有者仍能改动或禁用触发器；生产运行角色与迁移角色分离需部署验收。

## PostgreSQL 来源证据

证据来自 ba427474 的 tracked 文件；对应目录为 docs/uat-evidence/history-operational-closeout-20261104/，相关日志 blob 与 447d 完全相同。说明见 docs/uat-evidence/history-operational-closeout-20261104/README.md。

- 首轮全量 logs/postgres17-full.log：1341 项、31 跳过、11 错误。来源 README 将错误归因于 Windows 默认 GBK 解码 UTF-8 子进程输出；该轮失败，没有记作通过。
- UTF-8 重跑 logs/postgres17-full-utf8.log：1342 项，OK (skipped=31)，即 1311 通过、31 环境跳过、0 错误、0 失败。
- 专项 logs/postgres17-guard-focused-final.log：90 项通过、0 跳过、0 失败，覆盖历史承接、旧资料及测试库清理/设置相关回归。
- logs/postgres17-upgrade.log 验证升级至 0107；logs/postgres17-legacy-upgrade.log 验证 0104 前已有合成客户、SKU、订单、仓库及数量保留。
- logs/postgres17-0108-upgrade.log 与 logs/postgres17-0108-guard-final.log 验证带历史记录升级、TRUNCATE 拒绝、带数据回退拒绝及记录保留。
- logs/postgres17-migration-guards.log 验证 0104、0105、0106 有数据回退被拒且恢复最新迁移。
- logs/postgres17-truncate-first.log 留存首次延迟外键拦截失败；最终 90 项日志显示经 SET CONSTRAINTS ALL IMMEDIATE 后专测通过。失败证据未删除或冒充通过。

本报告没有把以上 ba427474 来源结果说成 447d 本轮运行。

## 本轮检查和边界

冻结代码使用 Python 3.12.16；工作目录为 backend，DATABASE_URL=sqlite:///:memory:，UTF-8：

- python manage.py check：退出码 0，无问题。
- python manage.py makemigrations --check --dry-run：退出码 0，No changes detected。
- MigrationLoader 图检查：退出码 0、无冲突、0104–0108 连续、CRM 唯一叶节点为 0108。

原始输出见 closing-logs/django-system-check-447d.log、closing-logs/makemigrations-check-447d.log、closing-logs/migration-graph-447d.log。本次只读来源审查未运行全量测试、未连接 PostgreSQL、未触发 CI。主审随后提供的实际集成验收结果如下；这不是本报告审查者亲自启动的运行：[`README.md` 集成验收索引](README.md#实际本地结果各自源码不混计)记录 447d SQLite 全量 1410 项中 1330 通过、80 跳过、0 失败；PostgreSQL 17.11 全量 1410 项中 1378 通过、32 跳过、0 失败，102 表、1218 行、133 迁移及 5 个私有媒体文件恢复核对一致，cleanup complete。PG 原始日志为 [`postgres-final-447d-opseed-receipt-relation.log`](postgres-final-447d-opseed-receipt-relation.log)，其中包含 `Ran 1410 tests`、`OK (skipped=32)`、历史/财务/历史运营恢复 PASS 和清理完成记录。

剩余条件：447d 的全量 PostgreSQL 与 SQLite 结果已由主审记录；完整浏览器与历史业务闭环仍按本报告审查时点待集成回归（后续由独立的 `FINAL-HISTORY-CHROME-447D.md` 记录）。可复用的来源 PG 证据仅覆盖 blob 相同的 0104–0108 迁移及已记录场景；主审提供的 447d 全量 PG 日志和恢复记录另作为集成版证据。数据库高权限账号可绕过触发器的边界仍在。

确定缺陷：上述审查范围内未发现。本报告不代表 ChatGPT 独立接受、Issue 关闭或上线就绪。
