# Inventory Management UX Review — Phase A

日期：2026-10-07。起点：`3f73ed9da88c7a26bb0e22b37afbb1516e8cb054`（基线 CI #163 三项 SUCCESS）。用户本次规范确认 Customer、Quote、Order、Purchase UX 已接受/冻结。

本次仅优化库存概览、SKU 库存工作台与跨模块上下文。库存流水页面仍为 Phase B；未改库存计算、预留、采购入库、发货、冲销、Trade Units、后端生产代码或迁移。Inventory 模块未标记 UX-FROZEN，独立 ChatGPT 审查待完成。

## 问题与路由设计

原页面使用本地 query/sortKey/sortDirection/selectedSku/detailTab，离开页面后无法恢复原 SKU、标签和列表条件。现在 URL 为持久状态来源：

| 参数 | 约定 |
|---|---|
| search | 字符串；300ms 防抖，初始化/刷新/Back 从 URL 恢复 |
| sort | sku、display_name_cn、actual_quantity、reserved_quantity、available_quantity、in_transit_quantity、to_procure_quantity、status；无效值回退 sku |
| direction | asc / desc；回退 asc |
| attention | 仅 `1` 激活；关闭删除参数 |
| detail | 正整数 SKU id；非法或已删除显示错误且允许关闭 |
| tab | movements、orders、purchases、shipments、operation_logs；回退 movements |

例：`/inventory?search=COB&sort=available_quantity&direction=asc&attention=1&detail=12&tab=orders`。

查询变更通过串行 Router 更新合并当前 query，保留无关上下文，避免短时间搜索/排序/筛选更新相互覆盖。排序/标签变化不重载列表；搜索继续前端匹配 SKU、中文名、产品名、产品编号、规格。页面离开与卸载清除搜索定时器。详情只跟随 detail 或列表刷新加载，不受可见行筛选影响；优先用完整 rows，缺失才 GET `/skus/<id>/`。异步请求标识防止旧 SKU 响应覆盖新工作台。失败保持抽屉，显示“库存详情加载失败”与“重新加载”。关闭仅删除 detail/tab。

## 列表与库存语义

五项概览维持 SKU 数量、实际库存、可用库存、在途采购、待关注，按当前筛选范围统计。数量继续按基础单位 Map 分组，pcs/m 等不相加。真实环境只有 pcs，混合单位由自动化样本 `8 pcs / 340 m` 验证。

待关注条件严格为 `row.has_anomaly || Number(row.to_procure_quantity || 0) > 0`。普通零库存不属于待关注；没有加入安全库存/补货点。待关注卡与“仅看待关注”按钮均可切换、显示激活状态，其他卡不作筛选。状态优先级保持需处理（异常或可用负数）、待采购、无库存、有库存。

列表八列：SKU、中文 SKU 名称、实际库存、已预留、可用库存、在途采购、待采购、状态。名称格保留基础单位，页面提示所有数量以 SKU 基础单位显示。快捷入口顺序改为盘点与库存流水、采购与验货入库、订单发货，路由不变。

## SKU 库存工作台

沿用原抽屉、数据接口和表格，宽度 min(900px,100%)，<=980px 为100vw，绿色头部 #123C36。身份包含 SKU、中文名称、基础单位、库存状态；原六项后端指标全部保留，无金额。指标下解释实际/预留/可用/在途/待采购的既有语义，经 backend/crm/services/fulfillment.py、serializers.py 只读核对，未增加公式。

| 指标 | 工作台标签 |
|---|---|
| 实际库存、可用库存 | 库存流水 |
| 已预留 | 关联订单 |
| 在途采购、待采购 | 采购记录 |

使用可键盘访问按钮、轻量 hover/focus 样式。标签固定顺序：库存流水、关联订单、采购记录、出库记录、SKU 操作日志。标签通过 URL 保存，标签内搜索/排序仍为本地临时状态，切换标签清空。空状态分别说明该 SKU 无流水、无关联销售订单、无采购记录、无发货、无 SKU 本身操作记录。

顶端“查看采购单 / 查看销售订单 / 查看库存流水”继续携带 sku。记录链接分别保持 `/purchase-orders?sku=<id>&detail=<purchaseId>`、`/orders?sku=<id>&detail=<orderId>`、`/inventory-movements?sku=<id>&detail=<movementId>`。Browser Back 自然恢复来源 URL，无 returnTo 子系统。发货记录订单链接继续使用 row.order。

日志查询继续 entity=crm.sku/object_id；明确提示“这里只显示 SKU 本身的操作记录；库存增减、入库、出库和冲销请查看‘库存流水’”。后端 InventoryMovement 审计属于 crm.inventorymovement，未声称这里是完整库存审计。开发身份和审计开关不改。

## 真实 UI UAT

使用 localhost:5191 现有数据；只查询与导航，未提交任何库存或业务变动。

| UAT | 结果与证据 |
|---|---|
| A001 | PASS；3 个 SKU，实际0.01 pcs、可用0.01 pcs、在途6.99 pcs、待关注0；分单位汇总自动化补充 |
| A002 | PASS；搜索SKU-000001、可用库存升序，刷新后仍保留搜索与排序 |
| A003 | PASS；启用attention后无匹配；现有两条普通零库存未进入。缺口/异常正例自动化补充 |
| A004 | PASS；点击SKU-000001生成detail=1、tab=movements，原search/sort/direction保留 |
| A005 | PASS；工作台显示SKU/中文名/pcs/状态与原六指标 |
| A006 | PASS；已预留→orders，在途→purchases，实际→movements；其余指标自动化覆盖 |
| A007 | PASS；采购记录PO-2026-00006→sku=1&detail=6，Back恢复SKU1/purchases及search/sort/direction/attention |
| A008 | PASS；关联订单SO-2026-00035→sku=1&detail=35，Back恢复SKU1/orders及完整上下文 |
| A009 | PASS；流水REV-4198B418E1814CF1→sku=1&detail=82，Back恢复SKU1/movements及完整上下文 |
| A010 | PASS；SKU日志范围提示、开发审计状态明确；刷新恢复operation_logs，关闭仅删除detail/tab |

attention=1 下列表为空仍成功直达 SKU1，实证筛选外详情不会被关闭。

截图：`uat-evidence/inventory-phase-a/overview.jpg`、`workbench.jpg`、`sku-log-scope.jpg`。

## 自动化与回归

新增 `frontend/tests/inventory-workbench.spec.js` 19 个交互用例，使用真实 Vue Router/RouterView，覆盖规范24项行为（合并用例），包括300ms、防并发覆盖、白名单回退、分单位、安全零库存、行打开关闭、筛选外/缺失/非法详情、原始指标、五指标跳转、标签顺序/刷新、三种准确链接及页面卸载后Back、日志范围、失败重试、旧响应保护。PCR-010现有2项测试仅调整三个入口文字断言。

- Node 单元：111 PASS。
- Vitest 全前端：262 PASS（30个测试文件）。
- 抽屉字体检查：1 PASS。
- Vite build：PASS；保留现有大包体提示。
- Django：565 tests OK，10 skipped（本地PostgreSQL专属测试由CI覆盖）；system check无问题。
- makemigrations --check --dry-run：No changes detected。
- git diff --check：PASS。

## CI 与验收

最终提交后的 HEAD SHA、CI run 链接、backend/backend-postgres/frontend 结果在交付回复中记录，避免文档自引用提交哈希。必须确认三项 SUCCESS 后交付；独立 ChatGPT review 仍待外部审查。Phase A 实施与验证不代表 Inventory UX-FROZEN；不启动 Phase B。

# Inventory Phase B — 库存流水与手工调整 UX

实施与 UAT：2026-10-07 至 2026-10-08。起点 `93170f6ebb4154345eba71fe149fad302ac4c6db`；Phase A 已由用户接受，基线 CI #164 三项 SUCCESS。此节更新前节的历史阶段状态。

## 流水与导航

沿用 ResourcePage、InventoryMovementCreateModal、EntityDetailModal。仅库存流水的 search/type/direction/source/detail 成为 URL 状态，搜索继续调用后端原搜索能力并保持 300ms 防抖。类型为十种手工类型；方向按 type 语义映射，同时识别自动 purchase_in/sale_out；来源依据 is_automatic/source_type 区分系统自动、手工登记、冲销生成。筛选在完整分页结果上执行，未新增后端逻辑。

重置只移除四个筛选字段；详情关闭只移除 detail，保留 sku 和其余上下文。关闭使用 replace，使 Inventory → Movement → 关闭 → Back 恢复来源工作台的 search/sort/direction/detail/tab，无 returnTo。SkuContextBanner 保留，SKU 名称与基础单位从精确 SKU 或历史交易快照取得。

四张卡仅统计当前筛选的流水、入库、出库、冲销记录数，不混合汇总 SKU 数量。列表顺序为日期、流水号、SKU/产品、类型、库存变动、来源、仓库、关联单据、冲销状态、操作。数量带安全基础单位；窄屏横向滚动并固定操作列。三类来源使用独立徽标，状态区分正常、已冲销、冲销流水。

详情先显示流水号、日期、SKU、类型、基础数量变化、交易规格/数量、仓库、订单/单据、来源、备注、冲销状态。流水操作日志仍查询 crm.inventorymovement。其他资源搜索及 Customer 详情路由不变。

## 手工登记与冲销

创建表单分为流水基本信息、关联业务、SKU 明细、保存说明。流水号只读自动生成；保留可选多订单和多个 SKU，每个 SKU 一条独立流水，沿用现有 SKU 选择模型（每个 SKU 一行）。补齐现有后端支持的生产入库/生产领料选项。交易单位控件独立成列，原 tradePayload 与批量 API 不变。默认仓、可选成本和成功刷新/toast 保留。

明确提示正式采购使用“验货入库”、正式销售使用“确认发货”；手工流水仅用于非标准调整。数量必须正数，方向由类型决定；成本参考依现有规则。底部说明保存后生成 N 条独立流水。

自动或已冲销流水没有编辑；只有未冲销手工流水可以冲销；所有流水没有删除。冲销对话框说明保留原记录并生成反向流水，展示原流水号/SKU/类型/数量/日期/订单，原因必填、确认按钮为破坏性样式。原 API、库存效果和业务校验不变。

## 真实 UI UAT

使用 localhost:5191 现有数据。只读取、导航、填写后取消；未保存新流水或执行冲销。

| UAT | 结果 |
|---|---|
| B001 | PASS；90条，入库41/出库49/冲销12；四卡与十列层级正确 |
| B002 | PASS；sku=1 搜索 GR-BC0D4E04B9CE4171，刷新保留搜索及 SKU 名称 |
| B003 | PASS；手工/入库/盘盈筛选9条，日期、SKU、数量、来源与参考号可辨 |
| B004 | PASS；点击 GR-BC0D4E04B9CE4171 得 detail=75，刷新同一详情 |
| B005 | PASS；来源库存 SKU1/movements → REV-4198B418E1814CF1（detail=82）→ 关闭保留sku=1 → Back恢复原完整工作台 URL；键盘激活链接验证 |
| B006 | PASS；自动采购入库 GR-BC0D4E04B9CE4171 明确来源，无编辑/冲销/删除 |
| B007 | PASS；手工 IM-67A35DF8FEE147E3 有编辑/冲销，无删除；未执行冲销 |
| B008 | PASS；创建四层级、采购/销售正式流程边界与正数提示明确 |
| B009 | PASS；SKU000001用箱（2箱=20pcs），SKU000003用pcs；独立数量2/3、成本7.1/8.2、仓库A/B、参考号及备注，取消不保存 |
| B010 | PASS；冲销对话框展示原记录与反向流水说明，原因空时确认禁用，取消 |

证据：`uat-evidence/inventory-phase-b/ledger.jpg`、`movement-detail.jpg`、`manual-create.jpg`、`multi-sku.jpg`、`reversal-dialog.jpg`。

## 自动化与回归

新增 inventory-ledger.spec.js 20项挂载交互测试，覆盖规范28项要求，包括真实 Router/RouterView 回退、详情刷新、筛选保留上下文、混合单位仅计数、操作保护、精确冲销ID/原因、取消无提交、多SKU TradeUnit精确payload、成功刷新、正数校验与失败保留输入。其他资源搜索行为有回归断言。

- Vitest 全前端：282 PASS（31文件）。
- Node 单元：111 PASS；抽屉字体检查：1 PASS。
- Vite build：PASS（最终布局再次构建）；现有大包体提示保留。
- Django：565 tests OK，10 skipped；system check 无问题。
- makemigrations --check --dry-run：No changes detected。
- 无后端生产代码、模型、迁移、权限或库存核算语义变动。

## CI 与阶段状态

最终 HEAD 与 CI run/三项结果在交付回复记录，避免提交哈希自引用。仅正常 commit/push。Phase B 实施及验证完成，等待独立 ChatGPT review；尚未 UX-FROZEN，未启动 Finance UX。
