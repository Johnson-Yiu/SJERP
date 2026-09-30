# Task I2 — 供应来源、交易单位、包装与销售规则

## 供应来源

- Supplier Candidate 与 SupplierSKU 是不同概念。Candidate 只表示供应商可能供应某 SKU；SupplierSKU 才是已经人工维护的真实采购身份。
- 系统不再自动创建 `AUTO-*` SupplierSKU。候选查询、供应能力、历史采购都不会制造供应来源主数据。
- 手工采购可以明确供应商但不选择 SupplierSKU。采购行会保留采购单供应商名称快照，其他供应来源快照字段为空。
- 若当前供应商对 SKU 有一个启用的真实 SupplierSKU，系统可以自动带入；多个启用来源仅在存在 preferred 来源时自动选择，否则要求用户明确选择。
- 销售订单自动采购仍要求 OrderItem 已有明确的 SupplierSKU；没有来源时采购计划保持阻断，不能以模糊供应商生成采购草稿。

## 交易单位

- SKU 基础单位始终是库存、发货和销售规则的唯一数量口径。
- Trade Unit 只负责交易换算，例如 `10m / roll` 换算为 `10m` 库存数量。
- Trade Unit 的定义创建后不可覆盖；规格变化应停用旧规格并创建新规格。
- Quote、Order、Purchase 等业务行保存自己的交易单位快照，后续停用或新增规格不会改写历史换算事实。

## 包装

- PackagingTemplate 提供共享物理包装资料；SKUPackagingProfile 提供 SKU 级关联和覆盖。
- 包装 verification 只代表当前有效配置。修改 Profile 的有效包装字段，或修改模板的物理包装参数，会清除关联 Profile 的验证状态；同一次保存后可重新确认最终配置。
- 模板名称、说明或供应商修改不会改变物理包装验证；物理模板修改不会改写已有 PackingPlan 的快照。
- 被 SKU Profile 引用的包装模板不能删除，应先替换关联关系或将模板停用。

## 销售规则

- SalesRule 当前只承担 MOQ，不包含折扣、客户等级价格、促销或复杂定价。
- MOQ 永远按 SKU 基础单位判断。卷、箱等交易单位会先换算为基础数量再校验。
- Product / filter 范围的规则保存时，会校验当前所有匹配且启用的 SKU 基础单位；没有当前匹配 SKU 时允许保存，报价运行时仍会再次保护。
- QuoteItem 保存当时命中的 SalesRule snapshot，后续修改、停用或删除规则不会改变历史报价。
