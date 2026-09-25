# Phase 3B-0 执行记录：备份、清理与空业务基线

**执行阶段：** Phase 3B-0  
**执行日期：** 2026-09-25  
**执行分支：** `phase-03b-real-ui-uat`  
**Phase 3A squash merge SHA：** `154a73792687fbc0d2ccec6359c427c59de16022`  
**Phase 3B branch SHA（建立时）：** `154a73792687fbc0d2ccec6359c427c59de16022`

## 1. 环境确认

- `APP_STAGE=development`（未设置环境变量时由 `DEBUG=true` 得到）。
- `DEBUG=True`。
- 数据库引擎：`django.db.backends.sqlite3`。
- 数据库绝对路径：`D:\Codex项目\森爵照明管理系统\backend\db.sqlite3`。
- 不是 production database；不是远程 PostgreSQL/MySQL。
- 清理前分支：`phase-03b-real-ui-uat`。
- 清理前 HEAD：`154a73792687fbc0d2ccec6359c427c59de16022`。
- 清理前数据库文件大小：`1,675,264` bytes。
- 清理前 read-only SQLite `integrity_check`：`ok`。
- 清理前开发端口无 Django/Vite 监听；未终止无关 Python/Node 进程。

## 2. 备份

- 备份文件：`backend/backups/before-phase3-20260925-161712.sqlite3`
- 源大小：`1,675,264` bytes。
- 备份大小：`1,675,264` bytes。
- 备份 read-only SQLite `integrity_check`：`ok`。
- 备份目录已被现有 `.gitignore` 忽略；没有修改 `.gitignore`，没有将数据库或备份加入 Git。

## 3. 清理前只读计数（before counts）

### 业务模型

| 模型 | 数量 | 模型 | 数量 |
|---|---:|---|---:|
| `crm.OperationLog` | 0 | `crm.Customer` | 51 |
| `crm.CustomerCodeSequence` | 1 | `crm.Contact` | 50 |
| `crm.FollowUp` | 1 | `crm.FollowUpAttachment` | 0 |
| `crm.ProductCategory` | 2 | `crm.CategoryAttribute` | 3 |
| `crm.ProductCodeSequence` | 1 | `crm.HSCode` | 0 |
| `crm.SKUCodeSequence` | 1 | `crm.Product` | 51 |
| `crm.SKU` | 303 | `crm.SKUVersion` | 2 |
| `crm.SKUParameterPlan` | 3 | `crm.SKURelationship` | 0 |
| `crm.SupplierCapability` | 0 | `crm.SupplierCandidateOverride` | 0 |
| `crm.PackagingTemplate` | 1 | `crm.SKUPackagingProfile` | 1 |
| `crm.QuoteNumberSequence` | 12 | `crm.ProductParameter` | 2 |
| `crm.ProductCertificate` | 1 | `crm.Quote` | 201 |
| `crm.QuoteRevisionCounter` | 2 | `crm.QuoteChildRevisionCounter` | 2 |
| `crm.SKUTradeUnit` | 0 | `crm.QuoteItem` | 203 |
| `crm.QuoteImportantNote` | 0 | `crm.Order` | 101 |
| `crm.OrderItem` | 101 | `crm.Supplier` | 3 |
| `crm.SupplierSKU` | 3 | `crm.PurchaseOrder` | 3 |
| `crm.PurchaseCostAllocation` | 2 | `crm.PurchaseOrderItem` | 3 |
| `crm.PaymentPlan` | 202 | `crm.ContractChangeRequest` | 0 |
| `crm.Shipment` | 2 | `crm.PackingPlan` | 0 |
| `crm.PackingPlanCarton` | 0 | `crm.PackingPlanCartonItem` | 0 |
| `crm.ShipmentPackage` | 0 | `crm.ShipmentPackageItem` | 0 |
| `crm.InventoryReservation` | 0 | `crm.InventoryMovement` | 4 |
| `crm.GoodsReceipt` | 2 | `crm.ShipmentItem` | 2 |
| `crm.Transaction` | 3 | `crm.AdvanceAllocation` | 0 |
| `crm.SalesRule` | 0 |  |  |

### 保留模型及系统表

| 模型/表 | 数量 | 保留理由 |
|---|---:|---|
| `auth.User` | 0 | 用户账号；开发身份由配置判定，本次没有账号记录可删除。 |
| `auth.Permission` | 248 | Django 权限定义。 |
| `auth.Group` | 0 | 用户组配置。 |
| `crm.OrganizationUnit` | 12 | 项目明确要求保留组织。 |
| `crm.Position` | 6 | 项目明确要求保留职位。 |
| `crm.AccessRole` | 0 | 角色配置。 |
| `crm.RolePermission` | 0 | 角色权限关系。 |
| `crm.EmployeeProfile` | 0 | 用户与组织/职位/角色关系。 |
| `contenttypes.ContentType` | 62 | Django 系统元数据。 |
| `sessions.Session` | 0 | 登录会话表。 |
| `admin.LogEntry` | 0 | Django 管理系统表。 |
| `django_migrations` | 86 | 迁移历史，禁止删除。 |

## 4. 清理方法与保留白名单

使用一次性 Django ORM 事务（`manage.py shell`）从下游到上游删除业务数据；没有执行直接 SQL DELETE、没有关闭外键、没有删除 SQLite、没有执行全库 `flush`。

删除范围包括客户、联系人、跟进、报价及修订、报价条目/notes、订单及订单行/预留/装箱、采购及成本分配、收货、发货及装箱、库存流水、PaymentPlan、Transaction/拆分/AdvanceAllocation、ContractChangeRequest、产品/SKU/SKUVersion/交易单位/包装、供应商/SupplierSKU/能力/候选 override、编号序列和 OperationLog。

保留范围为用户账号、Django 权限和会话表、组织、职位、角色及角色权限关系、EmployeeProfile、Django content types、migrations，以及项目运行所需系统配置。Excel 报价模板未修改。`backend/media` 未删除任何物理文件。

所有删除操作在同一事务中完成；事务成功提交后才继续验证。残留的 1 条 `PackagingTemplate` 被识别为业务包装档案并单独清除。

## 5. 清理后只读计数（after counts）

所有下列业务模型均为 `0`：

`OperationLog`、`Customer`、`CustomerCodeSequence`、`Contact`、`FollowUp`、`FollowUpAttachment`、`ProductCategory`、`CategoryAttribute`、`ProductCodeSequence`、`HSCode`、`SKUCodeSequence`、`Product`、`SKU`、`SKUVersion`、`SKUParameterPlan`、`SKURelationship`、`SupplierCapability`、`SupplierCandidateOverride`、`PackagingTemplate`、`SKUPackagingProfile`、`QuoteNumberSequence`、`ProductParameter`、`ProductCertificate`、`Quote`、`QuoteRevisionCounter`、`QuoteChildRevisionCounter`、`SKUTradeUnit`、`QuoteItem`、`QuoteImportantNote`、`Order`、`OrderItem`、`Supplier`、`SupplierSKU`、`PurchaseOrder`、`PurchaseCostAllocation`、`PurchaseOrderItem`、`PaymentPlan`、`ContractChangeRequest`、`Shipment`、`PackingPlan`、`PackingPlanCarton`、`PackingPlanCartonItem`、`ShipmentPackage`、`ShipmentPackageItem`、`InventoryReservation`、`InventoryMovement`、`GoodsReceipt`、`ShipmentItem`、`Transaction`、`AdvanceAllocation`、`SalesRule`。

保留数量与清理前一致：`auth.User=0`、`auth.Permission=248`、`auth.Group=0`、`crm.OrganizationUnit=12`、`crm.Position=6`、`crm.AccessRole=0`、`crm.RolePermission=0`、`crm.EmployeeProfile=0`、`contenttypes.ContentType=62`、`sessions.Session=0`、`admin.LogEntry=0`。`django_migrations=86`。

清理后 read-only SQLite `integrity_check=ok`。

## 6. 清理后自动化验证

- Django `check`：PASS。
- `makemigrations --check --dry-run`：PASS（No changes detected）。
- Django 完整测试：287 项已执行；无失败输出，测试数据库已销毁。
- 前端 `npm run test:unit`：57/57 PASS。
- 前端 Node-only typography：1/1 PASS。
- 前端 Vitest：31/31 PASS。
- 前端 `npm run build`：PASS（仅标准 chunk size advisory）。
- 首次启动时 Django/Vite 本地服务健康检查均可访问（记录为 `http://127.0.0.1:8000` 与 `http://127.0.0.1:5191` 返回 200）。本轮真实 UI 复验时，Vite `5191` 返回 200；Django `8000` 端口可响应但根路径返回 404，未将该 HTTP 结果当作 UI 验收。

## 7. media 附件只读盘点

- `backend/media` 文件总数：50。
- 数据库引用的文件：0。
- 孤立文件：50（历史 follow-up attachment 与 SKU image 文件）。
- Phase 3B-0 不删除这些物理文件；后续只有在明确证明属于旧测试业务附件且获得单独授权后才处理。

## 8. UI 空基线（10 项）

Django 与 Vite 已重新启动并进行了只读环境诊断：Vite `http://127.0.0.1:5191` 返回 200；Django `http://127.0.0.1:8000` 端口可响应但根路径返回 404（这不是 UI 通过结果）。随后已使用 Codex 内置浏览器真实点击页面控件完成复验；未创建任何业务数据。

当前数据库只读复核确认所有 CRM 业务模型仍为 `0`，未重新清库、未执行 seed/fixture、未创建任何 Phase 3B 业务数据。

| UI 项目 | 结果 | 说明 |
|---|---|---|
| 开发系统可正常打开并进入主界面 | PASS | 通过内置浏览器打开 `/`，看到“经营概览”和空数据概览。当前 development 配置为 `DEBUG=True`、`DEVELOPMENT_SUPERADMIN=True`、`RBAC_ENFORCEMENT=False`、`AllowAny`，且 `auth.User=0`，没有真实登录/RBAC 流程；登录验收为 N/A，不是业务失败。 |
| 主导航可打开 | PASS | 通过内置浏览器真实点击左侧导航，页面路由可打开。 |
| 客户列表为空 | PASS | 点击“客户管理”，页面显示“客户总数 0”和“还没有数据”。 |
| 产品/SKU 列表为空 | PASS | 分别点击“产品管理”和“SKU 管理”，页面显示“产品总数 0 / 还没有产品”和“SKU 总数 0 / 还没有 SKU”。 |
| 供应商列表为空 | PASS | 点击“供应商管理”，页面显示“供应商总数 0”和“还没有数据”。 |
| 报价列表为空 | PASS | 点击“报价管理”，页面显示“总报价数 0”和“还没有报价”。 |
| 订单列表为空 | PASS | 点击“订单管理”，页面显示“订单总数 0”和“还没有订单”。 |
| 采购列表为空 | PASS | 点击“采购管理”，页面显示“采购单数 0”和“暂无采购单”。 |
| 库存流水为空 | PASS | 点击“库存流水”，页面显示“库存流水总数 0”和“还没有数据”。 |
| 财务流水/PaymentPlan 为空 | PASS | 点击“财务流水”显示“流水笔数 0 / 当前条件下暂无流水”；点击“应收计划”和“应付计划”均显示“计划笔数 0 / 暂无计划”。 |

## 9. 发现的问题与停止点

1. 之前的浏览器自动化阻断已恢复；本轮通过 Codex 内置浏览器真实点击并观察了 10 项 UI 空基线，全部 PASS。
2. 本轮环境诊断确认 Vite `5191` 可访问；Django `8000` 端口可响应但根路径为 404，未以该 HTTP 结果替代 UI 验收。
3. 未发现真实 UI bug：未见 500、白屏、无限 loading、错误 toast、导航打不开或空列表组件异常。
4. `backend/media` 有 50 个未被数据库引用的历史文件；按指令仅记录，未删除。
5. 未发现清库后的数据库完整性、迁移或后端业务测试失败。
6. 本轮未创建客户、产品、SKU、供应商、报价、订单、采购、库存或财务测试数据；未开始 Phase 3B 数据录入，也未开始 Phase 3C。
