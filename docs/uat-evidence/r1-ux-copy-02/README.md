# R1-UX-COPY-02 文案优化验收报告

日期：2026-10-29  
基线：`bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`  
分支：`codex/ux-copy-sales-purchase`

## 结论

本轮仅优化报价、销售订单、PI / Packing List、采购来源、收货/发货及采购付款相关的员工可见中文文案；没有改变业务计算、API 请求、状态机、权限、库存、金额或历史记录行为。

最终定向单元回归、构建和三条真实 Chrome 隔离浏览器流程均通过。采购 MOQ 仍是可说明原因后继续下单的软提醒；供应商固定付款规则编辑器、筛选器和比例输入框没有重新引入；一张采购单关联多个销售订单的语义保留。

## 文案对照表

| 业务区域 | 原文/旧表达 | 本轮表达 | 目的与约束 |
|---|---|---|---|
| 报价版本 | `新建报价`、`修改说明` | `新建报价单`、`创建报价修订版`、`修订说明` | 明确报价主单与修订版的关系，原报价保留。 |
| 报价状态 | `发送`、`接受` | `标记为已发送`、`标记为客户已接受`、`标记为客户已拒绝` | 明确这是状态记录操作，不暗示自动发送或自动成交。 |
| PI | `预览`、`导出` | `PI 预览`、`导出 PI PDF` | 使用外贸单据术语，区分预览与导出。 |
| 销售订单 | `保存`、`交期` | `保存销售订单草稿`、`预计出货日期`、`订单总额` | 区分草稿与确认后的履约；确认订单才预留库存并生成应收计划。 |
| 历史订单 | `历史订单` | `录入历史销售/采购订单`、`仅保存分析资料，不进入正式履约` | 不把历史资料误解为当前履约主单。 |
| Packing List | `预计装箱单`、`实际箱单` | `预计装箱方案`、`实际装箱（Packing List）` | 区分预计方案与本次实际装箱记录；实际记录不改预计装箱、库存或订单数量。 |
| 采购来源 | `供应商`、`更换` | `选择采购来源`、`确认采购来源`、`更换供应商来源` | 明确更换来源会修改整张采购单供应商并重新匹配供货档案。 |
| MOQ | `低于 MOQ` | `本次采购有明细低于供应商 MOQ；填写例外原因后仍可下单；取消则保留当前采购草稿` | 保留软提醒，不写成绝对禁止采购；例外原因进入留痕。 |
| 采购状态 | `确认下单`、`取消采购` | `确认采购下单`、`取消采购单`、`保存采购草稿` | 区分保存草稿、正式下单和取消，明确正式下单后才生成应付计划并进入在途采购。 |
| 采购付款 | `付款`、`付款条件` | `供应商应付`、`本单付款计划`、`未协商时可暂不填写` | 不恢复供应商固定付款规则；保留本单约定和历史付款计划。 |
| 采购归属 | `关联订单` | `一张采购单可关联多个销售订单，具体归属在成本分配中处理` | 保留多销售订单语义，不把采购单限制为单一销售订单。 |
| 历史主体 | `供应商信息` | `交易主体快照`、`当前主档参考` | 区分正式下单保存的历史快照与当前供应商主档。 |

## 边界与实现

- 修改集中在 `DocumentPage.vue`、报价编辑/详情/预览弹窗、`OrderDraftModal.vue`、`HistoryOrdersPage.vue`、采购单页面及采购工作台/来源选择/实际装箱组件。
- 同步更新了受影响的可见文案断言和新增 `frontend/tests/ux-copy-sales-purchase.spec.js` 文案契约测试。
- 未修改业务 API、serializer、计算逻辑、状态机、权限、共享台账或财务逻辑。
- 未改动任务 D/F 负责的通用共享组件；`OrderDetailModal.vue` 保留既有库存、冲销和历史快照安全提示。
- 未出现 `payment_terms_config` 编辑器、固定付款规则筛选器或比例输入框。

## 自动化验证

以下均在本地隔离 worktree 执行，未触发 GitHub Actions：

| 命令 | 结果 |
|---|---|
| `node --test src/views/PurchaseOrderPage.test.js tests/ux-copy-sales-purchase.spec.js` | 16 passed, 0 failed |
| `npx vitest run tests/quote-list-ux.spec.js tests/purchase-editor-receipt.spec.js tests/purchase-safety.spec.js tests/purchase-workbench.spec.js tests/purchase-order-navigation.spec.js tests/order-overview-ux.spec.js tests/phase2c-editors.spec.js tests/second-review-foundation.spec.js tests/final-polish.spec.js tests/sales-safety.spec.js tests/shipment-actual-packing.spec.js --environment jsdom` | 11 files / 173 tests passed |
| `npm run build` | Vite build passed；保留既有大 chunk warning：主 chunk 约 1,126 kB，gzip 约 394 kB；本任务不做无依据的包体重构 |
| `npm run test:browser:isolated -- --business-test iss022-moq-real.spec.js`（`PLAYWRIGHT_CHANNEL=chrome`） | 1 passed；隔离迁移、Django check、API/Vite identity 均通过 |
| `npm run test:browser:isolated -- --business-test iss029-recipient-snapshot.spec.js`（`PLAYWRIGHT_CHANNEL=chrome`） | 1 passed；报价修订、PI 快照、导出流程通过 |
| `npm run test:browser:isolated -- --business-test iss075-payment-terms-real.spec.js`（`PLAYWRIGHT_CHANNEL=chrome`） | 1 passed；供应商 UI、空付款条件草稿/正式采购单、历史付款计划、窄屏通过 |

ISS-022 的浏览器日志保留了预期的低 MOQ `400` 响应，随后填写例外原因后 `200` 成功；这证明页面仍允许软提醒例外流程。ISS-022 和 ISS-075 的窄屏检查均记录 `noHorizontalOverflow: true`。API 日志、响应状态和原始截图保存在 `screenshots/iss022`、`screenshots/iss075`、`screenshots/iss029`。

## Chrome 视觉证据

截图来自本地隔离 Django API + Vite，并通过 Playwright Chrome channel 采集；没有连接生产服务：

- [MOQ 例外确认](screenshots/iss022/05-low-moq-exception-dialog.png)
- [MOQ 低于阈值提醒](screenshots/iss022/04-low-moq-conversion-warning.png)
- [采购窄屏列表](screenshots/iss022/09-narrow-purchase-list.png)
- [报价修订版编辑器](screenshots/iss029/chrome-version-b-editor-1440.png)
- [700px PI 预览](screenshots/iss029/chrome-version-b-saved-pi-700.png)
- [供应商页面无固定规则](screenshots/iss075/01-supplier-list-no-fixed-rule.png)
- [空付款条件采购草稿](screenshots/iss075/02-new-po-empty-payment-terms.png)
- [历史采购单付款计划](screenshots/iss075/03-history-po-payment-plan.png)
- [700px 供应商列表](screenshots/iss075/04-narrow-supplier-list.png)

## 交付边界

本报告和截图随分支提交；未合并 `master`、未部署、未关闭 Issue、未触发 CI。最终提交 SHA 以交付时该分支 `git rev-parse HEAD` 为准。
