# R1-HIST-01 验收证据

本目录记录历史销售/采购订单隔离的本地验收结果。所有业务写入均发生在本工作区的隔离开发 SQLite 数据库；没有设置正式启用日期，没有转换既有订单，也没有修改 ISS-121 的定义或状态。

## 已验证范围

- 独立入口：`POST /api/orders/historical/`、`POST /api/purchase-orders/historical/`。
- 保存真实历史日期，状态固定为 `historical`，并以 `historical_only=true` 作为后端隔离标记。
- 普通销售订单/采购订单列表默认排除历史记录；历史列表必须显式请求 `status=historical`。
- 历史订单不生成应收/应付计划、收付款流水、库存预留、采购草稿或正式履约记录。
- 正式确认、生产、发货、到货、付款、退款、成本归属等入口对历史记录安全拒绝。
- 正式销售/采购报表排除历史记录；`/api/reports/historical/` 单独提供历史销售额、采购额、客户/供应商及 SKU 分析。
- 历史分析利润明确为“不计算”，不从缺失成本推导虚构利润。
- 旧迁移测试使用 0076/0077 对应历史模型，并在 `finally` 恢复测试开始时记录的最新迁移目标。

## 自动化结果

| 命令 | 结果 |
|---|---|
| `python manage.py test crm.tests.test_historical_orders --verbosity 2` | PASS，4/4，退出码 0（初次功能验证） |
| `python manage.py test crm.tests.test_cash_events.CashMigrationTests --verbosity 2` | PASS，1/1，退出码 0；SQLite 历史行哈希/Decimal 字段保持不变 |
| `python manage.py test crm.tests.test_historical_orders crm.tests.test_cash_events.CashMigrationTests --verbosity 2` | PASS，5/5，退出码 0（服务层防护补修后定向回归） |
| `python manage.py test --verbosity 1` | 最终 PASS，772 项，跳过 13 项，退出码 0（最终分析口径修正后 322.998s） |
| `python manage.py check` | PASS，退出码 0 |
| `python manage.py makemigrations crm --check --dry-run` | PASS，`No changes detected`，退出码 0 |
| `npm run test:unit` | PASS，138/138，退出码 0 |
| `npm run build` | PASS，退出码 0；保留既有大 bundle warning |

全量 SQLite 首次运行发现了历史迁移测试使用当前模型读取 0077 数据的问题（`crm_order.historical_only` 不存在）；该测试已改为使用 0076/0077 historical app state，并重新完成全量 772 项通过。该失败没有通过跳过、删除或弱化断言处理。

本机 `127.0.0.1:5432` 不可连接，因此未声称 PostgreSQL 本地通过；GitHub Actions 按项目策略保持 CI PENDING。

## 真实 Chrome 验收

Codex 内置 Chrome 连接到本工作区的真实 HTTP 服务 `http://127.0.0.1:5194/historical-orders`，完成了以下实际页面操作：

1. 历史销售订单：客户“Chrome历史客户”，日期 `2019-06-15`，SKU `CHROME-SKU`，数量 12，单价 80；保存成功，页面显示 ¥960.00、1 张订单、12 件。
2. 历史采购订单：供应商“Chrome历史供应商”，日期 `2020-05-20`，SKU `CHROME-SKU`，数量 20，单价 30；保存成功，页面显示 ¥600.00、1 张订单、20 件。
3. 页面保留“历史订单 · 仅用于经营分析”标签，并显示不生成应收、应付、采购或库存记录。
4. 页面提供分析日期范围，默认使用最近十年，避免 API 默认范围超过安全查询上限。

截图文件为真实 Chrome 页面捕获，未编辑或拼接：

- [销售历史分析页](screenshots/history-orders-chrome-full.png)
- [销售历史分析页首屏](screenshots/history-orders-chrome-1440.png)
- [采购历史分析页](screenshots/history-purchase-chrome-full.png)

操作日志与状态摘要见 [browser-steps.md](browser-steps.md)。

## 数据库与边界

- 新增迁移：`crm.0078_historical_contract_scope`，仅新增两个 `historical_only` 字段并扩展状态选项；不回填历史数据。
- 迁移已在 SQLite 完整升级至 0078；旧 0076/0077 迁移文件未修改。
- 历史主体、SKU 和金额使用当次录入的现有主档/行快照结构；不会把历史订单转为正式履约事实。
- 正式启用日期仍未配置。历史订单的受控更正页面、PostgreSQL 本地回归和 GitHub CI 仍待后续独立验收。
