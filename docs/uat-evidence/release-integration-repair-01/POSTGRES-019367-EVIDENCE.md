# RELEASE-INTEGRATION-REPAIR-01 PostgreSQL 候选验证

候选：019367baa389c2a73ea2d8c58162313e4868fcca。2026-11-09，独立本机 PostgreSQL 17（127.0.0.1:55459）。数据库仅为本轮合成数据，未操作正式数据库；本记录不含凭据。

## 三入口

- 空库 `fic_rir01_019_fresh`：候选 `python manage.py migrate --noinput` 成功，应用至 `crm.0128_merge_release_integration`。
- `fic_rir01_019_c90`：先用 c90cacaa 执行 `python manage.py migrate --noinput` 至 crm.0122，再以候选 `test_support/finance_inventory_migration_probe.py c90 seed` 在旧版本模型种入样本；另建历史来源快照和余额快照。候选执行 `python manage.py migrate --noinput`，然后 `python test_support/finance_inventory_migration_probe.py c90 verify` 成功。
- `fic_rir01_019_c978`：先用 c978758f 执行 `python manage.py migrate --noinput` 至 crm.0120，以同一探针 `c978 seed` 在旧版本模型种入样本；另建历史来源快照和余额快照。候选执行 `python manage.py migrate --noinput`，然后 `python test_support/finance_inventory_migration_probe.py c978 verify` 成功。

所有命令的 DATABASE_URL 分别指向以上本机隔离库；探针使用旧版本时通过 PYTHONPATH 指定当前旧版 backend。候选核对两条存量路径现金拆分、抹零、三项约束；c90 核对更正，c978 核对缺汇率以及凭证与抵减关联。两库 SQL 核对历史来源快照金额 123.45、未知 null、余量 17.25 及 0128 迁移记录均保留。仅验证合成样本，不覆盖升级前审计、真实凭证文件、全部历史财务场景及完整业务样本，不能描述为全量迁移验收。

## 定向数据库测试

在候选 backend、DATABASE_URL 指向 `fic_rir01_019_fresh` 时运行：

```powershell
python manage.py test crm.tests.test_inventory_finance_idempotency crm.tests.test_finance_closeout.FinanceBankReturnConcurrencyTests crm.tests.test_finance_closeout.FinanceCloseoutTests.test_cny_bank_return_restores_receivable_atomically crm.tests.test_finance_closeout.FinanceCloseoutTests.test_cny_bank_return_restores_payable_atomically crm.tests.test_receipt_refund_attribution.ReceiptRefundConcurrencyTests --noinput
```

9 项通过，0 跳过；包括库存单/批审计失败回滚、库存并发、人民币收付退回、外币退回并发和原收款退款并发。日志中的审计异常由测试注入，断言通过。第一次携带 `--keepdb` 的尝试被安全测试运行器拒绝，没有执行测试；上述无 `--keepdb` 重试已通过。未执行 CI、部署或浏览器验收。
