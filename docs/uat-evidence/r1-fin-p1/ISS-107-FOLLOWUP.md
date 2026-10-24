# ISS-107 财务金额口径区分复核

日期：2026-10-24

基线：`71ec4a4c2d860b9944624a1434d9d7580e9a6d38`

分支：`codex/iss-107-finance-labels`

## 结论

已确认缺陷只有两处显示元数据问题：`Transaction.rmb_amount` 的模型 `verbose_name` 仍为“实际人民币金额”，以及财务流水资源入口描述未明确人民币汇总为账面折算参考。财务概览、流水序列化标签、报表来源/指标、CSV、银行资金页面和历史共享报表配置在修复前已能区分两套口径，本轮未重构这些路径。

已修复：

- `rmb_amount` 模型元数据改为“账面人民币折算参考”，新增 `0081_transaction_rmb_reference_label`；数据库字段、API 键和数值精度不变。
- 财务流水入口文案明确“账面折算参考”，并指向银行实际人民币资金页面。
- 未修改 `income_rmb`、`expense_rmb`、`net_cash_rmb`、`rmb_amount`、`source=cash` 等稳定键；未修改 ISS-048 统计或权限逻辑。

## 同一批合成数据金额对比

| 事实/口径 | 金额 | 说明 |
|---|---:|---|
| USD 流水 | USD 100.0000 × 7.100000 = ¥710.0000 | 账面人民币折算参考 |
| CNY 流水 | CNY 250.0000 = ¥250.0000 | 账面人民币折算参考 |
| 账面收支合计 | ¥960.0000 | 财务概览、cash 报表和 CSV |
| 银行已确认人民币净额 | ¥705.00 | `ISS107-BANK-001`，按银行日期统计 |
| 禁止的混合值 | 不计算 | ¥960.00 与 ¥705.00 不相加冒充公司现金 |

在同一 SQLite 副本上先回退到 0080、记录业务金额，再前进到 0081、再次记录业务金额：before/after SHA-256 均为 `2c10f1295ccfb73c4f8c89773b37004f20d5f206732fee5e219ce02062f55fa7`。对比覆盖两笔 Transaction、银行事件、来源分配和旧共享报表配置；金额、汇率、状态和配置完全一致。

## API、导出和旧配置

- `/api/finance-dashboard/`：`income_rmb=960.0`、`net_cash_rmb=960.0`，basis=`book_rmb_reference`。
- `/api/actual-rmb-cash/`：`inflow=705.00`、`net=705.00`、count=`1`，basis=`bank_cash_confirmed_v1`。
- `source=cash` 报表：总额 `960.0`、2 笔；`source=actual_cash` 报表：总额 `705.0`、1 笔。
- CSV 分别输出“人民币折算参考金额”和“银行实际净额（人民币）”；不合并两列。
- 旧共享模板 `旧账面现金流配置` 原 `source=cash` / `metric=amount` 配置恢复成功，显示为“账面收支（人民币折算参考）”。

原始响应和 CSV 已在本轮隔离验证目录保留；浏览器截图路径如下：

- [财务概览截图](C:/Users/Johnson/.codex/visualizations/2026/10/23/01a1690a-0a0e-7b72-826e-17ae19ef53e2/iss107-finance.png)
- [财务流水截图](C:/Users/Johnson/.codex/visualizations/2026/10/23/01a1690a-0a0e-7b72-826e-17ae19ef53e2/iss107-transactions.png)
- [旧保存报表截图](C:/Users/Johnson/.codex/visualizations/2026/10/23/01a1690a-0a0e-7b72-826e-17ae19ef53e2/iss107-reports.png)
- [银行实际资金截图](C:/Users/Johnson/.codex/visualizations/2026/10/23/01a1690a-0a0e-7b72-826e-17ae19ef53e2/iss107-bank-cash.png)

## 测试

- 后端定向：16 项通过。
- 后端全量：857 项通过，13 项跳过；Django system check 无问题。
- 迁移：SQLite 全量迁移至 0081 通过；`makemigrations crm --check --dry-run` 显示 `No changes detected`。
- 前端 Node 单元：151 项通过。
- 财务/报表 Vitest：3 文件、12 项通过。
- 生产构建：Vite 8.2.0，2009 modules，构建通过；仅有既有大 chunk 警告。
- 真实 Chrome：财务概览、财务流水、报表中心旧配置、银行资金页面均观察到目标中文口径和分离金额。

状态：`FIXED_PENDING_REVIEW`。本轮不合并 master、不关闭 Issue，等待统一独立审查。
