# R0-D4B2-C Final Acceptance API 权限矩阵

基线：`efc9ed4827024bc5a68158c82b9f64b66eb916cc`。本矩阵对应本轮最终代码提交。路由来源为 `backend/crm/urls.py` 的 DRF Router、自定义 APIView 与 function view；权限来源为 `backend/crm/permissions.py`、视图内业务校验和各资源 queryset。除特别标注外，列表、详情、搜索、筛选均只作用于已授权 queryset。ModelViewSet 公开 GET/POST/PUT/PATCH/DELETE；ReadOnlyModelViewSet 仅公开 GET；未注册的方法返回 405。`HEAD/OPTIONS` 遵循对应视图的 DRF 权限策略。

## 判定规则

| 符号 | 判定 |
| --- | --- |
| `module.view/create/update/delete/export/import` | 对应模块的单项 RBAC 权限。标准 CRUD 的 GET 是 view，POST collection 是 create，PUT/PATCH detail 是 update，DELETE detail 是 delete。包含 `export` 的路径或导出 query 在 SAFE_METHODS 前识别为 export。 |
| `scope` | 销售类记录按客户归属执行 self / department / department_tree / all；共享采购、供应商、产品主数据和企业库存按模块权限访问。 |
| `cross` | 从一个模块返回/修改另一个模块的数据时，还要满足目标模块权限、目标对象 Data Scope；写操作另需目标模块 update/create。未授权关联字段被过滤或隐藏。 |
| `PASS` | 路由有明确服务端授权；该行所列自动化套件覆盖其主要允许/拒绝及业务成功路径。真实浏览器/API 验收结果见文末。 |
| `BLOCKED` | 应用层无法判断部署外部控制面的真实 ACL；详情见 C-08。 |

## Router CRUD 入口

| API 路径 | HTTP 方法 | 模块与操作权限 | 数据范围与跨模块校验 | 自动化回归 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `/api/customers/`；`/api/customers/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `customers.view/create/update/delete` | 按客户 owner 和 Data Scope 过滤；关联 contacts、follow-ups、orders、finance 指标按各模块权限和范围裁剪 | `test_sales_data_scope.py`、`test_customer_h1.py`、`test_functional_rbac.py` | PASS |
| `/api/contacts/`；`/api/contacts/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `contacts.view/create/update/delete` | 联系人通过所属客户范围；创建/改绑客户时验证 customer ID 可访问 | `test_sales_data_scope.py`、`test_customer_h1.py` | PASS |
| `/api/follow-ups/`；`/api/follow-ups/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `followups.view/create/update/delete` | 按关联客户范围；customer 改绑校验；附件使用同一跟进/客户授权 | `test_sales_data_scope.py`、`test_customer_h1.py`、`test_functional_rbac.py` | PASS |
| `/api/quotes/`；`/api/quotes/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `quotes.view/create/update/delete` | 按客户范围；SKU、客户快照和库存字段另受关联模块限制 | `test_sales_data_scope.py`、`test_quotes.py`、`test_functional_rbac.py` | PASS |
| `/api/orders/`；`/api/orders/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `orders.view/create/update/delete` | 按客户范围；customer/order item 改绑校验目标范围；财务/库存/采购派生字段按对应模块过滤 | `test_sales_data_scope.py`、`test_procurement_data_scope.py`、`test_finance_data_scope.py` | PASS |
| `/api/suppliers/`；`/api/suppliers/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `suppliers.view/create/update/delete` | 供应商为共享业务；采购关联允许按 purchases 权限显示；付款计划和财务指标还需 finance 权限；销售订单编号/ID/分配需 orders.view + 客户范围 | `test_supplier_context_scope.py`、`test_procurement_data_scope.py`、`test_functional_rbac.py` | PASS |
| `/api/supplier-skus/`；`/api/supplier-skus/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `suppliers.view/create/update/delete` | 供应来源共享；SKU、采购与订单关联字段按 skus / purchases / orders 权限裁剪 | `test_procurement_data_scope.py`、`test_supplier_allocation.py`、`test_product_workspace.py` | PASS |
| `/api/supplier-capabilities/`；`/api/supplier-capabilities/{pk}/` | GET list/detail；POST；PUT/PATCH；DELETE | `suppliers.view/create/update/delete` | 供应商能力共享；供应商 ID 必须存在且可访问 | `test_procurement_data_scope.py`、`test_supplier_allocation.py` | PASS |
| `/api/purchase-orders/`；`/api/purchase-orders/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `purchases.view/create/update/delete` | 采购单共享，不按销售员隔离；销售来源订单和分摊仅在 orders.view + 范围内返回；写入、成本分摊、草稿生成要求目标订单写权限 | `test_procurement_data_scope.py`、`test_supplier_context_scope.py`、`test_supplier_allocation.py`、`test_functional_rbac.py` | PASS |
| `/api/categories/`；`/api/categories/{pk}/` | GET list/detail；POST；PUT/PATCH；DELETE | `categories.view/create/update/delete` | 共享产品分类资料；SKU/产品嵌套字段受 skus / products 权限裁剪 | `test_product_workspace.py`、`test_functional_rbac.py` | PASS |
| `/api/category-attributes/`；`/api/category-attributes/{pk}/` | GET list/detail；POST；PUT/PATCH；DELETE | `categories.view/create/update/delete` | 随分类共享；分类外键在可访问 queryset 中校验 | `test_product_workspace.py` | PASS |
| `/api/products/`；`/api/products/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `products.view/create/update/delete` | 产品主档共享；SKU、类别、客户订单引用按相关模块权限裁剪 | `test_product_workspace.py`、`test_functional_rbac.py` | PASS |
| `/api/hs-codes/`；`/api/hs-codes/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | GET `hs_codes.view`；所有写操作还要求 `HSCodeMaintenancePermission` 管理员 | HS 编码主数据共享；assign-products 写入验证产品关联 | `test_functional_rbac.py`、`test_product_workspace.py` | PASS |
| `/api/skus/`；`/api/skus/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `skus.view/create/update/delete` | SKU 主档共享；库存、订单次数、供应商来源、包装及版本按 inventory / orders / suppliers / packaging 权限过滤 | `test_product_workspace.py`、`test_sku_images.py`、`test_trade_units.py` | PASS |
| `/api/sku-trade-units/`；`/api/sku-trade-units/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `trade_units.view/create/update/delete` | 单位换算共享；关联 SKU 与文档数量校验 | `test_trade_units.py`、`test_functional_rbac.py` | PASS |
| `/api/packaging-templates/`；`/api/packaging-templates/{pk}/` | GET list/detail；POST；PUT/PATCH；DELETE | `packaging.view/create/update/delete` | 包装主数据共享；产品/SKU 关联按相应模块过滤 | `test_product_workspace.py`、`test_functional_rbac.py` | PASS |
| `/api/sku-packaging-profiles/`；`/api/sku-packaging-profiles/{pk}/` | GET list/detail；POST；PUT/PATCH；DELETE | `packaging.view/create/update/delete` | SKU 包装配置共享；SKU 关联还需 skus 权限 | `test_product_workspace.py` | PASS |
| `/api/product-parameters/`；`/api/product-parameters/{pk}/` | GET list/detail；POST；PUT/PATCH；DELETE | `parameters.view/create/update/delete` | 参数模板共享；产品分类关联按 categories 权限 | `test_product_workspace.py` | PASS |
| `/api/product-certificates/`；`/api/product-certificates/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `certificates.view/create/update/delete` | 证书主档按所属 SKU/产品范围；关联采购/客户字段按目标模块权限过滤 | `test_functional_rbac.py`、`test_product_workspace.py` | PASS |
| `/api/shipments/`；`/api/shipments/{pk}/` | GET list/detail/search；其他方法 405 | `inventory.view` | 共享发货记录；订单及客户字段须 orders.view + Data Scope | `test_fulfillment.py`、`test_sales_data_scope.py` | PASS |
| `/api/inventory-movements/`；`/api/inventory-movements/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `inventory.view/create/update/delete` | 企业库存流水共享；关联订单明细需 orders.view + 范围；写入/冲销影响销售订单时还需 orders.update | `test_inventory_movement_reversal.py`、`test_procurement_data_scope.py`、`test_sales_data_scope.py` | PASS |
| `/api/sales-rules/`；`/api/sales-rules/{pk}/` | GET list/detail；POST；PUT/PATCH；DELETE | `quotes.view/create/update/delete` | 规则共享；SKU/分类引用校验对应模块 | `test_quotes.py`、`test_functional_rbac.py` | PASS |
| `/api/transactions/`；`/api/transactions/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `transactions.view/create/update/delete` | 客户收款及销售订单费用按客户范围；供应商付款/公共费用共享；关联计划/订单/采购及分配分别执行 finance / orders / purchases 附加校验 | `test_finance_data_scope.py`、`test_trade_finance_upgrade.py`、`test_functional_rbac.py` | PASS |
| `/api/payment-plans/`；`/api/payment-plans/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `finance.view/create/update/delete` | 客户/销售计划按客户范围；供应商采购计划共享；订单、采购、流水分配依关联模块权限筛选 | `test_finance_data_scope.py`、`test_procurement_data_scope.py`、`test_supplier_context_scope.py` | PASS |
| `/api/contract-changes/`；`/api/contract-changes/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `ContractFinancePermission` 按合同记录类型选择 `orders` 或 `purchases` 对应动作；业务审批另需 finance 对应写权限 | 销售合同变更按关联客户订单范围；采购变更按共享采购权限；订单/采购/付款关联写入各自再授权 | `test_finance_data_scope.py`、`test_trade_finance_upgrade.py`、`test_sales_data_scope.py` | PASS |
| `/api/organization-units/`；`/api/organization-units/{pk}/` | GET list/detail；POST；PUT/PATCH；DELETE | `organization.view/create/update/delete` | 组织结构共享；角色、员工关联由权限管理操作约束 | `test_functional_rbac.py`、`test_audit.py` | PASS |
| `/api/positions/`；`/api/positions/{pk}/` | GET list/detail；POST；PUT/PATCH；DELETE | `organization.view/create/update/delete` | 职位与组织单元共享；引用需有效 | `test_functional_rbac.py` | PASS |
| `/api/employees/`；`/api/employees/{pk}/` | GET list/detail/search；POST；PUT/PATCH；DELETE | `employees.view/create/update/delete` | 员工资料共享；角色分配及权限字段仅管理员接口修改 | `test_functional_rbac.py`、`test_sales_data_scope.py` | PASS |
| `/api/access-roles/`；`/api/access-roles/{pk}/` | GET list/detail；POST/PUT/PATCH/DELETE 及 matrix action | GET `permissions.view`；写操作另需 PermissionAdminOnly；矩阵 POST 需管理员 | 不作为业务数据范围边界；服务端重新计算有效权限 | `test_functional_rbac.py` | PASS |
| `/api/role-permissions/`；`/api/role-permissions/{pk}/` | GET list/detail；POST/PUT/PATCH/DELETE | GET `permissions.view`；写操作另需 PermissionAdminOnly | 权限配置仅管理员；普通用户不能通过改权限记录提权 | `test_functional_rbac.py` | PASS |
| `/api/operation-logs/`；`/api/operation-logs/{pk}/` | GET list/detail/filter；其他方法 405 | 按 `entity` 映射所属模块 `.view` | 日志对象按对应客户范围筛选；快照字段再次按跨模块权限脱敏；合同变更日志按 orders/purchases 身份识别 | `test_audit.py`、`test_sales_data_scope.py`、`test_functional_rbac.py` | PASS |

## 自定义 ViewSet Action 与直接 APIView

| API 路径 | HTTP 方法 | 模块与操作权限 | 数据范围与跨模块校验 | 自动化回归 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `/api/supplier-capabilities/preview/` | POST | `suppliers.update` | 校验供应商与 SKU 组合；不持久化 | `test_supplier_allocation.py` | PASS |
| `/api/suppliers/{pk}/supplier-skus/` | GET | `suppliers.view` | 供应商来源列表共享；SKU 字段按 skus.view 过滤 | `test_procurement_data_scope.py`、`test_supplier_allocation.py` | PASS |
| `/api/supplier-skus/{pk}/set-preferred/` | POST | `suppliers.update` | 仅更改该供应商/SKU 来源优先级 | `test_supplier_allocation.py` | PASS |
| `/api/purchase-orders/{pk}/place/`；`cancel/` | POST | `purchases.update` | 采购单共享；取消/下单时校验状态和关联库存/付款流程 | `test_procurement_data_scope.py`、`test_trade_finance_upgrade.py` | PASS |
| `/api/purchase-orders/{pk}/cost-allocation-preview/` | POST | `purchases.update` | 目标订单逐项需 orders.view + orders.update + 客户范围 | `test_procurement_data_scope.py`、`test_supplier_allocation.py` | PASS |
| `/api/purchase-orders/{pk}/cost-allocation/` | GET / POST | GET `purchases.view`；POST `purchases.update` | 多订单分摊只返还可访问订单；保存时要求所有目标销售订单可写且在范围 | `test_procurement_data_scope.py`、`test_finance_data_scope.py` | PASS |
| `/api/purchase-orders/{pk}/receive/`；`/receipts/{receipt_id}/reverse/` | POST | `purchases.update` + `inventory.create/update` | 入库/冲销校验共享库存；如影响销售订单同时需 orders.update + scope | `test_procurement_data_scope.py`、`test_inventory_movement_reversal.py` | PASS |
| `/api/purchase-orders/{pk}/pay/` | POST | `purchases.update` + finance/transactions 对应写权限 | 供应商付款共享；付款计划和交易关联逐项验证 | `test_finance_data_scope.py`、`test_trade_finance_upgrade.py` | PASS |
| `/api/access-roles/{pk}/permission-matrix/` | POST | `permissions.update` + 管理员 | 仅管理员可写角色矩阵 | `test_functional_rbac.py` | PASS |
| `/api/customers/owner-options/`；`next-code/`；`sources/` | GET | `customers.view` | owner 列表只含有效员工；sources 不返回越权客户 | `test_customer_h1.py`、`test_sales_data_scope.py` | PASS |
| `/api/customers/{pk}/insights/` | GET | `customers.view` | 当前客户范围；跟进、订单、财务统计分别要求 followups/orders/finance 权限与范围 | `test_customer_h1.py`、`test_sales_data_scope.py`、`test_finance_data_scope.py` | PASS |
| `/api/contacts/methods/` | GET | `contacts.view` | 返回联系人方式枚举，不包含业务数据 | `test_customer_h1.py` | PASS |
| `/api/follow-ups/methods/`；`/api/follow-ups/{pk}/attachments/` | GET methods；POST attachments | GET `followups.view`；POST `followups.update` | 跟进对象必须在客户范围；文件使用受控介质路由 | `test_customer_h1.py`、`test_functional_rbac.py` | PASS |
| `/api/follow-ups/{pk}/attachments/{attachment_id}/` | DELETE | `followups.delete` | attachment 必须属于已授权跟进记录 | `test_functional_rbac.py` | PASS |
| `/api/categories/tree/`；`/api/categories/reorder/`；`/api/category-attributes/reorder/` | GET / POST | GET `categories.view`；POST `categories.update` | 分类节点均在共享分类 queryset；排序不修改外部模块业务对象 | `test_product_workspace.py` | PASS |
| `/api/products/next-code/`；`/api/products/{pk}/sales-model-prefix-preview/`；`sales-model-prefix-apply/` | GET / POST | GET `products.view`；POST `products.update` | 产品主档共享；写入时检查产品和子 SKU 关联 | `test_product_workspace.py` | PASS |
| `/api/products/{pk}/customers/` | GET | `products.view` | 客户/销售引用需 customers.view + Data Scope | `test_sales_data_scope.py`、`test_product_workspace.py` | PASS |
| `/api/products/{pk}/combination-rules/` | GET / POST | `skus.view/update` + `products.view` | 规则属于共享产品主档；POST 校验组合规则后才保存 | `test_product_workspace.py` | PASS |
| `/api/products/{pk}/sku-plan/` | GET / POST / PATCH / DELETE | GET `skus.view`；写方法 `skus.update/delete` + `products.view` | plan、SKU 和 successor 关系限制在该产品；版本快照不暴露其他产品 | `test_product_workspace.py` | PASS |
| `/api/products/{pk}/sku-plan/{operation}/` (`analyze`, `publish`) | POST | `skus.update` + `products.view` | 计划锁定到目标产品；要求当前草稿版本；未知 operation 拒绝 | `test_product_workspace.py` | PASS |
| `/api/hs-codes/{pk}/assign-products/` | PUT | `hs_codes.update` + 管理员 | 每个 product ID 在可访问集合中；管理员外拒绝 | `test_product_workspace.py`、`test_functional_rbac.py` | PASS |
| `/api/skus/batch-create/` | POST | `skus.create` | 产品、分类、参数和供应商来源逐项校验模块权限与有效 ID | `test_product_workspace.py`、`test_supplier_allocation.py` | PASS |
| `/api/skus/inventory-list/`；`/api/skus/{pk}/inventory-detail/` | GET | `inventory.view` | SKU 需可见；库存列表/流水共享；销售订单引用按 orders.view + scope 过滤 | `test_inventory_movement_reversal.py`、`test_product_workspace.py` | PASS |
| `/api/skus/{pk}/versions/`；`/supplier-skus/`；`/sales-model-abbreviations/` | GET | `skus.view` | 供应商来源子字段另需 suppliers.view；版本快照按 SKU 权限 | `test_product_workspace.py`、`test_supplier_allocation.py` | PASS |
| `/api/skus/{pk}/thumbnail/`；`/api/skus/{pk}/image/` | GET；POST/DELETE | GET `skus.view`；POST `skus.update`；DELETE `skus.update` | 图片绑定已授权 SKU；受控文件访问不使用公开 `/media/` URL | `test_sku_images.py`、`test_functional_rbac.py` | PASS |
| `/api/skus/{pk}/packaging/` | GET / PUT | GET `skus.view`；PUT `skus.update` + `packaging.update` | SKU 与包装 profile 必须有效且有权操作 | `test_product_workspace.py` | PASS |
| `/api/shipments/{pk}/reverse/`；`/packages/`；`/packages/{package_id}/`；`/copy-estimated-packing/` | POST reverse；GET/POST packages；POST/PUT/PATCH/DELETE package；POST copy | `inventory.view/create/update/delete`，按动作区分 | 共享库存/发货数据；订单履约关联需 orders.view/update + 客户范围 | `test_fulfillment.py`、`test_inventory_movement_reversal.py` | PASS |
| `/api/quotes/availability-preview/`；`/{pk}/availability/` | POST；GET | `quotes.update`；`quotes.view` | SKU/库存只在各自模块授权后查询；报价受客户范围 | `test_quotes.py`、`test_sales_data_scope.py` | PASS |
| `/api/quotes/{pk}/packing-plan/` | GET / POST | GET `quotes.view`；POST `quotes.update` | 库存关联字段需 inventory 权限；客户报价仍按 scope | `test_quotes.py`、`test_fulfillment.py` | PASS |
| `/api/quotes/{pk}/mark-sent/`；`accept/`；`reject/`；`expire/` | POST | `quotes.update` | 仅改变范围内报价状态；转订单动作不改变独立订单范围 | `test_quotes.py`、`test_sales_data_scope.py` | PASS |
| `/api/quotes/{pk}/important-notes/`；`/important-notes/{note_id}/deactivate/`；`restore/` | GET / POST | GET `quotes.view`；POST `quotes.update` | note 必须属于当前范围报价 | `test_quotes.py` | PASS |
| `/api/quotes/{pk}/workbench/`；`order-draft/` | GET | `quotes.view` | 关联订单、客户、SKU、库存字段均按对应模块权限和客户范围裁剪 | `test_quotes.py`、`test_sales_data_scope.py` | PASS |
| `/api/quotes/{pk}/revise/` | POST | `quotes.create/update` 按原报价版本动作检查 | 原报价须在客户范围；SKU 引用还需可见 | `test_quotes.py`、`test_sales_data_scope.py` | PASS |
| `/api/quotes/{pk}/pi-data/`；`/export/` | GET | PI `quotes.view`；export `quotes.export` | 报价客户范围；SKU 图片 URL 由 quotes.view + skus.view 过滤并经受控媒体端点返回 | `test_quotes.py`、`test_sku_images.py`、`test_functional_rbac.py` | PASS |
| `/api/orders/{pk}/confirm/`；`start-production/`；`complete/`；`cancel/` | POST | `orders.update` | 客户范围；会改库存/财务/采购派生记录时需要 inventory/finance/purchases 对应权限 | `test_sales_data_scope.py`、`test_fulfillment.py`、`test_finance_data_scope.py` | PASS |
| `/api/orders/{pk}/fulfillment/`；`procurement-plan/` | GET | `orders.view` | 另需 inventory 或 purchases/suppliers 模块权限；仅返回可见关联 | `test_fulfillment.py`、`test_procurement_data_scope.py` | PASS |
| `/api/orders/{pk}/generate-purchase-drafts/` | POST | `purchases.create` + 目标订单 `orders.update` | 不允许利用采购草稿写入跨范围销售订单；共享采购本身仍可用 | `test_procurement_data_scope.py`、`test_supplier_allocation.py` | PASS |
| `/api/orders/{pk}/packing-plan/`；`/ship/` | GET / POST | GET `orders.view`；修改 `orders.update` 或 `inventory.create` | 订单范围；库存与发货记录关联另验权限 | `test_fulfillment.py`、`test_sales_data_scope.py` | PASS |
| `/api/orders/{pk}/workbench/` | GET | `orders.view` | Workbench 每个嵌套来源模块 separately filtered | `test_sales_data_scope.py`、`test_finance_data_scope.py`、`test_procurement_data_scope.py` | PASS |
| `/api/transactions/{pk}/void/`；`/allocate/` | POST | `transactions.update` / finance 对应更新权限 | 来源流水按交易归属；分配/冲销逐项校验客户/订单/收付款计划范围及权限 | `test_finance_data_scope.py`、`test_trade_finance_upgrade.py` | PASS |
| `/api/inventory-movements/batch/`；`/{pk}/reverse/` | POST | `inventory.create/update` | batch 的订单 ID、order item ID 和 related_orders 必须在 orders.view/update 授权范围 | `test_inventory_movement_reversal.py`、`test_procurement_data_scope.py` | PASS |
| `/api/payment-plans/{pk}/settle/` | POST | `finance.update` + `transactions.create/update` | 计划及关联客户/订单/采购/流水逐项校验；共享供应商付款不按销售员归属隔离 | `test_finance_data_scope.py`、`test_procurement_data_scope.py` | PASS |
| `/api/contract-changes/{pk}/approve/`；`reject/` | POST | `finance.create/update` + 合同所属 orders 模块权限 | 按订单客户范围；审批导致订单/采购/付款更新时每个目标对象另验写权限 | `test_finance_data_scope.py`、`test_trade_finance_upgrade.py` | PASS |
| `/api/sales-rules/check-quote/` | POST | `quotes.update` | 校验 quote 与 SKU 引用；不开放其他客户报价 | `test_quotes.py` | PASS |
| `/api/products/{pk}/supplier-candidate-pool/` | GET / POST | GET `suppliers.view`；POST `suppliers.update`；两者均另需 `products.view` + `skus.view` | SKU 必须属于该产品且有效；候选来源限授权供应商数据；批量写入只绑定传入的该产品 SKU | `test_supplier_allocation.py`、`test_product_workspace.py` | PASS |
| `/api/skus/{pk}/supplier-candidates/` | GET / POST | GET `suppliers.view`；POST `suppliers.update`；两者均另需 `skus.view` | SKU 在共享 SKU 主档中存在；supplier 必须有效且供应商模块授权已通过 | `test_supplier_allocation.py`、`test_product_workspace.py` | PASS |
| `/api/orders/{order_id}/items/{item_id}/supplier-allocation/` | GET / POST | `orders.view/update` + `suppliers.view` + `skus.view` | 销售订单及 item 在客户范围；分配写操作还要求目标 supplier/source 可写 | `test_supplier_allocation.py`、`test_sales_data_scope.py` | PASS |

## Function View / APIView 与 GET 导出

| API 路径 | HTTP 方法 | 模块与操作权限 | 数据范围与跨模块校验 | 自动化回归 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `/api/reports/catalog/` | GET | `reports.view` | 目录仅呈现当前来源模块可用报告 | `test_reporting.py`、`test_dashboard_import.py` | PASS |
| `/api/reports/data/` | GET；`?export=1/true/csv/xlsx` | 普通查询 `reports.view`；导出 `reports.export` | 每个 source 需其来源模块 view 和数据范围；CSV/XLSX 与屏幕聚合使用相同 filtered records | `test_reporting.py`、`test_functional_rbac.py` | PASS |
| `/api/dashboard/` | GET | `dashboard.view` | 客户、销售、财务、库存等分项数据仅在对应来源模块 view + Data Scope 下聚合 | `test_dashboard_import.py`、`test_finance_data_scope.py` | PASS |
| `/api/finance-dashboard/` | GET；`?export=...` | `finance.view` + `transactions.view`；导出另需 `finance.export` | 销售相关金额按客户范围，供应商与公共费用共享；摘要/导出采用同范围数据 | `test_finance_data_scope.py`、`test_reporting.py` | PASS |
| `/api/organization/overview/` | GET | `organization.view` 或权限管理员特例 | 只返回组织和权限汇总；普通员工业务对象不外露 | `test_functional_rbac.py` | PASS |
| `/api/session/current-operator/` | GET | 显式公开（AllowAny） | 返回经过服务端计算的当前 operator 和权限矩阵，不返回业务记录；匿名响应只提供空权限态 | `test_functional_rbac.py` | PASS |
| `/api/exchange-rates/usd-cny/` | GET | `finance.view` | 外部汇率参考信息，无客户记录 | `test_trade_finance_upgrade.py` | PASS |
| `/api/context/{entity}/{pk}/` | GET | Context 模块映射的 `{module}.view` | 父对象按 Data Scope；每个嵌套 section/metric 再校验自身模块权限、scope；supplier context 对请求用户执行财务与订单字段过滤 | `test_supplier_context_scope.py`、`test_finance_data_scope.py`、`test_sales_data_scope.py`、`test_functional_rbac.py` | PASS |
| `/api/media/{relative_path}` | GET | 文件归属模块 view；DRF 登录策略 | Follow-up 文件跟随跟进/客户范围；quote snapshot 需 quotes.view + skus.view 和报价范围；SKU 图片需 skus.view；私有 no-store，旧 `/media/` 路由 404 | `test_functional_rbac.py`、`test_sku_images.py`、`test_quotes.py` | PASS |
| `/api/import/templates/` | GET | `imports.view` | 只返回静态模板定义，不含业务数据 | `test_dashboard_import.py` | PASS |
| `/api/import/csv/` | POST | `imports.import` | 仅解析/校验上传，不持久化业务对象 | `test_dashboard_import.py` | PASS |
| `/api/import/csv/preview/` | POST | `imports.import` + 目标模块相应 view/write 权限 | 每行外键必须在可访问集合；预览签名绑定当前用户和数据 | `test_dashboard_import.py`、`test_sales_data_scope.py` | PASS |
| `/api/import/csv/execute/` | POST | `imports.import` + 目标模块写权限 | 校验预览签名、用户和目标关联范围；执行前再次校验，不信任旧预览 | `test_dashboard_import.py`、`test_sales_data_scope.py` | PASS |

## 未映射、文件和运行环境边界

| 入口 | 规则 | 自动化回归 | 状态 |
| --- | --- | --- | --- |
| 任一未登记 API 路径 | RBAC 开启时 `module_for_request()` 返回空即 fail closed；公开入口必须显式声明。方法/路径判定先识别 export，再处理 SAFE_METHODS。 | `test_functional_rbac.py` | PASS |
| Django `/admin/` | 独立于 `/api/` 的 Django admin，受 staff 和 Django admin 权限控制；不作为业务 API。 | Django admin 默认权限机制；本轮范围外 | PASS（独立鉴权） |
| 生产对象存储/CDN/Nginx 直链与外部证书 `file_url` | 仓库只能验证 API 路由；外部 ACL 及链接是否公开须按部署策略验证。 | 无仓库级部署 ACL 配置 | BLOCKED · C-08 |

## 本轮最终验收补充

- C-09（P1，已修复）：直接以 `Accept: text/html` 打开越权订单时，DRF Browsable API 的 HTML 表单呈现关联字段选择项，即使 JSON 详情已经 404。默认 renderer 改为 JSON-only，HTML 请求返回 406；新增回归验证响应中无隐藏客户选项。`test_functional_rbac.py::test_html_api_forms_cannot_disclose_out_of_scope_relation_choices`。
- 文件回归：真实 HTTP 验收确认跟进附件、SKU 图片及报价历史快照的受控 URL 在授权账号下返回 200 和实际内容；跨客户跟进附件和报价图片直接 URL 返回 404；旧 `/media/` URL 返回 404。自动化覆盖于 `test_functional_rbac.py` 中的三个媒体测试。
- 数据库兼容：完整 PostgreSQL job 由最终 CI 验证；本地测试数据库为 SQLite 隔离副本，不替代 PostgreSQL CI。
- 真实浏览器及 HTTP 验收：隔离账号验证了 self 与 department 数据边界、无 purchases 权限、reports.view 无 reports.export、无 finance.view、跨客户附件/报价快照 URL、授权附件/SKU 图片/报价快照，以及无 orders.view 时共享采购与库存可用。越权详情/文件返回 404，缺少模块权限返回 403，授权媒体返回 200 且有内容；报表查看为 200、CSV 导出为 403。浏览器中捕获的视觉结果已在本会话展示。
- 截图文件上传：目标目录为 `ux-review-evidence/ux-review/r0-d4b2c-final-permission-audit/final/`，当前为 BLOCKED。Codex 内置浏览器的安全策略拒绝将截图数据写入仓库，并明确禁止通过其他浏览器面、间接方式或原始浏览器命令绕过；因此本矩阵不声称截图文件已提交。
- 本地验证：Django 完整套件 715 项通过（10 项按套件配置跳过），前端 Vitest 492 项、Node UI 测试 1 项、独立单元测试 121 项及生产构建通过。PostgreSQL 与 GitHub Actions 三项结果以本轮推送后的 CI 为准。
