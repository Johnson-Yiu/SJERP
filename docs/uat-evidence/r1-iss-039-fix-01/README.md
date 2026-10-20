# R1-ISS-039-FIX-01 权限安全补修验收

## 范围与基线

- 分支：`codex/r1-iss-039`
- 修复基线：`35d62b3d3761e53a8d3ccaca18a3c694037a6f92`
- 最终提交：由交付报告按最终分支 HEAD 核对
- 本轮没有合并或修改 R1-SKU-01、R1-MOQ-02、R1-INV-03、R1-PO-04，也没有修改成本分摊算法、数据库模型、历史采购/销售数据。

本轮只修复两条后端数据权限边界：采购专用订单选择接口改为必须拥有 `purchases.update`；成本分配只读摘要对无销售数据范围的订单隐藏 ID/订单号，保留金额、数量和明确的“销售订单（详情受限）”占位。授权采购员工仍可在没有 `orders.view/update` 的情况下完成跨销售订单成本归属。

## 实际自动化命令与结果

| 命令 | 实际结果 |
|---|---|
| `python manage.py test crm.tests.test_iss039_shared_purchase_costs crm.tests.test_procurement_data_scope --keepdb` | 16 tests，`OK`，退出码 0；包含 A/B/C/D、匿名、撤销 `purchases.update`、普通订单 API 作用域及无写入断言 |
| `python manage.py test --keepdb` | 首次运行 774 tests，1 个环境型 `backend/media` 写入 `PermissionError`，退出码 1；未出现本轮业务失败 |
| `python manage.py test --settings=r1_iss039_test_settings --keepdb` | 使用临时可写 `MEDIA_ROOT` 重跑 774 tests，`OK (skipped=13)`，退出码 0；Django system check 0 issues；临时设置文件未提交 |
| `npm run test:unit` | 137 tests，137 pass，0 fail，退出码 0 |
| `npx vite build --outDir C:\\Users\\Johnson\\AppData\\Local\\Temp\\r1-iss039-fix01-dist` | 2005 modules transformed，构建成功，退出码 0；仅有既有 chunk size warning。未删除受限的共享 `frontend/dist` |
| `Test-NetConnection 127.0.0.1 -Port 5432` | `TcpTestSucceeded=False`；本机 PostgreSQL 未监听，本轮未伪造 PostgreSQL 结果 |

## 权限回归矩阵

| 身份 | 订单选择接口 | 成本分配 GET | 订单标识可见范围 | 写入 |
|---|---:|---:|---|---:|
| A：`purchases.view/update`，无 `orders.view/update` | 200 | 200 | 采购分配所需的最小 ID/订单号 | 允许 |
| B：仅 `purchases.view` | 403 | 200 | 跨范围订单 ID/订单号隐藏，占位提示 | 拒绝 |
| C：`purchases.view` + 本人订单 `orders.view` | 403 | 200 | 本人订单保留，其他订单隐藏 | 拒绝 |
| D：无采购权限 | 403 | 403 | 无 | 拒绝 |
| 未登录 | 401/403 | 401/403 | 无 | 拒绝 |
| A 撤销 `purchases.update` 后 | 403 | 200、只读脱敏 | 全部跨范围标识隐藏 | 拒绝 |

回归同时确认：订单和客户普通 API 权限未放宽；采购金额、公共费用、归属数量、库存归属及既有分配记录未因拒绝请求改变；审计查询仍不暴露订单号或销售详情。

## 真实 Chrome 验收

隔离数据库：`backend/iss039-uat.sqlite3`。服务配置：`RBAC_ENFORCEMENT=true`、`DEVELOPMENT_SUPERADMIN=false`、`AUDIT_LOG_ENABLED=true`。通过真实 Chrome 的临时 Django admin session 分别登录采购员工 A 和只读采购员工 E。

实际观察：

1. A 打开 `ISS039-B-PO` 的“采购成本分配”，看到销售订单 A、B 和库存归属；页面只显示订单号及“不展示客户、售价或利润”的提示。
2. A 在普通桌面和 700px 窄屏下看到成本分配弹窗，弹窗内部可滚动，选择器和保存按钮未被隐藏或截断。
3. E 打开同一采购单详情，看到采购金额和成本分配说明，但没有成本分配编辑入口，也没有客户、售价或利润。

截图均来自真实 Chrome：

- [授权采购员工成本分配（1440px）](authorized-cost-allocation-1440.png)
- [授权采购员工成本分配（700px）](authorized-cost-allocation-700.png)
- [授权采购员工成本分配（700px 完整视图）](authorized-cost-allocation-700-full.png)
- [只读采购员工采购详情（1440px）](readonly-purchase-detail-1440.png)

## 代码与状态

- 变更文件：`backend/crm/procurement_scope.py`、`backend/crm/views.py`、`backend/crm/tests/test_iss039_shared_purchase_costs.py`、`frontend/src/components/PurchaseCostAllocationModal.vue`、`frontend/src/views/PurchaseOrderPage.test.js`。
- 不新增迁移；不修改普通销售订单权限；不修改成本金额、数量或历史业务记录。
- PostgreSQL 本地环境不可用；GitHub Actions 按项目额度策略保持 `CI PENDING`，本轮没有反复触发 CI。
- ISS-039 保持 `FIXED_PENDING_REVIEW`，等待 ChatGPT 独立代码、权限及视觉复审；不得自行标记 CLOSED。
