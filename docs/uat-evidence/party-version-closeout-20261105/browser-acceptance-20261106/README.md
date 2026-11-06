# 主体替换与审批差异浏览器验收（部分完成）

基线 506b14f293fe8fcb989eeaf1c5d35866624553ad。使用隔离 SQLite、合成数据、两个独立认证账号和真实 Google Chrome；开发超级管理员模式，不代表自然人独立或正式 RBAC 验收。CI 因额度暂停，未触发，不能记为通过。

- 报价同主体更正：既有 `party-quote-approval-real.spec.js` 1 项通过。桌面申请、390px 独立账号审批和生成草稿；原报价地址及金额未变。截图与 HTTP 结果在 `party-approval/`；本次运行未保存完整控制台日志。
- 销售订单主体替换：既有 `party-replacement-real.spec.js` 1 项通过；追加 `party-replacement-acceptance-20261106.spec.js` 1 项通过，桌面申请、390px 审批及新建关联草稿。完整脱敏日志见 `replacement-acceptance.log`，截图和实际 HTTP 结果见 `replacement/`。申请前后原订单详情和履约接口响应逐项相等，数据保存在 `replacement/original-order-before-after.json`。该合成原单没有实际收付款或发货事实，因此不能证明非零资金和履约事实不变。
- 申请时对目标主体缺失字段逐项点击确认留空；390px 审批截图中显示差异为“未记录”。尚未核对持久化留空与历史未知的区分，不能据此认定显示存在缺陷或符合语义。
- 未完成：扩展双方资料审批差异、历史未知和明确留空持久化对照；报价与采购替换本轮双视口验收；非零资金、发货/入库事实前后核对；审批差异完整桌面与390px视觉矩阵。原有报告的旧证据不能代替本轮这些项目。
- 控制台出现订单详情 Vue Transition 非元素根节点警告；目前仅确认警告，未确认对本任务造成业务影响，不登记为主体替换业务缺陷。

未修改业务代码，未修改公共台账。本次结果仅限上述已执行场景，不构成整体验收通过。

注意：结束时发现工作树中 OrderDetailModal.vue 和 PurchaseDetailModal.vue 有非本任务产生的未提交改动；本轮没有编辑或还原这些文件，运行结果对应当时工作树状态，不能称为干净基线 HEAD 验收。

## 2026-11-06 追加：扩展资料、非零资金及履约

使用指定工作树当时的未提交业务组件状态，隔离 SQLite、Google Chrome、两个合成认证账号（不证明自然人独立）。未触发 CI；不修改业务代码。销售订单、采购订单的扩展资料替换各完成桌面申请、桌面和 390px 审批差异查看、390px 独立账号审批及创建关联草稿。完整实际日志：[扩展验收](extended-run-03.log)，数据：[申请与结果](extended/http-results.json)、[销售新单](extended/order-result-details.json)、[采购新单](extended/purchase-result-details.json)。截图包括[销售桌面](extended/order-review-desktop.png)、[销售390](extended/order-review-390.png)、[采购桌面](extended/purchase-review-desktop.png)、[采购390](extended/purchase-review-390.png)。人工查看销售桌面及采购390截图，差异可读，显示“未知 → 已留空”。

资料在草稿阶段保存，通过现有正式化、收付款、入库和发货服务建立事实：确认客户收款 USD 2、确认供应商付款 USD 2、采购入库 1、销售发货 1。替换前后比较原销售单和采购单、两笔资金流水、3 个付款计划、入库、发货及发货明细、2 条库存流水和原始扩展资料；[前](extended/source-before.json)、[后](extended/source-after.json)逐项相同。范围为此合成样本及列出的表，不代表对所有资金和履约情况穷尽验证。

两种单据原始扩展税号为历史未知 `null`；替换时明确选择税号留空、电话维持未知、账单地址另行填写。申请响应和新草稿资料分别证实税号 `""`、电话 `null`、账单地址为新值；原始资料未改写。报价替换独立通过：双账号、桌面及390px查看审批差异，申请201、批准200、创建200、PI读取200，明确留空国家在新报价保存为空；[日志](quote-run-02.log)、[HTTP](replacement-quote/http-results.json)、[桌面](replacement-quote/review-desktop.png)、[390](replacement-quote/review-390.png)。报价样本不含扩展资料，不能据此声称报价含扩展资料的替换草稿可创建；现有产品明确提示该场景暂不支持。

### 发现：SO/PO 基础主体审批差异混淆未知与确认留空

复现：替换申请中对拟议国家或地址点击“确认留空”，提交后查看主体变更记录。扩展资料差异正确显示“未知 → 已留空”，但同一审批记录的基础主体字段把明确留空显示为“未记录”，例如[销售桌面截图](extended/order-review-desktop.png)的国家 Germany → 未记录；[采购390截图](extended/purchase-review-390.png)的地址亦如此。`DocumentPartyVersions.vue` 的 `textValue` 将 `null` 和 `''` 均映射为“未记录”，使审批者无法从基础字段差异辨别历史未知与明确留空。申请快照为明确空字符串，持久化结果未因此被证明错误；缺陷为审批展示语义。本轮按用户限定不修改业务代码；建议统一区分“未知”和“已留空”，并对销售、采购两种视口复核。

首次扩展运行是 seed 路径错误（[日志](extended-run-01.log)）；第二次因先正式化后写扩展资料，被草稿保护拒绝（[日志](extended-run-02.log)）；已按合法顺序建立草稿资料后正式化。报价首次尝试使用非专用 spec，模板隔离入口不适用，复制目标与源重合被 Windows 拒绝（[日志](quote-run-01.log)）；后改用已有专用 spec 和隔离模板路径通过。失败未计入通过，未绕过保护。
