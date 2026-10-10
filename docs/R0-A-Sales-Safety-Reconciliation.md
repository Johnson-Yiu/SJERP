# R0-A — Sales Safety Reconciliation

2026-10-10. 修改前 master：`5d86403842347836c522c70b3cb2ceddf70de779`。执行前已 fetch / fast-forward pull，确认无新增远端提交，未回退既有修改。

## 实现结果

| 项目 | 结果 |
| --- | --- |
| R0-A-01 | 三个销售编辑入口共用 documentCurrency。新 SKU 仅在币种一致时采用默认售价；不一致时留空并提示，允许人工填写。交易单位默认价按既有换算因子初始化。已保存 QuoteItem 价格、交易单位快照继续继承。 |
| R0-A-02 | 使用现有 confirmDialog。取消保留币种、价格、汇率；继续后重新检查默认售价并清除不匹配价格。无已填价格时直接切换。报价修订使用同一编辑器规则。 |
| R0-A-03 | USD 参考默认 7.2；CNY 1；EUR/GBP/其他外币留空。保存前校验正数，CNY 必须为 1，前后端均保护。编辑时不自动覆盖已保存汇率。未接入汇率 API。 |
| R0-A-04 | 新报价 UI 默认 30%，API 未传比例也默认 0.30。历史 100%/50%/0% 修订保留；Quote 转订单按其保存比例；无来源订单继续现有 30/70 服务规则。无模型字段或迁移。 |
| R0-A-05 | order-draft 用订单当天日期加报价 lead_time_days；null 保持 null，0 对应当天。订单草稿仍可人工修改交期。 |
| R0-A-06 | 直接订单改为“从报价载入（可选）”，复用现有 order-draft API，载入客户、商品、保存价格/交易单位、币种、汇率、运费、折扣、备注及预计交期。有内容时确认覆盖；取消无变化；加载期间禁保存，过期请求不写入新草稿。仅 draft/sent/accepted 可选；来源客户锁定。清除仅解除来源，保留已载入内容；已有订单来源仍只读。 |
| R0-A-07 | 新报价/修订和直接订单保存后进入返回 ID 的 overview Workbench，保留列表查询。returnTo 继续返回来源页。原 Quote Workbench 转 Order 保存路径保留，未重写。客户筛选下新订单正确预填客户。 |

## 文件范围

- frontend/src/utils/documentCurrency.js
- frontend/src/components/QuoteEditorModal.vue
- frontend/src/components/OrderDraftModal.vue
- frontend/src/views/DocumentPage.vue
- backend/crm/serializers.py
- backend/crm/views.py
- frontend/tests/sales-safety.spec.js
- frontend/tests/quote-editor-availability.spec.js（补齐真实 SKU 币种测试数据）
- frontend/tests/route-lifecycle.spec.js（来源报价路由预填改为真实 order-draft 响应）
- backend/crm/tests/test_sales_safety.py
- 本验收文档

无 Purchase/Inventory/Finance UI、SKU 页面、权限/RBAC、Dashboard 重构；无数据库迁移、历史业务数据修改、快照/修订身份规则变更。

## 自动回归

- 新增前端销售安全 15 项：三个入口币种安全、取消/确认切换、汇率、新默认定金、来源覆盖取消/完整载入/解绑、快照价格继承、真实 API 报价保存、工作台查询保留、returnTo。
- 新增后端 6 个测试方法，含多币种/多比例子用例：CNY/非正汇率拒绝、新建默认和外币显式汇率、30% 默认、历史修订、交期 null/0/10、来源及直接订单确认后的付款计划。
- Frontend Vitest：38 文件 / 404 项 PASS。
- Frontend Node：111 项 PASS；独立详情排版 Node：1 项 PASS。
- Production build：PASS（既有 chunk size 提示仍存在）。
- Backend：573 项运行，PASS；SQLite 下跳过 10 个 PostgreSQL 专用测试，最终 backend-postgres CI 单独核验。
- Django check / makemigrations --check --dry-run：PASS，未生成迁移。
- 最终生产 HEAD 的 exact-head Actions URL、三个作业实际状态和证据 SHA 在交付回复报告，不引用旧提交 CI 替代。

## 真实 Chrome UAT

通过原生 Chrome 页面及现有应用控件完成。使用现有专用 customer13 `UAT-SR-FINAL-20261009-NEW`，SKU `UAT-R1-CSV-SKU-001`（默认 USD 9.90）。截图原始内容保留，仅 JPG 转 PNG；未裁剪、重绘、拼接。正常 100% 缩放，DOM devicePixelRatio=1 / visualViewport.scale=1，视口宽 1920；未设置临时视口。

- USD 默认价 9.90 自动带入；人工价格 12.00 切 EUR 出现自定义确认框。
- 取消保持 USD、12.00、7.2；再次确认后 EUR 单价和汇率为空，显示明确的 USD 9.90 / EUR 提示。
- GBP 汇率为空；CNY 汇率 1、只读，定金默认 30%。直接订单 EUR 切换亦留空价格并显示提示。
- 从报价页新建保存 `SJ20261010DE001`（Quote48，lead_time_days=10，USD12.00），自动进入 `/quotes?customer=13&detail=48&tab=overview`。
- 从新报价 Workbench 转订单，草稿日期 2026-10-10 / 预计交期 2026-10-20。保存生成 `SO-2026-00039`，自动进入 `/orders?detail=39`，原路径 PASS。
- 直接订单先选 SKU，再载入 Quote48：出现覆盖确认；取消来源仍为空；确认后客户13、SKU、保存价12.00、USD/7.2、备注、0运费/0折扣和预计交期 2026-10-20 正确载入，客户锁定。未被 SKU 默认9.90覆盖。
- 直接订单保存生成 `SO-2026-00040`，自动进入 `/orders?customer=13&detail=40&tab=overview`。

仅 UI 创建上述一个报价、两个订单草稿以供独立复核。保留草稿，未确认订单、未生成应收/库存预留，未删除非本任务创建数据。未用 API 或数据库写入替代 Chrome 操作。付款计划确认规则通过隔离自动测试验收。

## 视觉证据

仅在 `ux-review-evidence` 分支的 `ux-review/r0-a-sales-safety/`，不合并到 master。

| 文件 | 状态 |
| --- | --- |
| R0A_01_currency_mismatch.png | 完成，报价异币种提示及空单价 |
| R0A_02_currency_change_confirm.png | 完成，自定义币种切换确认 |
| R0A_03_cny_rate.png | 完成，CNY=1 和 30% 默认定金 |
| R0A_04_quote_to_order_delivery.png | 完成，报价转订单日期及10天交期 |
| R0A_05_direct_order_from_quote.png | 完成，来源、客户、币种、汇率及交期载入 |
| R0A_06_quote_saved_workbench.png | 完成，新报价正式工作台 |
| R0A_07_order_saved_workbench.png | 完成，新直接订单正式工作台 |
| R0A_08_quote_order_saved_workbench.png | 补充，原报价转订单保存落点 |
| R0A_09_loaded_quote_price.png | 补充，报价价12.00、SKU默认9.90及备注 |
| R0A_10_direct_currency_mismatch.png | 补充，直接订单币种安全 |

必需七张截图无缺失。R0-A 本轮未发现未解决的范围内问题；后续独立审查仍需完成。停止于 R0-A，不启动 R0-B/C/D，不声明全系统 UX-FROZEN。


## Focused Repair — 2026-10-10

基线：c36f6bae386176e36d9e9b6eb78a229ef46bbab4。仅修复独立复审的三个确认问题。

- Quote lead_time_days 使用 ?? 默认10，输入允许0，保存 payload 保留0（空输入仍为null）。新增0/null/undefined修订初始化及保存测试。
- Direct Order 比较 fresh() 保存的日期、预计交期、币种、汇率默认值，手工变更触发既有自定义确认。默认空白无需确认；汇率按 compactDecimalInput 比较。取消不发 order-draft 请求且不改变内容，确认才载入。
- SkuPickerPanel 列表和详情显示 SKU 自身币种，如 USD 9.90、pcs / USD 9.90；缺失币种显示“币种未设置”。价格逻辑未改。价格不拆行，详情允许合理换行。

新增 focused 测试11项；原 sales-safety 15项仍通过。完整 Frontend Vitest 39文件/415项、Node111项、独立排版1项均通过；Backend573项通过（本地SQLite跳过10个PostgreSQL专用测试）；Production build通过；Django check和makemigrations --check --dry-run通过。最终exact-head CI结果在交付回复报告。

真实 Chrome 100% zoom 验收：新报价默认10天；通过UI新建专用0天报价SJ20261010DE002，创建SJ20261010DE002-1修订，初始化0天并保存。已保存修订转订单草稿显示0天，订单日期与预计交期均2026-10-10。再次打开原报价修订编辑器仍为0天，原报价未修改。仅创建专用报价及修订，未保存/确认订单。

默认空白订单载入该报价无需确认。新空白订单手改日期至2026-10-11再载入弹出自定义确认，取消后日期仍为2026-10-11；再确认正确载入。另一次EUR/8.25/预计交期2026-10-15手工输入，载入取消后均保留。三个编辑入口SKU列表及详情USD9.90标签经截图人工检查，picker scrollWidth=clientWidth=919，无水平溢出。

仅证据分支 ux-review-evidence，目录 ux-review/r0-a-sales-safety/focused-repair/，三张必需原始Chrome截图已完成（仅JPG转PNG，无裁剪或内容修改）：
- R0A_FIX_01_zero_day_quote_revision.png
- R0A_FIX_02_source_overwrite_date_confirm.png
- R0A_FIX_03_sku_price_currency_label.png

OPEN / deferred: Order reference cost currency semantics。
OrderItem.cost_price 跨币种语义留待采购/财务/成本阶段统一设计；本轮未修改其值、业务逻辑或工作台显示。

本轮三个修复无BLOCKED项。停止并等待独立ChatGPT复审，不进入R0-B。
