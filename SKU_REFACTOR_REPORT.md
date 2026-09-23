# SKU 模块修复与数据安全增强报告

## 实际修改内容

- 修复 Sales Model 前端保存链：`SKUPage.vue` 现在将 `form.sales_model` 提交至 `POST/PUT /api/skus/`；后端仅在调用方没有提交型号时才使用规则生成的候选值。
- 将 `SKU.sku` 设置为创建后只读的 Serializer 字段，保留后端自动分配 `SKU-######` 的行为。
- 新增 `SKU.identity_signature`，由 Product 与身份属性规范化产生；创建/编辑时阻止同 Product 的相同组合。
- 新增 `SKUVersion`，在 API 修改商业身份字段前保存旧状态。纳入 Sales Model、内部名、双语描述、参数、规格、产品明细；价格、图片和库存等变更不创建版本。
- 增加历史版本查询、历史型号搜索命中标记和 SKU 页面“历史版本”入口。
- 为采购行与库存流水增加商业身份快照；新事件保持当前 SKU 关联，同时不会因日后改名/改型号改变历史显示。
- SKU 删除在已有业务引用时返回明确业务错误；Product 有 SKU 时拒绝物理删除，提示使用停产/停用流程。
- 修复包装字段契约：`packaging_summary()` 新增 `template_name`，与 `SKUPage.vue` 编辑回填一致。

## Sales Model Root Cause

旧审计结论在当前工作树中仍有效，并非过时结论。

原调用链：

```text
SKUPage.allPreviews.sales_model（仅计算预览）
  → 模板以 readonly input 显示
  → save() 的 shared payload 不含 sales_model
  → POST / PUT /api/skus/
  → SKUSerializer 收不到用户确认的型号
  → 创建时可能以规则候选值覆盖；编辑时保留旧 SKU.sales_model
  → GET 后仍显示旧型号
```

依据：`frontend/src/views/SKUPage.vue` 原 `form`、`allPreviews`、`save` 逻辑。现在输入绑定 `form.sales_model`，创建和编辑 payload 都发送 `sales_model`；`SKUSerializer.create()` 不再覆盖非空提交值。当前正式字段仍只有 `SKU.sales_model`。`Product.sales_model_prefix` 仅生成候选前缀，`sales_model_abbreviations` 仅保存参数缩写。

## 数据库 Migration

新增 `backend/crm/migrations/0033_sku_safety_history.py`：

- 新增 `SKU.identity_signature` 和索引。
- 新建 `SKUVersion` 表及 `(sku, version_no)` 唯一约束。
- 为 `PurchaseOrderItem` 增加 Code、Sales Model、显示名、描述快照。
- 为 `InventoryMovement` 增加 Code、Sales Model、显示名快照。
- 数据迁移回填已有签名和事件快照。历史采购/库存快照由升级时的当前 SKU 值补录，**不宣称为事件发生时的原始历史值**。
- 如回填发现重复身份签名，迁移只输出待人工处理的 SKU 清单，不删除、合并或让迁移失败。

## 新增 Model / 字段

- `SKU.identity_signature`
- `SKUVersion`
- `PurchaseOrderItem.sku_code_snapshot`
- `PurchaseOrderItem.sales_model_snapshot`
- `PurchaseOrderItem.display_name_snapshot`
- `PurchaseOrderItem.description_snapshot`
- `InventoryMovement.sku_code_snapshot`
- `InventoryMovement.sales_model_snapshot`
- `InventoryMovement.display_name_snapshot`

## API 修改

- `GET /api/skus/{id}/versions/`：返回不可编辑的 SKU 历史版本。
- `GET /api/skus/?search=...`：同时搜索当前 SKU 信息和 SKUVersion 快照；历史命中返回当前 SKU，`historical_matches` 标记命中记录。
- SKU `POST/PUT/PATCH`：`sku` 只读；支持明确提交 `sales_model`、描述；冲突参数组合返回友好错误。
- `DELETE /api/skus/{id}/`：有业务引用时返回“请将其停用”。
- `DELETE /api/products/{id}/`：存在 SKU 时拒绝删除。

## 前端修改

- `SKUPage.vue` 显示只读 SKU Code。
- 新增可编辑 Sales Model、中文描述、英文描述字段。
- 已有报价/订单计数时，编辑 Sales Model 显示历史保护提示。
- SKU 列表显示“命中历史 SKU 信息”，并提供历史版本 modal。
- 包装编辑回填使用后端现已提供的 `template_name`。

## 修复的前后端 Bug

- Sales Model 预览没有进入保存 payload。
- 后端创建逻辑会覆盖调用方明确提交的 Sales Model。
- `row.packaging?.template_name` 被前端读取但后端摘要未返回。
- 采购/库存事件只回读实时 SKU 商业字段，无法保持历史展示。

## 保留的预留 API

- `/api/sku-packaging-profiles/` 独立 CRUD 未删除。当前正式 UI 使用 `/api/skus/{id}/packaging/`，独立 endpoint 作为合理预留能力保留。
- `/api/skus/{id}/packaging/` GET 未强制接入页面；现有列表摘要足以服务当前 UI。

## 废弃但暂未删除的代码

- `frontend/src/resourceConfigs.js` 中的旧 SKU resource config 仍保留；router 已明确让 `/skus` 使用专用 `SKUPage`。本次未删除，以避免扩大改动范围。

## 测试结果

- `python backend/manage.py makemigrations --check --dry-run`：通过。
- `python backend/manage.py test crm.tests.test_sku_commercial_identity --verbosity 1`：16 项通过。
- `python backend/manage.py test crm.tests.test_quotes crm.tests.test_packaging crm.tests.test_fulfillment --verbosity 0`：完成，无失败输出。
- `npm run test:unit`：19/19 通过。
- `npm run build`：通过。

新增 SKU 测试覆盖：Code 不可改、手工 Sales Model 持久化、版本生成、价格不生成版本、旧型号搜索、重复身份签名拒绝、采购/库存快照、已引用 SKU 禁删与停用。

## 仍存在的风险

- 当前 REST Framework 默认权限仍为 `AllowAny`。项目存在角色模型，但 SKU 写操作未在本次接入新权限，以免无认证上下文下破坏现有本地流程。
- `identity_signature` 由业务层保证唯一性而非数据库唯一约束，以允许迁移保留既有重复数据并交由人工处理；并发创建的极端竞争仍需后续按部署数据库能力强化。
- `SKUVersion` 记录 API Serializer 的关键字段变更。绕过 API 直接用 ORM 批量更新的运维脚本不会自动产生版本，需作为运维约束。
- 前端引用提示目前来自报价/订单计数；后端删除保护覆盖采购、库存、预留、发货、装箱等更多真实引用。

## 需要人工决定的问题

- 已有重复 identity signature 的 SKU：迁移会报告但不自动处理，需要决定保留、合并还是停用。
- 已进入采购/库存但尚未报价/订单的 SKU，前端未显示引用警告；后端会保存版本并阻止物理删除，但是否需要把所有引用计数暴露到页面需产品决策。
- 是否在生产启用认证后，将 SKU 写操作接入现有角色权限体系。
