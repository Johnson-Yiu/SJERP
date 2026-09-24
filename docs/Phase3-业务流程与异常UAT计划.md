# Phase 3：业务不变量、异常流程与真实 UI UAT 计划

**阶段：** Phase 3A（计划与当前契约梳理）  
**基线：** `master` / `7509ed96ce9f02fbf158b0099cd6baa2ef0eded1`  
**执行分支：** `phase-03-business-invariant-uat`  
**状态：** 等待 Code Review；本文件不是 Phase 3B 的执行记录。

## 1. 范围、证据与执行边界

本计划以当前 `models`、serializers、views、`fulfillment.py`、`finance.py` 和 Vue 页面为准。`docs/业务流程与修改回归测试报告-20260922.md`、`docs/真实用户E2E-UAT-20260923.md` 与三个管理命令仅是历史参考，不能替代本次 UAT 结论。

Phase 3B 的每一条业务数据都必须经浏览器 UI 的页面、按钮、输入框、下拉框、弹窗和表格操作创建或修改。禁止 seed、fixture、SQL、Django shell、脚本批量造数、APIClient、curl、Postman、浏览器 console 或历史管理命令造 Phase 3 业务数据。数据库只能用于开始前备份、开始前清理以及结束后的只读核对。

本次基线验证已在本分支完成：Django `check`、migration dry-run 和 287 项测试均通过；前端 unit 57 项、Node typography 1 项、Vitest 31 项及 build 均通过。

## 2. 完整业务流程树（11 条主链、61 个最小可操作子流程/分支）

以下编号是 Phase 3B 的操作清单索引；“分支”指用户实际会作出的选择或系统必须拦截的转换，并非仅页面导航。

### 2.1 CRM 与客户主数据（C01–C05）

1. **C01** 新建客户：名称、国家/地区、来源及基础联系信息校验。
2. **C02** 新建/编辑联系人：同一客户设置唯一主联系人、电话/邮箱与职位。
3. **C03** 新建跟进：记录时间、类型、内容、下次跟进日期及附件。
4. **C04** 修改客户名称、联系人信息后，检查客户列表、搜索、报价/订单关联及历史快照。
5. **C05** 无效国家、必填字段缺失、重复客户编码/名称（如适用）应有明确 UI 错误。

### 2.2 产品、SKU、交易单位与包装（P01–P08）

1. **P01** 新建分类、层级分类与分类参数；验证重复属性、循环层级被拒绝。
2. **P02** 新建产品并绑定分类、HS Code、英文/中文描述与销售规则。
3. **P03** 按产品参数创建 SKU，确认 SKU Code、内部显示名、Sales Model 与 identity signature 的身份稳定性。
4. **P04** 修改 SKU 描述、Sales Model、参数、图片；确认生成 SKUVersion 而不是替换历史单据快照。
5. **P05** 新建多个交易单位（pcs、set、m、roll），指定 factor、默认单位与是否允许小数。
6. **P06** 停用交易单位；新单据不可错误选用，历史交易行仍应使用其 trade snapshot 显示并可计算。
7. **P07** 新建包装模板和 SKU 包装档案；生成报价/订单预计装箱并检查尾货策略。
8. **P08** 修改包装模板或 SKU 包装档案；既有 packing plan 必须保持快照，新计划才使用当前配置。

### 2.3 供应商与 SupplierSKU（S01–S05）

1. **S01** 新建供应商及供货分类、国家、付款条款。
2. **S02** 为 SKU 建立单供应商、双供应商、三供应商及无来源四类样本。
3. **S03** 设置/切换首选 SupplierSKU；确认每 SKU 仅一个启用的首选来源。
4. **S04** 修改供应商名称、供应商型号、采购价、MOQ、特点或停用来源；检查历史订单/采购行保存的供应来源快照。
5. **S05** 无 SupplierSKU、停用来源、MOQ/价格非法或重复供应商 SKU code 时，采购 UI 必须阻止或给出可理解反馈。

### 2.4 报价、修订、PI 与历史快照（Q01–Q08）

1. **Q01** 选择客户、新建报价并加入多个 SKU/交易单位行，填写数量、单价、币种、汇率、运输、折扣和条款。
2. **Q02** 校验销售规则、交易单位因子及不允许小数包装的数量约束。
3. **Q03** 保存 draft/sent/accepted/rejected/expired 报价，检查状态展示与允许操作。
4. **Q04** 通过“创建迭代版”生成同一 root quote 的子版本；原版本不可被覆盖，修订说明必填且客户不可换链。
5. **Q05** 新增、停用、恢复 Important Notes，检查只作用于正确的报价树。
6. **Q06** 从报价创建订单草稿，确认客户、币种、金额、交易单位及订单行快照的继承关系。
7. **Q07** 真实导出 PI/XLSX，验证报价编号、客户信息、币种、Sales Model、描述、数量、交易单位、折扣、条款、图片和模板样式。
8. **Q08** 改客户名、SKU Sales Model/描述/图片后重新导出旧报价，并与新修订版比较历史快照与实时显示字段。

### 2.5 销售订单、履约与库存预留（O01–O07）

1. **O01** 从报价创建订单或在订单页创建草稿，核对客户、报价来源、订单行、币种、汇率、运费和折扣。
2. **O02** 确认订单：生成默认应收 PaymentPlan，按当时实际库存建立 SKU 级 reservation。
3. **O03** 为订单行选择或更换 SupplierSKU；只影响本订单的供应来源快照，不改写 SKU 主档。
4. **O04** 修改商业条件：必须生成 accepted 报价子版本/正确的合同追溯，既有报价与已结算计划不应被静默改写。
5. **O05** 订单进入 production；检查手工不能把订单直接置为 shipped/partial/completed。
6. **O06** 取消未履约订单：释放该订单的 reservation、取消未结计划；已有履约/财务历史时必须遵守后端禁止规则。
7. **O07** 在订单工作台核对 ordered、purchased、received、reserved、shipped、remaining、支付和库存流水的交叉一致性。

### 2.6 采购、收货、入库与收货冲销（R01–R08）

1. **R01** 从订单缺口或独立需求创建采购单，选择供应商，添加交易单位采购明细并关联销售订单。
2. **R02** 调整采购单 draft/ordered 状态；禁止人工写入 partial/completed。
3. **R03** 维护采购成本归属：按订单、库存或其他归属分配采购数量。
4. **R04** 录入公共费用并预览/确认成本分配，检查数量、金额与归属之和。
5. **R05** 第一次部分验货合格入库：产生 `purchase_in` 自动流水，更新 actual、在途、received、PO status 和当前 SKU reservation。
6. **R06** 第二次/完整入库与经授权的超到：验证 partial/completed、超到原因及库存可解释性。
7. **R07** 对未被后续出库消耗的 receipt 冲销：原 receipt 保留，产生 `adjust_out/reversal`，received/remaining、PO status 和本 SKU reservation 重新计算。
8. **R08** 对已被下游消耗库存的 receipt、重复冲销或空原因冲销：整个操作原子失败，不新增流水、不改变 PO/库存/预留。

### 2.7 库存、装箱、发货与发货冲销（F01–F08）

1. **F01** 在库存页查看 SKU actual、reserved、available 及全部正负流水；验证手工调整的类型与库存下限。
2. **F02** 从报价/订单生成预计装箱方案，检查包装快照、尾箱、体积/重量、缺失包装警告。
3. **F03** 从订单工作台确认普通发货：创建 confirmed Shipment、每个 ShipmentItem 的 `sale_out/shipment` 流水并消耗 reservation。
4. **F04** 分两次发货：确认 shipped/remaining、订单仍可继续履约与状态变化。
5. **F05** 库存不足发货失败；不能生成 Shipment/库存流水或释放 reservation。
6. **F06** 超发、客户追加、赠品和包装尾差：必须有原因；含超发/增补 Shipment 不允许直接冲销。
7. **F07** 正常 Shipment 冲销：先验证所有原 sale_out 流水，再产生一一对应 `adjust_in/reversal`，Shipment 变 cancelled，订单状态和每个 SKU reservation 重算。
8. **F08** 缺失/异常原 sale_out、重复冲销、已完成/取消订单冲销：全单原子失败，库存、订单、Shipment 与 reservation 全部保持不变。

### 2.8 应收、应付、预收预付与财务作废（M01–M08）

1. **M01** 订单确认后生成默认应收计划（定金/尾款）；采购单生成默认应付计划。
2. **M02** 从 PaymentPlan 结算部分客户收款/供应商付款，检查 planned、settled、remaining 和 open/settled 状态。
3. **M03** 使用财务流水页登记客户收款、供应商付款、订单费用、期间费用、退款及其他收支；方向、合同、往来方、币种、汇率必须匹配。
4. **M04** 一次实际收款跨多个计划：根流水与 split child 的金额、plan、支付方式和参考号应可追溯。
5. **M05** 超额收款/付款：仅超额部分形成 `unallocated_advance`/`unallocated_payment` child，不伪造 PaymentPlan settled。
6. **M06** 将预收/预付核销到同币种、同客户/供应商的另一有效计划，检查 `AdvanceAllocation`、allocated_amount 与两个计划。
7. **M07** 作废根 Transaction：递归取消所有 confirmed split child、撤回 active allocation、恢复每个关联 PaymentPlan，并保存统一 reason/voided_at。
8. **M08** 直接作废 split child、重复作废、空原因、历史 allocation 总额不匹配或计划不足：必须拒绝且无部分修改。

### 2.9 采购成本、毛利与报表（A01–A04）

1. **A01** 采购明细成本与公共费用分摊到多个订单/库存归属，核对 quantity 和金额归属。
2. **A02** 在订单工作台核对销售额、采购基础成本、附加成本、费用和预计毛利。
3. **A03** 在财务 Dashboard 核对 confirmed 现金流、待收待付、未核销预收/预付和日期范围。
4. **A04** 在客户/SKU/订单报表核对状态、金额、数量与 drill-down 关联；cancelled Transaction 不能进入现金统计。

### 2.10 审计与跨模块回看（X01–X03）

1. **X01** 对收货冲销、发货冲销、财务作废和预收核销回看 operation log、原因、时间与关联 ID。
2. **X02** 从客户、SKU、报价、订单、采购单、流水互相打开详情，检查没有断链或错误的实时/快照字段替换。
3. **X03** 对每一张关键订单执行 UI 截图/导出、只读数据库核对和不变量结果记录。

### 2.11 异常与重复操作回归（E01–E05）

1. **E01** 对必填、日期、币种、汇率、数量、重复编码和非法状态统一记录前端提示与后端返回。
2. **E02** 对库存、收货、发货、财务的失败操作记录执行前/后实体快照，证明没有部分提交。
3. **E03** 对主数据修改后历史报价/订单/采购/收发货/财务分别回归。
4. **E04** 对浏览器刷新、重复点击、重复提交和错误返回后重新加载做幂等性检查。
5. **E05** 记录本计划外缺陷为单独候选任务；本阶段不在 UAT 中顺手改业务实现。

## 3. 状态机矩阵

| 实体 | 状态 | 合法进入/前置条件 | 用户可做 | 禁止或系统保证 |
|---|---|---|---|---|
| Quote | draft / sent / accepted / rejected / expired | UI 新建或修订；修订须同 root quote 且客户不变 | 编辑/新建修订、导出、管理 Important Notes | 修订不能覆盖来源报价或切换报价树客户 |
| Order | draft | 新建订单草稿 | 编辑、确认、取消 | 有履约/财务历史后不能随意回 draft/cancel |
| Order | confirmed / production | 确认订单后；production 为合法业务推进 | 选择供应来源、采购、收款、发货 | 手工选 shipped 不合法；不能绕过 Shipment |
| Order | shipped | 所有订单行有效发货量达到数量 | 看履约、继续财务操作 | 不是手工下拉状态；冲销后按规则回 confirmed/production |
| Order | completed / cancelled | 受 serializer/既有历史约束 | 只读/受限操作 | 已完成/取消订单不允许冲销发货、登记不合法款项 |
| PurchaseOrder | draft | 新建采购单 | 编辑、下单 | 不允许手工改 partial/completed |
| PurchaseOrder | ordered | 下单 | 收货、付款、成本分配 | receipt 决定到货状态，不由下拉伪造 |
| PurchaseOrder | partial / completed | 有效 GoodsReceipt 汇总小于/等于采购量 | 继续收货或查看历史 | 已冲销 receipt 必须排除；冲销后可回 ordered/partial |
| PurchaseOrder | cancelled | 业务取消且无冲突历史 | 受限查看 | 不允许录入 receipt/payment |
| GoodsReceipt | 有效（无 reversal movement） | ordered/partial PO、正数数量、必要超到授权 | 查看、填写原因冲销 | 原 receipt 不删除，数量不修改 |
| GoodsReceipt | 已冲销 | `reverse_receipt` 成功且库存足够 | 只读查看原因、时间、reversal movement | 不允许二次冲销；不能凭空增加库存 |
| Shipment | draft | 模型状态预留 | 正常 UI 不以草稿完成出库 | 不应产生已确认 sale_out |
| Shipment | confirmed | 所有发货行库存足够并成功生成 sale_out | 查看、正常条件下冲销 | 超发/追加 Shipment 不可直接冲销 |
| Shipment | cancelled | `reverse_shipment` 成功 | 查看原因及 reversal | 不允许二次冲销；异常原流水必须整单失败 |
| Transaction | confirmed | 服务层校验金额、汇率、合同/计划、方向 | 核销 advance、作废 root | split child 不可直接作废；不可更新/删除替代作废 |
| Transaction | cancelled | root void 成功，所有 child 同步 | 查看 void reason/time | 不进入现金流；不可重复作废 |
| PaymentPlan | open / settled / cancelled | 合同创建或合法结算/取消 | 从 UI 结算、查看 | settled 不得超过 planned；取消计划不可结算 |
| ContractChangeRequest | pending / approved / rejected | 创建、approve action | UI 创建/查看 | 目前批准 action 无专用 UI，见 GAP-01 |

## 4. Business Invariant Matrix（54 项）

| ID | 类型 | 不变量 / Phase 3B 核对 |
|---|---|---|
| I01 | 身份 | SKU 主键和 SKU Code 是库存、订单与供应来源的身份；描述或 Sales Model 修改不能替换 SKU 身份。 |
| I02 | 身份 | SKU Code 创建后不可改，display name 规范化键唯一。 |
| I03 | 身份 | SupplierSKU 只描述供应商对内部 SKU 的采购身份，不能成为库存 SKU 身份。 |
| I04 | 身份 | 每 SKU 最多一个启用且首选的 SupplierSKU。 |
| I05 | 身份 | 客户改名不改变 quote/order/transaction 的 customer 关系。 |
| I06 | 身份 | 报价修订的 root/parent 必须属于同一报价树，不能跨客户。 |
| I07 | 快照 | QuoteItem 创建时保存 SKU Code、Sales Model、产品名、单位、描述及图片快照。 |
| I08 | 快照 | OrderItem 保存 SKU Code、Sales Model、显示名、描述、单位、供应商名称/型号/特点与交易单位快照。 |
| I09 | 快照 | PurchaseOrderItem、GoodsReceipt、ShipmentItem/InventoryMovement 的交易数量和交易单位须可回溯到当时 trade snapshot。 |
| I10 | 快照 | Quote 的 buyer_company_name 是客户版 PI 历史快照；客户列表/关联关系可显示当前客户名。 |
| I11 | 快照 | 既有 packing plan 使用包装/尺寸/重量快照；改包装只影响以后生成的计划。 |
| I12 | 快照 | 供应商改名或 SupplierSKU 停用不得改写历史采购/订单行快照。 |
| I13 | 库存 | `actual = Σ InventoryMovement.signed_quantity`，每 SKU 以流水而非手工累计为准。 |
| I14 | 库存 | `reserved = Σ InventoryReservation.quantity`（仅活动订单行）；不能为负。 |
| I15 | 库存 | `available = actual - reserved`；有效 reservation 不得令 reserved 超过 actual。 |
| I16 | 库存 | 有效收货仅产生一次 `purchase_in/receipt` 自动流水；重复提交不得双增库存。 |
| I17 | 库存 | 收货冲销必须以原 receipt 的数量、SKU、成本、供应来源为依据产生一次 `adjust_out/reversal`。 |
| I18 | 库存 | 后续出库使 actual 小于 receipt quantity 时，receipt reversal 必须失败且无状态改变。 |
| I19 | 库存 | 正常发货每个 ShipmentItem 必须有同 SKU、同订单、同数量的 `sale_out/shipment` 原流水。 |
| I20 | 库存 | 发货冲销前全单校验所有原 sale_out；任一缺失/异常则零条 reversal、零库存变化。 |
| I21 | 库存 | 有效 Shipment reversal 为每行产生一次 `adjust_in/reversal`；不得创造超过原出库的库存。 |
| I22 | 库存 | 手工库存调整只能使用允许的 manual types，自动流水不可编辑/删除。 |
| I23 | 履约 | 订单行 `shipped_quantity` 仅统计有效 confirmed Shipment，已冲销 Shipment 不得计入。 |
| I24 | 履约 | 采购行 `received_quantity` 仅统计 reversal movement 为空的 GoodsReceipt。 |
| I25 | 履约 | PO status 由每行有效 received 与购买数量决定：ordered/partial/completed。 |
| I26 | 履约 | 单 SKU reservation 重算仅影响该 SKU 的活动订单行，按 order_date、pk 分配。 |
| I27 | 履约 | 发货消耗 reservation；收货/发货冲销之后 reservation 重新平衡且不越 actual。 |
| I28 | 履约 | 采购、收货、发货数量可不同，但工作台必须显示可解释的 purchased/arrived/in-transit/shipped/remaining。 |
| I29 | 财务 | `PaymentPlan.remaining_amount = planned_amount - settled_amount`，settled 范围为 `[0, planned]`。 |
| I30 | 财务 | 订单只关联 receivable plan，采购单只关联 payable plan；一个 plan 只能关联一个合同。 |
| I31 | 财务 | 合同收付款币种、方向、往来方和合同必须匹配对应 PaymentPlan。 |
| I32 | 财务 | 一次合同收付款可产生根/child split；每个 child 金额和 plan 可追溯，合计解释原现金事件。 |
| I33 | 财务 | 真正超额部分才生成 unallocated advance/payment，不能把它计入原计划 settled。 |
| I34 | 财务 | `Transaction.allocated_amount = Σ active AdvanceAllocation.amount`。 |
| I35 | 财务 | 预收/预付只能核销同方向、同币种、同客户或同供应商且 open 的计划。 |
| I36 | 财务 | 作废 root 时，所有 confirmed split child 同时 cancelled，active allocations 全部 inactive，allocated_amount 归零。 |
| I37 | 财务 | 作废前必须能完整解释 allocation 与 plan delta；任何不安全状态必须原子拒绝。 |
| I38 | 财务 | cancelled transaction 不进入 Dashboard 现金流、未核销 advance 或订单 paid amount。 |
| I39 | 金额 | Quote total 与其行 amount、运费、折扣一致；Order total 同样可复算。 |
| I40 | 金额 | 订单改商业条件生成报价 revision；来源报价金额/条款不可静默改写。 |
| I41 | 金额 | 默认 PaymentPlan 合计等于有效合同 total；合同变更只能以批准的正数 plan 增补。 |
| I42 | 金额 | PurchaseOrder total 由采购行计算；支付/退款/advance allocation 共同解释 paid 与 unpaid。 |
| I43 | 金额 | 成本归属数量不得超过对应采购行数量；公共费用分摊必须可解释。 |
| I44 | 金额 | 订单毛利使用销售额、采购基础成本、附加成本与费用，不把 cancelled cash 误算在内。 |
| I45 | 金额 | 外币必须有正汇率，CNY 汇率必须为 1，rmb_amount 可由 amount × rate 复算。 |
| I46 | 状态 | Order shipped 仅由全部有效发货量达到订单数量进入，不能通过编辑表单直接设置。 |
| I47 | 状态 | PurchaseOrder partial/completed 仅由有效 receipt 汇总驱动；receipt reversal 可回退。 |
| I48 | 状态 | 只有 confirmed Shipment 可冲销；completed/cancelled Order 不允许冲销发货。 |
| I49 | 状态 | 只有 confirmed Transaction root 可作废；split child 与 cancelled row 不可单独作废。 |
| I50 | 回滚 | receipt reversal 保留 receipt、原 `purchase_in`、reversal movement、时间与原因，且阻止二次冲销。 |
| I51 | 回滚 | shipment reversal 保留 Shipment/ShipmentItem 和原 `sale_out`，且更新 status、reversed_at、reason 与每行 reversal reference。 |
| I52 | 回滚 | transaction void 保留 root/child 行，写入统一 voided_at/reason，不物理删除。 |
| I53 | 回滚 | 每个失败的 reversal/void 要证明没有新的 InventoryMovement/Transaction、库存、预留或状态的部分变化。 |
| I54 | 回滚 | UI 必须可见可操作状态、原因和已冲销/已作废结果；隐藏后端能力不等于业务完成。 |

## 5. Backend ↔ Frontend Coverage Matrix

| 能力 | 后端契约 | UI 入口 | UI 状态/结果 | 校验与错误反馈 | 结论 |
|---|---|---|---|---|---|
| 客户/联系人/跟进 | CRUD、附件、关联查询 | Resource/客户详情 | 列表、详情、主联系人 | 表单/API 错误 | 覆盖 |
| 产品/SKU/版本/交易单位/包装 | CRUD、batch、SKU detail | 产品、SKU、交易单位、包装页面 | SKU/包装/来源详情 | 页面校验与反馈 | 覆盖 |
| SupplierSKU/首选/停用 | CRUD、set-preferred | SKU 页面供应来源面板 | 首选/启用状态 | 后端错误通知 | 覆盖 |
| Quote/修订/notes/PI export | quote actions、export | Document、QuoteDetail/Editor | 版本树、notes、下载 | modal 与下载错误 | 覆盖 |
| Order/供应来源/预计装箱/发货 | order actions | Document、OrderDetail | fulfillment、shipment history | 对话框错误 | 覆盖 |
| PO/成本分配/付款/收货 | PO actions | PurchaseOrder、付款/成本 modal | PO、receipt history | 对话框错误 | 覆盖 |
| Receipt reversal | `POST receipts/{id}/reverse` | PurchaseOrder receipt history | 已冲销、原因/流水由 API 返回 | 原因必填、后端错误展示 | 覆盖 |
| Shipment reversal | `POST shipments/{id}/reverse` | OrderDetail shipment history | confirmed/cancelled、已冲销 | 原因必填、禁用超发 | 覆盖 |
| Inventory/手工调整 | CRUD/batch、inventory detail | Inventory 页面 | actual/reserved/available、流水 | 类型/库存错误 | 覆盖 |
| PaymentPlan 结算 | settle action | PaymentPlan 页面 | open/settled/remaining | 表单/API 错误 | 覆盖 |
| Transaction/advance/void | create、allocate、void | Transaction 页面 | split、allocation、cancelled/reason | 原因必填、后端错误 | 覆盖 |
| Finance dashboard/订单毛利 | dashboard/workbench | FinanceDashboard、OrderDetail | 指标、明细、毛利 | 日期查询错误 | 覆盖 |
| ContractChangeRequest approval | create/approve action | 通用资源页仅能 CRUD/查看 | 无批准后专用状态流 | 无正常 UI 的 approve 按钮 | **UI COVERAGE GAP-01** |

**UI COVERAGE GAP 总数：1。** GAP-01 是本轮发现，不在 Phase 3A 修复。Phase 3B 可通过 UI 创建并记录 pending 变更单，但“批准”须在 Code Review 后决定补 UI 或将该流程从本轮真实 UAT 的可完成闭环中明确排除；不得用 API 绕过。

## 6. Phase 3B 的 20 张订单矩阵

统一目标数据规模：8–10 客户、10+ 联系人、3–4 供应商、4–6 产品、12–20 SKU、15+ 报价、20 订单、8–12 PO、20+ 有结构的财务流水。建立顺序分批进行，不批量造数。

| 订单 | 场景/数据组合 | 主验证 |
|---|---|---|
| A | 1 SKU，全额预付款，全部现货 | reservation、全额收款、全额发货、shipped |
| B | 3 SKU，部分现货 + 部分采购 | 缺口、采购、入库后 reservation |
| C | 2 SKU，两个供应商 | SupplierSKU 快照、双 PO/成本归属 |
| D | 同一 SKU 分别从两个供应商采购 | 供应商来源不混淆、库存身份一致 |
| E | 部分收货、部分发货 | partial PO、两次 shipment 与数量链 |
| F | 入库后冲销一次再入库 | receipt reversal、库存/PO/reservation 回退再恢复 |
| G | 发货后冲销再发货 | shipment reversal、防重复、订单状态回退 |
| H | 同一订单两次客户收款 | 多计划/部分 settled |
| I | 客户超额付款 | root + unallocated advance child |
| J | 预收核销至同客户另一订单 | AdvanceAllocation、allocated/plan 一致 |
| K | 已核销 root transaction 作废 | root/child/allocation/两订单计划恢复 |
| L | 多订单采购公共运费分摊 | additional cost、毛利和归属 |
| M | 采购一部分归订单、一部分进库存 | PurchaseCostAllocation 数量解释 |
| N | 客户改名后继续履约 | 实时客户关联与 buyer snapshot |
| O | SKU 描述/Sales Model 修改后 | quote/order/PI 历史快照与新单据分离 |
| P | 供应商改名、SupplierSKU 修改/停用后 | 历史 PO/订单来源快照 |
| Q | 交易单位停用后 | 历史订单、采购、收发货仍可阅读/计算 |
| R | 未履约订单取消 | reservation 释放、未结计划取消、禁止错误后续操作 |
| S | 库存不足发货 | 失败原子性、无 Shipment/库存扣减 |
| T | 端到端完整 happy path | 报价→订单→采购→收货→成本→发货→收款→Dashboard |

## 7. 异常状态矩阵（30 项）

| ID | 异常操作 | 预期 |
|---|---|---|
| E01 | 必填字段为空（客户、报价、原因、金额） | 前端阻止或 400，零部分提交 |
| E02 | 非法日期/起止日期倒置 | 清晰错误，不写入 |
| E03 | 重复 SKU Code | 唯一性错误 |
| E04 | 重复/循环分类或重复属性 | 规则错误 |
| E05 | 无 SupplierSKU 创建来源采购 | 阻止或明确要求供应来源 |
| E06 | MOQ 不满足 | 规则反馈/记录当前行为 |
| E07 | 非法/停用交易单位 | 新行不能错误使用；旧行保留快照 |
| E08 | roll 等不允许小数规格填小数 | 数量校验失败 |
| E09 | 库存不足确认发货 | 无 Shipment/出库流水/预留变化 |
| E10 | 超额发货无原因 | 拒绝 |
| E11 | 超额发货有原因 | 创建可解释超发行；不可直接 reversal |
| E12 | 收货数量为零/负数 | 拒绝 |
| E13 | 未授权超到 | 拒绝 |
| E14 | 重复收货冲销 | 拒绝，零新增流水 |
| E15 | 下游出库后收货冲销 | 拒绝，库存/PO/预留不变 |
| E16 | 收货冲销空原因 | 拒绝 |
| E17 | Shipment 原流水缺失或 SKU/订单/数量/source 异常 | 全单拒绝，零 reversal |
| E18 | 重复发货冲销 | 拒绝 |
| E19 | 含超发/增补 Shipment 冲销 | 拒绝 |
| E20 | 已完成/取消订单冲销发货 | 拒绝 |
| E21 | split Transaction 直接作废 | 拒绝 |
| E22 | root Transaction 重复/空原因作废 | 拒绝 |
| E23 | allocation 明细与 allocated_amount 不一致时作废 | 安全拒绝 |
| E24 | PaymentPlan 币种不匹配 | 拒绝 |
| E25 | 外币缺失/零/负汇率或 CNY 非 1 | 拒绝 |
| E26 | 预收跨客户/跨供应商/跨方向/超余额核销 | 拒绝 |
| E27 | 无效国家生成报价 | 规则错误 |
| E28 | 报价修订尝试换客户 | 拒绝，原报价不变 |
| E29 | 手工订单状态改 shipped/PO 改 partial/completed | 拒绝或 UI 不提供入口 |
| E30 | 浏览器重复点击收货、发货、付款、冲销、作废 | 记录结果，不能产生重复业务副作用 |

## 8. 主数据修改回归矩阵

| 修改 | 先建立的历史对象 | 必查页面/结果 |
|---|---|---|
| 客户名称 | Quote、PI、Order、Transaction | 客户列表/搜索显示当前名；buyer snapshot 与既有 PI 按设计保留 |
| 联系人 | 客户、Quote | 客户详情当前联系人与报价 recipient/buyer 联系字段不被意外覆盖 |
| 产品名称 | SKU、Quote/Order | 当前产品显示变化；SKU/历史行快照符合设计 |
| SKU 描述 | Quote、Order、PO、Shipment | 旧 quote/order/PI 用快照；新报价用当前描述 |
| Sales Model | Quote、Order、PI | 旧 Sales Model snapshot 不变；新 revision/报价按当前输入 |
| SKU 参数 | SKUVersion、后续报价 | 产生/保留版本链，不替换 SKU 身份 |
| 供应商名称 | SupplierSKU、PO、OrderItem | 当前关联显示当前名；历史供应商快照可追溯 |
| SupplierSKU 信息/停用 | 已有 PO/订单与待采购行 | 新选源受启用状态限制，旧采购/订单行保持来源快照 |
| 包装模板 | 已有 packing plan、报价预计装箱 | 旧 plan 快照稳定，新计划采用新参数 |
| 交易单位停用 | 已有 quote/order/PO/receipt/shipment | 旧 trade snapshot 可读可算，新建行不误选 |
| 订单商业条件 | 已接受 Quote、Order、PaymentPlan | 必须走正确修订/合同变更规则；历史金额/计划不静默改写 |

## 9. 报价/订单历史快照专项

1. 使用客户、SKU、图片、Sales Model、描述、交易单位建立报价 **A**，导出 **PI A** 并保存 UI 证据。
2. 从 A 创建订单，至少产生一张关联采购单、一个 receipt 和一个 Shipment。
3. 仅通过 UI 修改客户名、SKU Sales Model、SKU 描述（必要时图片）；另修改供应商名/SupplierSKU 和交易单位启用状态。
4. 重新查看/导出 A：验证 QuoteItem、buyer_company_name、交易行及文件是否按快照保持；同时记录列表中允许显示当前主档的字段。
5. 从 A 创建 **A-1** 修订，确认 root/parent/revision_summary、客户锁定、A 与 A-1 金额/描述/Sales Model 分离。
6. 查看订单、采购、收货、发货和库存流水：验证对应的 snapshot 字段仍解释历史操作，而不是被当前主档覆盖。

## 10. Phase 3B 清库方案（设计，绝不在 Phase 3A 执行）

1. 由操作者确认当前为开发环境，分支为经 Code Review 批准的 Phase 3 分支，且不是生产库。
2. 停止本地 Django/前端进程，记录当前 HEAD、数据库绝对路径、文件大小、时间及 `sqlite3` 完整性检查结果。
3. **先备份** SQLite 到 `backend/backups/before-phase3-YYYYMMDD-HHMMSS.sqlite3`；校验备份存在、大小合理且可只读打开。备份不成功即停止。
4. 清理范围须在 Phase 3B 批准的显式脚本/操作清单中逐表确认：客户、联系人、跟进/附件、报价/修订/notes、订单/明细/预留/装箱、采购/明细/成本归属、GoodsReceipt、Shipment/明细/实际装箱、库存业务流水、Transaction/split/AdvanceAllocation、PaymentPlan、合同变更，以及仅为业务演示建立的产品/SKU/供应商/SupplierSKU/交易单位/包装数据。
5. 必须保留：Django migrations、开发超级管理员与用户账号、组织、职位、角色、权限、系统基础配置及保证登录/运行所必需的静态配置。若某条业务数据同时是基础配置，先列入白名单并由操作者确认，不凭名称猜测删除。
6. 清理后只读核对保留对象、迁移状态、登录能力和空业务基线；不得利用 SQL/脚本直接创建 Phase 3 UAT 数据。
7. 任何表关系、文件附件或保留边界不明确时停止并提交 Code Review 决定。

## 11. Phase 3B UI 操作顺序

1. 获得本计划 Code Review 批准，按第 10 节备份/清库并记录空基线。
2. UI 建立组织已允许的基础资料、客户/联系人/跟进、分类/产品/SKU/交易单位/包装、供应商/SupplierSKU。
3. 先建立 A–D 的报价与订单，录入现货、采购和部分履约样本；每批后检查库存/预留/订单工作台。
4. 建立 E–H，完成部分收货、部分发货、两次付款与收货/发货回滚；每次回滚立即做只读核对。
5. 建立 I–K，完成超额收款、跨订单核销和 root void 的完整财务闭环。
6. 建立 L–M，完成公共费用、多订单成本归属、库存归属和毛利核对。
7. 建立 N–Q，按第 8、9 节主动修改主数据并完成历史快照/导出回归。
8. 建立 R–T，完成取消订单、库存不足及完整 happy path。
9. 执行第 7 节 30 个异常场景；每一项记录 UI 步骤、错误文本、前后只读核对、截图和关联对象 ID。
10. 汇总不变量 54 项、Dashboard/报表、已知风险和 UI gap；只在获得授权后提出 Phase 3B 后续缺陷修复任务。

## 12. 旧管理命令偏差（LEGACY TEST TOOL DRIFT，6 项）

| ID | 工具 | 当前偏差 | Phase 3 处理 |
|---|---|---|---|
| LTD-01 | `run_business_flow_checks.py` | 使用 `APIClient` 并创建保留业务数据，不是真实 UI 操作。 | 仅作历史规则参考，禁止作为 UAT 造数。 |
| LTD-02 | `run_business_flow_checks.py` | 直接调用 `record_supplier_payment` 等服务，绕过 UI/序列化契约；未覆盖当前 receipt/shipment reversal、root-split void 与 openpyxl 导出链。 | 记录为旧自动化，不用其成功代替当前 UAT。 |
| LTD-03 | `run_edge_business_flow_checks.py` | 使用 APIClient 且创建持久数据，违反 Phase 3B 真实 UI 原则。 | 仅阅读异常意图。 |
| LTD-04 | `run_edge_business_flow_checks.py` | 未覆盖 Phase 2A/2B/2C 的完整回滚原子性与当前 UI 入口；部分断言面向旧 contract。 | 不在 Phase 3A 擅改，后续另立维护任务。 |
| LTD-05 | `seed_demo.py` | 直接 ORM `update_or_create` 业务主数据、订单、库存流水和财务流水，非真实用户路径。 | 禁止用于 Phase 3 UAT。 |
| LTD-06 | `seed_demo.py` | 直接预设业务状态/流水，可能绕过当前状态机、快照、payment plan 和 reversal 约束。 | 保留为演示工具候选，需独立审查后才维护/删除。 |

## 13. 验收标准与已知风险

### 验收标准

1. 20 张订单全部按矩阵经 UI 建立，至少 8–12 张 PO、完整/部分/多次收发货和 20+ 条结构化财务流水均有可追溯证据。
2. 54 条 Business Invariant 均有 PASS/FAIL/不适用结论；任何 FAIL 附复现步骤、对象 ID、截图、UI 错误和只读核对。
3. 30 个异常场景均实际执行；所有要求原子失败的场景证明无部分副作用。
4. PI 历史快照专项通过，旧报价/订单与 A-1 修订版可区分且 renderer 正常导出。
5. 收货冲销、发货冲销、root 财务作废各至少一次成功、一次重复/非法失败；前后库存、预留、状态、计划和流水均符合矩阵。
6. 所有发现的 UI 覆盖缺口和历史工具偏差均独立记录，不用 API/脚本绕过。

### 已知风险 / 待决项

1. **GAP-01：** ContractChangeRequest 有后端 approve action，但当前正常 UI 没有专用批准入口；本轮不修复。
2. 历史 2026-09 UAT 结果在 Phase 1/2/2C、CI baseline 与 quote renderer 迁移前完成，只能参考，不能作为当前通过凭据。
3. SQLite 清库存在误删基础配置和附件文件关联风险；未核实白名单前不得执行。
4. 真实 UI UAT 的数据规模与浏览器稳定性会影响工期；失败时应记录，不得降级为 API/脚本造数。
5. 自动化测试通过只能证明代码基线，不证明 20 单 UI 业务组合已通过。

## 14. Phase 3A 交付摘要

- 完整主业务链：**11** 条。
- 最小可操作子流程/分支：**61** 个。
- Business Invariant：**54** 条。
- UI COVERAGE GAP：**1** 个。
- LEGACY TEST TOOL DRIFT：**6** 项。
- 计划订单：**20** 张。
- 计划异常场景：**30** 项。

本阶段到此停止，等待 Code Review；不清库、不造业务数据、不改业务代码，也不开始 Phase 3B。
