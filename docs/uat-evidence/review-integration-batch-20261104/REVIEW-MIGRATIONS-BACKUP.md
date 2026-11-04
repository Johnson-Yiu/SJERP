# 财务迁移与备份恢复交叉审查

日期：2026-11-04

## 审查边界与结论

- 指定财务来源：`3a07e7ef1a9e63c98077d45492ba23b798c7fcdd`。
- 指定历史承接来源：`a0729a0965850028fe52f5b6fcc3e825f23b1289`。
- 当前集成工作树 HEAD：`1f189c3f74fda2908620dd3860230d860f1cbb43`。已核实上述财务与历史来源均为当前 HEAD 的祖先。本报告不将来源分支结果或较早的 SQLite 结果冒充当前 HEAD 的 PostgreSQL/CI 验收。
- 本报告核对当前 SHA 的全量 PostgreSQL 日志及金融恢复产物；本轮没有运行测试或迁移，没有连接真实业务数据库。全量 PG 日志：`logs/postgres-full-all-sources-1f189c3.log`；财务恢复验证：`artifacts/postgres-backups/finance-restored-1f189c3f74fd.json`。
- 冻结 SHA 的 SQLite 全量实际结果为 1312 项、1251 通过、61 跳过、0 失败，816.678 秒；PG 全量为 1312 项、1282 通过、30 跳过、0 失败，1008.032 秒，`POSTGRES_REGRESSION_EXIT=0`。两份日志均列出跨包测试通过；PG 日志还列出 0098–0102 回退矩阵 9 项均 `ok`。PG 17.11 备份恢复记录亦为 PASS。CI 41829100528 的状态按当前收到的信息为 Backend 与 PostgreSQL 成功、Frontend 仍运行中；不据此称三项 CI 全部完成。
- 主要来源路径（均从指定 SHA 读取）：`backend/crm/migrations/0091_csv_import_audit.py`–`0102_bank_private_voucher_binding.py`；`backend/crm/models.py`；`backend/crm/services/finance_closeout.py`；`backend/crm/services/backup_recovery.py`；`backend/crm/services/postgres_drill_backup.py`；`backend/crm/services/private_media.py`；`backend/crm/tests/test_csv_import_audit_migration_rollback.py`、`test_cash_duplicate_review.py`、`test_finance_closeout.py`、`test_postgres_drill_backup.py`、`iss018_drill_fixture.py`。

| 项目 | 结论 | 证据边界 |
|---|---|---|
| 0091–0102 迁移依赖 | 静态检查未发现循环或缺失的分支合并；PG 全量/恢复日志记录 128 项迁移，0091–0102 均应用到当前叶节点。 | 本轮未运行 Django migration graph、`migrate --plan` 或 `makemigrations --check`；未做逐列/约束/触发器清单核对。 |
| 迁移与模型状态 | 当前集成代码的 0102 银行凭证来源回退保护已检查绑定、bank scope 和非空 `bank_sources`；M1 已修复。 | 本报告未运行 `makemigrations --check`；不据静态对读宣称当前模型 state 完全一致。 |
| 不可逆保护 | 当前 HEAD 的 PG 全量日志中，0098–0102 空状态回退/重迁及各项有数据拒绝矩阵 9 项全部通过，包含 0102 account scope 非空 `bank_sources`。 | 这九项验证由 PG 全量测试中的独立 `MigrationExecutor` 场景提供；不包含所有迁移 schema 对象的逐项审计。 |
| 通用 SQLite 备份 | 可捕获完整 SQLite 数据库文件及 `MEDIA_ROOT` 下全部本地文件；数据库/媒体 SHA 和 SQLite 恢复检查并非财务实体级验收。 | `create_consistent_backup` 明确拒绝 PostgreSQL；不能作为 PostgreSQL 备份验收。 |
| PostgreSQL 17 隔离演练 | 当前集成 SHA 的实证恢复报告为 PASS：99 表、1081 行、128 项迁移、4 个媒体文件；财务专项产物还记录 10 张财务表及关联事件/分配表、凭证文件、序列和 HTTP 结果。 | 仅覆盖本次合成 seed 与产物列明的实体/断言；逐关系核对、未入 seed 的实体和部署代理验收仍按下方范围处理。 |

## 迁移依赖与既有审计兼容

依赖图按指定来源 SHA 静态展开如下：

```text
0089
 ├─ 0090_fulfillment_idempotency ─┐
 └─ 0091_csv_import_audit → 0092_merge_fulfillment_and_csv_audit
                                  → 0093_csv_import_preview_audit
                                  → 0094_csv_import_audit_truncate_guard ─┐
 0090_fulfillment_request_idempotency ────────────────────────────────────┴→ 0095_merge_fulfillment_idempotency
 0095 ─┬→ 0096_quote_pi_template_snapshots ─────────────────────────────────┐
      └→ 0096_rmbcashevent_bank_counterparty_and_more ──────────────────────┴→ 0097_merge_quote_and_cash_review
 0097 → 0098_finance_accounts → 0099_finance_closeout_workflows
      → 0100_finance_legacy_fact_links → 0101_finance_historical_transfer_links
      → 0102_bank_private_voucher_binding
```

`0096_rmbcashevent_bank_counterparty_and_more` 复用 0089 建立的 OperationLog append-only 函数和 0094 建立的 CSV 审计 TRUNCATE 函数。其依赖经 0095→0094 汇合；回退时 0096 先删除 CashDuplicateReview 触发器，之后才可回退 0094 删除共享函数。0092/0095/0097 分别保留两个 0090 分支、两个 0096 分支的汇合点，不应删除或改写历史迁移。

0098–0102 新增表和字段如下。模型定义位置均为 `3a07e7ef1a9e63c98077d45492ba23b798c7fcdd:backend/crm/models.py`：

| 迁移 | 表/字段 | 关键关系或保护 |
|---|---|---|
| 0098 | `FinanceAccount` | 唯一账户 code；类型、归属及归属说明检查约束。 |
| 0099 | `FinanceVoucher`、`FinanceAccountMapping`、`FinanceFact`、`FinanceClassification`、`FinanceInstruction`、`FinanceTransferMatch`、`FinanceReview` | 资金事实关联账户、凭证、指令、父事实或旧 `RmbCashEvent`；分类关联事实；转账两端分别 OneToOne；对账记录关联账户和凭证；映射 legacy code 到账户；指令保留幂等键、请求指纹、审批和替代链。 |
| 0100 | `FinanceFact.legacy_parent` 与 `finance_fact_one_parent` | 保留旧 RMB 事件来源；禁止同时填 `parent` 和 `legacy_parent`。 |
| 0101 | `FinanceHistoricalTransfer` | 收/付两端分别指向新 `FinanceFact` 或旧 `RmbCashEvent`，并关联两份凭证；两端各有 exactly-one-source 检查约束。 |
| 0102 | `FinanceVoucher.bank_sources`、`FinanceVoucher.scope`、`FinanceBankVoucherBinding` | 银行凭证与 `RmbCashEvent` OneToOne 绑定，凭证、事件、操作人和来源范围需一起保留。 |

同一汇合链前段 0096 还新增 `CashDuplicateReview`，扩展 `RmbCashEvent` 的银行对手方、摘要和交易编号；另一个 0096 分支新增 `QuoteTemplateAsset` 和 `Quote.pi_template_snapshots`。0091/0093 新增 CSV 批次、行审计、预览审计表，0094 为三表增加 PostgreSQL TRUNCATE guard。这些既有表/关系也必须留在全量备份恢复断言中。

## 反向迁移保护核对

| 迁移 | 反向检查 | 静态结果/尚缺验证 |
|---|---|---|
| 0098 | `preserve_accounts` 检查 `FinanceAccount` 是否有行。 | 有账户记录时拒绝删表；当前 `test_finance_closeout.py` 直接调用该函数，没有 MigrationExecutor 回退测试。 |
| 0099 | `preserve_finance_history` 检查七张工作流表：凭证、账户映射、事实、分类、指令、转账匹配、对账。 | 有任一行即拒绝删历史；当前测试直接调用函数，没有逐表填充/Executor 实测。 |
| 0100 | `preserve_legacy_links` 检查 `FinanceFact.legacy_parent IS NOT NULL`。 | 保护旧事件链接；在来源测试中未找到此分支的直接或 MigrationExecutor 回退用例。 |
| 0101 | `preserve_historical_transfers` 检查历史转账表是否有行。 | 有行时保护；在来源测试中未找到此分支的直接或 MigrationExecutor 回退用例。 |
| 0102 | `preserve_bank_proofs` 检查银行绑定行、`FinanceVoucher.scope='bank'` 或非空 `FinanceVoucher.bank_sources`。 | 已覆盖 bank scope 和 account scope 携带来源的反向保护；后者由修复后的 SQLite 矩阵实测。 |

与 0091–0097 的现有保护兼容性：`test_csv_import_audit_migration_rollback.py` 覆盖 CSV 审计有历史时拒绝回退及空表允许回退/重迁；`test_cash_duplicate_review.py` 对 0096 guard 作直接检查并执行包含 0102 在内的反向路径，另有 PostgreSQL 原始 UPDATE/DELETE/TRUNCATE 拒绝测试。需要注意，执行包含 0102 的反向路径时，测试可能先被 0102 银行凭证 guard 拦截；不能仅凭该结果声称 0096 的 MigrationExecutor 回退分支也被单独执行。`test_finance_closeout.py::test_history_and_migration_reversal_are_protected` 只直接调用 0098/0099 两个 guard。原财务来源测试没有覆盖 0100/0101 guard 及 0098–0102 空状态完整回退、重迁；集成后的独立 MigrationExecutor 矩阵已在 SQLite 与当前 PG17.11 全量中通过，详见 M2。该矩阵不等于 0091–0094 和 0096 所有 UPDATE/DELETE/TRUNCATE 保护逐表复测。

## 修复记录与验收缺口

### M1 — 0102 `bank_sources` 回退保护（已修复，SQLite 已验证）

修复提交 `319941c05e4682d80cd718f577514a39231fabfa` 将 `0102_bank_private_voucher_binding.py::preserve_bank_proofs` 扩展为检查任意非空 `bank_sources`，保留原绑定行和 bank scope 检查，未更改迁移操作、依赖或历史 DDL。当前代码路径为 `backend/crm/migrations/0102_bank_private_voucher_binding.py`。

修复前的实际 SQLite 日志 [finance-migration-rollback-sqlite.log](logs/finance-migration-rollback-sqlite.log) 为 9 项中 8 通过、1 失败；失败复现为 `scope='account'` 且 `bank_sources` 非空时回退未被拒绝。修复后的实际日志 [finance-migration-rollback-fixed.log](logs/finance-migration-rollback-fixed.log) 为 9 项通过、0 失败，运行 11.443 秒，Django system check 无问题。修后测试时 SHA：`7ca7a7aea7c9b76dc2136fdbe3eda3af8ebebda7`，已核实为当前集成 HEAD 的祖先。另在当前 SHA 的 PG 全量日志中，同一 account-scope 非空来源拒绝测试为 `ok`（第 2616 行）。修前日志保留，未被覆盖。

### M2 — SQLite 与 PostgreSQL 迁移矩阵已通过（9 项）

当前 SHA 的 PostgreSQL 全量日志第 2611–2619 行逐项记录 0098、0099、0100、0101、0102 有数据拒绝路径、0102 bank/account scope 边界及空状态完整回退重迁，9 项全部 `ok`。对应测试在 PG17.11 全量中执行；完整日志末尾为 1312 项、1282 通过、30 跳过、0 失败、退出码 0。修后 SQLite 矩阵日志仍保留于 `logs/finance-migration-rollback-fixed.log`（9/9）。本证据覆盖测试中构造的各路径及断言；不等于对所有迁移字段、约束、触发器逐项人工盘点。

### M3 — 综合 PostgreSQL 恢复与财务 seed 已有实证；仍有未覆盖实体和验收项

全量 PostgreSQL 日志末尾的恢复摘要为 `status=PASS`、`table_count=99`、`row_count=1081`、`migrations=128`、4 个媒体文件；源媒体未变化且 cleanup 为 complete。保留备份 SHA256 为 `6c0dc8077710edb1c47c853d39f62a5d5ce0b6d591607e3745ca45727c4d0688`。日志同时记录 `HISTORY_RESTORE_VERIFICATION=PASS` 与 `FINANCE_RESTORE_VERIFICATION=PASS`。

财务恢复产物 `artifacts/postgres-backups/finance-restored-1f189c3f74fd.json` 的 `source_sha` 与当前集成 SHA 一致，状态 PASS。产物列出 10 张 `crm_finance*` 表的快照（合计 20 行），另有 `RmbCashEvent` 1 行、`CashSourceAllocation` 1 行；`CashDuplicateReview` 在该 seed 中为 0 行。产物记录 97 个序列条目、4 个媒体引用及两份私有凭证；每份凭证的数据库 SHA/size 与恢复文件 SHA/size 一致。整体恢复日志报告包含 99 张表，但这不代表每个业务实体都在 seed 中有记录。

恢复产物中的本地 HTTP 证据为匿名下载 403、受限用户 403、授权用户 200 且返回字节 SHA 与凭证一致，`/media/` 直链 404。该 JSON 未保存 HTTP 响应头，因此仅凭当前指定文件不能核验 `Cache-Control: private, no-store`；部署反向代理验收仍待保留可审查的响应头证据。历史恢复 marker 为 PASS，但本财务 JSON 未列出历史五表的逐表行数/关系快照。

## 可执行验收清单

以下项目需在主审确认财务源已完整合入后的精确集成 SHA 上完成；单独来源 SHA `3a07e7e` 不能替代集成版结果。

- [x] 当前集成 SHA 的 SQLite 与 PostgreSQL 全量回归均已记录：SQLite 1312 项（1251 通过、61 跳过、0 失败，816.678 秒）；PG 1312 项（1282 通过、30 跳过、0 失败，1008.032 秒，退出码 0）。原始日志分别为 `logs/backend-full-all-sources-1f189c3.log` 和 `logs/postgres-full-all-sources-1f189c3.log`；隔离恢复摘要记录 128 项迁移及 PostgreSQL 17.11。
- [ ] 另行保存工作树干净证明、`showmigrations crm`、`migrate --plan`、`makemigrations --check --dry-run` 和双 0090/0096 汇合/model state 核验；全量运行日志不替代这些独立检查。
- [x] PG 全量中的 0098–0102 MigrationExecutor 回退矩阵 9/9 通过；含各迁移有数据拒绝、0102 account scope 非空来源拒绝、空状态回退及重迁。详见该 PG 日志第 2611–2619 行。
- [x] 财务恢复 seed 已覆盖 10 张财务表，并有 `RmbCashEvent` 与 `CashSourceAllocation` 记录；详见 `finance-restored-1f189c3f74fd.json`。该产物中的 `CashDuplicateReview` 为 0 行，且未列出 `Transaction`、`OperationLog` 的逐表快照，不能据此勾选这些表的 seed 覆盖。
- [x] 两份合成私有凭证、FinanceReview、FinanceHistoricalTransfer、FinanceBankVoucherBinding 均列于财务恢复证据；凭证恢复文件 SHA/size 与数据库记录一致。完整逐关系端点清单未在 JSON 里展开，需按其 PASS 范围理解，不据此声称所有历史/旧 Transaction 链接均逐项验收。
- [x] 本次合成 PostgreSQL 全库恢复报告记录 99 表、1081 行、128 迁移、4 个媒体文件，状态 PASS，源媒体未改变且清理完成；财务 artifact 记录 97 个序列条目及凭证 SHA/size 匹配。
- [ ] 对 `QuoteTemplateAsset` 文本主键、`Quote.pi_template_snapshots`、全部 FK/OneToOne 目标和恢复后序列插入行为做逐项对照；当前摘要未逐项列出这些断言结果。
- [x] 恢复后真实 HTTP 已验证匿名 403、受限 403、授权 200 且授权响应字节 SHA 与凭证一致，`/media/` 直链 404。
- [ ] 当前指定恢复 JSON 未保留 `Cache-Control: private, no-store` 响应头；需保存该头的真实 HTTP 证据并完成部署反向代理验收。
- [x] PG 全量日志包含 OperationLog 原始 UPDATE/DELETE 拒绝测试及 CSV 审计 append-only 测试通过记录。
- [ ] 0091–0094 三张审计表和 0096 CashDuplicateReview 的完整 PG UPDATE/DELETE/TRUNCATE 逐表矩阵及原始证据仍需单独核对；不因全量套件通过而全勾。

## 当前状态（当前集成 HEAD `1f189c3f74fda2908620dd3860230d860f1cbb43`）

- **PASS（SQLite 与 PG 迁移矩阵）**：0102 非空 `bank_sources` 防护已实现；SQLite 9/9、PG17.11 全量中的迁移矩阵 9/9 均通过。修前 SQLite 失败日志仍保留。
- **PASS（SQLite/PG 全量及合成恢复的已证范围）**：当前 SHA SQLite 1312 项（1251 通过、61 跳过、0 失败），PG 1312 项（1282 通过、30 跳过、0 失败）；99 表/1081 行/128 迁移/4 媒体恢复摘要 PASS；财务十表及相关凭证、97 序列条目与 HTTP 状态有专项产物支持。
- **NEEDS VERIFICATION（未覆盖的备份细节）**：`CashDuplicateReview` 本次为 0 行；`Transaction`、`OperationLog`、历史五表逐表快照及所有 FK/OneToOne 目标未由财务 JSON 全部列明；Quote 模板快照和恢复后序列插入也未逐项显示。
- **NEEDS VERIFICATION（HTTP/审计）**：当前指定 JSON 未保存 `Cache-Control` 响应头；0091–0094 和 0096 的全量 UPDATE/DELETE/TRUNCATE 逐表矩阵仍待单独核实。已通过的 HTTP 状态、OperationLog UPDATE/DELETE 与 CSV append-only 子集不代替这些缺项。
- **NEEDS VERIFICATION（模型/CI）**：`makemigrations --check`、迁移图/干净升级与完整 schema 清单未见本次证据。CI 41829100528 的 Backend、PostgreSQL 成功；Frontend 仍在运行，因此最终三项 CI 尚未全部结束。

## 交付前CI更新

代码1f189c3的CI41829100528最终为Backend/PG成功、Frontend失败（ISS039快照子进程2项）。已保留原始失败证据并最小补修有界输出缓冲/诊断；大快照2/2、受影响Chrome2/2和Node179/179通过，原全库/业务/权限断言保留。最终完整前端与精确SHA三CI见统一交付回执，本文各早期运行中/待验句仅保留当时状态，不是当前通过声明。后端全量1312项SQLite/PG均无失败，PG额外8命令专项8/8；未关闭Issue或替代ChatGPT独立复审。
