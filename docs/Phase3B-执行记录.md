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

1. LED Strip 通过参数方案 UI 创建并发布 V3：Length/Color 的历史字段分别重命名为 Voltage（V）/CCT（K），新增 Width（mm），三项均按实际 SKU/销售型号/必填规则配置。
2. 现有 4 个组合通过草稿、分析、发布流程保留原 SKU Code，并更新为 `24V/3000K/8mm`、`24V/4000K/8mm`、`24V/6000K/8mm`、`12V/3000K/5mm`。
3. LED Driver 发布 V2：Output Voltage（V）、Power（W）、Color；保留 2 个组合 `24V/60W/White`、`48V/100W/White`。
4. Wireless Sensor 发布 V2：Mode、Voltage（V）；保留 2 个组合 `Indoor/5V`、`Outdoor/5V`。
5. 三次分析均显示 current_count=result_count、new_count=0、无 missing；发布后的新建 SKU 向导可识别对应已发布方案。SKU 描述也通过 SKU 编辑 UI 刷新为当前参数语义，历史版本保留。

### 10.2 SKU 覆盖

- LED Strip：4 个实际组合为 `LED Strip-24V-3000K-8mm`、`LED Strip-24V-4000K-8mm`、`LED Strip-24V-6000K-8mm`、`LED Strip-12V-3000K-5mm`。
- LED Driver：2 个实际组合为 `LED Driver-24V-60W-White`、`LED Driver-48V-100W-White`。
- Wireless Sensor：2 个实际组合为 `Wireless Sensor-Indoor-5V`、`Wireless Sensor-Outdoor-5V`。
- 所有 8 个 SKU 均已通过 UI 生成 Sales Model 和参数组合；LED Strip 使用单位 `m`，其余使用 `pcs`。
- 一次未填写型号缩写的创建尝试被 UI 明确拒绝（要求为参与生成型号的参数填写 1–8 位缩写）；补齐缩写后创建成功，记录为已验证 UI guard。

### 10.3 供应商、来源与包装

- 供应商：Supplier A、Supplier B、Supplier C，共 3 个，均通过供应商管理 UI 创建。
- 产品级候选来源绑定：LED Strip 绑定 A/C；LED Driver 绑定 B；Wireless Sensor 绑定 B/C；只读盘点得到 `SupplierCandidateOverride=14`。
- 实际 SupplierSKU 来源均通过 SKU 编辑 UI 建立并可回看。最终业务矩阵为：SKU-000001 仅 Supplier A；SKU-000002 为 Supplier A+B；SKU-000003 为 Supplier A+B+C；SKU-000004 无启用 SupplierSKU。SKU-000005/006/007/008 另有实际来源供订单分配使用。E05 曾由采购 UI 自动建立 `AUTO-SKU-000004`，随后仅通过 UI 停用，保留历史证据。
- 交易单位：SKU-000001 保留启用 Roll-50，并新增启用 Roll-5m（factor=5）与 Roll-10m（factor=10），均 `allow_fraction=false`；SKU-000001 的重复 Roll-50、SKU-000002 的重复 Roll-30 均通过 UI 停用而未删除。E08 临时创建的 0.5m factor 规格也已通过 UI 停用；该观察记录为“factor 可输入小数，需区分 factor 与包装数量规则”，不在本轮修改业务代码。
- 包装：通过包装管理 UI 建立 `LED General Carton`（Supplier A、60×40×30 cm、皮重 1.2 kg、整箱优先）；当前模板存在，但尚未通过 UI 关联到 SKU，记为本批 UI coverage gap，不用数据库补写。

### 10.4 报价 A–D

通过报价管理 UI 建立 4 个原始报价（Quote ORM 行数为 8，包含修订/子记录）：

| 场景 | 报价编号 | 客户 | 币种 | 状态 | 内容/总额 |
|---|---|---|---|---|---|
| Quote A | `SJ20260925US001` | Customer A | USD | 已发送 | LED Strip，5，含运费/折扣；USD 77.50 |
| Quote B | `SJ20260925DE001` | Customer B | CNY | 已接受 | LED Driver，10；CNY 255.00 |
| Quote C | `SJ20260925SG001` | Customer C | EUR | 草稿 | Wireless Sensor，2；EUR 85.00 |
| Quote D | `SJ20260925AU001` | Customer D | GBP | 已发送 | LED Driver，3；GBP 100.00 |

Quote B 最终修订 `SJ20260925DE001-1-1` 已通过报价列表真实点击“导出”；浏览器自动化通道没有暴露 download event 或本地文件路径，Windows Downloads 目录也未出现可核验文件，因此记录为 `TEST INFRASTRUCTURE BLOCKER-PI-01`，不宣称 PI 文件落盘/解析通过。

### 10.5 订单 A–D

通过订单管理 UI 建立并检查 4 个原始订单：

| 场景 | 订单号 | 来源 | 客户 | 币种 | 状态 | 总额 |
|---|---|---|---|---|---|---:|
| Order A | `SO-2026-21939` | Quote A | Customer A | USD | 已确认 | USD 170 |
| Order B | `SO-2026-52556` | Quote B 最终修订 | Customer B | CNY | 生产中 | CNY 640 |
| Order C | `SO-2026-77325` | Quote C 最终修订 | Customer C | EUR | 已确认 | EUR 215 |
| Order D | `SO-2026-42504` | Quote D | Customer D | GBP | 已确认 | GBP 190 |

Order C 首次尝试直接以“已完成”创建时被 UI guard 拒绝（提示新合同需从草稿或已确认/已下单开始）；随后先创建已确认订单，再通过已有订单编辑 UI 设置为“已完成”成功。这与当前契约一致，也说明 `completed` 目前仍可人工选择；没有将其记录为业务 bug。

本轮随后通过订单编辑 UI 将 Order C 恢复为已确认并补齐第二个 SKU；在“采购与发货”页为两行分别分配 Supplier A、Supplier B（均 `order_only`）。Order D 的同一 SKU 先分配 Supplier A（`recommended`），再切换为 Supplier B（`order_only`），页面保留最终来源快照。

### 10.6 库存与本批异常场景

- 通过库存流水 UI 建立 SKU-000001 +100 `m` 初始库存；又为 SKU-000002 通过 UI 建立 +2 `m` 调整。Order A 履约页显示 10/10 可预留；Order B 三行分别显示 SKU-000001 5/5、SKU-000002 2/5、SKU-000005 0/10，覆盖 full/partial/none。
- 通过采购管理 UI 创建 9 张采购单（覆盖 Supplier A/B/C、Order A/B/C/D 及无订单的 SKU-000004 E05 场景），并对 PO-20260925-231818 登记 10 `m` 合格入库；采购页显示入库记录、剩余数量归零和可冲销按钮。
- 已验证的 UI guard：SKU 型号缩写缺失时创建被阻止；Order C 直接创建“已完成”被阻止后按正常状态流转成功。
- E01：报价缺少客户时点击保存，UI 显示“请选择客户”，未创建数据（PASS）。E03：重复 LED Strip 组合在新建 SKU 向导中显示“已有相同 SKU，请使用现有记录”，创建勾选 disabled（PASS）。E05：无显式 SupplierSKU 的采购 UI 明确显示“保存采购单时建立此供应商的供货档案”，实际生成 AUTO 来源后已通过 UI 停用并记录。E06：已维护 MOQ=5 的来源以数量 1 的采购单成功保存，当前未确认 MOQ 为采购强制约束。E07：重复交易单位通过 UI 停用保留历史。
- E08（正确场景）：在 Quote UI 选择 SKU-000001 的 Roll-5m（`allow_fraction=false`），输入 `1.5` 卷并点击保存；UI 保留编辑器、未创建报价，页面出现“1.5 卷 = 7.5 m；此规格仅支持整包装”，但错误 toast 实际显示为 `[object Object]`。随后改为 `1` 卷保存成功，生成 `SJ20260925US002`，金额 USD 10.00。该场景证明业务保存被阻止且没有错误业务记录，同时记录错误信息展示不清晰的 UI observation。
- E34（正确场景）：通过客户 UI 创建并保留 `Customer Unsupported Country`，country=`Sweden`；Quote UI 选择该客户和正常 SKU 后点击保存，显示 `Unsupported country: Sweden`，编辑器保持打开，Quote 数量未增加（只读查询确认该客户没有 Quote）。

### 10.7 当前只读盘点

只读 ORM 复核未执行任何写入，结果如下：

| 模型 | 数量 | 说明 |
|---|---:|---|
| Customer / Contact | 5 / 6 | A–D 客户，另有 E34 临时 Sweden 客户 |
| Product / ProductCategory / CategoryAttribute | 3 / 1 / 2 | Lighting Components、Length、Color |
| SKU / SKUParameterPlan / SKUVersion | 8 / 7 / 17 | 8 个销售组合；三套产品的发布方案/历史版本保留 |
| Supplier / SupplierCandidateOverride / SupplierSKU | 3 / 14 / 15（14 active） | 实际来源矩阵与 E05 停用 AUTO 来源分开记录 |
| Quote / 原始 Quote | 11 / 5 | 4 个正式原始报价、E08 合法保存的临时报价及修订链 |
| Order | 4 | A–D |
| InventoryMovement | 3 | +100 m SKU-000001、+2 m SKU-000002、+10 m receipt |
| PackagingTemplate | 1 | 尚未关联 SKU |
| SKUTradeUnit | 13 | 8 个 SKU 覆盖；重复项与 E08 临时项均保留但已停用 |
| PurchaseOrder / GoodsReceipt / Shipment | 9 / 1 / 0 | 9 张采购单、1 次收货；发货尚未开始 |
| PaymentPlan / Transaction | 22 / 0 | 订单修订产生的计划；尚未开始收款/核销流水 |

### 10.8 当前范围与下一步

- 本轮已完成参数方案纠偏、8 个 SKU、3 个供应商及实际来源矩阵、交易单位、包装模板、Quote A–D、Order A–D、9 张采购单、1 次收货和库存覆盖，均由真实 UI 操作产生。
- `EXPECTED CURRENT CONTRACT-01` 与 `UX ISSUE-01` 已替代上一轮错误的 `REAL BUSINESS BUG-01`；没有确认新的生产业务 bug。
- 包装模板尚未通过 UI 关联到 SKU，记录为 `UI COVERAGE GAP-PACKAGING-01`；Quote B PI 文件记录为 `TEST INFRASTRUCTURE BLOCKER-PI-01`。发货、收款/核销及其余异常矩阵仍未执行，不通过 API/DB 补齐。
- 不开始 Phase 3B-2；后续只继续 Phase 3B-1 尚未完成的真实 UI 场景。

### 10.9 回归验证

- `python manage.py check`：PASS。
- `python manage.py makemigrations --check --dry-run`：PASS（No changes detected）。
- `python manage.py test`：287/287 PASS。
- `npm run test:unit`：57/57 PASS。
- `node --test tests/detail-drawer-typography.spec.js`：1/1 PASS。
- `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js`：31/31 PASS。
- `npm run build`：PASS。

### 10.10 Phase 3B-1 最后四项证据

#### Quote → Order revision evidence

只读 ORM 逐条核对 `Order.customer == Order.quote.customer`、订单实际指向 linked revision，且 linked quote total 与 order total 相等；原始报价金额保持不变。

| Scenario | Order No | Order Total | Original Quote No / Total | Linked Quote ID | Linked Quote No / Total | Root Quote No | Parent Quote No | Revision No |
|---|---|---:|---|---:|---|---|---|---:|
| A | `SO-2026-21939` | USD 170.00 | `SJ20260925US001` / USD 77.50 | 273 | `SJ20260925US001-1` / USD 170.00 | `SJ20260925US001` | `SJ20260925US001` | 1 |
| B | `SO-2026-52556` | CNY 640.00 | `SJ20260925DE001` / CNY 255.00 | 278 | `SJ20260925DE001-1-1` / CNY 640.00 | `SJ20260925DE001` | `SJ20260925DE001-1` | 2 |
| C | `SO-2026-77325` | EUR 215.00 | `SJ20260925SG001` / EUR 85.00 | 277 | `SJ20260925SG001-1-1` / EUR 215.00 | `SJ20260925SG001` | `SJ20260925SG001-1` | 2 |
| D | `SO-2026-42504` | GBP 190.00 | `SJ20260925AU001` / GBP 100.00 | 276 | `SJ20260925AU001-1` / GBP 190.00 | `SJ20260925AU001` | `SJ20260925AU001` | 1 |

未发现 linked quote total 与 order total 不一致，未触发 `REAL BUSINESS BUG` 停止条件。

#### Order D supplier scope evidence

| 阶段 | 订单行供应商 | scope | SKU preferred SupplierSKU |
|---|---|---|---|
| before | Supplier B / `SB-LDRIVER-48V100` | `order_only` | Supplier A / `SA-LDRIVER-48V100` |
| after `recommended` | Supplier B / `SB-LDRIVER-48V100` | `recommended` | Supplier B / `SB-LDRIVER-48V100` |

两次均通过 Order Detail → 采购与发货 → Supplier Allocation UI 完成；未通过数据库修改 preferred，订单行仍为 Supplier B。未发现供应商范围不变量问题。

#### A/B inventory invariant evidence

以下为只读 ORM 服务层指标（`actual`、SKU 级 active reservation、`available=actual-reserved`、订单行 `to_procure/shipped/remaining`）；订单页同时确认了订单行 reservation。由于后续采购/收货已改变状态，表中是当前状态，早期基线另行保留在 10.6。

| Order / SKU | ordered | actual | reserved (SKU active) | available | to_procure | shipped | remaining | 订单行 reservation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A / SKU-000001 | 10 | 110 | 15 | 95 | 0 | 0 | 10 | 10（full） |
| B1 / SKU-000005 | 10 | 0 | 0 | 0 | 0 | 0 | 10 | 0（zero） |
| B2 / SKU-000001 | 5 | 110 | 15 | 95 | 0 | 0 | 5 | 5（full） |
| B3 / SKU-000002 | 5 | 2 | 2 | 0 | 0 | 0 | 5 | 2（partial） |

`available = actual - reserved` 对所有 SKU 成立；B1/B2/B3 的 full/partial/none 是初始 UI 验证语义，当前 `to_procure` 已因后续采购单存在而归零。未为恢复旧状态而改写数据库。
