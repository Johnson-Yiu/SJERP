# R1-ISS-039 共享采购成本分摊验收

## 范围与基线

- 分支：`codex/r1-iss-039`
- 实施基线：`origin/master` / `25405e1b25ff8a218b67883acf489ada8a53e146`
- 本证据对应最终提交：以提交后的 Git SHA 为准
- 本轮未修改或合并 R1-SKU-01、R1-MOQ-02、R1-INV-03、R1-PO-04。

本轮只处理共享采购成本归属的最小权限边界、采购专用订单选择数据和成本分配审计记录。没有改变采购数量、付款、库存流水、历史销售单据、订单销售权限或财务统计口径。

## 已验证结果

1. 采购员工 A 只有 `purchases.view/update`，没有 `orders.view/update`，仍可把同一采购单的 10 件分配为：销售订单 A 3、销售订单 B 2、公司库存 5。
2. 成本分配订单选择接口只返回 `id`、订单号和状态，不返回客户、售价、合同金额或利润；页面只显示订单号，并明确提示销售详情受限。
3. 商品成本 3,000 / 2,000 / 5,000 CNY，公共运费 1,000 CNY 按采购金额比例分摊为 300 / 200 / 500 CNY；最终归属成本为 3,300 / 2,200 / 5,500 CNY。
4. 成本归属总量保持 10；保存后重新打开仍为 V1。修改成本归属没有新增付款计划、交易或库存流水。
5. 取消订单目标和过期版本均在服务层拒绝，事务回滚且不留下成功审计记录。
6. 成功修改写入 OperationLog 的标准 `before_data/after_data`，普通采购权限查询返回脱敏结果；客户和销售订单号不出现在该查询响应中。
7. 只读采购员工 E 的真实页面没有成本修改入口，也没有客户、售价或利润信息；直接写入权限由后端拒绝。

## 实际自动化命令与结果

| 命令 | 结果 |
|---|---|
| `python manage.py test crm.tests.test_iss039_shared_purchase_costs crm.tests.test_procurement_data_scope crm.tests.test_purchase_costs crm.tests.test_purchase_order_related_orders crm.tests.test_audit --verbosity 1` | 34 tests，`OK`，退出码 0 |
| `python manage.py test --verbosity 1` | 773 tests，`OK (skipped=13)`，退出码 0；Django system check 0 issues |
| `npm run test:unit` | 137 tests，137 pass，0 fail，退出码 0 |
| `npm run build` | 2005 modules transformed，构建成功，退出码 0；仅有既有 chunk size warning |
| `Test-NetConnection 127.0.0.1 -Port 5432` | `TcpTestSucceeded=False`；本机没有 PostgreSQL 服务，未伪造 PostgreSQL 通过 |

前端构建第一次以受限权限运行时仅因隔离 worktree 的 `dist` ACL 返回 EPERM；随后以受控权限重跑同一命令成功，未修改业务代码。

## 真实 Chrome 验收

使用隔离 SQLite 数据库 `backend/iss039-uat.sqlite3`，开启 `RBAC_ENFORCEMENT=true`、`DEVELOPMENT_SUPERADMIN=false`、`AUDIT_LOG_ENABLED=true`。采购员工和只读员工均为隔离测试账号，通过临时 Django admin session 登录；应用本身没有新增登录功能。

实际操作：

1. 采购员工 A 打开 `ISS039-B-PO`，进入“分配采购成本 / 公共费用”。
2. 选择订单 A、订单 B 和库存，输入 3 / 2 / 5；页面只展示订单号。
3. 添加公共运费 1,000 CNY，确认实时预览为 300 / 200 / 500。
4. 保存、关闭并重新打开，确认 V1、数量和费用分配保持不变。
5. 切换只读员工 E，确认页面不显示成本修改入口及销售敏感资料。
6. 在 700px 窄屏下确认弹窗可滚动、字段不产生横向溢出，订单选择器仍可操作。

截图均来自真实 Chrome 页面：

- [01-desktop-purchase.png](01-desktop-purchase.png)
- [02-desktop-cost-allocation.png](02-desktop-cost-allocation.png)
- [03-700px-cost-allocation.png](03-700px-cost-allocation.png)
- [04-readonly-no-sensitive-data.png](04-readonly-no-sensitive-data.png)

## 权限与审计边界

本轮实现的是采购成本归属专用授权，不授予 `orders.view` 或 `orders.update`，不放宽订单、客户、报价、财务模块权限。销售订单常规 API 仍按原权限拒绝；成本归属目标接口只提供完成采购分配所需的最小订单号信息。审计数据库层 append-only 仍属于既有 ISS-043 部署安全事项，不在本轮扩大。

## 状态

本地结果：`LOCAL PASS`。

PostgreSQL 本地不可用；GitHub Actions 按项目当前免费额度策略保持 `CI PENDING`，本轮没有反复触发 CI。

ISS-039 更新为 `FIXED_PENDING_REVIEW`，不标记 `CLOSED`。等待 ChatGPT 独立代码、权限、审计和视觉复审。
