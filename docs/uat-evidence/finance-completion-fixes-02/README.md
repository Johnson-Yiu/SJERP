# FINANCE-COMPLETION-FIXES-02 验收记录

来源分支为 `codex/release-integration-repair-01`。拉取后远端仍指向审定基线 `1e45e42cc4fa38afbf856143228dada7c8a2e86f`。本包提交分支为 `codex/finance-completion-fixes-02`。测试使用合成资料和隔离 PostgreSQL，CI 为 `NOT_RUN`。

| 反例 | 基线表现 | 修复后验证 |
| --- | --- | --- |
| 50 元收款作废时审计抛错 | 收款已作废，应收变回 100 | 流水仍已确认，剩余应收 50。同身份重试完成作废并留下单条审计。响应丢失后重放返回原结果，同身份换原因返回 409。真实 PostgreSQL 两请求竞争只逆向核销一次。 |
| 原币退款补录日期 | 接口拒绝日期字段 | 日期写入退款流水与审计。非法日期按字段拒绝。同一身份跨日重放保留首次日期，改日期返回 409。10 月补录退款只进入 10 月列表、账面支出和 CSV。 |
| 换账号恢复待确认付款 | 原组件在另一账号下显示上一账号的待确认付款 | Vue 组件使用真实工作区管理器。账号乙看不到甲的原金额、参考号和备注，甲关闭后重新打开另一工作区可按原身份和内容提交。核对完成后再次新建使用新身份。 |
| 原账号重开财务操作 | 全局缓存混用，或工作区临时键变化后无法找到原请求 | 客户收款、计划收付、采购付款、预收核销、原收款退款、结汇登记及确认均使用账号与操作、业务对象的组合。组件覆盖收款、计划、采购、退款、结汇登记与确认的重放。 |
| 同权限不同账号重放 | 结构化收款和银行事件部分路径只核对内容 | 隔离后端验证另一账号重放结构化收款、银行登记或确认时返回 409。 |

新页面总是提交实际退款日期和作废请求身份。兼容旧客户端的无日期退款及无身份作废请求。历史收款若缺少能证明操作人的创建审计及扣减身份，须通过流水查询核对，提交重放会被拒绝。旧浏览器缓存原样保留，只提示核查，页面不会自动恢复其内容。对于同一业务对象上的同种操作，界面先恢复现有待确认请求，完成核对后可另起请求。

## 实际命令及结果

在独立工作树执行：

```powershell
git fetch origin refs/heads/codex/release-integration-repair-01:refs/remotes/origin/codex/release-integration-repair-01
```

在 `backend` 执行：

```powershell
$env:DATABASE_URL='postgresql://postgres@127.0.0.1:55459/postgres'
python manage.py test crm.tests.test_finance_receipt_convergence crm.tests.test_finance_data_scope crm.tests.test_cash_events crm.tests.test_receipt_refund_attribution --noinput
python manage.py makemigrations --check --dry-run
```

94 项通过，模型迁移一致性检查通过。基线用同文件内的 `ReceiptConvergenceTests.test_void_audit_rollback_and_replay`、`ReceiptConvergenceTests.test_refund_uses_actual_date_and_replays_across_days` 复现，两项均按预期失败。

在 `frontend` 执行：

```powershell
npx --no-install vitest run tests/transaction-safety.spec.js tests/payment-plan-filters.spec.js src/components/PurchasePaymentModal.spec.js src/components/CashEventEntryForm.spec.js --environment jsdom
npm run build
```

组件测试 26 项通过，生产构建通过。相同采购组件测试用基线组件临时替换时，账号乙隔离断言失败。真实 Chrome 视觉复核仍待执行，当前会话缺少符合用户既定内置浏览器限制的可用工具。

## A2 接入

共享文件为 `backend/crm/views.py`，接入时保留 `TransactionViewSet.void` 和 `refund_cash` 改动。财务服务另涉及 `backend/crm/services/finance.py` 和 `cash_events.py`。前端复用现有账号与工作区接口，新增财务专用存储组合函数。公共台账由 A2 统一接入，建议关联 ISS-105/108，并保留独立复审与真实浏览器验收状态。
