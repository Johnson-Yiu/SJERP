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
- E08（正确场景）：在 Quote UI 选择 SKU-000001 的 Roll-5m（`allow_fraction=false`），输入 `1.5` 卷并点击保存；UI 保留编辑器、未创建报价，页面出现“1.5 卷 = 7.5 m；此规格仅支持整包装”，但错误 toast 实际显示为 `[object Object]`。随后改为 `1` 卷保存成功，生成 `SJ20260925US002`，金额 USD 10.00。该场景证明业务保存被阻止且没有错误业务记录；错误 toast 记录为 `UX ISSUE-02`，本轮不修。
- E34（回归通过）：在修复分支合并并重启当前分支 Django 服务后，通过 Quote UI 选择既有 `Customer Unsupported Country`（country=`Sweden`）和正常 SKU，点击保存成功，生成 `SJ20260925SE001`，金额 USD 10.00。随后通过客户 UI 创建并保留 `Customer Atlantis Unsupported`（country=`Atlantis`），Quote UI 选择该客户和正常 SKU 后点击保存，显示 `Unsupported country: Atlantis`，编辑器保持打开且未创建报价。`REAL BUSINESS BUG` 已修复并通过 UI regression。

### 10.7 当前只读盘点

只读 ORM 复核未执行任何写入，结果如下：

| 模型 | 数量 | 说明 |
|---|---:|---|
| Customer / Contact | 6 / 7 | A–D 客户，另有 E34 Sweden 客户与 Atlantis 测试客户 |
| Product / ProductCategory / CategoryAttribute | 3 / 1 / 2 | Lighting Components、Length、Color |
| SKU / SKUParameterPlan / SKUVersion | 8 / 7 / 17 | 8 个销售组合；三套产品的发布方案/历史版本保留 |
| Supplier / SupplierCandidateOverride / SupplierSKU | 3 / 14 / 15（14 active） | 实际来源矩阵与 E05 停用 AUTO 来源分开记录 |
| Quote / 原始 Quote | 12 / 6 | 4 个正式原始报价、E08 合法保存的临时报价、E34 Sweden 回归报价及修订链 |
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
- `python manage.py test`：288/288 PASS。
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

## 11. Phase 3B-2：部分收货、部分发货与履约冲销

**执行日期：** 2026-09-26
**执行分支：** `phase-03b-real-ui-uat`
**执行方式：** 只使用内置浏览器中的真实页面、按钮、输入框、下拉和弹窗；没有使用 APIClient、curl、Postman、browser console、fetch、Django shell/ORM 写入、SQL、seed、fixture 或脚本创建/修改业务数据。以下 ORM 内容仅为最终只读复核。

### 11.1 Order E：部分收货与部分发货

| 项目 | 结果 |
|---|---|
| 来源报价 | `SJ20260925US003` |
| 订单 | `SO-20260926-281-2A82B3`，Customer A Lighting Ltd，USD 110.00 |
| 采购单 | `PO-20260925-013407`，Supplier A，状态最终为 `completed` |
| 订单行 | SKU-000007 / 10 pcs；SKU-000008 / 20 pcs；两行均通过 Supplier Allocation UI 选择 Supplier A |

SKU-000007 先通过采购 UI 收货 4，再收剩余 6；页面实际显示 `采购 10.00 · 已到 4.00 · 剩余 6.00`，随后显示 `已到 10.00 · 剩余 0.00`。SKU-000008 通过同一采购单一次收货 20，页面显示 `已到 20.00 · 剩余 0.00`。

之后通过订单工作台真实 UI 分两批发 SKU-000007（4、6），再发 SKU-000008（20）。订单页最终显示 `已发货`、已发 30、待发 0；没有重复 Shipment。

只读 movement 链：

| 业务记录 | 原始 movement | 数量 | source_type | 结果 |
|---|---:|---:|---|---|
| GoodsReceipt 47 / SKU-000007 | 95 | 4 | `receipt` | 保留 |
| GoodsReceipt 48 / SKU-000007 | 96 | 6 | `receipt` | 保留 |
| GoodsReceipt 49 / SKU-000008 | 97 | 20 | `receipt` | 保留 |
| Shipment 44 / `SH-82F6FA6CD7084785` | 98 | 4 | `shipment` | confirmed |
| Shipment 45 / `SH-1C7772774F2D4482` | 99 | 6 | `shipment` | confirmed |
| Shipment 46 / `SH-90497A92ED584B1B` | 100 | 20 | `shipment` | confirmed |

### 11.2 Order F：Receipt → Reversal → Re-receipt

正式 F 场景严格通过 Quote→Order 完成：

| 项目 | 结果 |
|---|---|
| Quote | `SJ20260925DE002`，Customer B GmbH，USD 10.00，已接受 |
| Order | `SO-20260926-282-A5565B`，由上述报价工作台“转为订单”生成，已确认 |
| PO | `PO-20260925-020722`，Supplier A，最终 `completed` |
| PO 行 | SKU-000001，ordered 1.00，最终 received 1.00，remaining 0.00 |

首次收货后通过 UI 验证 PO 为已完成、received=1、remaining=0；GoodsReceipt `52` 的原始 `purchase_in` movement 为 `108`。填写原因 `UAT formal receipt reversal` 后执行冲销，原 Receipt 和 movement 均保留，Receipt 显示“已冲销”，并生成 compensating `adjust_out` movement `109`；再次打开同一 Receipt 时 UI 不再提供普通“冲销”按钮（E14 UI GUARD）。随后通过正常收货 UI 新建 GoodsReceipt `53`，对应新的 `purchase_in` movement `110`，PO 恢复为 received=1、remaining=0。

本场景另观察到 E16：冲销原因为空时“确认冲销”按钮保持 disabled，未产生任何记录。收货确认、冲销和重新收货均只产生预期数量的记录。

### 11.3 Order G：Shipment → Reversal → Re-shipment

| 项目 | 结果 |
|---|---|
| Order | `SO-2026-01061`，Customer C Pte Ltd，SKU-000001，ordered 2.00，confirmed |
| 原始 Shipment | `SH-210A99D443934564`，Shipment id 47，2.00，confirmed |
| 原始 movement | `104`，`sale_out`，`source_type=shipment` |
| 冲销结果 | Shipment 保留并变为 `cancelled`；生成 `adjust_in` movement `105`，原因 `Phase 3B-2 shipment reversal UAT` |
| 重新发货 | 新 Shipment `SH-AF3C12D68AA544D3`（id 48），新 `sale_out` movement `106`，2.00，confirmed |

冲销后订单回到可发货状态，UI 再次发货后恢复为 `shipped`；原 Shipment、已冲销 Shipment 与新 Shipment 同时保留。E18 UI GUARD 已确认：已冲销 Shipment 不再显示普通“冲销”按钮。

### 11.4 E09–E20 本批实际结果

本批另建立独立的 `OVERAGE-UAT` 订单，避免复用正式 E/F/G 场景：Customer A Lighting Ltd，SKU-000001，ordered=1、shipped=0、remaining=1；执行前 SKU 库存只读基线为 `actual=108`、`reserved=17`、`available=91`，该订单 Shipment 数量为 0、订单 movement 数量为 0。库存充足且未被库存不足保护触发。

| 场景 | Execution / 实际结果 | 数据结果 |
|---|---|---|
| E09 库存不足发货 | 在 `SO-2026-77325` 的 SKU-000008 上通过 UI 提交 1 pcs，页面显示“库存不足，不能确认发货” | Shipment、`sale_out`、库存、reservation、shipped 数量均无变化 |
| E10 超额发货无理由 | 在独立 `OVERAGE-UAT` 中通过真实发货 UI 输入 2（待发 1），保持“超发原因”为“请选择”并提交；页面拒绝并停留在确认弹窗 | 无 Shipment、无 `sale_out`、无 movement；订单仍 shipped=0、remaining=1，SKU 库存与 reservation 不变；本次失败原因为缺少 overage_reason，而非库存不足 |
| E11 超额发货有理由 | 在同一 `OVERAGE-UAT` 中输入 2，选择“赠品或样品”（`gift_or_sample`）并确认发货；页面成功生成 1 个 Shipment，包含正常 1 + 超发 1 两条明细 | Shipment `SH-3AAD8D5602EA422C`（id=50）为 confirmed；ShipmentItem 53 为正常 1、movement 111；ShipmentItem 54 为 `is_overage=true`、`overage_reason=gift_or_sample`、movement 112 同样标记。订单拆为两个各 1 的明细行，状态为 shipped |
| E12 收货 0 / 负数 | 收货表单输入 0、-1 时确认按钮 disabled | 无 GoodsReceipt、无 InventoryMovement |
| E13 超过剩余可收数量 | 在已完成 PO 上输入超过 remaining 的数量，确认按钮 disabled | 无部分写入 |
| E14 Receipt 二次冲销 | 正式 F Receipt 冲销后重新打开 | UI 不再提供冲销入口，历史保留 |
| E15 下游发货后 Receipt reversal | 对 Order E 的 SKU-000008 Receipt（20 已全部发货）提交冲销 | 弹窗显示“当前 SKU 实际库存不足以冲销，请先处理后续出库”，Receipt/PO/Shipment/库存/reservation 无变化 |
| E16 空冲销原因 | Receipt reversal 空原因 | 确认按钮 disabled |
| E17 | 本批不执行，留给 Phase 3C 自动化不变量测试 | — |
| E18 Shipment 二次冲销 | 正式 G 原始 Shipment 冲销后重新打开 | UI 不再提供冲销入口，历史保留 |
| E19 overage Shipment reversal guard | 在 `OVERAGE-UAT` 发货记录中重新打开该 overage Shipment | 页面明确显示“包含超发/增补，暂不能直接冲销”，普通“冲销”按钮数量为 0；未调用 API 或服务层 reversal |
| E20 completed Order + Shipment reversal | 独立订单 `SO-2026-40674` 先真实 UI 发货 1，再人工设置 `completed`，尝试冲销 Shipment `SH-EA92CC3A20B5483F` | 页面显示“已完成或已取消的订单不能冲销发货”，Shipment/库存/Order/shipped 数量不变，无 `adjust_in`；记录 `STATE-MACHINE GAP-01` 组合行为 |

E38 仅做正常 UI 观察：收货 0/负数时提交控件 disabled；本次 E11 点击“确认发货”后按钮立即出现 disabled 属性，最终只产生 1 个 Shipment（id=50），没有用脚本并发或人为双击攻击。

### 11.5 履约库存不变量（最终只读状态）

服务层只读指标定义为 `actual = signed_inventory_quantity`、`reserved = active reservation`、`available = actual - reserved`。本批最终状态（包含并发订单与历史业务数据）如下：

其中 Order G、正式 Order F、E20 三行的 SKU-000001 数字是执行独立 OVERAGE-UAT 前的正式场景快照；独立场景改变全局库存后的当前值以 OVERAGE-UAT 的 E11 前/后两行记录为准。

| SKU / 订单上下文 | actual | reserved | available | Order ordered / shipped / remaining |
|---|---:|---:|---:|---|
| SKU-000007（Order E 已发完；辅助 Order F 仍保留 4） | 4 | 4 | 0 | Order E 10 / 10 / 0 |
| SKU-000008（Order E 已发完） | 0 | 0 | 0 | Order E 20 / 20 / 0 |
| SKU-000001（Order G 重发后） | 108 | 16 | 92 | Order G 2 / 2 / 0 |
| SKU-000001（正式 Order F） | 108 | 16 | 92 | Order F 1 / 0 / 1 |
| SKU-000001（E20 completed guard） | 108 | 16 | 92 | E20 1 / 1 / 0 |
| SKU-000001（独立 OVERAGE-UAT，E11 前） | 108 | 17 | 91 | OVERAGE-UAT 1 / 0 / 1 |
| SKU-000001（独立 OVERAGE-UAT，E11 后） | 106 | 16 | 90 | OVERAGE-UAT 两行各 1 / 1 / 0 |

所有列均满足 `available = actual - reserved`，没有出现负数。独立 OVERAGE-UAT 中 actual 从 108 减至 106，恰为本次 Shipment 总数量 2；reserved 从 17 变为 16，available 从 91 变为 90。正式 F 的 Receipt 链为 `purchase_in 108 → adjust_out 109`，再收货为新的 `purchase_in 110`；正式 G 的 Shipment 链为 `sale_out 104 → adjust_in 105`，再发货为新的 `sale_out 106`。原始 movement 未被删除或覆盖，冲销 movement 通过 Receipt/Shipment reversal 字段及 reference 可追溯。

### 11.6 本批问题分类与停止点

- `REAL BUSINESS BUG`：0。E09/E10/E15/E20 均按当前库存、原因或状态保护工作，且失败后无部分写入；E11 合法 overage 正常完成，E19 UI guard 正常阻止冲销。
- `UI COVERAGE GAP`：1，延续 `UI COVERAGE GAP-PACKAGING-01`；本批没有声称完整 packing workflow 已通过。
- `UX ISSUE`：2，延续 `UX ISSUE-01` 与 `UX ISSUE-02`；本批没有修改 UI。
- `TEST INFRASTRUCTURE BLOCKER`：1，延续 `TEST INFRASTRUCTURE BLOCKER-PI-01`。
- `EXPECTED CURRENT CONTRACT`：1，延续 `EXPECTED CURRENT CONTRACT-01`。

本批已完成 E/F/G 及 E09–E20 中属于真实 UI ACTION/UI GUARD 的项目；E17、E21、E40、E41 未执行，留给 Phase 3C temporary test database。停止进入 H–T、财务收款、advance、void 或 cost-allocation 后续专项。

### 11.7 Phase 3B-2 回归验证

本批回归已执行并通过：后端 `check`、`makemigrations --check --dry-run`、完整 `python manage.py test`（288/288）；前端 unit（57/57）、Node-only typography（1/1）、Vitest（31/31，排除 Node-only）与 build 均通过。业务代码、测试、CI、数据库模型和迁移均未修改。E10、E11、E19 已形成完整闭环，Phase 3B-2 已完成并封版。

## 12. Phase 3B-3：Finance H–K

**执行日期：** 2026-09-26
**执行分支：** `phase-03b-real-ui-uat`
**执行方式：** Order、Quote、收款、核销与作废均通过内置浏览器中的真实页面、按钮、输入框、下拉和弹窗完成；未使用 APIClient、curl、Postman、fetch、browser console、Django shell/ORM 写入、SQL、seed、fixture 或脚本创建/修改业务数据。以下 ORM 内容仅为最终只读复核。

### 12.1 H/J 基础订单

| 场景 | Quote | Order | Customer / Currency | Total | PaymentPlan |
|---|---|---|---|---:|---|
| Order H | `SJ20260926US001` | `SO-20260926-283-4CD49B`（id=157） | Customer A Lighting Ltd / USD | 30.00 | id=379，planned=30.00，settled=0.00，remaining=30.00，open |
| Order J | `SJ20260926US002` | `SO-20260926-284-022A30`（id=158） | Customer A Lighting Ltd / USD | 25.00 | id=380，planned=25.00，settled=0.00，remaining=25.00，open |

两个订单均由接受状态 Quote 通过“转为订单”创建，状态为 `confirmed`，客户、币种和 PaymentPlan 方向均一致。

### 12.2 H：两次独立客户收款

第一次通过“应收计划 → 登记收款”完成：

| 项目 | 结果 |
|---|---|
| Receipt #1 | Transaction id=106，`FIN-DD28FFE2D90D408A`，`customer_receipt`，20.00 USD，confirmed，plan=379 |
| H 第一次收款后 | plan 379 settled=20.00，remaining=10.00，status=open；Order H paid=20.00，remaining receivable=10.00 |

第二次通过“财务流水 → 新增记账 → 客户收款”关联 Order H，实际输入 20.00 USD。系统将该单现金事件拆为：

| 链节点 | Transaction | kind | amount | plan / split_from | status |
|---|---|---|---:|---|---|
| Receipt #2 root | id=107，`FIN-B2230197D6014812` | `customer_receipt` | 10.00 | plan=379 | confirmed（作废前） |
| 超额 child | id=108，`ADV-81802819CDD1478B` | `unallocated_advance` | 10.00 | split_from=107，未关联计划 | confirmed（作废前） |

root 与 child 合计 20.00 USD，等于第二次实际收款金额。第二次收款后 H 的 plan 379 为 settled=30.00、remaining=0.00、status=settled，Order H paid=30.00；第一次 Receipt #1 仍独立存在。

E22 UI GUARD：打开 child `ADV-81802819CDD1478B` 时没有独立“作废”按钮，页面显示“由原始流水统一作废”，通过。

### 12.3 J：预收款核销与 E31/E32

打开 child 的“核销”弹窗后，候选计划仅显示同一往来方、同一 USD、receivable、open 计划；列表没有其他客户、其他币种或应付计划，E31 UI GUARD 通过。Order J 的 plan 380 在候选列表中。

先输入 11.00 USD（超过 advance 未分配余额 10.00），页面拒绝并显示“分配金额不能超过未分配余额”，没有生成 AdvanceAllocation，advance 与 plan 均不变，E32 超额核销通过。

随后输入合法 10.00 USD 并确认：

| 项目 | 结果 |
|---|---|
| AdvanceAllocation | id=2，advance=108，plan=380，amount=10.00，`is_active=true` |
| Advance child | allocated_amount=10.00，未核销余额=0.00 |
| Order J plan 380 | settled=10.00，remaining=15.00，status=open |
| Order J | paid=10.00；未新增现金 Transaction |

核销提交按钮在点击后立即 disabled，最终只有 1 条 allocation。

### 12.4 K：作废第二次收款 root 与完整回滚

只对 Receipt #2 root `FIN-B2230197D6014812` 操作，未作废 Receipt #1。E23 空原因验证时“确认作废”按钮为 disabled；填写 `Phase 3B-3 finance void UAT` 后通过 UI 确认。

作废后整棵链保持历史记录但均为 cancelled：

| Transaction | status | void_reason / voided_at |
|---|---|---|
| root 107 / `FIN-B2230197D6014812` | cancelled | `Phase 3B-3 finance void UAT` / 有值 |
| child 108 / `ADV-81802819CDD1478B` | cancelled | 同上 / 有值 |

回滚只撤销第二次收款的影响：

| 对象 | 作废前 | 作废后 |
|---|---:|---:|
| H plan 379 settled | 30.00 | 20.00 |
| H plan 379 remaining | 0.00 | 10.00 |
| H Order paid | 30.00 | 20.00 |
| J plan 380 settled | 10.00 | 0.00 |
| J plan 380 remaining | 15.00 | 25.00 |
| AdvanceAllocation 2 | active=true，10.00 | active=false，10.00 历史保留 |
| Advance child allocated_amount | 10.00 | 0.00 |

Receipt #1 `FIN-DD28FFE2D90D408A` 仍为 confirmed，20.00 USD，H 最终保留第一次收款结果。E24 UI GUARD 通过：root 重新打开后显示“已作废”、作废原因和时间，不再显示“作废”按钮。作废提交后只产生这一棵取消链，没有重复 side effect。

### 12.5 E28/E30/E31/E38 结果

| 场景 | 结果 |
|---|---|
| E28 PaymentPlan 币种 | PaymentPlan 收款弹窗只显示计划原币（H 显示 USD），没有用户可编辑的币种控件；通过 |
| E30A 外币汇率 0 | 对现有 GBP PaymentPlan（`SO-2026-42504`）输入 1、汇率 0，UI 未关闭弹窗且未生成 Transaction；计划仍 settled=0.00，未写入 |
| E30B CNY 汇率 2 | 对现有 CNY PaymentPlan（`SO-2026-52556`）输入 1、汇率 2，UI 显示“人民币流水汇率必须为 1。”，未生成 Transaction，计划未变化 |
| E31 候选过滤 | 预收核销候选只列同客户、同币种、receivable、open 计划；通过 |
| E38 重复提交保护 | 收款、核销提交后按钮立即 disabled；root 作废单次点击后仅生成 1 个 root+child cancelled 链、1 条 allocation 被撤回；未用脚本并发 |

### 12.6 Finance H–K 金额去向总表

| 阶段 | Order H（total / planned / settled / remaining / paid） | Order J（total / planned / settled / remaining / paid） | Advance / Allocation |
|---|---|---|---|
| before I（第一次收款后） | 30 / 30 / 20 / 10 / 20 | 25 / 25 / 0 / 25 / 0 | child 尚未产生 |
| after I | 30 / 30 / 30 / 0 / 30 | 25 / 25 / 0 / 25 / 0 | child 108：10，allocated=0 |
| after J | 30 / 30 / 30 / 0 / 30 | 25 / 25 / 10 / 15 / 10 | allocation 2：10，active=true |
| after K | 30 / 30 / 20 / 10 / 20 | 25 / 25 / 0 / 25 / 0 | child 108：cancelled，allocated=0；allocation 2 inactive |

### 12.7 本批问题分类与停止点

- `REAL BUSINESS BUG`：0。H/I/J/K 及 E22/E23/E24/E28/E30/E31/E32 均按当前契约通过，作废和核销均无部分写入或幽灵余额。
- `UI COVERAGE GAP`：1，延续 `UI COVERAGE GAP-PACKAGING-01`。
- `UX ISSUE`：2，延续 `UX ISSUE-01` 与 `UX ISSUE-02`。
- `TEST INFRASTRUCTURE BLOCKER`：1，延续 `TEST INFRASTRUCTURE BLOCKER-PI-01`。
- `EXPECTED CURRENT CONTRACT`：1，延续 `EXPECTED CURRENT CONTRACT-01`。

本批 H/I/J/K 已完成；E25、E26、E27、E29、E33 仍留给 Phase 3C temporary test database。本批不开始 L–T。

### 12.8 Phase 3B-3 回归验证

本批回归已执行并通过：后端 `python manage.py check`、`python manage.py makemigrations --check --dry-run`、完整 `python manage.py test`（288/288）；前端 `npm run test:unit`（57/57）、Node-only typography（1/1）、Vitest（31/31，排除 Node-only）与 `npm run build` 均通过。业务代码、测试、CI、数据库模型和迁移均未修改。

## 13. Phase 3B-4：Purchase Cost Allocation / Shared Expenses（L–M）

**执行日期：** 2026-09-26
**执行分支：** `phase-03b-real-ui-uat`
**执行方式：** 订单、采购单、成本分配、公共费用、超额校验和到货均通过内置浏览器中的真实页面、按钮、输入框、下拉和弹窗完成；没有使用 APIClient、curl、Postman、fetch、browser console、Django shell/ORM 写入、SQL、seed、fixture 或脚本创建/修改业务数据。以下 ORM 内容仅用于最终只读复核。

### 13.1 L1/L2 订单与独立采购单

| 场景 | Quote | Order | SKU / 数量 | Customer / Currency | Order total | 状态 |
|---|---|---|---:|---|---:|---|
| L1 | `SJ20260926US003` | `SO-20260926-285-CF4831`（id=159） | `SKU-000001` / 200 m | Customer A Lighting Ltd / USD | 200.00 | confirmed |
| L2 | `SJ20260926US004` | `SO-20260926-286-32BFE6`（id=160） | `SKU-000001` / 300 m | Customer A Lighting Ltd / USD | 300.00 | confirmed |

两个订单均由 Quote 接受后通过“转为订单”创建，数量和金额在 UI 中确认。独立采购单通过“新建采购单”创建：

| Purchase Order | Supplier | 关联订单 | Purchase Item | 数量 / 单位成本 | 创建后状态 |
|---|---|---|---|---:|---|
| `PO-20260926-220833`（id=56） | Supplier A | 无（`order_id=null`） | id=60，`SKU-000001` | 1000 m × USD 10.00 | 已下单 |

采购单没有用订单头部关联 L1/L2，后续由成本分配明细分别归属订单与库存。

### 13.2 初次成本分配与 Freight UAT 预览

在“分配采购成本 / 公共费用”界面，第一次只填写订单归属 200、300，未分配的 500 自动显示为库存。保存前 UI 预览为：

| 归属 | 数量 | 商品成本 | Freight UAT（按采购金额） | 合计 |
|---|---:|---:|---:|---:|
| L1 / `SO-20260926-285-CF4831` | 200 | 2,000.00 | 20.00 | 2,020.00 |
| L2 / `SO-20260926-286-32BFE6` | 300 | 3,000.00 | 30.00 | 3,030.00 |
| 库存 | 500 | 5,000.00 | 50.00 | 5,050.00 |
| **合计** | **1000** | **10,000.00** | **100.00** | **10,100.00** |

保存前只读复核仍为 `cost_allocation_version=0`、`additional_costs=[]`、无 `PurchaseCostAllocation`、无该 PO 的 GoodsReceipt/InventoryMovement/Transaction，证明预览不会持久化。保存后版本变为 1，三条归属和 `Freight UAT / 100.00 USD / method=amount` 持久化；成本分配没有创建入库、库存流水或财务流水。

### 13.3 订单成本与库存归属

保存后订单成本只计算订单归属，不把库存 500 m 计入订单毛利。正式重分配保存后（见 13.4）只读服务结果为：

| Order | 销售额（RMB） | 订单商品成本（RMB） | 订单附加费用（RMB） | 预估毛利（RMB） |
|---|---:|---:|---:|---:|
| L1 / id=159 | 1,440.00 | 18,000.00（250×10×7.2） | 180.00（25×7.2） | -16,740.00 |
| L2 / id=160 | 2,160.00 | 18,000.00（250×10×7.2） | 180.00（25×7.2） | -16,020.00 |

库存归属 500 m 的商品成本 5,000.00 USD、Freight 50.00 USD 保留在库存成本分配中，不进入 L1/L2 的订单成本。

### 13.4 未保存编辑、正式重分配与版本替换

重新打开已保存结果后，通过 UI 把订单数量临时改为 250/250，预览显示 250/250/500 与 Freight 25/25/50；点击“关闭”取消后重新打开，已保存值仍为 200/300/500，证明未保存编辑不会写入。

随后再次通过 UI 保存正式重分配 250/250/500。只读复核：

- `cost_allocation_version` 从 1 增至 2；
- 当前恰好三条 `PurchaseCostAllocation`：L1=250、L2=250、库存=500，无叠加重复行；
- `additional_costs` 仍只有 `Freight UAT=100.00`，按采购金额分摊为 25/25/50；
- PO 状态与订单状态不被成本分配改变。

### 13.5 超额分配与归属名称校验

将订单数量改为 800+300（合计 1100）并点击保存，UI 预览立即标记“`SKU-000001 分配数量超过采购数量`”，提交后对话框仍停留在未保存状态。只读复核确认版本仍为 2，持久化仍为 250/250/500，Freight 仍为 100.00，订单成本未变化，故 E 超额分配通过。

将第一条归属切换为“其他”而不填写归属名称，UI 阻止预览并提示需要填写成本归属名称；提示文本出现现有的 `[object Object]` 展示问题，但没有写入，关闭后持久化数据不变。该表现记录为既有 UX 观察，不在本批修复。

### 13.6 按数量公共费用预览

新增未保存的 `Handling UAT=10.00 USD`，选择“按数量比例”，预览显示 2.50/2.50/5.00（L1/L2/库存），总附加费用 110.00；点击“关闭”不保存。重新读取 PO 后仍只有 `Freight UAT=100.00 / method=amount`，证明数量分摊预览不会产生额外费用。

### 13.7 分配后部分收货与库存不变量

通过采购单“验货入库” UI 登记合格入库 100 m，勾选“已核对”后确认。页面变为“部分到货”，显示已到 100 m、剩余 900 m。库存页面真实显示 `SKU-000001`：实际 206 m、预留 106 m、可用 100 m、在途 900 m；`available = actual - reserved = 206 - 106 = 100`。

只读复核显示本 PO 新增 GoodsReceipt id=54（100.00 m）及唯一 `purchase_in` InventoryMovement id=113（100.00 m，`source_type=receipt`，unit_cost=10.00）。收货前该 SKU 实际库存 106 m，收货后 206 m，实际库存恰好增加 100 m，而不是 1000 m；成本分配阶段本身没有新增 GoodsReceipt/InventoryMovement。该 PO 没有 Transaction；现有 2 条 PO 默认 payable PaymentPlan（订金/尾款）未因成本分配或公共费用新增或改变，未登记供应商付款。

### 13.8 L1/L2 shared purchase fulfillment evidence

分别通过订单工作台的“采购与发货”页签读取真实 UI。UI 的“预留”列与只读 `order_item_metrics()` 的 `allocated_quantity` 一致；UI 没有单独渲染“待采购”列，因此该列以同一服务函数的只读结果记录，并未通过 UI 推断：

| Order | ordered | allocated / reserved | purchased | received | in_transit | to_procure | shipped | unshipped |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| L1 / `SO-20260926-285-CF4831` | 200 | 88 | 250 | 25 | 225 | 0 | 0 | 200 |
| L2 / `SO-20260926-286-32BFE6` | 300 | 0 | 250 | 25 | 225 | 75 | 0 | 300 |

L1 UI 实际显示 `200 / 88 / 250 / 25 / 225 / 0 / 200`，L2 UI 实际显示 `300 / 0 / 250 / 25 / 225 / 0 / 300`（顺序为 ordered / reserved / purchased / received / in_transit / shipped / unshipped）。只读服务结果分别为：

- L1：`allocated=88, purchased=250, received=25, in_transit=225, to_procure=0, shipped=0, unshipped=200`；
- L2：`allocated=0, purchased=250, received=25, in_transit=225, to_procure=75, shipped=0, unshipped=300`。

因此 PurchaseCostAllocation 的 250/250 分别进入 L1/L2 的 `purchased_quantity`；100 m Receipt 按共享采购行比例分配为各 25 m arrived、各 225 m in-transit；库存归属 500 m 没有被计入任何订单的 purchased 数量。未发现共享采购重复计算、订单错归或 received/in-transit 不守恒。

### 13.9 Other target 合法 Preview

重新打开 `PO-20260926-220833` 的“分配采购成本 / 公共费用”，将第一条临时切换为 `其他`，先保留空名称验证（UI 拒绝），随后填写 `UAT备用项目`，数量填写 100。实时 Preview 成功显示：

| target_type | target_name | quantity | base_amount | additional_amount | total_amount |
|---|---|---:|---:|---:|---:|
| other | UAT备用项目 | 100 | 1,000.00 | 10.00 | 1,010.00 |

该预览同时显示 L2=250、库存原有 500，剩余 150 自动归库存，合计仍为 1000 m。没有点击保存，直接关闭；重新打开后确认正式结果仍为 L1=250、L2=250、Inventory=500，`Freight UAT=100.00`，`cost_allocation_version=2`。Other 预览没有写入 `PurchaseCostAllocation` 或 `additional_costs`。

### 13.10 Phase 3B-4 回归验证

本轮文档更新前已完成完整回归：后端 `check`、`makemigrations --check --dry-run`、完整测试 `288/288 PASS`；前端 unit `57/57 PASS`、Node-only typography `1/1 PASS`、Vitest `31/31 PASS`、`npm run build` PASS。除本执行记录外未修改业务代码、测试、CI、模型或迁移。

### 13.11 本批结论、问题分类与停止点

- `REAL BUSINESS BUG`：0。L/M 的订单归属、库存余量、共享费用比例、版本替换、超额保护与部分收货均符合当前契约。
- `UI COVERAGE GAP`：1，延续 `UI COVERAGE GAP-PACKAGING-01`；本批未进入 packing/shipment 的正式 UAT。
- `UX ISSUE`：2，延续 `UX ISSUE-01` 与 `UX ISSUE-02`；本批另观察到“其他归属”空名称验证沿用 `[object Object]` 展示，但未修改 UI。
- `TEST INFRASTRUCTURE BLOCKER`：1，延续 `TEST INFRASTRUCTURE BLOCKER-PI-01`。
- `EXPECTED CURRENT CONTRACT`：1，延续 `EXPECTED CURRENT CONTRACT-01`。

本批完成 L/M 采购成本分配、共享费用、部分收货和数量分摊预览；不开始 N–T，也不修改任何业务代码、测试、CI、模型或迁移。
