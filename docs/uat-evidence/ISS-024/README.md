# ISS-024 采购来源推荐验收证据

## 范围与基线

- 项目：SUNJACK-ERP
- 任务：ISS-024 采购来源推荐
- 验收基线：`af018ac63cf71143d223b9f6db4a087707495693`
- 验收分支：`codex/iss-024-supplier-recommendation`
- 环境：独立 worktree、本地 SQLite、本地 Django API `127.0.0.1:8111`、Vite `127.0.0.1:5221`
- 说明：本记录是开发环境证据，不代表生产部署或生产安全验收。

## 先复现再修复

在基线代码上先运行了客户 A/B 历史采购场景：客户 B 的历史供应商为 B，SKU 全局首选为 A。基线的 `supplier_candidates.candidates(sku)` 没有客户上下文，采购来源选择器也按全局 SKU 候选恢复，因此客户 B 仍会得到全局 A 的推荐。这确认了“后端查询可拒绝/前端来源状态仍不准确”的同类问题存在，随后才实施客户+SKU 范围的修复。

修复后同一场景的 API 结果：

```text
GET /api/skus/1/supplier-candidates/?order=1
recommendation = supplier A, source = preferred

GET /api/skus/1/supplier-candidates/?order=2
recommendation = supplier B, source = customer_preference
candidates[0] = supplier B, recommendation_reason = 该客户此 SKU 的优先来源
candidates[1] = supplier A, recommendation_reason = SKU 全局首选来源
can_set_customer_preference = true（开发超级管理员）
```

客户 B 的候选返回不包含客户 A 名称或客户 A 订单号；客户偏好表使用 `(customer, sku)` 唯一约束，不会跨客户复用。

## 数据库证据

本地演示数据经 Chrome 操作客户 B 的订单行后查询得到：

```text
CustomerSupplierPreference:
  customer_id=2, sku_id=1, supplier_sku_id=2

SupplierSKU.is_preferred:
  supplier_id=1, sku_id=1, is_preferred=True
  supplier_id=2, sku_id=1, is_preferred=False

OrderItem #2:
  supplier_sku_id=2
  supplier_allocation_scope=customer_preferred
  supplier_allocation_source=historical_purchase

PurchaseOrderItem:
  supplier_sku_id=2
  supplier_name_snapshot=ISS-024 供应商 B
  unit_price=2.800000000000

SKU:
  sku=ISS024-UI-SKU
  cost_price=9.0000
```

这证明客户级优先来源没有改写 SKU 全局首选；本次采购价格使用 PO 的 `2.80`，SKU 内部参考成本 `9.00` 保持独立。

## 业务场景结果

| 场景 | 结果 |
|---|---|
| 新客户 / 无客户历史 | 使用启用中的 SKU 全局首选作为弱推荐，并显示推荐来源说明 |
| 客户 A/B 差异 | 客户 A 无历史时推荐 A；客户 B 有历史时优先 B；未泄露另一客户名称或订单号 |
| 一次性更换 | 默认“仅本次采购使用”，不创建 `CustomerSupplierPreference`，不修改全局首选 |
| 永久偏好修改 | “设为该客户此 SKU 今后优先来源”只更新客户+SKU 偏好，不影响其他客户或全局 SKU |
| 停用供应商 | 不进入自动推荐；历史偏好停用时返回明确“已停用”提示 |
| 无维护来源采购 | 允许手工采购，PO 保存供应商名称快照，不自动创建 SupplierSKU |
| 供应商更换 | 已有来源改选其他供应商时提示核对包装、LOGO、认证和供货特点差异 |
| 权限与敏感信息 | 客户上下文由订单数据范围校验取得；候选 payload 不返回其他销售员客户资料、售价或利润 |

## 浏览器证据

使用 Chrome Use 在真实 Chrome 中打开客户 B 订单 `ISS024-UI-SO-B` 的“采购与发货”页签，确认：

1. 供应商 B（客户历史采购）位于供应商 A（SKU 全局首选）之前。
2. 两个分配范围为独立单选项，默认选中“仅本次采购使用”。
3. 先保存 B 为当前来源，再改选 A，页面显示包装、LOGO、认证及供货特点差异提示。
4. 保存客户级优先来源后刷新，来源仍恢复为 B。

截图：

- [窄屏候选来源与客户推荐](./iss024-mobile-supplier-warning.png)
- [窄屏供应商更换风险提示](./iss024-mobile-supplier-warning-detail.png)

Chrome Use 桌面端截图已在验收过程中直接核验：右侧来源面板同时显示客户 B 历史推荐、全局首选弱推荐和两个独立分配选项；更换供应商警示也已直接显示。

## 自动化验证

```text
python manage.py test -v 1
Ran 867 tests in 381.121s
OK (skipped=13)

npm run test:unit
tests 151
pass 151
fail 0

npm run test:unit -- --test-name-pattern='supplier|Purchase|purchase|allocation'
tests 50
pass 50
fail 0

npm run build
Vite 8.2.0 build succeeded

python manage.py makemigrations crm --check --dry-run
No changes detected

补修后定向回归：

python manage.py test crm.tests.test_iss024_reproduction crm.tests.test_supplier_allocation -v 1
Ran 11 tests
OK

npm run test:unit
tests 151
pass 151
fail 0
```

ISS-039 成本归属规则、报表金额计算和核心采购查询引擎未修改。

## 交付限制

- 未合并 master。
- 未部署生产环境。
- 未关闭 Issue。
- 最终 commit SHA 以提交完成后的 Git 输出为准。
