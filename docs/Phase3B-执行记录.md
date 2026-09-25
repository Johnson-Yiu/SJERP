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

## 10. Phase 3B-1：基础主数据与第一批订单 A–D

**执行日期：** 2026-09-25
**执行分支：** `phase-03b-real-ui-uat`
**执行方式：** 仅使用 Codex 内置浏览器中的真实页面、按钮、输入框、下拉和弹窗；未使用 APIClient、curl、HTTP API、browser console、fetch、Django shell/ORM 写入、SQL、seed、fixture 或脚本创建业务数据。

### 10.1 分类方案纠偏与真实 UI 操作

上一轮记录的 `REAL BUSINESS BUG-01` 已撤销。当前真实契约和本轮复现结果为：

- `EXPECTED CURRENT CONTRACT-01`：首个 SKU 创建后会建立 published `SKUParameterPlan`；`Product.sku_definitions` 优先读取 published plan，后续 CategoryAttribute 修改不会自动改写已有 Product 的参数 schema。现有测试 `test_category_changes_do_not_change_existing_product_schema` 也覆盖这一契约。
- `UX ISSUE-01`：Product 已存在 published plan、分类模板后来新增/修改属性时，SKU 新建向导仍显示“该产品的分类尚未配置……”，没有说明应前往“参数变更与历史方案”升级 Product schema；本轮升级方案后向导即可识别参数。该 UX 问题本阶段只记录，不修 UI。

全部操作均通过浏览器中的产品详情、SKU 管理、参数方案弹窗和 SKU 表单完成，没有使用 API、数据库写入、seed、fixture 或脚本绕过 UI。

实际参数方案操作：

1. 在 LED Strip 产品的“参数变更与历史方案”中创建 V2 草稿。
2. 通过“新增参数”加入 Length、Color；Length 单位 `mm`；两项均启用 `include_in_sku`、`include_in_sales_model` 和 `required`。
3. 为已有 SKU-000001 填写 Length=`5000`、Color=`Warm White`。
4. “保存草稿并分析”显示 current_count=1、result_count=1、new_count=0，无 missing，原 SKU Code 保留；随后按 UI 确认发布 V2。
5. 发布后已有 SKU 刷新为 `LED Strip-5000mm-Warm White` / `LSTRIP-WW`，SKU Code 保留；新建 SKU 向导已能正常显示 Length/Color。

### 10.2 SKU 覆盖

- LED Strip：通过新建 SKU 向导实际建立 4 个组合（已有 5000mm/Warm White，加新建 3000mm、1000mm、2000mm 三个组合），总计 4 个。
- LED Driver：先在产品编辑 UI 绑定 Lighting Components 分类，再通过向导建立 `LDRIVER-24V1000`、`LDRIVER-48V1000`，总计 2 个。
- Wireless Sensor：先在产品编辑 UI 绑定 Lighting Components 分类，再通过向导建立 `WSENSOR-IN2000`、`WSENSOR-OUT2000`，总计 2 个。
- 所有 8 个 SKU 均已通过 UI 生成 Sales Model 和参数组合；LED Strip 使用单位 `m`，其余使用 `pcs`。
- 一次未填写型号缩写的创建尝试被 UI 明确拒绝（要求为参与生成型号的参数填写 1–8 位缩写）；补齐缩写后创建成功，记录为已验证 UI guard。

### 10.3 供应商、来源与包装

- 供应商：Supplier A、Supplier B、Supplier C，共 3 个，均通过供应商管理 UI 创建。
- 产品级候选来源绑定：LED Strip 绑定 A/C；LED Driver 绑定 B；Wireless Sensor 绑定 B/C；只读盘点得到 `SupplierCandidateOverride=14`。
- 实际 SupplierSKU 来源也通过 SKU 编辑 UI 建立并可回看：
  - SKU-000001 → Supplier A / `SA-LSTRIP-5000`，参考价 USD 4.50，MOQ 10，交期 14 天，首选。
  - SKU-000005 → Supplier B / `SB-LDRIVER-24V1000`，参考价 USD 15，MOQ 5，交期 10 天，首选。
  - SKU-000007 → Supplier C / `SC-WSENSOR-INDOOR`，参考价 USD 20，MOQ 5，交期 12 天，首选。
- 交易单位：8 个 SKU 均通过交易单位 UI 建立了卷/箱换算；当前 `SKUTradeUnit=10`，其中 SKU-000001 有重复 Roll-50、SKU-000002 有重复 Roll-30，均保留并记录，不通过数据库删除。
- 包装：通过包装管理 UI 建立 `LED General Carton`（Supplier A、60×40×30 cm、皮重 1.2 kg、整箱优先）；当前模板存在，但尚未通过 UI 关联到 SKU，记为本批 UI coverage gap，不用数据库补写。

### 10.4 报价 A–D

通过报价管理 UI 建立 4 个原始报价（Quote ORM 行数为 8，包含修订/子记录）：

| 场景 | 报价编号 | 客户 | 币种 | 状态 | 内容/总额 |
|---|---|---|---|---|---|
| Quote A | `SJ20260925US001` | Customer A | USD | 已发送 | LED Strip，5，含运费/折扣；USD 77.50 |
| Quote B | `SJ20260925DE001` | Customer B | CNY | 已接受 | LED Driver，10；CNY 255.00 |
| Quote C | `SJ20260925SG001` | Customer C | EUR | 草稿 | Wireless Sensor，2；EUR 85.00 |
| Quote D | `SJ20260925AU001` | Customer D | GBP | 已发送 | LED Driver，3；GBP 100.00 |

Quote B 在保存时通过“保存并导出 Excel”触发过真实 UI 导出；随后在报价列表点击“导出 SJ20260925DE001”。浏览器自动化通道没有暴露 download event 或本地文件路径，因此本记录只确认“导出动作已触发”，不宣称已经验证文件落盘/解析。

### 10.5 订单 A–D

通过订单管理 UI 建立并检查 4 个原始订单：

| 场景 | 订单号 | 来源 | 客户 | 币种 | 状态 | 总额 |
|---|---|---|---|---|---|---:|
| Order A | `SO-2026-21939` | Quote A | Customer A | USD | 已确认 | USD 170 |
| Order B | `SO-2026-52556` | Quote B | Customer B | CNY | 生产中 | CNY 265 |
| Order C | `SO-2026-77325` | Quote C | Customer C | EUR | 已完成 | EUR 170 |
| Order D | `SO-2026-42504` | Quote D | Customer D | GBP | 已确认 | GBP 190 |

Order C 首次尝试直接以“已完成”创建时被 UI guard 拒绝（提示新合同需从草稿或已确认/已下单开始）；随后先创建已确认订单，再通过已有订单编辑 UI 设置为“已完成”成功。这与当前契约一致，也说明 `completed` 目前仍可人工选择；没有将其记录为业务 bug。

### 10.6 库存与本批异常场景

- 通过库存流水 UI 建立 1 条盘盈入库：SKU-000001，数量 100 `m`，单位成本 5，仓库 Main Warehouse，引用 `UAT-INV-A`，备注为 Phase 3B 初始库存；流水号 `IM-970061BEB5B24A0C`。
- 已验证的 UI guard：SKU 型号缩写缺失时创建被阻止；Order C 直接创建“已完成”被阻止后按正常状态流转成功。
- 本批没有通过 UI 创建采购单、收货、发货或财务流水；这些场景仍待当前 Phase 3B-1 的后续真实 UI 操作完成，不能以已有数量推断通过。

### 10.7 当前只读盘点

只读 ORM 复核未执行任何写入，结果如下：

| 模型 | 数量 | 说明 |
|---|---:|---|
| Customer / Contact | 4 / 5 | A–D 客户，A 有 2 个联系人 |
| Product / ProductCategory / CategoryAttribute | 3 / 1 / 2 | Lighting Components、Length、Color |
| SKU / SKUParameterPlan / SKUVersion | 8 / 4 / 2 | 8 个销售组合；发布方案/历史版本保留 |
| Supplier / SupplierCandidateOverride / SupplierSKU | 3 / 14 / 3 | 候选绑定与实际来源分开记录 |
| Quote / 原始 Quote | 8 / 4 | 8 行含修订；4 个原始报价 |
| Order | 4 | A–D |
| InventoryMovement | 1 | +100 m |
| PackagingTemplate | 1 | 尚未关联 SKU |
| SKUTradeUnit | 10 | 8 个 SKU 覆盖，含一次重复记录 |
| PurchaseOrder / GoodsReceipt / Shipment | 0 / 0 / 0 | 尚未开始该批采购/履约流程 |
| PaymentPlan / Transaction | 4 / 0 | 订单创建产生的计划；尚未开始收款/核销流水 |

### 10.8 当前范围与下一步

- 本轮已完成参数方案纠偏、8 个 SKU、3 个供应商、3 个实际 SupplierSKU 来源、交易单位、包装模板、Quote A–D、Order A–D 和 1 条库存调整，均由真实 UI 操作产生。
- `EXPECTED CURRENT CONTRACT-01` 与 `UX ISSUE-01` 已替代上一轮错误的 `REAL BUSINESS BUG-01`；没有确认新的生产业务 bug。
- 包装模板尚未关联 SKU、Quote B Excel 下载未能在浏览器通道验证落盘，以及采购/收货/发货/财务仍未执行，均是当前 Phase 3B-1 的未完成项或 UI coverage gap，不通过 API/DB 补齐。
- 不开始 Phase 3B-2；后续只继续 Phase 3B-1 尚未完成的真实 UI 场景。

### 10.9 回归验证

- `python manage.py check`：PASS。
- `python manage.py makemigrations --check --dry-run`：PASS（No changes detected）。
- `python manage.py test`：287/287 PASS。
- `npm run test:unit`：57/57 PASS。
- `node --test tests/detail-drawer-typography.spec.js`：1/1 PASS。
- `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js`：31/31 PASS。
- `npm run build`：PASS。
