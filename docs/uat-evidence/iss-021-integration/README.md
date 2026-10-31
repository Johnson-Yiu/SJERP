# ISS-021 正式销售订单数量变更：迁移与复审

日期：2026-10-26。状态：FIXED_PENDING_REVIEW，等待统一独立审查；未合并 master，未关闭 Issue，未部署。

## 基线与差异

- 统一基线：`b3559f3bf83b967d06166bd409b00fc92e4e5902`。
- 独立 worktree 分支：`codex/next-iss-021-integration`。未修改其他任务分支。
- 参考开发分支：`codex/r1-iss-021-dev` / `92d32ad856fdd056fab0be56a70a9af52fbb99f2`；独立审查分支：`codex/r1-iss-021-audit-01` / `12c0ea9d60537d202393266f7850fcc188276860`。
- 原规则：用户指定 2026-10-24 包的“新增议题逐项移交”未包含 ISS-021；按业务规则总表追溯并完整读取同包 `既有移交原件_2026-10-20/04_ISS-021_正式销售订单的数量及合同变更.md`，并核对本轮用户明确规则。
- 按差异迁移模型、专用服务/API、历史与 UI，不整文件覆盖。保留当前基线 ISS-037 主体快照、ISS-039 共享采购及历史订单隔离。旧现金测试迁移兼容补丁在本基线已有等效处理，不重复迁移。
- 不复制旧 `0078`；仅新增依赖 `0084` 的 `0085_order_quantity_adjustment`。所有已有迁移原样保留。新增版本字段和历史表，不重写既有业务事实。

必要补修包括：预览显式事务及 PostgreSQL nullable join 锁范围、提交沿用发货锁顺序、历史订单拒绝、单位换算精度保护、响应采购指标脱敏、开发身份不伪装实名操作人、已有采购人工处理提示、过期异步预览丢弃、二次确认期间锁定表单，以及到货指标字段和历史时间显示。

## 业务与权限矩阵

| 场景 | 结果与证据 |
|---|---|
| 正式 SO 100→150 | 原 SO/行不变，需求与合同金额增加；追加应收计划和变更历史 |
| 有效已发 50，150→60 | 允许，未发需求 10；只调整未结应收和派生预留，不改变实物库存 |
| 已发 70，100→60 | 预览及提交均 400；无历史、版本或业务事实修改 |
| 已收 900，拟将合同 1000→600 | 预览 can_submit=false，UI 禁用确认；提交 400，不自动退款 |
| 已有采购/收货 | 提示人工核对需求或处理过剩；采购归属、数量、收货和银行/收款事实不变 |
| 无变化、版本冲突、重复请求 | 无变化 400、旧版本 409；相同请求键重放 200，不重复记账/审计 |
| 保存中异常 | 在财务写入后注入异常，整笔数量/版本/计划/历史回滚 |
| 订单修改授权，缺少财务/采购查看 | 可调整自己范围内订单；响应、历史、工作台和日志脱敏 |
| 只读或跨客户范围外 | 提交拒绝；外部订单历史/工作台不可读 |
| 开发环境 | 沿用 development_superadmin_enabled()，未启用正式 RBAC；匿名开发操作历史标明“开发身份（未实名）” |
| 主体快照 | 当前客户更名后，数量修改仍保留“ISS021 原确认客户 / 原合同地址” |

应收处理边界：增加时新增差额计划；减少时仅调减未结部分，原计划行保留，余额归零的未结计划标记 cancelled。已结算金额及 Transaction 不变，不删除或冲销已有资金事实。没有新增复杂审批流程。

## 原始自动化日志

| 验证 | 命令（对应工作目录） | 结果 |
|---|---|---|
| 后端全量 | backend: `python manage.py test` | [904 项，跳过 13，OK](backend-full.log) |
| 最终定向 | backend: `python manage.py test crm.tests.test_order_quantity_adjustments crm.tests.test_formal_party_snapshots crm.tests.test_iss039_shared_purchase_costs --verbosity 2` | [38 项通过](backend-targeted-final.log) |
| 脱敏新增断言 | backend: `python manage.py test crm.tests.test_order_quantity_adjustments.QuantityAdjustmentRBACApiTests.test_orders_update_user_can_adjust_but_receives_no_finance_or_procurement_details --verbosity 2` | [禁止顶层及历史 after_metrics 泄漏](backend-redaction-final.log) |
| Node | frontend: `npm run test:unit` | [151 项通过](frontend-node.log) |
| Vue/Vitest | frontend: `npx vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js` | [66 文件、650 项通过](frontend-vitest-tests.log) |
| 最终组件 | frontend: `npx vitest run tests/order-quantity-adjustment.spec.js --environment jsdom` | [2 项通过，含异步预览失效](frontend-targeted-final.log) |
| 最终构建 | frontend: `npm run build` | [通过；保留既有大 chunk 警告](frontend-build-final.log) |
| 模型一致性 | backend: `python manage.py makemigrations --check --dry-run` | [无变化](migration-check.log) |
| 新库 | backend: `python manage.py migrate --noinput`，隔离 SQLite | [迁移至 0085](migrations-browser.log) |
| 既有链升级/回放 | 隔离探针库：0084→0085→0084→0085 | [原 Customer 哨兵保留](migration-upgrade.log)；回滚时新增审计表为空，不代表可无损回滚已有变更历史的生产库 |

本地使用 Python 3.14 / Django 6.0.6、SQLite；本地 PostgreSQL 不可用，未将 SQLite 结果冒充 PostgreSQL 并发验收。最终精确提交的远端 CI 另见交付结果。

### 推送及远端 CI 边界

实现提交为 `07f349f80d5244243867a7841ec0dc1e77f6eb3c`，完整原始日志提交为 `7fb7ff875b312fb277e9b3b06056cbca1a6a8e42`；均已推送目标分支。对应 [CI run 40257290673](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/40257290673) 三个 job（frontend / backend / backend-postgres）均 failure 且 steps 为空。GitHub [原始注释](ci-annotations-40257290673.log)明确报告账户近期付款失败或消费限额需提高，任务未启动；不是已经执行的代码测试失败。详见 [jobs 原始响应](ci-jobs-40257290673.log)。首次读取 run 详情出现 TLS 超时亦保留 [原始日志](ci-40257290673.log)，随后 API 成功核验。没有修改账户、额度或工作流来规避此问题。

因此 CI / PostgreSQL 验收仍 BLOCKED，不能宣称合并就绪。需仓库所有者处理 GitHub Actions 计费/额度后对最终交付 SHA 重跑三项 CI，并完成独立审查。本段之后只补充证据文档，不改实现；最终分支 SHA 以交付消息和远端为准。

透明记录失败的准备命令：`frontend-vitest-wrong-runner.log` 是未限定 tests 目录误收集 Node 测试；`backend-targeted-wrong-labels.log` 是两个模块名写错，其余数量测试正常通过；`migration-probe-wrong-fixture.log` 是探针 SQL 使用错误字段。均已修正命令/夹具并重新执行成功，未为通过而放宽业务断言。全量日志中的故意异常来自失败回滚测试，最终结果为 OK。

## 真实 API 与数据库

仅使用本 worktree 隔离合成数据库 `backend/iss021-browser.sqlite3`（不提交数据库），服务为 `127.0.0.1:28321`；前端 `28322`。未使用其他任务占用的端口或数据库。

- [seed_and_verify.py](seed_and_verify.py)：通过现有确认订单、收款、收货和发货服务建立真实关联事实；仅允许空隔离库 seed，verify 不修改业务数据。
- [seed.log](seed.log)、[seed.json](seed.json)：3 张 SO，各采购并收货 100；订单 1 已发 50/已收 200，订单 2 已发 70/已收 200，订单 3 已收 900。
- [api_probe.py](api_probe.py)、[api-probe.log](api-probe.log)、[api-evidence.json](api-evidence.json)：12 次真实 HTTP 请求，含预览、提交、幂等重放、409、拒绝和历史/工作台。不是 mock 响应。
- [database-before.json](database-before.json)、[database-after.json](database-after.json)、[database-verification.log](database-verification.log)：API 和浏览器操作前后逐字段比对 PO、POItem、PurchaseCostAllocation、GoodsReceipt、Shipment、ShipmentItem、InventoryMovement、Transaction。

保护事实 SHA-256 前后均为 `4aee929137be345eaf5fa3a315f9f60496b9758cf6632641bd058cf97394b8be`，`protected_facts_unchanged=true`。最终订单 1 数量 60、合同 600、已收 200、待收 400、实物库存 50、预留 10、版本 4，完整保留 4 次历史；订单 2/3 数量仍为 100，版本 0，无变更历史。ISS-037 正式主体快照保持原值。

## 真实浏览器与截图

Chrome Use 连接被另一 Codex 对话占用/超时；用户明确授权改用内置 browser use。因此以下为真实内置浏览器验收，不声称 Chrome 扩展验收已通过。截图均为接口原始 JPEG，桌面及 390×844 窄屏已目视检查；临时视口覆盖已恢复。

- [增加预览](browser-increase-preview.jpg)：60→150、金额差额及人工采购提示；随后二次确认保存。
- [增加后历史](browser-increase-history.jpg)。另外执行一次 150→120 预览后取消，未产生变更。
- [减少预览](browser-decrease-preview.jpg)：150→60、过剩采购 40；随后确认保存。
- [刷新后历史](browser-refreshed-history.jpg)：数量 60、已发 50、待发 10、4 次变更和开发身份说明。
- [窄屏已发 70 拒绝](browser-shipped70-rejection-390.jpg)、[原始提示](browser-shipped70.txt)。
- [窄屏已收 900 拒绝](browser-paid900-rejection-390.jpg)、[底部禁用确认](browser-paid900-footer-390.jpg)、[原始提示](browser-paid900.txt)；已读取 isEnabled=false，滚动/键盘可达底部。

已人工检查本轮可见文案：保留正式 SO、预留、采购、到货、收款、应收、交易单位等业务语义。独立代码、业务和视觉复审仍待完成；不代表全站权限或生产安全验收。
