# 财务迁移与备份恢复只读交叉审查

日期：2026-11-04

## 审查边界与结论

- 指定财务来源：`3a07e7ef1a9e63c98077d45492ba23b798c7fcdd`。
- 本地集成工作树 HEAD：`ce74f8b7cf6cd1e1e4e8f50141d9fc38e86c3903`。财务来源 SHA 不是此 HEAD 的祖先；本报告只核对指定来源树，不把该来源的状态、测试或 CI 结果写成集成验收。
- 只读检查迁移、模型、测试与备份实现；未切换工作树、未连接数据库、未运行测试或迁移，也未检查主审正在核对的远端 CI。
- 主要来源路径（均从指定 SHA 读取）：`backend/crm/migrations/0091_csv_import_audit.py`–`0102_bank_private_voucher_binding.py`；`backend/crm/models.py`；`backend/crm/services/finance_closeout.py`；`backend/crm/services/backup_recovery.py`；`backend/crm/services/postgres_drill_backup.py`；`backend/crm/services/private_media.py`；`backend/crm/tests/test_csv_import_audit_migration_rollback.py`、`test_cash_duplicate_review.py`、`test_finance_closeout.py`、`test_postgres_drill_backup.py`、`iss018_drill_fixture.py`。

| 项目 | 结论 | 证据边界 |
|---|---|---|
| 0091–0102 迁移依赖 | 静态检查未发现循环或缺失的分支合并；0098–0102 依次依赖 0097→0098→0099→0100→0101。 | 未运行 Django migration graph、`migrate --plan` 或干净 PostgreSQL 升级。 |
| 迁移与模型状态 | 所列新表、字段、外键和约束在迁移文件与源 SHA 的 `models.py` 中可对应；0102 的银行凭证来源回退保护有一个不完整条件，见缺陷 M1。 | 未运行 `makemigrations --check`；不据静态对读宣称 state 完全一致。 |
| 不可逆保护 | 0098–0102 均有反向 RunPython 检查；0091–0094、0096 的既有审计保护顺序兼容。针对 0100、0101 及空数据回退/重迁的迁移执行测试不足，见缺口 M2。 | 财务来源中的迁移保护测试仅直接调用部分 guard，且本轮未执行。 |
| 通用 SQLite 备份 | 可捕获完整 SQLite 数据库文件及 `MEDIA_ROOT` 下全部本地文件；数据库/媒体 SHA 和 SQLite 恢复检查并非财务实体级验收。 | `create_consistent_backup` 明确拒绝 PostgreSQL；不能作为 PostgreSQL 备份验收。 |
| PostgreSQL 17 隔离演练 | 指定来源的 `pg_dump`/`pg_restore` 机制会包含数据库表、数据和序列；媒体清单覆盖本地媒体文件。现有合成夹具和比较表未包含本批财务实体，故尚无其备份恢复实证，见缺口 M3。 | 只读检查源代码；不代表这次财务来源或未来集成版本已通过 PostgreSQL 演练。 |

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
| 0102 | `preserve_bank_proofs` 检查银行绑定行或 `FinanceVoucher.scope='bank'`。 | 正常服务路径在传入 `bank_sources` 时设置 `scope='bank'`，因此已有银行凭证路径受保护；该条件未检查 `bank_sources` 自身，见 M1。 |

与 0091–0097 的现有保护兼容性：`test_csv_import_audit_migration_rollback.py` 覆盖 CSV 审计有历史时拒绝回退及空表允许回退/重迁；`test_cash_duplicate_review.py` 对 0096 guard 作直接检查并执行包含 0102 在内的反向路径，另有 PostgreSQL 原始 UPDATE/DELETE/TRUNCATE 拒绝测试。需要注意，执行包含 0102 的反向路径时，测试可能先被 0102 银行凭证 guard 拦截；不能仅凭该结果声称 0096 的 MigrationExecutor 回退分支也被单独执行。`test_finance_closeout.py::test_history_and_migration_reversal_are_protected` 只直接调用 0098/0099 两个 guard。当前来源没有覆盖 0100/0101 guard 及 0098–0102 空状态完整回退、重迁的对应测试。

## 具体缺陷与验收缺口

### M1 — 0102 回退守卫没有检查非空 `bank_sources`

`0102_bank_private_voucher_binding.py::preserve_bank_proofs` 仅阻止存在 `FinanceBankVoucherBinding` 或 `FinanceVoucher.scope='bank'` 的回退。`FinanceVoucher.bank_sources` 是有意义的 JSON 字段；模型未定义 scope choices 或数据库约束来保证“`scope != bank` 时 `bank_sources` 必为空”。因此数据库可存入 `scope='account', bank_sources=[...]` 的行，而回退 0102 会通过检查并删除该列，丢失已保存的来源关联。这种状态不由当前正常上传服务产生，但数据库/模型状态并未排除它。

最小处理建议：确认该状态非法后，在 schema 层约束字段组合；或让 reverse guard 对任何非空 `bank_sources` 一并拒绝。补一条 MigrationExecutor 回退测试，构造该状态并证明迁移拒绝，清空/无来源状态则可安全回退。审查本身未修改迁移或模型。

### M2 — 0098–0102 回退测试没有形成逐迁移有数据/空数据矩阵

当前证据不能证明 0100 legacy link、0101 historical transfer 的保护分支实际执行，也不能证明空账户/空财务历史时 0098–0102 按预期完整回退并重新迁移。请在一次性 PostgreSQL 环境用 MigrationExecutor 逐迁移验证：对每个守卫分别准备一行命中数据和空表场景；断言拒绝时原记录、迁移记录、外键/约束/触发器状态保留；空场景回退再迁移成功。每个独立场景使用隔离数据库，避免某个较新的守卫提前阻断并掩盖较旧守卫。

### M3 — 当前通用备份可全量捕获，但财务实体没有被既有恢复验收夹具覆盖

`backup_recovery.py::create_consistent_backup` 对 SQLite 使用 SQLite backup API 复制整个数据库文件，并递归复制 `MEDIA_ROOT` 中媒体清单列出的文件；其 manifest 保存数据库整体 SHA、媒体路径/大小/SHA 和恢复配置。该机制没有按模型 allowlist，因此已迁移的新表、关联行及 SQLite 序列会随数据库文件捕获。它不生成财务表级行数/关系清单，也不验证恢复后 `FinanceVoucher.sha256/size` 与对应文件内容一致。

PostgreSQL 路径不是该通用命令：`_assert_sqlite` 明确 fail-closed。隔离 PostgreSQL 演练使用全库 `pg_dump --snapshot`、`pg_restore --single-transaction`，媒体清单复制 MEDIA_ROOT，并将数据库迁移记录与 `pg_sequences` 纳入恢复比较；但 `test_postgres_drill_backup.py::_business_snapshot` 的固定表清单没有 `crm_finance*`、`crm_rmbcashevent`、`crm_cashduplicatereview`、`crm_cashsourceallocation`，合成夹具也未建立这些财务记录或 `finance-vouchers/` 文件。现有测试因此只证明通用 dump/archive 路径，不证明新财务表、外键、序列和私有凭证已经被实际 seed 后恢复。

恢复接受还应核对每个 `FinanceVoucher.file` 对应文件存在、相对路径保持、文件 SHA256 等于数据库字段及媒体清单、size 相符；现有通用 manifest 只核实数据库包整体 SHA 与媒体文件自己的 SHA，不做这项跨库/文件关联校验。

## 可执行验收清单

以下项目需在主审确认财务源已完整合入后的精确集成 SHA 上完成；单独来源 SHA `3a07e7e` 不能替代集成版结果。

- [ ] 记录集成 SHA、工作树干净状态和迁移图；执行 `showmigrations crm`、`migrate --plan`、`makemigrations --check --dry-run`，确认双 0090/0096 分支最终汇合为一个完整叶节点且模型 state 无差异。
- [ ] 一次性隔离 PostgreSQL 17 空库从基线升级到最新，逐项确认 0091–0102 的表、列、外键、唯一/检查约束、追加保护触发器和迁移记录；不得连接实际业务数据库。
- [ ] 在隔离 PostgreSQL 中分开执行 M2 所列每个 populated reverse guard 与 empty reverse/re-migrate 场景；确认 0102 非空 `bank_sources` 保护已覆盖。
- [ ] 用合成数据覆盖 10 张 0098–0102 财务表，以及 `RmbCashEvent`、`CashSourceAllocation`、`Transaction`、`OperationLog`、`CashDuplicateReview` 和必要用户/账户记录。至少填充：账户映射、指令及替代链、事实 parent 与 legacy_parent 两类路径、分类、普通转账、历史转账新/旧两种端点、账户核对、银行凭证绑定。
- [ ] 上传一份合成私有凭证到 `finance-vouchers/YYYY/MM/...`，在 `FinanceVoucher` 记录 file、原名、size、SHA、scope/source；从 `FinanceReview`、`FinanceHistoricalTransfer`、`FinanceBankVoucherBinding` 建立对应关联。备份 manifest 应记录该相对路径、字节数和 SHA。
- [ ] 备份前后比较上述所有新表的完整行值和 FK/OneToOne 目标；比较所有相关 `BigAutoField`/`AutoField` 序列当前值，并在恢复库逐表插入下一行证明不会重复主键。确认 `QuoteTemplateAsset` 文本主键和 `Quote.pi_template_snapshots` 也保存。
- [ ] 使用 PostgreSQL 全库 dump 和独立 MEDIA_ROOT 恢复到新的隔离数据库/目录；校验迁移状态、序列、外键和触发器，验证凭证文件 SHA 与 FinanceVoucher 行一致；源库与恢复库的数据库和媒体内容逐项一致。
- [ ] 在恢复库通过真实本地 HTTP 验证：未认证/无权限用户拿不到私有凭证；授权用户仅通过受控接口下载正确内容；`/media/` 直链拒绝；响应 `Cache-Control: private, no-store`。仅 Django 测试客户端不替代部署反向代理验收。
- [ ] 重新运行现有 0091–0094 审计回退/PG UPDATE、DELETE、TRUNCATE 保护和 0096 CashDuplicateReview PG 保护，并保存逐条原始日志；记录每项通过/失败/跳过数量及实际 PostgreSQL 版本。

## 当前状态

- **PASS（静态）**：迁移汇合关系可读且无明显缺失依赖；全量 SQLite 数据库快照与全量本地媒体清单机制可覆盖已迁移实体；PostgreSQL drill 使用全库 dump/restore。
- **FIX REQUIRED / 规则确认**：M1 的 0102 `bank_sources` 反向保护遗漏，至少需补防护或明确并强制字段组合约束。
- **NEEDS VERIFICATION**：M2 迁移保护矩阵；M3 新财务表、关系、序列和凭证文件的合成 PostgreSQL 备份恢复验收；模型 state 需在集成版实际跑 `makemigrations --check`。
- **NOT VERIFIED**：指定财务来源是否已合并、集成 SHA 的 CI、PostgreSQL 新库升级与新财务 seed 恢复。本报告不把主审正在执行的工作提前记为通过。
