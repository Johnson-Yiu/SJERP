# ISS-037 正式商业单据历史快照覆盖审查

审查分支：`codex/r1-iss-037-audit-01`
审查基线：`origin/master` / `25405e1b25ff8a218b67883acf489ada8a53e146`
审查日期：2026-10-21
当前结论：**审查完成，ISS-037 保持 BLOCKED，等待业务规则确认和独立复审**

## 1. 范围与安全边界

本轮只做代码、自动测试和隔离 SQLite 数据复现，没有修改生产业务代码、模型、迁移、历史业务数据或正式单据。临时数据库位于开发机临时目录，执行完成后未纳入 Git。临时审查探针已删除；仓库中仅保留本报告、日志和实际生成的 PI Excel 文件。

本轮没有合并 `master`，也没有改动 R1-SKU-01、R1-MOQ-02、R1-INV-03、R1-PO-04 或 ISS-039 分支。

## 2. 逐字段覆盖矩阵

状态含义：`PASS` = 已有快照且本轮变更主档后复现保持不变；`DEFECT` = 已有部分能力，但正式历史展示或数据来源仍不稳定；`MISSING` = 当前没有足够字段/接口；`DECISION` = 需要业务负责人先确认历史显示规则。

| 单据/对象 | 字段或能力 | 生成阶段与当前来源 | 本轮结论 | 后续建议 / 迁移 |
|---|---|---|---|---|
| Quote | `buyer_company_name` | 报价创建时保存；PI DTO/Excel 读取该字段 | **PASS**；客户改名后仍为原公司名 | 无；保持只读快照 |
| Quote | `recipient_name`、`buyer_address`、`buyer_email`、`buyer_phone` | Quote 创建时从主联系人/客户地址写入 | **PASS**；客户和联系人改名、改地址、改联系方式后仍为原值 | 无；如需更完整主体资料须另行确认 |
| Quote | `customer_name`（列表/详情标题） | 序列化器和 `QuoteDetailModal.vue` 读取实时 `Customer.name` | **DEFECT / DECISION**；报价标题会显示新客户名，和 PI 快照并存 | 先确认“工作台标题是否也必须历史化”；若确认，需要新增显示快照或改为优先快照。需迁移的可能性：是 |
| QuoteItem | SKU Code、Sales Model、产品名、单位、描述、销售规则、图片 | 创建报价行时保存；修订复制来源报价行快照 | **PASS**；SKU 改名、改型号、改单位后 PI 仍读取旧值 | 无 |
| Quote revision | `root_quote`、`parent_quote`、`revision_no` 与头/行快照复制 | 创建修订版时复制上一版本快照 | **PASS**；原版本保留，报价编号/修订链不改 | 无；继续保持原版本不可静默覆盖 |
| Quote PI Excel / `pi-data` | 买方主体、联系人、地址、SKU/型号/单位 | `quotation_export_dto.py` 和 PI 数据接口均只读已保存快照 | **PASS**；实际生成 Excel，旧值保留，新主档值未进入导出 | 无 |
| Order | 客户名称、客户国家、地址、联系人、主体资料 | 仅 `customer` 外键；`OrderSerializer` 和详情页读取实时 Customer | **MISSING / DEFECT**；订单没有主体快照，客户改名后历史订单标题变化 | 需要确认正式订单应保存哪些字段；建议最小增加订单主体/联系人/地址快照。需迁移：是 |
| OrderItem | SKU Code、Sales Model、显示名、描述、单位 | 订单创建时写入 `*_snapshot` 字段；有供应来源时也保存供应商来源快照 | **PASS**；本轮 SKU/供应来源改动后行快照保持原值 | 无 |
| Order history UI | 订单标题及关联采购历史供应商名 | 订单标题使用 `order.customer_name`；关联采购卡片使用采购序列化的实时 `supplier_name` | **DEFECT**；行项目快照稳定，但单据主体/供应商标题不稳定 | 应与正式单据主体规则统一，不能用当前主档补造历史事实 |
| PurchaseOrder | 供应商名称、地址、联系人、主体资料 | 仅 `supplier` 外键；`PurchaseOrderSerializer`/详情页读取实时 Supplier | **MISSING / DEFECT**；没有供应商主体快照，供应商改名后采购单标题变化 | 需要确认正式采购单主体快照字段；建议最小增加供应商名称及已确认的地址/联系人快照。需迁移：是 |
| PurchaseOrderItem | SKU、型号、产品名、描述、供应商名/型号/SKU/条码/特点 | 采购行创建时保存 `*_snapshot` 字段 | **PASS（模型数据）**；本轮供应商档案及 SKU 改动后旧行快照稳定 | 无；历史快照缺失时不得回填当前档案 |
| PurchaseOrderItem 展示 | 描述快照、供应特点、来源信息 | 模型有 `description_snapshot`；采购详情主要显示 SKU/型号/供应特点，序列化器未完整公开描述快照 | **DEFECT / MISSING（展示层）**；保存值存在但历史详情未完整展示 | 后续只读展示补齐，先确认是否需要导出；无需立即改模型 |
| Customer | 名称、编号、国家、地址 | 主档实时字段；Quote 另存部分交易快照 | **PASS（主档能力）/ 不等于单据快照** | 不应从主档变更推断历史单据内容 |
| Contact | 姓名、职位、邮箱、电话、WhatsApp、备注 | 主档实时字段；Quote 只快照姓名、邮箱、电话 | **DEFECT / MISSING**；职位、WhatsApp、备注没有进入报价快照 | 业务确认正式单据是否需要这些字段；需要时增加最小快照字段，需迁移：是 |
| Supplier | 名称、二字代码、联系人、电话、邮箱、付款条款 | 主档实时字段；没有独立地址字段 | **MISSING**；供应商无地址字段，无法安全保存供应商地址历史 | 业务确认地址来源及字段后再设计；禁止把备注或当前档案当地址。需迁移：是 |
| Sales-order export | 订单历史 Excel/PDF 导出 | 当前代码未发现独立销售订单正式导出入口 | **MISSING / DECISION**；无法声称已有历史导出快照覆盖 | 业务确认是否要求销售订单导出；若要求，应先确定快照字段和模板 |
| Purchase-order export | 采购单历史 Excel/PDF 导出 | 当前代码未发现独立采购单正式导出入口 | **MISSING / DECISION** | 业务确认是否要求采购单导出；不要在本轮擅自新增 |
| 合同变更/审计 | Order/PurchaseOrder 合同变更模型与 OperationLog | 现有变更记录和操作日志可追溯操作，但不是主体快照 | **PASS（审计能力存在）/ 不覆盖主体快照缺口** | 后续修复须记录快照字段变更，不得改写已发生的资金、库存或履约事实 |

## 3. 隔离数据库实际复现

临时数据库：`C:\Users\Johnson\AppData\Local\Temp\iss037-audit.sqlite3`。执行过程及退出码见 [iss037-audit-probe.log](iss037-audit-probe.log)。

复现步骤：

1. 创建客户、主联系人、供应商、SKU、SupplierSKU。
2. 创建已保存的 Quote、Order、PurchaseOrder 及对应行项目快照。
3. 修改客户名称/地址、联系人姓名/联系方式、供应商名称/联系人、SupplierSKU 特征/型号、SKU 型号/名称/单位。
4. 重新读取正式单据和行项目，生成实际 PI Excel。

实际结果：

- Quote 的 `buyer_company_name`、联系人、地址、报价行 SKU/型号/单位保持原始值。
- OrderItem 的 SKU、供应商名称/型号/特点快照保持原始值，但 Order 头部 `customer` 读取修改后的客户名。
- PurchaseOrderItem 的 SKU、供应商名称/型号/特点快照保持原始值，但 PurchaseOrder 头部 `supplier` 读取修改后的供应商名。
- PI Excel 已保存为 [ISS037-PI-after-master-change.xlsx](ISS037-PI-after-master-change.xlsx)。实际检查 `B3` 为原买方公司、`C11` 为 `MODEL-ISS037-OLD`、`K11` 为 `pcs`，文件中不含新型号。

这证明当前 Quote/行项目快照及 PI 导出边界相对安全，但不能把当前 Order/PurchaseOrder 主体标题当作交易时事实。

## 4. 迁移冲突记录

当前 `origin/master` 的 CRM 迁移基线为 `0077_rmb_cash_events`。未合并分支存在两个平行的 `0078`：

- R1-SKU-01：`0078_sku_cost_verification.py`，依赖 `0077_rmb_cash_events`。
- R1-MOQ-02：`0078_purchase_moq_exceptions.py`，依赖 `0077_rmb_cash_events`。

本审查没有修改或重写任何已发布迁移。未来整合两个功能时，应在整合分支保留两份 0078 文件，并新增一个只含依赖的合并迁移（例如 0079，依赖两条 0078 叶节点），由 Django 迁移图验证后再部署；不得通过删除、跳过或覆盖其中一条功能迁移来消除冲突。若整合顺序或发布状态发生变化，需在执行前重新生成迁移图并由独立审查确认。

## 5. 本地测试与环境结果

| 命令/检查 | 实际结果 |
|---|---|
| 隔离迁移 + ISS-037 复现探针 | 退出码 0；日志与 Excel 已保存 |
| `python manage.py test crm.tests.test_quotes crm.tests.test_purchase_order_related_orders crm.tests.test_supplier_sku crm.tests.test_supplier_allocation --verbosity 1` | **93 tests，OK，退出码 0**；见 [backend-targeted-tests.log](backend-targeted-tests.log) |
| `python manage.py check` | **0，退出码 0**；见 [django-check.log](django-check.log) |
| `python manage.py makemigrations --check --dry-run` | **No changes detected，退出码 0**；见 [makemigrations-check.log](makemigrations-check.log) |
| `python manage.py test --verbosity 1` | **768 tests，OK，13 skipped，退出码 0**；包含 P2A 数据库验证，历史金额哈希前后相同；见 [backend-sqlite-full.log](backend-sqlite-full.log) |
| `npm run test:unit` | 安装锁定依赖后 **136/136 pass，退出码 0**；见 [frontend-unit-after-install.log](frontend-unit-after-install.log) |
| `npm run build -- --outDir C:\Users\Johnson\AppData\Local\Temp\iss037-frontend-dist` | **构建成功，退出码 0**；见 [frontend-build-after-install.log](frontend-build-after-install.log) |
| PostgreSQL | 本机 `127.0.0.1:5432` 未监听（`POSTGRES_LISTENING=False`），未伪造 PostgreSQL 通过；见 [postgres-availability.log](postgres-availability.log) |
| GitHub Actions | 本审查未触发；按项目策略保持 **CI PENDING** |

首次前端命令因独立 worktree 未安装 `node_modules`，记录为环境原因；安装锁定依赖后已重新执行并通过，未修改 `package-lock.json`。

## 6. 建议的后续独立事项

1. 业务负责人确认正式 Quote/Order/PurchaseOrder 的主体展示是“交易时快照”还是“当前主档引用”，并明确地址、联系人职位/WhatsApp/备注、供应商地址的字段范围。
2. 若要求正式 Order/PurchaseOrder 历史主体稳定，新增最小快照字段并只在正式创建/确认阶段写入；不得批量回填历史记录，不得自动从当前主档补造历史事实。
3. 统一详情页、列表页和未来导出使用快照优先策略；草稿仍可按当前编辑语义显示，但正式单据必须明确区分。
4. 另行确认是否需要销售订单和采购订单 Excel/PDF 正式导出；本轮未新增导出。

ISS-037 当前仍为 `BLOCKED`，本报告不关闭 Issue，也不代表正式修复已完成。
