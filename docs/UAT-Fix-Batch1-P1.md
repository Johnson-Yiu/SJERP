# Formal UAT Round 1 — Fix Batch 1 (P1)

基线：`master` `12e7022e56fbd50b7f2d18941a2fcc522237bc2f`  
范围仅限：`UAT-ORD-001`、`UAT-PKG-001`、`UAT-SHIP-001`、`UAT-SKU-001`、`UAT-ORD-004`。  
原始执行结果仍保留在 [UAT-Round1-正式业务全流程测试.md](UAT-Round1-正式业务全流程测试.md)，本记录不改写历史 FAIL/BLOCKED。

## 修复与复核

| UAT | 根因 / 当前判断 | 处理 |
| --- | --- | --- |
| UAT-ORD-001 | 转订单草稿弹窗把后端生成的 `order_no` 显示为必填输入；后端校验又明确拒绝客户端传入该字段。 | 改为只读“保存后由系统自动生成”，提交 payload 明确剔除 `order_no`。后端编号生成与报价状态规则不变。 |
| UAT-PKG-001 | SKU 编辑详情以空 `preview_key` 初始化；`detailFor` 在单 SKU 的预览 key 更新/未匹配时会造出新的空详情对象，使模板选择不在保存所用对象上；包装保存函数遇到空模板 ID 会直接跳过。 | 单 SKU 唯一详情行 key 未匹配时复用并重绑该对象，避免包装模板、重量与每箱数量丢失。包装 API 数据模型未变。 |
| UAT-SHIP-001 | 按现有 UAT 证据，本地未复现 500：在 SQLite 中构造 production/confirmed 订单、足额库存及等量预留后，经 `/api/orders/{id}/ship/` 提交页面同型 payload 返回 201。20 件两次部分发货、收货后库存恰等于预留的全量发货、库存不足事务回滚与全量重复提交均通过。`APIClient` 未抛异常，因此没有 traceback 可报告。根因尚未确认，不据此猜改发货逻辑。 | 无业务实现改动；补充复现/验收回归。需结合远端 `backend-postgres` CI；若仍无法复现，历史 BLOCKED 原因应视为当时服务异常待调查，而非本次已修复。 |
| UAT-SKU-001 | SKU serializer 只要求调用方确认身份变更，未检查已有 Quote、Order、Purchase Order 或库存流水引用；因此确认标志可绕过历史 SKU 身份保护。 | 身份参数或规格确有变化且存在上述业务历史时返回指定中文错误。未引用 SKU 仍可演化并创建 `SKUVersion`；内部名称/Sales Model 等展示变更仍可版本化，历史快照保持不变。产品与计量单位现有限制保留。 |
| UAT-ORD-004 | 页面对草稿编辑使用 PUT 且删除只读 `status`/`order_no`，保存成功时关闭弹窗、提示并刷新，失败时显示错误；与页面字段同型的后端 PUT 已返回 200 并持久化明细。此次未能在当前代码基线复现原 UAT 的静默失败。 | 无业务实现改动；增加页面保存反馈断言及 API 持久化/副作用回归，避免后续退化。草稿编辑不会生成付款计划、库存预留、报价修订或库存流水。 |

## 回归测试

- `test_reserved_production_order_can_ship_partially_through_api`：20 件订单连续两次发 10，校验 Shipment、sale_out、剩余预留、订单状态及重复全量请求不重复出库。
- `test_reserved_order_with_inventory_exactly_equal_to_reservation_can_ship_all`：通过采购收货形成库存与预留后全量发货。
- `test_insufficient_inventory_shipment_rolls_back_all_records`：库存不足返回 400，且不留下 Shipment、ShipmentItem 或 sale_out。
- `test_sku_packaging_template_and_overrides_persist_across_detail_reads`：SKU、包装档案及模板关联数持久化，并验证后续修改重量/箱数不清模板。
- Quote → 草稿测试覆盖 draft/sent/accepted 可转单、rejected/expired 仍拒绝、系统订单号、来源报价不变以及无正式副作用。
- 草稿订单页面同型 PUT 校验 SKU、数量、单价、总额持久化与零副作用。
- SKU 历史身份保护测试覆盖 Quote/Order 引用、身份拒绝、展示变更版本化以及旧快照不变；无业务历史参数变更的既有允许路径继续覆盖。
- 前端测试覆盖报价转单弹窗不要求/不传订单号、单 SKU 包装详情 key 更新时复用，以及草稿订单保存成功/失败反馈。

## 验证状态

- SQLite 完整后端套件：`459 tests` 通过，`10 skipped`（PostgreSQL 专用）。
- 聚焦后端模块：`132 tests` 通过。
- 前端 Node-only：`96 tests` 通过（新增断言计入后待最终复跑）。
- Vitest：`4 tests` 通过。
- Vite production build：通过；保留既有大 bundle 提示。
- `manage.py check`：通过。
- `makemigrations --check --dry-run`：`No changes detected`，无 migration。
- PostgreSQL 完整套件与 CI Run：待推送后记录。
