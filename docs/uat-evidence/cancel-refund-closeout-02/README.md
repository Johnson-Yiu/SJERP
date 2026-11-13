# SJERP CANCEL-REFUND-CLOSEOUT-02

任务包 A；合成数据、独立 SQLite / MEDIA_ROOT 与临时 PostgreSQL 17 集群。未访问真实资金或正式数据库。

## 当前提交与验证

- 集成基线：`d7d155b994b652f6f4f777edde22a257a8ed7a2e`。
- 核心修复：`f4ec4bad72f16350981b75882618afc49f2f9bd1`。
- `sqlite.log`：76 项，73 通过，3 项真实 PG 并发专用测试跳过。
- `postgres.log`：76 项全部通过；包括并发退款、并发改量及冲突幂等键，临时数据库正常清理且集群关闭。
- `vitest.log`：订单数量调整、取消错误与忙碌保护、财务安全、订单应收入口和履约 UI，41 项通过。
- `build.log` 构建通过；`migrations.log` 无新增迁移。
- 补充取消后的并发：`postgres-cancelled-concurrency.log` 2 项通过，正常清理；两组 PG 测试合计覆盖 77 个不同测试。
- 41 项前端测试与最终构建通过。生产代码最终提交：`9b739faec0d85c7c62b6a1e1f02ea4f102445cba`。
- Chrome 首次完整闭环已通过（`browser-first-complete-pass.log`）；最终重采已将工作台滚动到付款摘要，避免结果截图只展示顶部资料。最终整轮再次通过，78 张截图覆盖 13 个状态。最终日志为 `browser-final.log`，原始 HTTP 请求/响应及几何/缩放数据为 `browser/chrome/run.json`。

## 逐项验收证据

| 编号 | 结论 | 实际操作与验证 | 前后截图（同名前缀均有 1366/1920/390 与 100/125%） |
| --- | --- | --- | --- |
| A1 | 已修复并验证 | 原收1000，正常退100后净实收900/待收100；取消后实际退400+500，原收款仍1000且已确认，净现金与应收均0；共享额度/幂等/超退/审计/并发由后端操作回归核对 | `refund-before-submit-*` → `normal-refund-after-*`；`cancel-after-*` → `cancel-refunds-complete-*` |
| A2 | 已修复并验证 | 收50取消后真实作废200，净实收/合同/应收均0；收999+抵减1取消后真实更正201，净实收999、合同/应收0 | `cancelled-void-before-*` → `cancelled-void-after-*`；`cancelled-correction-before-*` → `cancelled-correction-after-*` |
| A3 | 已修复并验证 | 100件已发40件+另一行20件未发，已收1000；先退600，再明确终止余项201；权威工作台确认数量[40,0]、已发40、剩余0、合同400、净实收400、应收0、已完成 | `terminate-paid-refund-guidance-*`、`terminate-before-submit-*` → `terminate-after-*` |
| A4 | 已修复并验证 | 已发订单取消400，错误保留在取消表单，原因保留；返回后改用终止余项流程完成；忙碌关闭/重复提交保护另有前端回归 | `cancel-before-submit-*`；`cancel-rejection-retained-*` |

真实 Chrome 版本 `156.0.8078.80`。所有业务写入使用普通可操作点击，不使用强制点击；截图仅作为视觉证据，完成判定还包括响应状态、重开工作台及权威数据断言。截图为当前集成代码下操作前后；旧审查截图仅用于复现线索。

权威结果：`final-workbench.json`、`cancelled-void-workbench.json`、`cancelled-correction-workbench.json`、`refunded-order-and-source.json`。取消更正、退款、履约摘要数据已逐项核对；退款源、凭证、日期及提交内容见 `run.json`。

财务子表单 P2-13：退款、作废、抹零更正均完成输入、实际提交、状态更新与原生缩放视觉验证。P3/P4 及其它任务台账由协调任务统一处理，本包未修改公共弹窗、全局工作区或权限框架。

## A1 退款来源与额度

直接关联计划的收款未分配现金为 0；空订单退款后端拒绝，无新流水、无新退款关系、计划余额不变。前端依据后端未分配余额决定是否显示未分配选项；仅一个原订单且未分配为 0 时默认选中。

`test_receipt_refund_attribution` 覆盖直接计划拒绝、原来源/订单/计划/凭证/日期绑定、共享 A/B/未分配三类额度不可串用、分次退款、重复请求、超退、审计失败回滚和 PostgreSQL 并发。原币退款仍为原币现金事实，不以合同汇率伪造实际人民币流出。

## A2 取消后允许的更正

零合同取消订单的应收计划随实际净现金和有效抵减重新核对；作废收款、更正非现金抵减不会打开新的应收。共享来源作废时，取消单保持关闭、有效单正常恢复未结计划。计划与原流水均保留。

已归属且可追溯的部分退款不再误阻止后续取消；无来源退款、银行事实等原安全拒绝不放开。公司承担手续费的取消与实际退款专项验证保留核销手续费且只退现金。

## A3 部分履约终止

真实入口为订单工作台「调整数量」中的「终止本次选中明细的剩余履约」。预览和提交均带 `terminate_remaining: true`；原数量进入追加变更记录，原订单行和已发货事实保留。

显式终止允许同单零发货余项填写 0；普通改量仍要求大于 0，尚未发货的整单指向取消订单。交易单位沿用原换算快照与整包装限制；关联采购不自动改动，过剩提示仍保留。

已收超过新合同有效金额时，沿用已有合同调减规则：先在财务流水从原收款登记真实退款，之后重新预览并终止剩余履约。未放开未经退款降低至现金以下的合同金额，也不猜测实际人民币退款。已结汇和历史来源不明仍拒绝，不能据此伪报完成对应资金操作。

## A4 取消错误与重试

业务拒绝显示在取消表单内，保留原因和背景订单。提交期间禁用原因、返回、重复提交及工作台关闭；失败恢复操作，返回继续处理。

## 重跑

后端测试标签：`crm.tests.test_receipt_refund_attribution crm.tests.test_contract_lifecycle crm.tests.test_order_quantity_adjustments crm.tests.test_refund_consistency`。

真实 Chrome：`frontend/browser-tests/cancel-refund-closeout-02.spec.js`，通过现有 isolated runner 运行，`ISOLATED_CODEX_TEST_SUPERADMIN=1`、`ISOLATED_PLAYWRIGHT_USE_CHROME=1`；凭据仅从 Git 忽略的本机配置加载。原生 Chrome appearance 页设置 100% / 125%，用实际 devicePixelRatio 核验；1366×768、1920×1080、390×844。没有 CSS zoom、强制点击或跳过 CI。

失败记录保留：首次登录被初始重载干扰；第二轮发现真实部分退款后取消误拒绝；第三轮失败于默认 5 秒断言等待，400 已返回但界面仍处于提交中。后续测试等待响应及合理 UI 完成时间。PG 首轮 71 项本身通过，但并发 worker 留连接导致清理退出失败；已修复 finally 关闭全部线程连接，最终 76 项正常退出。

补充执行记录：A2夹具曾因使用空操作人而被权限校验正确拒绝，改用隔离库已创建的codex超级管理员后通过；一次终止确认用例因模糊dialog名称同时匹配确认框而失败，已改exact；一次取消单结果断言错误地排除了“当前待收”字段名，已改核对服务端应收金额为零。以上均保留失败日志，不计入最终通过轮次。
