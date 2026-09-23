# SKU 管理模块 AS-IS 架构与业务设计审核

审计范围：当前工作树的 Django 后端与 Vue 前端；未执行写入、迁移或接口调用。本文件描述代码当前实际行为，不将界面文案、注释或理想方案视为已实现能力。

标记说明：**【当前已实现】** 表示存在可追踪代码链路；**【当前未实现】** 表示在本项目中未找到对应 Model、逻辑或 UI；**【从代码推断】** 表示由字段/FK/默认 DRF 行为得到的结论。

## 1. SKU 数据模型

### 直接相关 Model / 表

| 实际 Model | 与 SKU 的关系 | 关键实现 |
|---|---|---|
| `Product` | SKU 所属产品主档；一个 Product 有多个 SKU | `SKU.product`，`related_name="skus"` |
| `ProductCategory` / `CategoryAttribute` | 分类定义可参与 SKU 内部显示名和销售型号的属性规则 | `include_in_sku`、`include_in_sales_model`、`uppercase` |
| `SKU` | 可报价、下单、库存核算的最小商品实体 | `backend/crm/models.py:248` |
| `SKUPackagingProfile` | SKU 一对一默认包装档案 | `SKU.packaging_profile` |
| `PackagingTemplate` | 可被多个 SKU 包装档案引用的纸箱模板 | `SKUPackagingProfile.packaging_template` |
| `QuoteItem` | 关联 SKU，同时保存报价时的 SKU 快照 | `sku=PROTECT` + 快照字段 |
| `OrderItem` | 关联 SKU，同时保存成交时的 SKU 快照 | `sku=PROTECT` + 快照字段 |
| `PurchaseOrderItem` | 关联 SKU，但没有 SKU 文本快照 | `sku=PROTECT` |
| `InventoryMovement` | 以 SKU 为粒度的出入库流水 | `sku=PROTECT` |
| `InventoryReservation` | 订单行对 SKU 的库存预留 | `sku=PROTECT` |
| `GoodsReceipt` | 采购明细到货，关联自动生成的库存流水 | 间接通过 `PurchaseOrderItem.sku` |
| `ShipmentItem`、`ShipmentPackageItem` | 发货和实际装箱引用 SKU | `sku=PROTECT` |
| `PackingPlanCartonItem` | 预计装箱明细，保存 SKU 编码/名称/重量快照 | `sku=PROTECT` + 3 个快照 |

`ProductAttribute`、`SKUAttribute` 不是实际 Model 名称。当前属性规则存于 `CategoryAttribute`；每个 SKU 的取值存为 `SKU.parameter_values` JSON，而非独立属性值表。

### SKU 完整字段表

`SKU` 继承 `TimestampedModel`，另有 `created_at`、`updated_at`（`backend/crm/models.py:10-12`）。必填性按 Django Model 的 `blank` / `null` 与默认值描述；`id` 为 Django 默认主键。

| 字段 | 类型 | 是否必填 | 是否唯一 | 默认值 | 用途 |
|---|---|---:|---:|---|---|
| `id` | AutoField | 是（系统） | 是 | 自动 | SKU ID / 主键 |
| `product` | ForeignKey(`Product`) | 是 | 否 | 无 | 产品 ID；删除 Product 时 `CASCADE` |
| `sku` | CharField(80) | 是（创建时后端可补） | 是 | `SKU-######` 分配 | 内部 SKU Code |
| `specification` | CharField(200) | 否 | 否 | `""` | 规格文本；前端由属性标签拼接后提交 |
| `display_name_cn` | CharField(300) | 否 | 否 | `""` | 内部中文显示名称 / SKU Name |
| `sales_model` | CharField(80), nullable | 否 | 是（非空值） | `NULL` | 对外商业型号 / Sales Model |
| `sales_model_abbreviations` | JSONField | 否 | 否 | `{}` | 参数值到 2–3 位型号缩写的映射 |
| `description_cn` | TextField | 否 | 否 | `""` | 中文描述 |
| `description_en` | TextField | 否 | 否 | `""` | 英文描述；报价默认优先使用 |
| `unit` | CharField(30) | 是 | 否 | `pcs` | 单位 |
| `cost_price` | Decimal(14,4) | 是 | 否 | `0` | SKU 默认成本 |
| `default_price` | Decimal(14,4) | 是 | 否 | `0` | SKU 默认售价 |
| `currency` | CharField(10) | 是 | 否 | `USD` | 默认售价币种 |
| `active` | BooleanField | 是 | 否 | `True` | 停用标记；列表默认过滤停用 SKU |
| `parameter_values` | JSONField | 否 | 否 | `{}` | 属性组合 / 参数快照 |
| `product_details` | JSONField | 否 | 否 | `[]` | 前端每个组合的产品名称、单位、备注、重量、整件数量等明细；Serializer 会剥离旧 `model/length/width/height` 键 |
| `image` | ImageField | 否 | 否 | 空 | SKU 图片 |
| `created_at` | DateTimeField | 系统 | 否 | 创建时 | 创建时间 |
| `updated_at` | DateTimeField | 系统 | 否 | 更新时 | 最近更新时间 |

重点字段归属：SKU ID=`id`；SKU Code=`sku`（API 另给只读别名 `sku_code`）；Sales Model=`sales_model`；内部名称=`display_name_cn`；Description 没有通用同名 SKU 字段，实际为 `description_cn` / `description_en`；条码字段**【当前未实现】**；Product ID=`product_id`；属性组合=`parameter_values`，缩写=`sales_model_abbreviations`。

## 2. Product → SKU 创建流程

**【当前已实现】** 前端 `SKUPage.vue` 让用户先选 Product，再读该产品主分类、上级分类和附加分类的 `effective_attributes`。只展示 `include_in_sku || include_in_sales_model` 的属性（`SKUPage.vue:35-39`），计算笛卡尔积，逐组合 `POST /api/skus/`（`SKUPage.vue:263-269`）。因此是“用户选择属性值、前端批量发起单个 SKU 创建请求”，不是后端一键批量生成接口。

```text
Product
  ├─ category / additional_categories
  │     └─ CategoryAttribute（排序、参与内部名、参与型号、大写规则）
  ▼
SKUPage 输入每个属性值及型号缩写
  ▼（前端计算属性值笛卡尔积）
每个组合 POST /api/skus/
  ▼
SKUSerializer.create
  ├─ allocate_sku_code() → SKU-000001…
  ├─ build_sku_identity()
  └─ sales model base + 全局序号 → PREFIX-缩写-1
  ▼
SKU + （可选）PUT /skus/{id}/packaging/ + 图片上传
```

1. SKU 不是完全手工创建，也不是单个后端批量生成：属性值和组合由用户/前端填选及展开；每个组合由 API 创建。
2. SKU Code：`sku_numbers.allocate_sku_code()` 锁定 `SKUCodeSequence` 后递增，候选格式 `SKU-{last_value:06d}`，并查询现有 SKU 避免碰撞（`backend/crm/sku_numbers.py:7-14`）。Model `save()` 和 Serializer `create()` 都会在未提供 `sku` 时补它。
3. SKU Name：`build_sku_identity()` 用 `Product.name` + 标记 `include_in_sku` 的参数值拼 `display_name_cn`；没有参与参数时退回规格或产品名（`sku_identity.py:72-105`）。但客户端/API 也可显式提交该字段，生成值只在空值时填充。
4. Sales Model **【当前已实现】**，字段是 `SKU.sales_model`。
5. 创建时：`Product.sales_model_prefix` + 按分类属性顺序拼接的、标记 `include_in_sales_model` 的缩写，形成 base；`SKUSerializer._allocate_sales_model()` 在 base 后加 `-1/-2…`（`serializers.py:406-425`）。没有参与型号的参数值或前缀时，不生成型号。已有测试验证 `COB320-6K-1/-2`（`test_sku_commercial_identity.py:47-67`）。
6. 参与型号的是 `CategoryAttribute.include_in_sales_model=True` 的属性；参与内部名的是 `include_in_sku=True`。大写由 `uppercase=True` 在生成名称/描述时应用。
7. 规则保存位置：`CategoryAttribute` 的三项布尔字段与 `sort_order`；每个值的缩写保存在 SKU 的 `sales_model_abbreviations` JSON。规则编辑 UI 位于 `CategoryPage.vue:97-160, 214-219`。
8. Product / CategoryAttribute 后续变化不会批量更新已有 SKU。SKU 更新时若提交 `product/specification/parameter_values/product_details`，Serializer 重算名称和双语描述；它明确跳过重算 `sales_model`（`serializers.py:427-437`）。直接改 Product 名称、prefix 或属性规则，没有 signal/任务回写 SKU。 
9. `sku` 与非空 `sales_model` 有唯一约束，故这两个字段不会重复；但没有 `(product, parameter_values)` 或“属性组合”唯一约束。相同属性组合可创建多个 SKU，只会取得不同 Code 和不同 Sales Model 序号。

## 3. SKU 修改逻辑与历史影响

| 用户修改对象 | 当前实际行为 | 历史单据影响 |
|---|---|---|
| SKU Name / `display_name_cn` | 专用 UI 没有直接输入框；提交属性变化时会自动重算，API 可直接写该字段 | QuoteItem / OrderItem 有自己的名称快照，不被回写；采购、库存展示实时读 SKU，可能变更显示 |
| Sales Model | 专用 UI 只读预览并不提交 `sales_model`；API Serializer 未设只读，直接 API 可写。属性更新时不会自动重算或更新型号 | 报价/订单保存 `sales_model_snapshot`，不变；采购和库存 Serializer `source="sku.sales_model"`，会显示新值 |
| `description_cn/en` | 专用 UI 无编辑字段；属性更新时在请求未显式提供描述时重算；API 可写 | QuoteItem 保存 `description`；OrderItem 保存 `description_snapshot`，均不变；采购/库存未保存描述快照 |
| SKU Attribute / `parameter_values` | `SKUPage.save()` PUT 提交新组合；重算内部名与双语描述，但保留 `sku` 与 `sales_model` | 同上；已存在 SKU 身份码与属性含义可能脱节 |
| Product Attribute / `CategoryAttribute` | 分类页面可新增、改名、删、改开关、排序；没有遍历 SKU 的回写逻辑 | 不修改已存在单据快照；影响后续 SKU 创建与现有 SKU 之后的再次编辑/重算 |
| Product 名称/英文名/prefix/分类 | 产品页面 PUT 可修改；没有 SKU 级联重算逻辑 | 同上；实时关联展示（如 `product_name`）可变化 |

快照结论：

- **【当前已实现】** QuoteItem：`sku_code_snapshot`、`sales_model_snapshot`、`product_name_snapshot`、`unit_snapshot`、`image_snapshot`；描述存于 `description`。创建入口为 `quote_snapshots.create_quote_items()`（`quote_snapshots.py:23-51`）。
- **【当前已实现】** OrderItem：`sku_code_snapshot`、`sales_model_snapshot`、`display_name_snapshot`、`description_snapshot`、`unit_snapshot`；从 QuoteItem 创建订单时优先复制报价快照（`serializers.py:643-658`）。
- **【当前未实现】** PurchaseOrderItem SKU 文本/型号/描述快照。它的 Serializer 始终从 `sku.sku/display_name_cn/sales_model` 读值（`serializers.py:94-103`）。
- **【当前未实现】** InventoryMovement SKU 文本/型号/描述快照。Serializer 同样回读实时 SKU（`serializers.py:908-912`）。
- **【当前已实现，范围有限】** PackingPlanCartonItem 保存 SKU 编码、名称、单位重量快照；不是 SKU 版本体系。
- **【当前未实现】** SKU Version History、SKU Alias / Old Model、SKU 修改日志 / 操作人审计。`created_at/updated_at` 仅记录时间，不能记录旧值或修改人。

报价有版本链（`Quote.root_quote/parent_quote/revision_no`），且已保存报价 `update()` 被拒绝、需创建 revision（`QuoteSerializer.update`, `serializers.py:589-590`）。这是**报价版本**，不是 SKU 版本。

## 4. SKU 被其他模块引用

```text
Product ──1:N──> SKU
                    ├─1:1──> SKUPackagingProfile ──N:1──> PackagingTemplate
                    ├─1:N──> QuoteItem          [FK + 文本/图像快照]
                    ├─1:N──> OrderItem          [FK + 文本快照]
                    ├─1:N──> PurchaseOrderItem  [FK，无 SKU 文本快照]
                    ├─1:N──> InventoryMovement  [FK，无 SKU 文本快照]
                    ├─1:N──> InventoryReservation
                    ├─1:N──> ShipmentItem / ShipmentPackageItem
                    └─1:N──> PackingPlanCartonItem [FK + 部分快照]

Customer ──1:N──> Quote / Order ──items──> SKU
```

| 模块 | 保存 `sku_id` | 复制 SKU 数据 | SKU 后续修改影响 |
|---|---:|---|---|
| Quotation / `QuoteItem` | 是，`PROTECT` | Code、Sales Model、产品名、单位、图片；`description` 为报价行描述 | **通常不影响**已保存报价；报价行还允许客户化型号/描述覆盖（`QuoteEditorModal.vue:157,210`） |
| Sales Order / `OrderItem` | 是，`PROTECT` | Code、Sales Model、内部名、描述、单位；还保存成交成本 | **不影响**已保存订单行；若从报价创建，复制报价行快照 |
| Purchase Order / `PurchaseOrderItem` | 是，`PROTECT` | 无 | **影响显示**：响应中的 Code/名称/型号均取实时 SKU |
| Inventory / `InventoryMovement` | 是，`PROTECT` | 无 | 数量不受改名影响；列表/详情中 Code、名称、型号会随 SKU 当前值变化 |
| Packaging | `SKUPackagingProfile.sku` 一对一 | Profile 保存包装模板 FK 与覆盖数值；模板本身无版本快照 | 修改模板或 profile 会改变后续 `packaging_summary()` / 新生成装箱计划；已有 PackingPlan 保存部分包装与 SKU 快照 |
| Customer | 无 SKU→Customer 直接 FK | 无 | 客户通过 Quote / Order 关联到商品；`ProductViewSet.customers` 是从 OrderItem 聚合的只读查询（`views.py:341-349`） |
| Shipment / Packing Plan | 是 | PackingPlan 明细有 SKU code/name/weight snapshot；ShipmentPackageItem 无 | 已确认发货数量按 FK 保留，显示依赖对应 Serializer；装箱计划重生会先删除同源计划再新建（`services/packaging.py:77-122`） |

## 5. 删除 / 停用规则

1. SKU API 是普通 `ModelViewSet`，未覆盖 `destroy`，专用页面确实 `DELETE /skus/{id}/`（`SKUPage.vue:283`）。因此未引用 SKU 是**物理删除**，非软删除。
2. `SKU.active` 可通过 UI 勾选关闭；SKU 列表默认隐藏，`include_inactive=1` 才列出（`SKUViewSet.get_queryset`, `views.py:364-370`）。这是可用的停用标记，但并未替代 DELETE，也没有“仅允许停用”的删除策略。
3. 如果 SKU 被 QuoteItem、OrderItem、PurchaseOrderItem、InventoryMovement、InventoryReservation、PackingPlanCartonItem、ShipmentItem 或 ShipmentPackageItem 使用，均有数据库层 `on_delete=PROTECT`，删除将被 FK 保护阻止。`SKUPackagingProfile` 是 `CASCADE`，无其他引用时会随 SKU 删除。
4. 被报价、订单、采购、库存或出入库流水使用时，按上述 `PROTECT` 理应不能删除；视图没有将 `ProtectedError` 转换为友好业务提示，**【从代码推断】** 客户端会收到框架错误响应而非专门规则说明。
5. SKU Code：前端无字段、列表亦未显示，但 `SKUSerializer` 只把 `sku` 标为“创建可省略”，未标只读（`serializers.py:367-370`）；因此 API 可改。测试还直接保存改过的 `sku` 用于验证报价快照（`test_quotes.py:421-425`）。
6. Sales Model：前端无直接编辑入口；Serializer 未限制，API 可改，且有唯一约束。
7. 关键属性：前端与 API 均允许改 `parameter_values`，分类页面还允许改规则/排序/删除属性。

主要完整性风险：对已存在 SKU 改 Code / Sales Model / 属性并不会回写历史报价和订单（这是快照保护），但会使采购、库存、部分发运的实时显示与当时业务含义不一致；同一 `sku_id` 的属性语义发生变化也会干扰追溯。

## 6. SKU 前端页面与用户路径

| 页面 / 组件 | 路径 | 调用 API | 用户动作 → 效果 |
|---|---|---|---|
| SKU 列表、新建、编辑、删除、图片、组合预览 | `/skus` → `SKUPage.vue` | `/skus/`、`/products/`、`/categories/tree/`、`/product-parameters/`、`/packaging-templates/`、`/suppliers/`、`/skus/{id}/image/`、`/skus/{id}/packaging/`、`/skus/sales-model-abbreviations/` | 新建打开 modal；属性值生成预览；保存逐组合 POST / PUT SKU，再可保存包装与图片；编辑/删除来自列表按钮 |
| 产品主档 | `/products` → `ProductPage.vue` | `/products/`、`/products/next-code/`、`/categories/tree/`、`/suppliers/` | 建立/修改 Product、销售型号前缀与分类；不自动创建/刷新 SKU |
| 分类/属性规则 | `/categories` → `CategoryPage.vue` | `/categories/`、`/categories/tree/`、`/category-attributes/`、`/category-attributes/reorder/` | 配置 SKU/型号参与属性、大小写和排序；没有“重算已有 SKU”按钮 |
| 包装模板 | `/sku-packaging` → `PackagingPage.vue` | `/packaging-templates/`、`/suppliers/`、`/skus/` | 管理模板，查看前端按 SKU 响应 `packaging.template` 过滤出的关联 SKU |
| SKU 库存汇总 / 关联单据 | `/inventory` → `InventoryPage.vue` | `/skus/?include_inactive=1`、`/skus/{id}/inventory-detail/` | 选 SKU 打开采购、发货、订单关联明细；没有 SKU 编辑 |
| 报价选择 SKU | `/quotes` → `DocumentPage.vue` → `QuoteEditorModal.vue` | 父页面提供 SKU 列表；保存 `/quotes/` 或 `/quotes/{id}/revise/`；可 PUT `/skus/{id}/packaging/` | 勾选 SKU 自动产生报价行；可改单行型号与描述；包装缺失时在报价 modal 内补 SKU 默认包装 |
| 订单选择 SKU | `/orders` → `DocumentPage.vue` → `OrderDraftModal.vue` | `/orders/`（SKU 列表由父页面传入） | 选 SKU 带入默认价格/成本，保存后写订单行快照 |
| 采购 SKU | `/purchase-orders` → `PurchaseOrderPage.vue` | `/purchase-orders/`、`/suppliers/`、`/orders/`、`/skus/`、`/purchase-orders/{id}/receive/` | 新建采购单选择 SKU；到货生成库存入库 |

```text
侧栏 SKU 管理 (/skus) ──> SKU 新建/编辑 modal ──> 包装内嵌 modal
产品管理 (/products) ──> Product 主档 ──>（用户手动进入）SKU 管理
产品分类 (/categories) ──> CategoryAttribute 规则 ──>（影响）SKU 新建/编辑计算
报价 (/quotes) ──> QuoteEditor SKU picker ──>（可内嵌）SKU 包装配置
订单/采购/库存 ──> 读取 SKU 或 SKU 关联明细
```

`SKUPage` 没有独立 SKU 详情路由；编辑即 modal。`ResourcePage` 虽保留一段旧的 `skus` 配置（`resourceConfigs.js:61-87`），router 明确排除了 `skus`，实际 `/skus` 使用专用 `SKUPage`（`router.js:20,28`）。

## 7. SKU API

API 基路径为 `/api/`（`config/urls.py:8`），路由注册在 `crm/urls.py:13-27`。权限默认 `AllowAny`（`config/settings.py:75-78`）；SKU、产品、分类、包装、库存与采购相关 ViewSet 未另设权限，因此以下接口当前无 SKU 专用权限控制。

| HTTP 接口 | View / Serializer / 服务 | 主要逻辑 |
|---|---|---|
| GET, POST `/api/skus/` | `SKUViewSet` / `SKUSerializer` | 列表统计库存、报价数、订单数；POST 在 Serializer 分配 code、生成名称描述和新型号 |
| GET, PUT, PATCH, DELETE `/api/skus/{id}/` | 同上 | 默认 DRF CRUD；更新身份字段时重算名称/描述、保持 Sales Model；DELETE 未覆写 |
| GET `/api/skus/sales-model-abbreviations/?category={id}` | `SKUViewSet.sales_model_abbreviations` | 从该分类及附加分类的既有 SKU JSON 中返回缩写建议 |
| GET `/api/skus/{id}/inventory-detail/` | `SKUViewSet.inventory_detail` | 返回按 SKU 聚合的采购、发货、订单上下文 |
| POST, DELETE `/api/skus/{id}/image/` | `SKUViewSet.image` / `SKUSerializer` | 图片 MIME 校验、保存或清除 |
| GET, PUT `/api/skus/{id}/packaging/` | `SKUViewSet.packaging` / `SKUPackagingProfileSerializer` / `packaging_summary` | 读取或 get-or-create SKU 包装档案；`verify` 请求值会写验证时间/当前用户 |
| GET, POST, PUT, PATCH, DELETE `/api/sku-packaging-profiles/…` | `SKUPackagingProfileViewSet` / `SKUPackagingProfileSerializer` | 独立 CRUD 已注册；专用前端未直接调用此 endpoint |
| `/api/products/…`、`/api/products/{id}/next-code/`、`/api/products/{id}/customers/` | `ProductViewSet` / `ProductSerializer` | Product CRUD、预览下一个 code、按订单聚合客户 |
| `/api/categories/…`、`/api/categories/tree/`、`/api/category-attributes/…`、`/api/category-attributes/reorder/` | Category / Attribute ViewSet + Serializer | 分类树、属性规则及顺序维护 |
| `/api/packaging-templates/…` | `PackagingTemplateViewSet` / `PackagingTemplateSerializer` | 包装模板 CRUD |
| `/api/purchase-orders/…`、`POST /{id}/receive/` | `PurchaseOrderViewSet` / `PurchaseOrderSerializer` / `record_receipt` | 创建采购 SKU 行；到货生成 `GoodsReceipt` 和 `InventoryMovement(purchase_in)` |
| `/api/inventory-movements/…` | `InventoryMovementViewSet` / `InventoryMovementSerializer` | 库存流水 CRUD；数量按 `signed_quantity` 计算 |

除 `create/update` 的 SKU 身份生成逻辑、包装 action、采购到货 action 和履约 service 外，普通 CRUD 大多直接在 DRF ViewSet / Serializer 中，没有独立 SKU domain service。

## 8. 当前实际架构图

```text
CategoryAttribute ──(规则)──> Product(category/additional_categories)
                                  │
                                  ▼
                               SKU
             ┌────────────────────┼─────────────────────────┐
             ▼                    ▼                         ▼
  SKUPackagingProfile       QuoteItem [snapshots]     OrderItem [snapshots]
             │                    │                         │
             ▼                    ▼                         ▼
 PackagingTemplate         Quote ─ Customer          Order ─ Customer
             │                                              │
             └────> PackingPlan snapshots                   ├─ PurchaseOrder ─ PurchaseOrderItem
                                                            ├─ InventoryReservation
                                                            ├─ ShipmentItem / ShipmentPackageItem
                                                            └─ InventoryMovement
```

## 9. 当前设计风险

### 严重

- **SKU 身份可变且缺少 SKU 版本/别名。** API 可改 `sku`、`sales_model` 和属性组合；属性变化又会重算名称/描述。采购、库存和部分发货依赖实时 SKU 显示，而非快照。历史发生过的业务可能被重新解释。
- **SKU 属性组合无数据库唯一约束。** `parameter_values` 是 JSON，数据库不校验 Product + 属性组合唯一；同一组合可多次创建，只靠不同 Code/型号序号共存，容易产生重复可销售项。
- **Product 删除路径危险。** `SKU.product` 是 `CASCADE`，没有明确的产品停用/删除服务规则；如果没有下游 `PROTECT` 引用的 SKU，删除 Product 会连带物理删除 SKU。引用存在时会受下游保护，但规则并非显式业务校验。

### 中等

- **Sales Model 的生成与后续编辑脱节。** 创建时由规则生成；修改属性、属性规则、Product prefix 后不会重算 `sales_model`。既有型号可能与当前属性值不一致。该行为有测试明确固定内部 code 与商业型号（`test_sku_commercial_identity.py:89-105`）。
- **快照覆盖不一致。** Quote/Order 保护较完整；PurchaseOrderItem 与 InventoryMovement 无 SKU 文本快照，历史列表受当前 SKU 名称、Code、型号影响。
- **包装模板不是历史版本。** `SKUPackagingProfile` 指向可编辑模板；除已生成 PackingPlan 的部分值快照外，旧报价预估、当前包装汇总和未来计划都会使用新模板值。
- **直接 API 权限默认 AllowAny。** SKU CRUD、图片、包装、库存等未在 ViewSet 指定权限，当前设置下无认证授权限制。
- **删除错误缺少业务处理。** 后端有 FK `PROTECT`，但 SKU delete 无捕获/友好提示，也无“已引用自动改停用”的统一流程。

### 轻微

- **前端与字段可见性不完整。** 专用 SKU 页面不展示 SKU Code，不能直接编辑 Sales Model / 双语描述 / `specification`，尽管 API 返回或允许这些字段。
- **界面文案可能误导。** 分类页把 `include_in_sku` 称为“参与 SKU 编码”（`CategoryPage.vue:214-218`），实际 `sku` Code 始终是 `SKU-######`；该规则参与的是内部显示名称/描述。
- **销售型号缩写建议跨同分类产品复用。** API 按分类收集既有 SKU 缩写，而非按 Product；同类产品会共享建议，虽属便利功能但可能引入不合适的缩写。

## 10. 前后端覆盖矩阵

| 功能 | 数据库/Model | 后端逻辑 | API | 前端调用 API | 前端页面/UI | 用户可访问 | 状态 |
|---|---|---|---|---|---|---|---|
| SKU 基本 CRUD | 已实现 | Serializer + 默认 ViewSet | 已实现 | 已调用 | 已实现 | 是 | 完整；DELETE 为物理删除 |
| 自动 SKU Code | 已实现 | `allocate_sku_code` | 随 POST | 间接调用 | 无手填 UI | 是 | 完整自动生成；Code 不在专用列表显示 |
| 自动 Sales Model | 已实现 | identity + 序号 | 随 POST | 间接调用 | 属性缩写与预览已实现 | 是 | 创建链路完整 |
| Sales Model 手工修改 | 字段已实现 | Serializer 可写 | PUT/PATCH 可写 | 未调用 | 无输入控件 | 否 | 后端可写、前端缺失 |
| 属性组合生成 | JSON 已实现 | identity 读取 JSON | SKU POST/PUT | 已调用 | 已实现 | 是 | 完整；前端逐条 POST，不是批量 API |
| 分类属性规则维护 | 已实现 | CategoryAttribute ViewSet | 已实现 | 已调用 | CategoryPage 已实现 | 是 | 完整；不回写已有 SKU |
| SKU 名称/双语描述自动生成 | 已实现 | `build_sku_identity` | 随 SKU POST/PUT | 间接调用 | 只预览名称，未直接编辑描述 | 部分 | 后端生成完整，前端描述编辑缺失 |
| SKU 图片 | 已实现 | image action MIME 校验 | POST/DELETE image | 已调用 | SKUPage 已实现 | 是 | 完整 |
| SKU 默认包装 | 已实现 | Profile + resolver | GET/PUT nested | PUT 已调用；GET 未见调用 | SKUPage、报价 modal | 是 | 部分完整；前端基于 list 响应展示，不读 nested GET |
| 独立 Profile CRUD | 已实现 | `SKUPackagingProfileViewSet` | 已注册 | 未调用 | 无专用 UI | 否 | 后端已实现、前端未接入 |
| 包装模板 CRUD | 已实现 | ViewSet / Serializer | 已实现 | 已调用 | PackagingPage | 是 | 完整 |
| SKU 库存汇总 | 已实现（流水） | `sku_metrics` / queryset 聚合 | `/skus/` | 已调用 | SKUPage / InventoryPage | 是 | 完整读取 |
| SKU 库存关联详情 | 无独立表（查询） | `inventory_detail` action | 已实现 | 已调用 | InventoryPage | 是 | 完整 |
| 报价 SKU 选择及快照 | 已实现 | Quote serializer + snapshot helper | `/quotes/`, revise | 已调用 | QuoteEditorModal | 是 | 完整 |
| 订单 SKU 选择及快照 | 已实现 | Order serializer snapshot helper | `/orders/` | 已调用 | OrderDraftModal | 是 | 完整 |
| 采购 SKU 选择 | 已实现 | PurchaseOrder Serializer | `/purchase-orders/` | 已调用 | PurchaseOrderPage | 是 | 完整；无 SKU 文本快照 |
| 采购到货 → 库存 | 已实现 | `record_receipt` | `receive` action | 已调用 | PurchaseOrderPage | 是 | 完整 |
| SKU 停用 | `active` 已实现 | list 默认过滤 | SKU PUT/PATCH | 已调用 | SKUPage checkbox | 是 | 完整；仍可经 API/已持有引用使用 |
| SKU 历史版本 / Alias / 审计 | 未实现 | 未实现 | 未实现 | 未调用 | 无 UI | 否 | 当前未实现 |

### Backend-only Features

- `/api/sku-packaging-profiles/` 的独立 CRUD：已注册 ViewSet，未发现前端调用；实际 UI 走 `/skus/{id}/packaging/`。
- `/api/skus/{id}/packaging/` 的 GET：后端提供 profile + effective 摘要；前端只发现 PUT，显示依赖 `/skus/` 返回的 `packaging` 摘要。
- SKU API 的直接 `sku`、`sales_model`、`display_name_cn`、`description_cn/en` 写入能力：Serializer `fields="__all__"`，但专用 UI 未提供对应输入。
- `/api/products/{id}/customers/`：后端按 OrderItem 聚合客户；未发现 SKU 前端路径调用。

### Frontend-only Features

- 未发现“只有 UI、没有后端 endpoint”的 SKU 主链路按钮。
- 需要注意：`CategoryPage` 的“SKU 编码规则预览”仅为前端文案/预览；后端实际 `sku` Code 不使用分类属性。这不是缺接口，而是 UI 命名与实现语义不同。

### Partially Integrated Features

- SKU 默认包装：Model、resolver、nested endpoint、SKU/报价 UI 都在；但 nested GET 未接入，且 `PackagingPage` 的关联 SKU 是客户端筛选 SKU list 的摘要字段，不是包装模板专门关联接口。
- SKU 编辑页回填包装搜索文本时读取 `row.packaging?.template_name`（`SKUPage.vue:207`），但后端 `packaging_summary()` 只返回 `template` 和 `effective_*` 字段（`services/packaging.py:65-70`），没有 `template_name`。模板 ID 可保留并正常提交，但编辑时该搜索文本为空，是已确认的 API 返回字段与前端读取字段不一致。
- SKU 字段展示/编辑：后端提供完整字段，专用 UI 只显示内部名、Sales Model、状态、库存、单位、售价、图片，并只提交部分字段。
- 停用：可设置与过滤，但所有引用模块并未显示检查 `SKU.active` 的创建限制；是否禁止用停用 SKU 创建报价/订单/采购，当前未实现。

### Fully Integrated Features

- Product/分类属性 → SKU 组合创建 → 自动 Code/型号 → 列表与编辑。
- SKU → QuoteItem 快照 → Quote revision / OrderItem 快照。
- SKU → PurchaseOrderItem → 到货 → InventoryMovement。
- SKU 包装默认值的创建/更新（由 SKU 页或报价 modal PUT nested endpoint）。

## 11. Key Files

### 后端

- `backend/crm/models.py`
  - `TimestampedModel`: L10-L16
  - `ProductCategory`, `CategoryAttribute`: L186-L216
  - `Product`, `SKU`, `SKUCodeSequence`: L224-L290
  - `PackagingTemplate`, `SKUPackagingProfile`: L292-L355
  - `QuoteItem`: L469-L495
  - `OrderItem`: L549-L574
  - `PurchaseOrderItem`: L643-L661
  - `PackingPlanCartonItem`, `ShipmentPackageItem`, `InventoryReservation`, `InventoryMovement`: L774-L859
- `backend/crm/sku_numbers.py` — `allocate_sku_code`
- `backend/crm/sku_identity.py` — `parameter_pairs`, `build_sku_identity`
- `backend/crm/serializers.py`
  - `PurchaseOrderItemSerializer` / `PurchaseOrderSerializer`: L94-L127
  - `ProductSerializer`: L314-L346
  - `SKUSerializer`: L349-L476
  - `QuoteItemSerializer` / `QuoteSerializer`: L518-L590
  - `OrderItemSerializer` / `OrderSerializer`: L593-L766
  - `SKUPackagingProfileSerializer`, `InventoryMovementSerializer`: classes at L831 / L908
- `backend/crm/views.py`
  - `PurchaseOrderViewSet.receive/pay`: L50-L88
  - `ProductViewSet`: L321-L349
  - `SKUViewSet`: L352-L468
  - `PackagingTemplateViewSet`, `SKUPackagingProfileViewSet`: L471-L489
  - `OrderViewSet` actions: `fulfillment`, `packing_plan`, `ship`, `workbench` at L807 onward
- `backend/crm/quote_snapshots.py` — `create_quote_items`
- `backend/crm/services/fulfillment.py` — `sku_metrics`, `allocate_order`, `record_receipt`, `confirm_shipment`
- `backend/crm/services/packaging.py` — `resolve_packaging`, `packaging_summary`, `generate_packing_plan`
- `backend/crm/urls.py` — DRF route registrations L8-L32
- `backend/config/settings.py` — REST default `AllowAny` L75-L78
- `backend/crm/tests/test_sku_commercial_identity.py` — SKU identity, generation and historical snapshot assertions

### 前端

- `frontend/src/router.js` — `/skus`, `/sku-packaging`, `/inventory`, `/purchase-orders` routes L20-L35
- `frontend/src/App.vue` — SKU/包装/库存侧栏入口 L20-L37
- `frontend/src/api.js` — axios base `/api` L1-L17
- `frontend/src/views/SKUPage.vue`
  - 属性组合/型号预览：`allPreviews` L106-L125
  - 加载、创建、编辑、保存、删除：L168-L302
  - SKU 列表及编辑 modal：L305-L319
- `frontend/src/views/ProductPage.vue` — Product prefix/category 编辑、SKU 非级联行为入口 L54-L117
- `frontend/src/views/CategoryPage.vue` — 属性规则 CRUD/reorder L67-L160、规则 UI L214-L219
- `frontend/src/views/PackagingPage.vue` — 模板 CRUD 与关联 SKU 前端筛选 L20-L38
- `frontend/src/views/InventoryPage.vue` — `/skus/` 汇总与 `inventory-detail` L73-L85
- `frontend/src/views/PurchaseOrderPage.vue` — SKU 采购、到货 L21-L24
- `frontend/src/components/QuoteEditorModal.vue` — SKU picker、报价行快照输入、包装配置 L80-L87、L155-L218
- `frontend/src/components/OrderDraftModal.vue` — SKU 选择与订单创建 L37-L76、L99-L102
- `frontend/src/resourceConfigs.js` — 未被 SKU 路由使用的旧 SKU resource config L61-L87
