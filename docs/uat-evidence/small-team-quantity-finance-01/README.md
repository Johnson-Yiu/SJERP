# SMALL-TEAM-QUANTITY-FINANCE-01

基线 `30b3579a579174de5f3e4336619dcdb4c8502470`，来源 `codex/ui-delivery-closeout-04`。交付分支 `codex/small-team-quantity-finance-01`，待独立复审。

本包跟进 ISS-021 数量变更，并涉及 ISS-020 金额版本、ISS-105／ISS-108 收款与抵减口径。两项缺陷均为 `FIXED_PENDING_REVIEW`。下一步由独立复审核对回归、金额快照和同一提交的 CI。公共台账与阶段计划由集成协调任务维护，本包关闭 0 项。

## 基线失败与修复结果

| Django API 回归 | 基线 | 修复后 |
|---|---|---|
| `test_cent_rounded_contract_delta_supports_consecutive_changes` | 预览新增应收 `0.3350`，断言要求 `0.33` | 数量 1 → 2 后合同及有效计划均为 `0.67`，新增 `0.33`。再改为 3 后为 `1.01`。零差额不建计划，重放返回相同结果。 |
| `test_company_bank_fee_settlement_allows_increase_without_changing_cash` | 两条路径均返回 HTTP 400，提示核销 1000 与实收 980 不一致 | 直接收款、预收分配均返回 HTTP 201。合同 1100，净实收 980，手续费核销 20，待收 100。退款 40 后净实收 940，减量边界为 960。 |

数量变更按订单金额版本计算变更前后合同金额，保留交易单位、运费、折扣和已批准合同变更。资金校验按现有净实收口径核对已核销手续费，减量依据有效计划的未结余额，包含抹零或抵减及其更正。

## 定向验证

- SQLite，97 项，88 通过、9 条件跳过。
- 隔离 PostgreSQL 17.11，两次运行分别为 96 项和 1 项，全部通过。运行真实同版本并发及 CNY 银行退回后改量用例。两次均清理自建集群，残留测试库为空。
- 前端，`node --test src/components/OrderDetailModal.test.js`，7 项通过。`npm run build` 通过，有体积提示。
- 定向标签为 `crm.tests.test_order_quantity_adjustments`、`crm.tests.test_history_operational_contracts`、`crm.tests.test_cash_events`、`crm.tests.test_receipt_refund_attribution` 和 `crm.tests.test_finance_closeout.FinanceCloseoutTests.test_cny_bank_return_restores_receivable_atomically`。PostgreSQL 复现使用仓库现有 `docs/uat-evidence/core-business-closeout-20261105/run_postgres.py`，传入 PG17 的 `--pg-bin` 和对应 `--test-label`。

## Chrome 验收

用隔离运行器和 `codex` 验收身份，在有界面的真实 Chrome（1440 × 900）中完成两笔订单的预览、确认提交、关闭和重开。两次保存均返回 HTTP 201，重开时核对界面及订单工作台 API 的合同总额、计划金额、净实收和待收。

- 单价 0.335，数量 1 → 2。[预览](screenshots/CENTS-preview.png) · [重开后的回款状态](screenshots/CENTS-reopened.png)
- 到账 980、我方手续费 20，数量 10 → 11。[预览](screenshots/FEE-preview.png) · [重开后的回款状态](screenshots/FEE-reopened.png)

复现时从 `frontend` 运行 `node scripts/run-isolated-browser-tests.mjs --business-test small-team-quantity-finance-01.spec.js`，启用隔离验收账号和 Chrome channel。合成订单由本目录的 `seed.py` 创建，脚本写入前核对运行器的数据库和媒体身份。

GitHub Actions 的 CI 工作流适用于本分支推送。Linux operations acceptance 的推送分支清单不含本分支。[本分支 CI 记录](https://github.com/Johnson-Yiu/SJERP/actions/workflows/ci.yml?query=branch%3Acodex%2Fsmall-team-quantity-finance-01)

历史计划差额继续进入原有核对流程。本包验证使用合成订单、一次性数据库及媒体目录。后续交付事项见[小团队首发范围](small-team-launch-scope.md)。

## 独立复审补修

复审发现合同审批以原始变更额调整计划，当前版本的合同总额却按分舍入。销售合同审批现按变更前后完整合同总额求计划差额，保留原审批金额和旧版口径。舍入后零差额的审批仍留审计，API 返回 204。回归通过实际审批服务后再连续改量。

不同订单并发提交同一全局幂等键时，数据库唯一约束保留一笔成功，另一笔返回 HTTP 409。测试用两个数据库连接在插入前同步，验证仅有一笔订单版本和应收计划发生变化。另补银行退回后低于可调减边界的拒绝断言。
