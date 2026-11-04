# Workspace UI 只读证据预审

2026-11-04；核对工作树 HEAD `4388947d70d26bca66ca0bfc76b2383a2fc0d404`。这是 Codex 静态证据预审，不是 ChatGPT 独立复审。本次没有运行测试、操作浏览器、连接数据库或修改产品及公共台账。工作树存在其他任务的进行中修改，因此当前文件观察不能冒充该提交的全量运行结果。

已读取 AGENTS、PROJECT_ISSUES、PROJECT_PHASES、REVIEW_PROTOCOL；READINESS-GATES 实际位于 `docs/uat-evidence/r1-prelaunch-consolidation-20261104/READINESS-GATES.md`。以下路径均相对仓库根目录。代码/测试路径表示现存核对入口，不代表每个文件对该 Issue 均有完整专项覆盖。没有核实到精确引入提交的项写 UNKNOWN。

## 证据索引及后续变化

- E1 `docs/Product-UX-Second-Review.md`：FR-001/002/008 和 Final Polish 记录存在。早期图片明确保存在独立证据提交 `e958fe1518093d6179f8281f12bc5c722edd707e` 的 `ux-review/second-review-final/`；Polish 图片在 `2c585901f9e3b7f245dc966940ef70fbd2bba237`。当前工作树缺少这些图片不能直接推定历史成果不存在；本次未逐一读取这两个提交的图片对象，图片内容及可取得性仍待复核。
- E2 `docs/uat-evidence/iss-025-customer-status-labels/README.md` 与 `review-iss025-status-consistency/README.md` 均存在；后者明确补修报表客户状态分组，不能只看最初列表修复。代码来源 `a8dd277609d7364d301d1a330f717f00962d8619`，报表补修报告记 `20981f9`，视觉证据提交记 `f9e2c7493ba86007fb6969d826d336dc4077edb7`。
- E3 `docs/uat-evidence/integration-021-029-027/README.md` 存在，ISS-027 完整来源 `5a05a8b0c4d856c9378cad452b1e98307bd135c0`，集成映射 `d022e35`。早期 Chrome 超时不能覆盖后续保存、清除、失败重试及窄屏验收记录。
- E4 `docs/uat-evidence/iss-049-quick-filters/TEST_LOG.md` 存在；来源 `9d08009f62920c62399ec48defe7f4d1c2e21411`。
- E5 `docs/uat-evidence/r0-f5/README.md`、`r0-f5-final/README.md` 与 `iss-080-contact-duplicates/README.md` 为联系人/跟进与后续重复提醒证据入口。ISS-080 实现来源 `efb2546b69ae4ace60715dcb97803145248d3a1b`；当前集成历史另见 `d2d0a09`，不能因原提交不在直系历史就认定实现缺失。
- E6 `docs/uat-evidence/r0-f6/README.md`、`SCREENSHOTS.md`、`manifest.json` 及 products/parameters/categories JPG 实际存在。`r0-f7a/README.md`、`manifest.json`、`capture-records.json` 及 SKU/source 三尺寸 JPG 实际存在；历史尺寸错误已有替换记录，不能继续称“无归档能力”。
- E7 `docs/uat-evidence/r0-f7b/`、`r0-f8a/`、`r0-f8b/`、`r0-f8c/`、`r0-f9/`、`r0-f9-vis-01/` 目录存在。F9-VIS 中 suppliers、skus 等 complete/accepted/stable JPG 和 TXT 实际存在。文件存在不等于独立审图通过，也不证明历史特定状态、所有指定像素尺寸已补齐；ISS-100 的尺寸限制仍需按原范围处理。

## 逐 ID 核查

缩写：`V/` = `frontend/src/views/`，`C/` = `frontend/src/components/`，`T/` = `frontend/tests/`，`B/` = `frontend/browser-tests/`。下表关闭缺项仅用于仍开放范围；CLOSED 项保留既有接受，不重新打开。

| ID | 当前代码与测试入口 | 来源 SHA / 证据 | 具体关闭缺项或既有接受边界 |
|---|---|---|---|
| ISS-009 | C/EntityDetailModal.vue、V/ResourcePage.vue；T/second-review-foundation.spec.js、T/follow-up-safety.spec.js | UNKNOWN；E1 FR-001，后续 E3 | 独立核对保存跟进后不刷新页面的客户列表/详情日期同步及失败不改日期；取得历史 AFTER 原图。 |
| ISS-010 | C/QuoteEditorModal.vue；backend/crm/quote_numbers.py；T/sales-safety.spec.js | UNKNOWN；E1 FR-002 | 独立核对空/无效国家中文提示、表单保留及合法国家成功；ISS-008 映射另计。 |
| ISS-016 | V/DocumentPage.vue、C/OrderDraftModal.vue（117 行空日期转 null）；T/decimal-order-editors.spec.js | UNKNOWN；E1 FR-008 | 独立复核直建与报价转单空值、有效日期和非法输入；历史图片在独立证据提交，非当前截图。 |
| ISS-025 | V/ResourcePage.vue、frontend/src/utils/customerListStatus.test.js；backend/crm/serializers.py | E2 | 独立核对列表/详情/跟进/报表五种状态、URL 筛选及原始代码不变；业务接受简化措辞仍待凭证。 |
| ISS-027 | V/ResourcePage.vue、C/SegmentedDateInput.vue；T/follow-up-safety.spec.js、T/segmented-date-validation.spec.js | E3 | 独立复核 keep/set/clear、历史重放不覆盖当前计划、非法输入与失败重试；复用后续 Chrome 证据。 |
| ISS-030 | C/EntityDetailModal.vue、C/QuoteDetailModal.vue；T/final-polish.spec.js | `f936fda9d7276594dbe0edfe1b1f11ab3312c20d`；E1 | 独立核对显示去尾零、微小数和有效精度、payload 不变；取得 Polish 01/02 原图。 |
| ISS-031 | C/OrderDetailModal.vue、V/PurchaseOrderPage.vue；T/final-polish.spec.js | 同 ISS-030；E1 | 独立核对草稿只有一个主确认入口，其余收货/付款/发货操作保留；Polish 03/04。 |
| ISS-032 | C/OrderDetailModal.vue；T/final-polish.spec.js、T/order-overview-ux.spec.js | 同 ISS-030；E1 | 独立核对完成/取消/活动状态提示；应收待办由 ISS-001 后续成果另验，不能把旧缺口重复登记。 |
| ISS-033 | C/QuoteDetailModal.vue、C/OrderDetailModal.vue；T/final-polish.spec.js | 同 ISS-030；E1，另有 focused-order-columns 后续修补 | 独立检查长名称、SKU、基础/交易数量及表内滚动；后续列宽修复精确 SHA UNKNOWN。 |
| ISS-034 | C/QuotePreviewModal.vue、C/QuoteEditorModal.vue；T/final-polish.spec.js | 同 ISS-030；E1 | 独立核对 saved 属性、草稿/保存版标题及历史版本预览，Polish 07。 |
| ISS-049 | V/ResourcePage.vue、V/TransactionPage.vue；T/customer-ux.spec.js、T/payment-plan-filters.spec.js | E4 | 独立核对客户/跟进/流水组合筛选、重置、翻页和 URL 恢复，后端范围不得扩大。 |
| ISS-056 | backend/crm/tests/test_sales_data_scope.py | `4298c31ec043b2f3fc2d690768455d7df417de08` 为接受提交 | CLOSED，用户 2026-10-14 转述独立接受；CI 38433549045。保留金额泄漏断言修复范围；视觉不在关闭范围。 |
| ISS-059 | V/PaymentPlanPage.vue；T/r0f1-directed.spec.js、B/finance-layout.spec.js | 同 ISS-056 | CLOSED，同一用户接受与 CI；不因本次没运行布局测试重开。 |
| ISS-060 | V/PaymentPlanPage.vue、V/TransactionPage.vue；T/r0f1-directed.spec.js、T/payment-plan-order-context.spec.js | 同 ISS-056 | CLOSED，保留文案及订单编号显示接受；后续财务文案变化另按实际差异审查。 |
| ISS-061 | V/PaymentPlanPage.vue；T/r0f1-directed.spec.js | 同 ISS-056 | CLOSED，旧成功提示不与失败并存的代码/回归已接受；不扩大为独立视觉通过。 |
| ISS-071 | V/ResourcePage.vue；T/supplier-ux.spec.js、B/supplier-ux.spec.js | `8cb265e1645bf84d0274f77f2d684f71967fad83` | CLOSED，用户转述独立代码/交互接受，CI 38539359761；视觉归 ISS-073。 |
| ISS-072 | V/ResourcePage.vue；T/supplier-terms-display.spec.js、T/supplier-ux.spec.js | 同 ISS-071 | CLOSED，保留表单/详情规则说明及历史计算不变的接受；视觉归 ISS-073。 |
| ISS-073 | V/ResourcePage.vue；B/supplier-ux.spec.js | UNKNOWN；E7 后续供应商图已归档 | BLOCKED 的旧“不能归档”已有后续变化；仍需独立接受原图覆盖状态/尺寸，不能自行关闭。 |
| ISS-074 | V/PurchaseOrderPage.vue；T/purchase-payment.spec.js、B/iss075-payment-terms-real.spec.js | 后续 `64fb397aa065062e192ceb30040421f59b63a08c`；原缺陷来源 UNKNOWN | 独立回放真实默认/自定义供应商加载后不输入取消、加载中输入、取消后继续编辑；不能用付款保存主链替代此时序。 |
| ISS-076 | V/ResourcePage.vue；B/crm-ux.spec.js | UNKNOWN；E5、E7 | 归档能力已恢复；独立复核联系人/跟进原图来源、像素、状态和剩余尺寸限制。 |
| ISS-077 | V/ResourcePage.vue；T/crm-list.vitest.js、B/crm-ux.spec.js | `92e8c46d4ce01e18cd164e152d345c58433c9305`；E5 | 独立检查联系人列表/详情/返回及三尺寸图片，保留已有已覆盖交互成果。 |
| ISS-079 | frontend/src/composables/useUnsavedChangesGuard.js、V/ResourcePage.vue；T/crm-saving.spec.js、B/crm-saving.spec.js | `86650adc795ae18a087996b0bdbe37747397e3e0`；E5 | CLOSED，2026-10-15 用户明确接受保存竞态修复，CI 38605116907；不扩大为视觉接受。 |
| ISS-080 | V/ResourcePage.vue；T/customer-ux.spec.js、V/ResourcePage.test.js | E5 | 独立复核全分页联系人、隐藏记录、国际电话、编辑排除自身、跨客户授权和手动继续；精确专项测试映射待补。 |
| ISS-081 | V/ProductPage.vue；T/product-master-ux.spec.js、B/product-master-ux.spec.js | `0b721fcd455b00d35d886f842380a95c38c31b96`；E6 | 已有用户转述代码/交互接受；剩独立图片视觉；后续 ISS-028 修复应与当前分类/SKU 行为一并对照。 |
| ISS-082 | V/CategoryPage.vue；V/CategoryPage.test.js、B/product-master-ux.spec.js | 同 ISS-081；E6 | 独立审树/错误重试/冻结拒绝原图；继承业务限制保留，后续分类修复不能遗漏。 |
| ISS-083 | V/ResourcePage.vue；T/product-master-ux.spec.js、B/product-master-ux.spec.js | 同 ISS-081；E6 | 独立审参数列表、关联返回、重复拒绝和失败保留原图；已有代码/交互接受保留。 |
| ISS-084 | E6 parameters-create/edit-1440.jpg、manifest.json | 替换图片提交 UNKNOWN；E6/E7 | 独立核对两张替换图片实际像素/状态及清单，不推定所有旧图已修正。 |
| ISS-085 | V/SKUPage.vue；T/sku-ux.spec.js、B/sku-ux.spec.js | 初版精确 SHA UNKNOWN；E6 F7A | 已有代码/操作接受；剩独立三尺寸审图，后续 ISS-088/023/035 成果共同核对。 |
| ISS-086 | V/ResourcePage.vue、C/SupplierBatchBindingDrawer.vue；T/sku-ux.spec.js、B/sku-ux.spec.js | UNKNOWN；E6 F7A | 独立审来源拒绝重试/批量候选语义/停用确认及图片，不改变采购匹配规则。 |
| ISS-087 | V/SKUPage.vue；V/SKUPage.test.js、backend/crm/tests/test_sku_commercial_identity.py | 原样本来源 UNKNOWN；后续 ISS-023 报告 | 需要只读真实旧 SKU 缩写、保存型号和预览对照，普通保存前后身份/快照及业务期望；旧合成样本不证明生产损坏。 |
| ISS-088 | V/SKUPage.vue；T/sku-ux.spec.js、B/sku-ux.spec.js | `79841e382c882f33444627e65310170a47a444cf`；E6 test-results-iss088.txt | CLOSED，用户明确接受重复 watch/请求竞态修复，CI 38697043429；历史查询仍须保留。 |
| ISS-089 | V/PackagingPage.vue；T/packaging-management-ux.spec.js、B/packaging-ux.spec.js | `a2cbdecfdb9a827036a51e4d3acb74e45db3d6f2`；E7 | 保留已接受代码/交互；独立审三尺寸、错误保留、复制草稿和变更风险图。 |
| ISS-090 | V/TradeUnitsPage.vue；V/TradeUnitsPage.test.js、T/trade-units.spec.js | 同 ISS-089；E7 | 独立审不可变定义、备注/启停编辑、换算说明和返回原图；不重开已接受操作范围。 |
| ISS-091 | V/SKUPage.vue；T/sku-packaging-api.spec.js、B/packaging-ux.spec.js | 同 ISS-089；E7 | 独立审 profile 净重来源、内联失败保留/重试、父子锁和返回上下文图片。 |
| ISS-093 | V/HSCodePage.vue；T/certificates-hs-ux.spec.js、B/certificates-hs-ux.spec.js | `82514b1396e1e53d44bcd9314d19bbb65b0fbeed`；E7 | 保留条件接受代码/操作；独立审隐藏选择、拒绝恢复、三尺寸图及授权边界，不能借附件 UI 关闭真实文件议题。 |
| ISS-094 | V/ImportPage.vue；T/import-ux.spec.js、T/import-preview-state.spec.js、B/import-ux.spec.js | `10158f89b50ad477026f4ee2d4d4fd8177d5edcd`；E7 | 用户已接受代码/实际四类 CSV 有限范围；剩独立图片审查，后续 ISS-052 审计不由此自动通过。 |
| ISS-095 | V/OrganizationPage.vue；T/organization-access-ux.spec.js、B/organization-access-ux.spec.js | `b916fab613806a9fd00636cc87496803557d45a8` 接受提交；E7 | 已有代码/操作条件接受；剩独立图片，后续 ISS-097 有效权限显示补修应核对；不替代真实员工 UAT。 |
| ISS-096 | V/AccessDeniedPage.vue；T/organization-access-ux.spec.js、B/organization-access-ux.spec.js | 同 ISS-095；E7 | 独立审拒绝/读取失败不同状态原图、恢复和无权限空集合；保留已接受自动范围。 |
| ISS-098 | V/ProductPage.vue、V/SKUPage.vue、V/DocumentPage.vue；B/final-cross-module-ux.spec.js | `0f0747a9d449e26e93885b3bf469a726f99ffaa8`；E7 | 独立三尺寸审状态标签、长客户名、筛选及表内滚动，逐图核对实际像素。 |
| ISS-106 | V/DocumentPage.vue；T/fulfillment-receivables.spec.js、V/DocumentPage.test.js | 精确修复 SHA UNKNOWN；docs/R1-A-FUP-02-FIX-01-独立审查补修验收.md | 独立核对报价“状态”、订单“履约状态”及双向切换，关联原图与当前共享页面；不能把旧串改当当前缺陷。 |

## 结论与交接

共 40 个指定 ID；本次不改变任何状态。8 个已有 CLOSED 项（056、059、060、061、071、072、079、088）保留原用户/独立接受来源及有限范围。其余项的不足主要是独立图片接受、专项时序或真实样本，不应据旧 OPEN/BLOCKED 描述重新开发。

E1 中独立证据分支图片需要后续读取固定提交对象确认；本次仅核实报告的精确位置及来源记录，未声称已目视原图。E6/E7 已有本地归档；本次没有解码逐图验证像素，也未重新运行测试。历史通过数字和 CI 链接只属于原报告环境/提交，不是本次新测结果。当前未据上述静态核查确认新增产品缺陷；UNKNOWN 项保留具体补证动作，交集中独立复审决定接受范围。
