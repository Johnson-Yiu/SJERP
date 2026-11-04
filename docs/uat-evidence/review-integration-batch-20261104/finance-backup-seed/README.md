# 合成财务备份演练资料

此目录只包含 ISS-018 一次性 PostgreSQL drill 的证据 helper，不是产品代码。helper 依赖现有 `crm/tests/iss018_drill_fixture.py`，每次读写前调用 `_assert_synthetic_database()`；同时拒绝非 PostgreSQL。运行环境必须是 drill 自己创建的 `iss018_src_*` 或 `iss018_dst_*` 数据库、`sunjack-iss018-pg17-*` 临时集群和该 drill 的 `MEDIA_ROOT`。

## 调用顺序

先在源库执行现有 `iss018_drill_fixture.seed()`，再、且必须在备份快照前执行此 helper 的 `seed()`。它复用现有合成、已确认的 `ISS018-TX` 外币收款来源。该流水的可分配金额会被本 helper 消耗，因此每个 drill 数据库只运行一次；重跑请新建 owned drill 数据库。

推荐由 `runpy` 从 `manage shell` 中调用，脚本导入时不会自动连接或写入数据库：

```python
import runpy

seed_helper = runpy.run_path(r"<repository>/docs/uat-evidence/review-integration-batch-20261104/finance-backup-seed/seed_finance_backup.py")
source_manifest = seed_helper["seed"]()
```

主审将 `source_manifest` 保存到 owned drill 临时根目录，作为源快照的独立财务期望值。恢复到新的 owned 目标库后，在 `manage_database` 的恢复库环境中加载同一 helper 并执行：

```python
restore_helper = runpy.run_path(r"<repository>/docs/uat-evidence/review-integration-batch-20261104/finance-backup-seed/seed_finance_backup.py")
restore_result = restore_helper["verify"](source_manifest)
assert restore_result["ok"], restore_result["differences"]
```

`verify()` 无参数时只读返回当前库的清单；传入源清单或其 UTF-8 JSON 路径时，会与当前恢复库比较。返回值包含核心 10 张财务表和 3 张支撑现金事件表的行数、整表行 SHA256，以及每张 `FinanceVoucher` 的 ID、存储名、范围、来源编号、文件实际 SHA256/字节数和数据库记录的 SHA256/字节数。任何凭证内容与行内元数据不符都会直接报错；恢复对比不同则返回 `ok: false` 和逐表/逐凭证差异。

## 生成的数据

所有资金账户、指令、事实、分类、账户映射、余额核对、内部转账匹配、历史转账匹配、银行事件、凭证上传及凭证绑定均走 `finance_closeout`、`cash_events` 或其调用的 `bank_vouchers` 官方服务。没有对财务模型执行 `objects.create()`。

核心 10 张新表：

- `FinanceAccount`
- `FinanceVoucher`
- `FinanceBankVoucherBinding`
- `FinanceInstruction`
- `FinanceFact`
- `FinanceAccountMapping`
- `FinanceReview`
- `FinanceTransferMatch`
- `FinanceHistoricalTransfer`
- `FinanceClassification`

另将 `RmbCashEvent`、`CashDuplicateReview`、`CashSourceAllocation` 一并纳入表摘要，以覆盖旧银行来源、分配及重复审核记录。合成用户为两个独立的 Django superuser 数据库账号：发起人和复核人；开账指令使用不同账号复核。凭证是带有明确 Synthetic 标记的私有 PDF。服务流程要求实际入账事实采用 `truth="verified"`，本 helper 只在受 guard 保护的合成数据库中构造相应状态；这些记录不代表真实员工、真实凭证、真实银行到账或正式环境事实。

`RMB_CASH_ACCOUNT_IDS` 只在 `seed()` 运行期间通过 `override_settings` 设置为本次生成的两个合成银行编号，不会改变部署配置。

## 摘要算法和边界

每张表按主键排序，取所有 concrete fields（包括外键 ID、时间戳、JSON、文件名），将每行编码为 UTF-8、键排序、无空格的 JSON，再追加 LF，计算整表 SHA256。凭证文件逐块读取真实字节计算 SHA256/字节数，并同时核对 `FinanceVoucher.sha256` 和 `FinanceVoucher.size`。文件必须解析到本 drill 的 `MEDIA_ROOT` 内。

此清单核对数据行和财务凭证字节；它不替代迁移图、数据库序列、其它业务表、其它附件或整个归档文件的既有 drill 验收。helper 不保存清单、不改通用备份逻辑，也不自动挂钩 `IsolatedPostgresDrill`；调用方应将它放在核心 ISS-018 seed 之后、源快照之前，并在恢复库上对比源清单。

当前交付仅完成 helper 与说明的静态检查；未连接 PostgreSQL、未运行 seed/verify，也未执行 PG 恢复测试。实际 PG 测试由主审安排。
