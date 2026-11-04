# HISTORY-TAKEOVER-BATCH-01 验收报告

## 范围与结果

- 基线：`4388947d70d26bca66ca0bfc76b2383a2fc0d404`
- 分支：`codex/history-takeover-batch-20261104`
- 本次仅使用隔离 SQLite 与合成资料；未导入、修改或读取正式业务数据库。
- 已阅读项目 `AGENTS.md`、两份项目台账、`REVIEW_PROTOCOL.md`、ISS-121 及 ADD、ISS-037/038/062 已确认规则、历史预检与 FIX-01 证据，并检查当前实现。复用了原历史预检解析和模板能力，没有重复实现预检。
- 新增迁移：`crm.0098_history_takeover_workflow`，依赖现有 `0097`；未改写已发布迁移。
- 本包未修改公共台账、资金核心、报价打印或采购成本核心；未关闭 ISS-121、未合并 master、未部署。

## 子任务状态

| 子任务 | 状态 | 本轮处理与边界 |
|---|---|---|
| 申请与审核 | 合成验收通过 | 申请、真实性/覆盖标记、拒绝、待核实、审核依据和执行状态均独立记录。预检不自动批准。普通申请人只能查看本人申请，管理员审核视图可查看全部；开发身份明确标为“开发身份（非实名）”，不伪造审核人。 |
| 主档与依赖 | 合成验收通过 | 只允许人工明确关联到已有客户、供应商和 SKU；名称相似候选不能自动关联；缺失依赖、单据冲突和缺证据均阻止执行；不创建重复主档。 |
| 受控执行 | 合成验收通过 | 以关联组事务执行，执行前重新校验源记录和主档指纹；测试重复提交幂等、整组回滚、数据库追加式审计及源记录唯一性。 |
| 未结订单与履约 | 历史归档通过；正式履约接通待后续 | 生成只读历史销售/采购单快照，并计算剩余量；取消、结清、部分履约和取消履约事件分别验收。执行不会生成收发货、库存分配或付款。历史单据 API 禁止直接改写。 |
| 库存启用基准 | 明确未接通 | 模板和交接契约保留仓库归属、批次及盘点基准；本实现不创建库存流水、不改当前库存。现有库存模型/服务缺少可安全承接所有权与批次基准的稳定接口，不能据此假装完成正式库存启用。 |
| 历史资金暂存与交接 | 明确未接通 | 仅保留来源、凭证和审批交接契约，状态为 `not_connected`；不创建正式流水、付款计划或人民币资金事件，也不直接写资金表。待资金包提供稳定接口后由集成任务接通。 |
| 撤销、迟到记录与追溯 | 合成验收通过 | 执行前支持撤回；执行后采用追加式更正事件。迟到事实保留实际日期并标记期间重分类需复核；凭证核实不覆盖原快照；重复更正审核被拒绝。 |
| 操作界面与模板 | Chrome 合成验收通过 | 提供申请、审核、主档关联、执行、结果/错误定位、模板下载和 CSV 报告；报告对公式注入做转义。真实下载的 XLSX 已保存。 |

## 合成数据对账

一次性 SQLite 浏览器验收库执行了一组关联申请。对账明细见 [合成数据库核对日志](logs/synthetic-browser-db-reconciliation.log)：

- 1 个申请、1 个已执行关联组、12 条来源记录、3 条该组审计事件。
- 生成 1 张历史销售单和 1 张历史采购单，各有 1 条明细；主体和 SKU 历史快照保留，状态为 historical-only。
- 销售及采购历史单金额、已付/未付余额为零，不会把来源资金重复计入余额。
- 正式资金流水、付款计划、库存流水、预留、发货、收货及采购成本分配均为 0；三个 handoff 均为 `not_connected`。
- 订单生命周期用合成已核实履约事实计算剩余量；取消履约不计入有效履约。执行不会再次生成收发货或库存变化。

这证明本阶段归档流程不会二次记账或二次计库存；它不代表资金、库存基准或正式履约接入已完成。

## 自动化与迁移验证

| 检查 | 结果 | 原始记录 |
|---|---|---|
| Django CRM 完整测试 | 1183 tests，OK（52 skipped）；系统检查通过 | [backend-django-crm.log](logs/backend-django-crm.log) |
| 本包与预检定向测试 | 37 tests，36 passed、1 skipped；SQLite 下 PostgreSQL 并发用例按设计跳过 | [backend-history-takeover-targeted.log](logs/backend-history-takeover-targeted.log) |
| 迁移回滚隔离回归 | 16 tests，15 passed、1 PostgreSQL-only skipped；涵盖拒绝回滚后恢复最新迁移以及后续历史承接流程 | [migration-rollback-restore-regression.log](logs/migration-rollback-restore-regression.log) |
| SQLite 全新数据库迁移 | 全量迁移至 0098 成功 | [sqlite-fresh-migrations.log](logs/sqlite-fresh-migrations.log) |
| SQLite 0097 升级 | 从 CRM 0097 升至 0098 成功 | [sqlite-upgrade-0097-to-0098.log](logs/sqlite-upgrade-0097-to-0098.log) |
| Django 检查 | `makemigrations --check --dry-run --noinput` 与 `manage.py check` 通过 | [django-checks.log](logs/django-checks.log) |
| 前端 Node 单测 | 177 passed，0 failed | [frontend-node-unit.log](logs/frontend-node-unit.log) |
| 有效 Vitest | 70 files / 684 tests passed | [frontend-vitest-valid-suite-final.log](logs/frontend-vitest-valid-suite-final.log) |
| 前端生产构建 | 成功；Vite 报告主 JS chunk 超过 500 kB 的体积警告 | [frontend-build.log](logs/frontend-build.log) |

完整 CRM 测试有 52 项跳过；专项并发用例使用 `TransactionTestCase`，显式要求 PostgreSQL 行锁。当前机器没有可用 PostgreSQL 17 服务，因此本地并发验收不能用 SQLite 替代。GitHub PostgreSQL 17 job 先后发现并修复三项测试夹具问题：缺少创建申请 helper、ISS-052 413 用例留下的临时上传目录设置污染，以及 CSV 审计迁移拒绝回滚时未恢复之前已逐项撤销的 0095–0098 迁移。第三项会导致后续 PG 并发夹具访问的 `crm_historytakeoverapplication` 表缺失；回滚测试现无论成功或预期拒绝都会在 `finally` 中恢复迁移图，并断言承接表恢复。最新 PG17 原始失败日志已保存：[首次 helper 失败](logs/github-postgres17-initial-failure.zip)、[上传目录设置污染](logs/github-postgres17-upload-isolation-failure.zip)、[迁移状态未恢复](logs/github-postgres17-migration-restore-failure.zip)。这轮回归后会重新运行完整三项 CI；结果以本报告更新记录为准。Vitest 最终执行有效测试目录并排除了使用 `node:test` 的 `detail-drawer-typography.spec.js`；初次广域自动发现日志保留供追溯，不计为有效 Vitest 结果。

## Chrome 与模板证据

真实 Google Chrome `156.0.8078.80` 连接本地隔离应用，完成模板下载、审核、执行、重新加载和结果核对：

- 桌面 1440×1000：[执行结果截图](screenshots/history-takeover-desktop-executed.png)
- 窄屏 390×844：[执行结果截图](screenshots/history-takeover-390px-executed.png)
- 申请审核视图：[桌面申请截图](screenshots/history-takeover-desktop-before-review.png)
- 浏览器结果：[chrome-run.json](screenshots/chrome-run.json)，无页面错误，手机视口/文档/body 宽度均为 390 px，无水平溢出。
- 实际从应用下载的模板：[history-takeover-template-v1.xlsx](screenshots/history-takeover-template-v1.xlsx)；文件为 14,134 字节，SHA256 为 `ebb2a0f5a36a256bdcc8e4baadb6c6bfa7cd7fd7c726fe602ccc1031fabab0a0`；10 个工作表结构记录在 [合成数据库与模板结构日志](logs/synthetic-browser-db-reconciliation.log)。
- 浏览器正向执行日志：[chrome-uat-pass.log](logs/chrome-uat-pass.log)、[chrome-uat-visual-final.log](logs/chrome-uat-visual-final.log)；服务端 HTTP 日志：[django-chrome-server.log](logs/django-chrome-server.log)。

本地视觉与流程已通过。生产部署后的持久文件、实际员工会话和真实数据权限仍待部署环境验证。

## 真实迁移前仍需用户提供的资料

1. 每个来源系统的完整导出、字段口径、来源编号规则、导出时间/覆盖期间及原始凭证定位方式。
2. 每条关联组的真实/模拟/待核实标记、业务负责人、审核人、审核证据，以及取消、结清、部分完成等状态的权威依据。
3. 客户、供应商、SKU 的唯一业务映射；历史主体/产品名称、型号、单位、交易单位换算与单据行原始快照。相似名称只作人工排查线索。
4. 销售/采购订单原编号、日期、币种、原金额及更正链；逐行取消、发货、收货、冲销的事件编号、数量、单位、实际发生日期及凭证。
5. 资金来源系统的流水、银行/现金凭证、币种和汇率口径、已核/未核状态、关联单据及余额调节结果；正式导入需等待资金包稳定交接接口。
6. 库存盘点时点、SKU/单位、实盘数量、仓库归属（自有/第三方）、适用批次/库位、责任人与盘点凭证；需先确认与当前库存服务的正式接入方案。
7. 真实环境使用的实名审核账号与访问边界，以及未结业务接续的正式责任人和切换时间点。开发超级管理员身份不能作为真实审核人。

本次没有导入任何上述真实资料。

## 文件索引

- 后端：`backend/crm/history_takeover.py`、`history_takeover_api.py`、`history_takeover_models.py`、`migrations/0098_history_takeover_workflow.py`、`tests/test_history_takeover.py`
- 前端：`frontend/src/views/HistoryTakeoverPage.vue`、路由/导航接线、`frontend/tests/history-takeover.spec.js`
- 合成 Chrome 驱动：`frontend/scripts/history-takeover-chrome-uat.mjs`
- 合成 SQLite UAT 初始化：`seed_synthetic_uat.py`
