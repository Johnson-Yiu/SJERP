# SupplierSKU / Supplier Item 实现报告

> 审核/实现日期：2026-09-03
>
> 本报告描述当前工作树中的真实实现。`SupplierSKU` 是供应商对内部 SKU 的采购侧映射，不是新的库存 SKU，也不替换现有 SKU 编号、Sales Model 或 SKU 参数组合规则。另已补充内部识别名称的大小写不敏感重复限制。

## [现状]

实现前，项目已有：

- `Supplier` Model，以及 `Product.suppliers` 多对多关系。
- `PurchaseOrder.supplier` 采购单级供应商。
- `PurchaseOrderItem.sku` 采购行内部 SKU。
- `PackagingTemplate.supplier` 包装模板级供应商。
- `SKU` 作为销售、库存和采购统计的内部主对象。

实现前没有表示“同一个内部 SKU 在某个供应商处的型号、编码、条码和采购参考价”的中间实体；采购行也没有 `supplier_sku` 外键。现有 `/suppliers` 前端入口是通用 `ResourcePage`，没有独立的 Supplier Detail Component。

## [本次已实现]

### 0. 内部识别名称重复限制

当前用户看到的“内部识别名称”对应 `SKU.display_name_cn`。它原本不是数据库唯一字段；现已增加：

- `SKU.display_name_key`：不可编辑的规范化键。
- 规范化规则在 `backend/crm/sku_identity.py:12` 的 `normalize_display_name()`：`casefold()`、去首尾空格并折叠连续空格。因此 `Manual V`、`manual v` 和 `MANUAL V` 的比较键相同。
- `SKUSerializer._ensure_unique_display_name()` 会在新建、显式修改名称、以及由 SKU 属性重新生成名称时检查现有记录；重复时返回 `display_name_cn` 字段错误，不保存数据。
- `sku_display_name_key_unique` 数据库部分唯一约束保护所有已经有规范化键的干净记录，空键用于兼容迁移前已经存在的冲突记录。
- Migration：`backend/crm/migrations/0035_sku_display_name_key_sku_sku_display_name_key_unique.py`。

迁移前检查当前本地库发现 30 个 SKU 中已有 8 组内部名称冲突。Migration 只为没有冲突的历史名称回填 `display_name_key`；已有冲突记录保留原名称、不静默改名，以避免历史业务标签被擅自改变。新建和改名 API 仍会把这些历史名称视为占用并拒绝重复输入。后续如果要清理现有冲突，需要业务人员提供明确的改名对应关系。

SKU 编辑页面的生成名称仍经后端校验；`frontend/src/views/SKUPage.vue` 已将保存异常转换为后端字段错误，因此用户会看到“内部识别名称已存在（不区分大小写）”，而不是只有通用请求失败。

### 1. SupplierSKU 数据模型

新增 `backend/crm/models.py:626` 的 `SupplierSKU`：

| 字段 | 类型 | 必填 | 默认值 | 约束/用途 |
|---|---|---:|---|---|
| `id` | `BigAutoField` | 是 | 自动 | 中间实体主键 |
| `supplier` | `ForeignKey(Supplier)` | 是 | 无 | 供应商；`PROTECT`，反向名 `supplier_skus` |
| `sku` | `ForeignKey(SKU)` | 是 | 无 | 内部 SKU；`PROTECT`，反向名 `supplier_skus` |
| `supplier_model` | `CharField(120)` | 否 | `""` | 供应商型号 |
| `supplier_product_name` | `CharField(200)` | 否 | `""` | 供应商产品名称 |
| `supplier_sku_code` | `CharField(100)` | 是 | 无 | 供应商侧 SKU/物料编码 |
| `supplier_barcode` | `CharField(100)` | 否 | `""` | 供应商条码 |
| `purchase_price` | `DecimalField(14,4)` | 是 | `0` | 参考采购价；不能为负 |
| `currency` | `CharField(10)` | 是 | `USD` | 参考采购价币种 |
| `moq` | `DecimalField(14,2)` | 是 | `0` | 最小起订量；`0` 表示未设置/不限制 |
| `lead_time_days` | `PositiveIntegerField` | 是 | `0` | 参考交期；单位为天 |
| `is_active` | `BooleanField` | 是 | `True` | 是否允许在采购选择器中使用 |
| `is_preferred` | `BooleanField` | 是 | `False` | 是否为该内部 SKU 的首选供应来源 |
| `remarks` | `TextField` | 否 | `""` | 供应商来源备注 |
| `created_at` | `DateTimeField`（继承 `TimestampedModel`） | 是 | 自动 | 创建时间 |
| `updated_at` | `DateTimeField`（继承 `TimestampedModel`） | 是 | 自动 | 修改时间 |

数据库约束：

- `supplier_supplier_sku_code_unique`：同一个 `supplier` 下，`supplier_sku_code` 不可重复。不同供应商可以使用相同的供应商编码。
- `active_preferred_supplier_sku_unique`：同一个内部 `sku` 最多一个同时满足 `is_active=True`、`is_preferred=True` 的来源。
- `supplier_sku_purchase_price_non_negative`、`supplier_sku_moq_non_negative`：价格和 MOQ 不得小于 0。

没有添加供应商侧版本表、Alias 表、采购价历史表或 SupplierPackagingProfile。

### 2. 采购行和库存流水扩展

`backend/crm/models.py:713` 的 `PurchaseOrderItem` 新增：

- `supplier_sku`：可空 `ForeignKey(SupplierSKU)`，`PROTECT`，反向名 `purchase_items`。可空是为了兼容历史采购方式和未配置供应商来源的采购。
- `supplier_name_snapshot`、`supplier_model_snapshot`、`supplier_sku_code_snapshot`、`supplier_barcode_snapshot`：采购行创建时保存供应商来源快照。

采购行的 `unit_price` 仍然是采购单实际采用的行单价，不会因后续修改 `SupplierSKU.purchase_price` 而变化。

`backend/crm/models.py:924` 的 `InventoryMovement` 新增可空 `supplier_sku`：

- `purchase_in` 由 `backend/crm/services/fulfillment.py:134` 的 `record_receipt()` 创建时，写入 `purchase_item.supplier_sku`。
- `sku` 仍是必填且仍是库存核算粒度；供应商来源只是可选追踪字段。
- 该字段使用 `SET_NULL`，但 `SupplierSKUViewSet.destroy()` 会在有库存流水时拒绝 API 删除，因此正常业务入口不会丢失来源追踪。

### 3. Migration

新增并已应用：

- `backend/crm/migrations/0034_purchaseorderitem_supplier_barcode_snapshot_and_more.py`
- `backend/crm/migrations/0035_sku_display_name_key_sku_sku_display_name_key_unique.py`

`0034` 只新增 SupplierSKU 字段、模型和数据库约束，没有根据现有 `Product.suppliers` 自动猜测并生成 `SupplierSKU` 数据，也没有改写历史采购行。历史采购行的新增供应商快照字段保持空值，除非之后发生明确的数据编辑/补录。`0035` 为无冲突的既有内部名称回填规范化键，冲突名称保留为空键以兼容已有数据。

## 业务链路

### SupplierSKU 维护链路

```text
已有 Product / 内部 SKU
        │
        ▼
SKU 管理 / 编辑 SKU（/skus）
        │  GET /api/supplier-skus/?sku=<内部SKUID>
        ▼
Supplier Sources 区域
        │  POST/PATCH /api/supplier-skus/
        ├── 绑定 Supplier
        ├── 填供应商型号、供应商 SKU Code、条码
        ├── 填参考采购价、币种、MOQ、交期
        └── 设为启用/首选
```

`SupplierSKU` 不自动生成。用户必须选择供应商并填写 `supplier_sku_code`。创建、修改和设首选的业务锁与互斥逻辑在 `backend/crm/services/supplier_sku.py`：

- `create_supplier_sku()`：创建时锁定内部 SKU。
- `update_supplier_sku()`：更新时锁定目标内部 SKU，并在需要时取消该 SKU 的其他首选来源。
- `set_preferred_supplier_sku()`：启用并设为首选，同时取消其他首选来源。

该链路不会写入或重新生成 `SKU.sku`，也不会修改现有 `SKU.sales_model` 生成规则。

### 采购链路

```text
选择采购单 Supplier
        │
        ▼
选择内部 SKU
        │
        ▼
GET /api/supplier-skus/?supplier=<id>&sku=<id>&is_active=1
        │
        ▼
选择可选 Supplier Source
        │
        ├── 前端带出 purchase_price 作为参考值
        ├── 用户仍可编辑 unit_price
        └── POST /api/purchase-orders/
                    │
                    ▼
          PurchaseOrderItem.supplier_sku
          + 供应商名称/型号/编码/条码快照
                    │
                    ▼
          到货 record_receipt()
                    │
                    ▼
          InventoryMovement.sku
          + InventoryMovement.supplier_sku（可选追踪）
```

`PurchaseOrderSerializer.validate()` 会拒绝：

- Supplier Source 不属于当前采购单 `supplier`。
- Supplier Source 对应的内部 SKU 不等于当前采购行 `sku`。
- 新建采购单选择已停用的 Supplier Source。

未选择 `supplier_sku` 时不阻断采购单创建，保留原有兼容路径。

## API

### 主接口

路由注册位置：`backend/crm/urls.py:17`。

| HTTP | Endpoint | View/Controller | Serializer | Service/业务逻辑 |
|---|---|---|---|---|
| `GET` | `/api/supplier-skus/` | `SupplierSKUViewSet.list` | `SupplierSKUSerializer` | 支持 `sku`、`supplier`、`is_active`、`is_preferred` 过滤；也支持 DRF search |
| `POST` | `/api/supplier-skus/` | `SupplierSKUViewSet.create` | `SupplierSKUSerializer.create` | `create_supplier_sku()`；数据库唯一约束防重复 |
| `GET` | `/api/supplier-skus/{id}/` | `SupplierSKUViewSet.retrieve` | `SupplierSKUSerializer` | 返回供应商侧字段及内部 SKU 展示字段 |
| `PATCH/PUT` | `/api/supplier-skus/{id}/` | `SupplierSKUViewSet.update` | `SupplierSKUSerializer.update` | `update_supplier_sku()`；首选来源互斥 |
| `DELETE` | `/api/supplier-skus/{id}/` | `SupplierSKUViewSet.destroy` | 无 | 被采购行或库存流水引用时返回 `400`，否则允许物理删除 |
| `POST` | `/api/supplier-skus/{id}/set-preferred/` | `SupplierSKUViewSet.set_preferred` | `SupplierSKUSerializer` | `set_preferred_supplier_sku()` |

### 关联接口

| Endpoint | 当前行为 |
|---|---|
| `GET /api/skus/{id}/supplier-skus/` | 返回某个内部 SKU 的全部供应商来源，见 `SKUViewSet.supplier_skus()`（`backend/crm/views.py:458`）。 |
| `GET /api/suppliers/{id}/supplier-skus/` | 返回某个供应商的来源清单，见 `SupplierViewSet.supplier_skus()`（`backend/crm/views.py:50`）。 |
| `GET /api/skus/?search=<term>` | `SKUViewSet.filter_queryset()` 同时搜索内部字段和 `supplier_skus__supplier_model`、`supplier_skus__supplier_sku_code`、`supplier_skus__supplier_product_name`、`supplier_skus__supplier_barcode`，返回内部 SKU。 |

### 权限

项目当前 `DEFAULT_PERMISSION_CLASSES` 是 `AllowAny`；本次没有增加 SupplierSKU 专属权限，保持现有模块行为。代码位置为 `backend/config/settings.py` 的 REST Framework 配置。

## 前端页面和用户操作

### SKU 页面

- 路由：`frontend/src/router.js:28`，`/skus` → `SKUPage`。
- Component：`frontend/src/views/SKUPage.vue`。
- API Client：`frontend/src/api.js:3` 的 Axios `api`，`baseURL` 为 `/api`。
- Supplier Sources 状态与表单：`SKUPage.vue:28-29`。
- 打开已有 SKU 编辑时调用 `loadSupplierSources()`，请求 `/supplier-skus/?sku=...`。
- 编辑弹窗的 `Supplier Sources` 区域位于 `SKUPage.vue:354`，可添加、编辑、设首选、启用/停用。
- 保存函数 `saveSupplierSource()` 位于 `SKUPage.vue:229`，调用 `POST` 或 `PATCH /supplier-skus/{id}/`。
- “设为首选”调用 `POST /supplier-skus/{id}/set-preferred/`；停用调用 `PATCH`，并显式取消首选状态。
- 本次没有在页面提供供应商来源删除按钮，避免用户误删已被业务记录引用的来源；删除保护仍在后端 API。

新建 SKU 弹窗不会同时自动创建 SupplierSKU。因为新 SKU 可能还没有供应商物料编码，来源必须在已有内部 SKU 下明确维护。

### 采购页面

- 路由：`frontend/src/router.js:35`，`/purchase-orders` → `PurchaseOrderPage`。
- Component：`frontend/src/views/PurchaseOrderPage.vue`。
- 选择供应商或内部 SKU 后，`loadSupplierSkuOptions()`（`PurchaseOrderPage.vue:26`）请求：
  `/supplier-skus/?supplier=<supplier>&sku=<sku>&is_active=1`。
- 供应商来源下拉框只显示启用来源；选择后 `applySupplierSkuPrice()`（`PurchaseOrderPage.vue:33`）把 `purchase_price` 作为初始 `unit_price`，用户仍可改写。
- 如果当前供应商 + 内部 SKU 只有一条启用来源，前端会自动选中该来源并带入参考采购价；多条来源则要求用户选择。
- `createPurchase()`（`PurchaseOrderPage.vue:35`）提交 `supplier_sku`；未选择时提交 `null`，因此旧流程仍可用。
- 采购详情行显示 `supplier_name`、`supplier_model`、`supplier_sku_code` 快照，见 `PurchaseOrderPage.vue:46`。

### 供应商页面

- 入口：`frontend/src/App.vue:19`，`/suppliers`。
- 当前是 `ResourcePage` + `resourceConfigs.js` 的通用供应商目录，没有 Supplier Detail Component。
- 本次没有新增大规模供应商页面；供应商反查能力通过后端 `/api/suppliers/{id}/supplier-skus/` 提供，当前前端尚未有 UI 入口。

### 包装页面

当前包装仍按内部 SKU 使用 `SKUPackagingProfile` / `PackagingTemplate`。`PackagingTemplate.supplier` 仍是包装模板级字段；本次没有把包装绑定到 `SupplierSKU`，也没有新增 `SupplierPackagingProfile`。

## 历史数据和删除规则

### 历史采购

采购行会同时保存：

- 当前关系：`PurchaseOrderItem.supplier_sku`。
- 创建时快照：`supplier_name_snapshot`、`supplier_model_snapshot`、`supplier_sku_code_snapshot`、`supplier_barcode_snapshot`。
- 实际采购价格：`PurchaseOrderItem.unit_price`。

因此修改 SupplierSKU 的当前型号、编码、条码或参考价，不会改写已经创建的采购行快照和实际采购单价。当前没有 SupplierSKU 自身的 Version History、Alias 或修改日志。

### 库存和到货

- 库存数量仍按 `InventoryMovement.sku` 汇总。
- 采购到货生成的 `InventoryMovement` 会额外保存 `supplier_sku` 来源关系。
- 销售出库、手工调整等非采购流水可以不填写 `supplier_sku`。
- `GoodsReceipt` 仍通过 `purchase_item` 关联供应商来源，未增加冗余供应商字段。

### 删除/停用

- SupplierSKU 没有 `deleted_at` 软删除字段；停用由 `is_active=False` 表示。
- API 删除如果已有 `purchase_items` 或 `inventory_movements`，返回 `400` 并要求停用。
- `PurchaseOrderItem.supplier_sku` 使用 `PROTECT`。
- `SupplierSKU.supplier`、`SupplierSKU.sku` 使用 `PROTECT`。
- 数据库 FK 可以防止直接删除被 `PurchaseOrderItem` 引用的 SupplierSKU；库存字段本身是 `SET_NULL`，因此应用层的 `destroy()` 检查对保留库存来源追踪很重要。
- 修改 `supplier_sku_code` 当前仍被 API 允许。历史采购行不受影响，因为有快照；当前来源记录会变成新编码。

## 前后端覆盖矩阵

| 功能 | 数据库/Model | 后端逻辑 | API | 前端调用API | 前端页面/UI | 用户可访问 | 状态 |
|---|---|---|---|---|---|---|---|
| 内部识别名称大小写不敏感去重 | `SKU.display_name_key` + 部分唯一约束 | `SKUSerializer._ensure_unique_display_name()` | SKU POST/PATCH | SKU 页面保存链路 | 编辑/生成时显示后端错误 | 是 | 完整；既有冲突保留为历史例外 |
| SupplierSKU 基础实体 | 已实现 `SupplierSKU` | 已实现 Service + DB 约束 | 已实现 CRUD | SKU 页面已调用 | SKU 编辑弹窗有 Supplier Sources | 是 | 完整 |
| 同供应商编码去重 | 唯一约束 | Serializer/DB 校验 | POST/PATCH 返回错误 | 保存时可显示错误 | 表单保存 | 是 | 完整 |
| 同一内部 SKU 多供应商 | `SupplierSKU.sku` FK | 已实现 | `sku` 过滤 | SKU 页面加载 | 来源列表 | 是 | 完整 |
| 首选供应来源 | 条件唯一约束 | `set_preferred_supplier_sku()` | `set-preferred` + PATCH | 已调用 | “设为首选” | 是 | 完整 |
| 来源启用/停用 | `is_active` | 停用时清除首选 | PATCH | 已调用 | “启用/停用” | 是 | 完整 |
| SupplierSKU 编辑 | 已实现字段 | `update_supplier_sku()` | PATCH/PUT | 已调用 | 编辑来源弹窗 | 是 | 完整 |
| SupplierSKU 物理删除保护 | FK + 反向引用 | `SupplierSKUViewSet.destroy()` | DELETE | 未调用 | 无删除按钮 | 仅 API | 后端已实现，UI 有意不提供删除 |
| SKU 搜索供应商型号/编码 | `supplier_skus` 反向关系 | `SKUViewSet.filter_queryset()` | `/api/skus/?search=` | SKU 页面已有搜索调用 | 搜索框 | 是 | 完整，但占位文案未显式写供应商字段 |
| 供应商反查来源 | 反向关系 | `SupplierViewSet.supplier_skus()` | `/api/suppliers/{id}/supplier-skus/` | 当前未调用 | 无 Supplier Detail UI | 否 | 后端-only |
| 采购单选择供应商来源 | `PurchaseOrderItem.supplier_sku` | 供应商/SKU/启用状态校验 | `/api/supplier-skus/` + `/api/purchase-orders/` | 已调用 | 采购明细来源下拉框 | 是 | 完整 |
| 采购参考价建议 | `SupplierSKU.purchase_price` | 后端不自动覆盖 `unit_price` | 返回参考价 | 前端选择时带入 | 可编辑采购单价 | 是 | 部分：前端便利逻辑，非服务端默认规则 |
| 采购行供应商快照 | 4 个 snapshot 字段 | Serializer create + Model save | 采购单返回快照 | 已调用读取 | 采购详情显示 | 是 | 完整 |
| 采购到货供应商追踪 | `InventoryMovement.supplier_sku` | `record_receipt()` 写入 | 库存流水 API 返回字段 | 现有库存页面未展示该字段 | 无来源展示控件 | 部分 | 后端已实现，库存 UI 未展示来源 |
| 库存按内部 SKU 汇总 | `InventoryMovement.sku` | 既有库存统计逻辑 | 既有库存 API | 既有库存页面 | 库存数量/流水 | 是 | 完整；供应商来源不改变库存粒度 |
| SupplierSKU 专属版本历史 | 无 | 无 | 无 | 无 | 无 | 否 | 当前未实现 |
| SupplierSKU Alias/旧编码 | 无 | 无 | 无 | 无 | 无 | 否 | 当前未实现 |
| SupplierSKU 批量导入 | 无专用 Model/API/UI 链路 | 无 | 无 | 无 | 无 | 否 | 当前未实现 |
| SupplierPackagingProfile | 无 | 无 | 无 | 无 | 无 | 否 | 当前未实现；包装仍按 SKU 默认配置 |

## Backend-only Features

- `GET /api/suppliers/{id}/supplier-skus/` 供应商反向查询接口；当前没有 Supplier Detail 页面调用它。
- `SupplierSKUViewSet.destroy()` 的引用保护策略；前端不提供删除按钮，但 API 和数据库会执行保护。
- 内部识别名称的规范化键、API 重复校验和部分数据库唯一约束；前端只展示后端校验结果。
- `InventoryMovement.supplier_sku` 的供应商来源追踪字段；到货服务已写入，但当前库存页面没有展示该字段。
- SupplierSKU 的数据库条件唯一约束和行锁互斥逻辑；前端只触发保存/设首选，不直接实现并发一致性。

## Frontend-only Features

本次没有新增“只有前端、后端不支持”的功能。新增按钮均对应现有后端 endpoint：

- 添加/编辑来源 → `POST/PATCH /api/supplier-skus/`。
- 设首选 → `POST /api/supplier-skus/{id}/set-preferred/`。
- 启用/停用 → `PATCH /api/supplier-skus/{id}/`。
- 采购来源筛选 → `GET /api/supplier-skus/`。

## Partially Integrated Features

1. 供应商反查：Model、View、Serializer、API 已完成，但当前 `/suppliers` 是通用目录，没有 Supplier Detail UI 和路由入口。
2. 采购参考价：前端选择 SupplierSKU 后填入采购行 `unit_price`；后端只保存用户提交的 `unit_price`，不在服务端根据 `purchase_price` 自动补价。直接调用 API 的客户端仍需自己提交 `unit_price`。
3. 到货后的供应商来源：后端写入 `InventoryMovement.supplier_sku`，但现有库存流水页面没有展示或筛选供应商来源。
4. SupplierSKU 自身变更审计：当前采购历史有快照，但没有 SupplierSKU Version History、Alias 或变更日志。

## Fully Integrated Features

- SKU 编辑页维护 SupplierSKU：SKU 页面 → Axios API Client → SupplierSKU ViewSet → Serializer → Service → Model/DB。
- 同一内部 SKU 绑定多个供应商来源，并按供应商来源编码去重。
- 首选来源互斥：SKU 页面操作 → set-preferred endpoint → SKU 行锁 + 取消其他首选 → 条件唯一约束。
- 采购来源选择：采购页面选择 Supplier + 内部 SKU → 过滤启用来源 → 选择来源 → 参考价可编辑 → PurchaseOrder API 校验 → PurchaseOrderItem 关系和快照。
- 采购到货：PurchaseOrderItem → `record_receipt()` → GoodsReceipt + InventoryMovement，库存仍按内部 SKU 统计并保留可选 SupplierSKU 追踪。
- 供应商型号/编码搜索：SKU 页面搜索框 → `/api/skus/?search=` → `SKUViewSet.filter_queryset()` → 返回内部 SKU。

## 风险（只列当前代码事实）

### 严重

- `Product.suppliers` 与 `SupplierSKU` 是两套不同粒度的关系。现有产品供应商多对多关系不会自动产生 SupplierSKU；如果操作人员只维护产品供应商而不维护来源，采购来源下拉框会为空，但旧的无来源采购仍可创建。
- SupplierSKU 被采购/入库引用后，应用 API 拒绝删除；但 `InventoryMovement.supplier_sku` 的数据库 FK 是 `SET_NULL`，绕过应用直接执行数据库删除可能丢失库存来源追踪。正常 API 路径有 `destroy()` 检查，数据库没有对库存追踪建立 `PROTECT`。
- 当前全局 REST 权限是 `AllowAny`，SupplierSKU 没有额外权限隔离。这是项目现有权限基线，本次没有扩大或收紧该策略。

### 中等

- `supplier_sku_code` 仍允许在已有采购历史后被修改；历史采购行通过 snapshot 不受影响，但当前来源编码会变化，且没有 Alias/版本历史帮助用户识别旧编码。
- SupplierSKU 本身没有价格历史、版本历史和修改日志；修改 `purchase_price` 后只能从采购行实际 `unit_price` 看到历史采用价。
- 当前本地库中迁移前已经存在的 8 组内部名称冲突没有自动改名；它们仍会在列表中同时出现，直到业务人员确认改名关系。
- 旧采购行没有本次新增的供应商来源快照；它们保留原有内部 SKU 快照，但供应商侧字段为空。
- Supplier Detail UI 尚不存在，供应商反查 API 只能由其他页面或外部客户端使用。
- 库存页面当前不显示 `InventoryMovement.supplier_sku`，因此用户可以从采购/到货数据追踪来源，但不能直接在库存 UI 过滤供应商来源。

### 轻微

- SKU 搜索后端已支持供应商型号、供应商编码、供应商条码，但 SKU 搜索框占位文字仍主要提示内部名称、Sales Code、分类和规格。
- 没有 SupplierSKU 批量导入/批量停用界面；当前操作粒度是单条来源。
- 前端参考采购价是在选择来源时写入行表单的便利逻辑，不是后端强制的价格规则；用户可以改写，也可以通过其他 API 客户端直接提交不同的 `unit_price`。

## Key Files

### Backend

`backend/crm/models.py`

- `ProductCategory`：L186
- `CategoryAttribute`：L200
- `Product`：L228；已有 `suppliers` 多对多字段
- `SKU`：L248；`sku`、`sales_model`、`display_name_cn`、描述、`parameter_values`、`identity_signature`
- `SKU.display_name_key`：L253；内部名称的大小写不敏感规范化键
- `SKUVersion`：L293
- `PackagingTemplate`：L315
- `SKUPackagingProfile`：L357
- `QuoteItem`：L492；报价行 SKU/商业字段快照
- `OrderItem`：L572；销售订单行 SKU/商业字段快照
- `Supplier`：L610
- `SupplierSKU`：L626-L670
- `PurchaseOrder`：L673 附近
- `PurchaseOrderItem`：L713-L762；`supplier_sku` 与供应商快照
- `InventoryMovement`：L924-L979；可选 `supplier_sku`
- `GoodsReceipt`：L980 附近；通过 `purchase_item` 关联到采购来源

`backend/crm/serializers.py`

- `SupplierSerializer`：L86
- `SupplierSKUSerializer`：L95-L118
- `PurchaseOrderItemSerializer`：L120-L134；返回供应商来源快照
- `PurchaseOrderSerializer`：L136-L188；采购行来源校验和快照创建
- `InventoryMovementSerializer`：L1019 附近；校验来源必须对应当前库存 SKU

`backend/crm/sku_identity.py`

- `normalize_display_name()`：L12；用于内部名称去重的 `casefold` 规范化

`backend/crm/services/supplier_sku.py`

- `create_supplier_sku()`：L28
- `update_supplier_sku()`：L38
- `set_preferred_supplier_sku()`：L50
- `_apply_preferred()`：L12；按内部 SKU 取消其他首选来源

`backend/crm/services/fulfillment.py`

- `record_receipt()`：L134；采购到货创建库存流水时写入 `supplier_sku`

`backend/crm/views.py`

- `SupplierViewSet`：L45；供应商来源反查 action：L50-L54
- `SupplierSKUViewSet`：L57-L91；过滤、CRUD、首选和删除保护
- `PurchaseOrderViewSet`：L94；预取供应商来源及采购行
- `SKUViewSet`：L402；供应商来源搜索：L412、L433；SKU 来源 action：L458-L461
- `InventoryMovementViewSet`：L1079 附近

`backend/crm/urls.py`

- `router.register("skus", SKUViewSet)`：L16
- `router.register("supplier-skus", SupplierSKUViewSet, basename="supplier-sku")`：L17
- `router.register("suppliers", SupplierViewSet, basename="supplier")`：L9
- `router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")`：L10

`backend/crm/migrations/0034_purchaseorderitem_supplier_barcode_snapshot_and_more.py`

- 新增 SupplierSKU、采购行来源字段/快照、库存来源字段及约束。

`backend/crm/migrations/0035_sku_display_name_key_sku_sku_display_name_key_unique.py`

- 新增内部名称规范化键、历史无冲突名称回填和部分唯一约束。

`backend/crm/tests/test_supplier_sku.py`

- 7 个后端测试，覆盖多供应商、编码去重、首选互斥、搜索、采购快照、到货库存追踪、错误来源校验和删除保护。

`backend/crm/tests/test_sku_display_name.py`

- 2 个后端测试，覆盖新建和改名时的大小写不敏感重复拦截。

### Frontend

`frontend/src/api.js`

- L3：Axios Client，`baseURL: '/api'`
- L17：`listData()` 兼容分页和非分页响应

`frontend/src/router.js`

- L28：`/skus` → `SKUPage`
- L35：`/purchase-orders` → `PurchaseOrderPage`
- L21 附近：通用资源路由包含 `/suppliers` → `ResourcePage`

`frontend/src/views/SKUPage.vue`

- L28-L29：Supplier Sources 状态和表单
- L197-L209：编辑 SKU 时加载并打开来源区域
- L220-L243：来源加载、创建、编辑、设首选、启停
- L354：Supplier Sources 表格和操作按钮
- L359：SupplierSKU 编辑/新建弹窗

`frontend/src/views/PurchaseOrderPage.vue`

- L3、L12：采购页面状态
- L23-L35：按 Supplier + 内部 SKU 查询来源、参考价带入和采购提交
- L46：采购来源选择器及历史快照展示

`frontend/src/App.vue`

- L19：供应商管理入口
- L20：采购管理入口
- L22：SKU 管理入口

`frontend/src/views/SKUPage.test.js`

- 检查 SKU 页面确实调用 SupplierSKU API，并存在 Supplier Sources UI、首选和启停操作。

`frontend/src/views/PurchaseOrderPage.test.js`

- 检查采购页面保留创建、到货、付款链路，并接入 SupplierSKU 查询和 `supplier_sku` 提交字段。

## 验证记录

- `python backend/manage.py check`：通过。
- `python backend/manage.py makemigrations --check --dry-run`：`No changes detected`。
- `python backend/manage.py migrate --noinput`：已应用 `crm.0034...`。
- `python backend/manage.py migrate --noinput`：已应用 `crm.0035...`。
- 后端 SupplierSKU、SKU 名称去重及 SKU 商业身份专项测试：25/25 通过。
- 后端 SupplierSKU、SKU 商业身份、报价、包装、履约相关回归测试：通过。
- `npm run test:unit`：20/20 通过。
- `npm run build`：通过。
