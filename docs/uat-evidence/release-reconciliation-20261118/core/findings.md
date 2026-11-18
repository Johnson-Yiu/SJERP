# Core delivery audit against 3bb0970148ff98025d44d6c5ee42e17bfe180002

审查日期：2026-11-18。范围：采购、MOQ、交易数量、SKU 与成本、入库冲销、历史商品关联/导入和主体快照。源代码先核对，开发记录用于解释后续替代关系。

## 结论

本次已审查的核心范围确认一项后续功能修复未包含在 3bb：采购草稿 MOQ 的浮点等值误警。来源为 `60f75a0294d32951efe6555ef2361d7a024b8295`，位于后续分支 `252d7234bd138101b387f4612b389cba5a990af1` 的历史中。已最小接入计算和对应浏览器夹具/用例，并补实际 Vue 组件行为回归；没有整包接收该提交中的安装器脚本。

旧分支的“独有提交”不能直接计作遗漏。下表所列采购成本、数量幂等、历史数据快照及 SKU 关联等功能，当前基线已有实现或后继替代。不得把旧模型、同号迁移或过期页面整包覆盖回去。

此结论只覆盖下表列明的源码检查和定向测试，不声称穷尽未推送工作、已删除分支或所有未留存需求。本次不读取正式业务数据库，不证明 ALEX 实际运行的提交，也不把历史报告的 PASS 当作当前全站通过。

## 确认遗漏与最小接收

### MOQ 误警

- 3bb 的 `PurchaseOrderPage.vue` 直接将 `baseQuantity(item)` 的 JavaScript 二进制结果相加，再与 MOQ 比较。
- 在实际挂载组件上，`0.58` 箱 × 每箱 `100` 件、MOQ `58` 件误报不足；同一来源两行 `0.29 + 0.29` 箱也误报。修补前 8 项组件行为测试中恰有这两项失败，其余 6 项通过。
- 接收来源修复：逐行将有效基础数量和 MOQ 转为整数百分位后累计与比较，展示时转回数量。没有更改草稿保存 payload、正式采购例外审批、库存或财务算法。
- 后端 `crm/trade_units.py::number` 用 Decimal，拒绝基础数量超过两位小数、非有限数、负值和超过上限值；`normalize_trade` 对换算后的基础数量再次使用该校验。因此 `0.005` 件等输入仍由后端拒绝，并非新增“自动四舍五入业务数量”规则。
- `purchase_lifecycle.py::_purchase_moq_exceptions` 对同一个 SupplierSKU 的已存基础数量用 Decimal 累加。修复维持同源合计、不同来源不混算、MOQ 为 0 或未知时不编造阈值，加载中/失败时显示不可判断。
- 有效单行数量小于 10^12，整数百分位小于 10^14，在 JS 安全整数范围内。更大跨行合计已经超过任何有效 MOQ 上限；本次未改变后端数量域。

### 同一数量问题的展示收尾

根任务明确授权将行内“折合”辅助展示复用既有 `quantity()` 格式化，消除 `57.99999999999999` 尾数。0.58 箱 ×100 现在展示 `折合 58.00 pcs`。只修改显示表达式，`baseQuantity` 与提交数据保持原样。同步了既有采购编辑测试中 `20 m`→`20.00 m` 的唯一直接相关断言。

UI 审查代理已核对 `01b6fe73` 的中文优化还遗漏同文件一条展示语句，本代理按其交接接入：`供应商供货档案加载失败，暂无法判断 MOQ；请重试加载。`→`供应商供货档案加载失败，暂时无法判断 MOQ。请重新加载。`。该项不改变判断、请求或业务含义，完整文案来源证据由 UI 审查代理提供。

## 保留性核查

| 旧来源 / 审查项 | 当前 3bb 代码证据 | 判断 |
|---|---|---|
| `fa0edf18` SKU 批量操作串行化 | `frontend/src/components/ProductSkuManagement.vue` 的 `run` 忙碌保护、`setSelectedActive` 逐行 `await api.patch`、记录失败并保留选择、产品切换检查；`docs/deployment/alex-source-inventory.json` 已列此提交与受审 blob | 已保留。不能继续把旧演练包缺项算作 3bb 缺项。 |
| `6e7aaedd` / 更旧 R1 MOQ 分支 | `purchase_lifecycle.py`、`services/procurement.py`、`PurchaseOrderPage.vue` 现有软提醒、同来源汇总、正式下单例外原因/操作者/时间，以及 `0086_purchase_moq_exception` | 业务主体已保留。只补后来浮点修复；不接收旧分支中相冲突的迁移编号。 |
| `aadd2ff3` 公共费用仅按采购金额分摊 | `services/purchase_costs.py::ExpenseInput` 只接受 `amount`；`prepare_costs` 再防御校验；零采购金额拒绝有金额费用；旧 quantity 方式只供已有历史只读解释 | 已保留，不应恢复旧数量回退分摊。 |
| `72ffff52` 批准的采购合同变更进入成本 | `purchase_costs.py::cost_summary` 验证归属完整，按基础金额分配 `contract_change_amount`，保留四位小数、负数分摊/负成本阻断；`order_purchase_cost_components` 区分基础、合同变更和附加费用 | 已保留。源码与来源完整核心行为一致。 |
| `7e1d0376` 数量变更并发幂等键 | `order_quantity_adjustments.py::apply_quantity_adjustment` 锁订单/相关 SKU，校验版本和请求指纹，内层 savepoint 创建记录并捕获 IntegrityError；现行 `terminate_remaining` 对部分履约余项有明确限定 | 已保留，且后继终止余项规则仍在；不是简单恢复旧正数判断。 |
| `e0697eee` 采购入库冲销 | `services/fulfillment.py::reverse_receipt` 原因、重复冲销拒绝、原仓库/批次实际库存检查、保留冲销流水、重算采购状态和预留；现行顺序为采购单→入库→行→订单→SKU→原流水 | 已保留并有后继锁序增强。本轮源码检查，未重跑 PostgreSQL 并发。 |
| `1a966601` 报价未知主体快照不得被当前主档填回 | `models.py::Quote.__init__/save` 区分显式传入的空买方与未提供默认字段，排除父/根报价修订；收件人/买方导出读取已存快照 | 已保留；不能因当前客户名称非空而填回历史未知值。 |
| `4d205ece` 历史分类、国家和导入结果 | 正式单据的 `product_category_reference_snapshot` / `product_category_name_snapshot` 与 supplier_country_snapshot，预检用 setdefault 保留 v2 输入，未知分类输出待核实；`reporting.py` 使用冻结快照；`sales_order_import.py` 保留 customer_name | 已保留或已被后继表示替代。当前字段名与旧 patch 不完全相同，不构成功能缺失。 |
| H1/H2 历史商品关联 | `history_product_models.py::ArchivedHistoryLine` 保存独立历史事实；`history_takeover.py` 将来源原文存入 facts；`history_products.py::apply_links` 只更改关联，签名预览/操作者/版本检查、组与来源锁、幂等回执、审计和接续重新审批均在；`reporting.py` 同时读取归档行 | 已保留。把旧历史导入重新写正式 SKU 明细会破坏现行分离设计。 |
| `3dfd2b81` 成本金额与币种完整性 | `history_operational_contracts.py` 受控创建传入 unit_cost / cost_currency 并 `save(preserve_cost_snapshot=True)`；普通序列化只读币种快照；`sku_plans.py` 从选定来源一起继承金额、币种和核实人/时间并保留未知；`services/cost_integrity.py` 为只读检查 | 已保留。现有真实数据是否曾经错配，必须在授权副本运行检查并核原件，本次不能据源码推断全部历史已修正。 |
| `45047635` SKU 与来源价格核实 | `views.py::verify_cost/verify_price` 使用 verification_state 拒绝缺失/非正成本或币种；`services/sku_costs.py` 只输出风险状态，不泄漏采购金额；现有定向测试仍在 | 已保留。后续 closeout 提交的额外报价浏览器测试不代表新业务功能。 |
| `dc2bbbb2` / `f2b7fd64` CSV 导入审计 | models 的 append-only 批次/行/预览记录，views 的真实操作者核验、预览哈希、失败回执、逐行快照和事务原子性仍在 | 已保留。没有因旧分支 diverged 而重新复制审计模型/迁移。 |
| `ecb38a78` 历史预检切换文件竞态 | `HistoryPreflightPage.vue` 保留 selectionVersion、previewFile、旧成功/失败响应失效、下载绑定当前工作簿；后继还增加 alive 生命周期保护 | 已保留并增强。 |
| `2bff4790` 销售订单 XLSX 导入 | 当前 `sales_order_import.py`、urls、上传限流入口、来源去重和创建草稿存在；结果恢复再次核对操作者与销售数据范围；views 保留导入来源草稿不可删除约束 | 已保留。旧通用 CSV 的订单禁用说明与此 XLSX 业务入口不同，不构成功能缺失。 |

### 可复核固定源码链接

- [MOQ 来源提交](https://github.com/Johnson-Yiu/SJERP/commit/60f75a0294d32951efe6555ef2361d7a024b8295)
- [3bb 采购页面](https://github.com/Johnson-Yiu/SJERP/blob/3bb0970148ff98025d44d6c5ee42e17bfe180002/frontend/src/views/PurchaseOrderPage.vue)
- [3bb 交易单位规范化](https://github.com/Johnson-Yiu/SJERP/blob/3bb0970148ff98025d44d6c5ee42e17bfe180002/backend/crm/trade_units.py)
- [3bb 采购生命周期](https://github.com/Johnson-Yiu/SJERP/blob/3bb0970148ff98025d44d6c5ee42e17bfe180002/backend/crm/services/purchase_lifecycle.py)
- [3bb 采购成本](https://github.com/Johnson-Yiu/SJERP/blob/3bb0970148ff98025d44d6c5ee42e17bfe180002/backend/crm/services/purchase_costs.py)
- [3bb 数量变更](https://github.com/Johnson-Yiu/SJERP/blob/3bb0970148ff98025d44d6c5ee42e17bfe180002/backend/crm/services/order_quantity_adjustments.py)
- [3bb 历史商品关联](https://github.com/Johnson-Yiu/SJERP/blob/3bb0970148ff98025d44d6c5ee42e17bfe180002/backend/crm/history_products.py)
- [H1 原交付与后继独立历史事实设计](https://github.com/Johnson-Yiu/SJERP/blob/3bb0970148ff98025d44d6c5ee42e17bfe180002/docs/uat-evidence/history-product-sku-linking-01/README.md)
- [成本币种修复记录](https://github.com/Johnson-Yiu/SJERP/blob/3bb0970148ff98025d44d6c5ee42e17bfe180002/docs/uat-evidence/cost-currency-integrity-02/README.md)
- [历史数据准备原交付](https://github.com/Johnson-Yiu/SJERP/blob/3bb0970148ff98025d44d6c5ee42e17bfe180002/docs/uat-evidence/history-data-readiness-01/README.md)

上述旧交付记录中的未测/失败保留原事实，不能单独证明当前产品仍失败。当前测试覆盖范围如下，其他表项只声称源码保留性核对。

## 本轮实际验证

环境：`/workspace/scratch/845e333a0b4f/candidate_review/source`，原始 969 个运行/构建/测试文件以根任务 `runtime-manifest.json` 核对为精确 3bb Git blob；本代理在该副本做以下 5 个文件的小范围编辑。Node 24.22.3（与 CI Node22 不同）；Vue3.5.44 / Vite8.3.5 / Vitest4.1.12，安装依赖与锁定版本一致。Python 使用 `/workspace/scratch/cfa5cd342276/audit/venv/bin/python`，Django6.0.9。未跑全量。

| 验证 | 结果 | 命令 / 证据 |
|---|---|---|
| 原始 3bb 实际 Vue 组件反例 | 2 failed / 6 passed | 新增 `purchase-moq-precision.spec.js` 在修补前执行；失败为单行与同源分行等值误警，工具返回保留原失败。 |
| 修后 MOQ + 采购编辑/收货 | 28/28 通过，无跳过 | `node_modules/.bin/vitest run tests/purchase-moq-precision.spec.js tests/purchase-editor-receipt.spec.js --environment jsdom`；`core_review/frontend-purchase-tests.log` |
| 采购页面 Node 源码回归 | 14/14 通过 | `node --test src/views/PurchaseOrderPage.test.js`；原工具输出。此组不是行为端到端验收。 |
| 后端 MOQ / 交易单位拒绝边界 | 9/9 通过，无跳过 | `manage.py test crm.tests.test_purchase_moq crm.tests.test_trade_units.TradeUnitsTests.test_fractional_package_and_precision_limit crm.tests.test_trade_units.TradeUnitsTests.test_reject_cross_sku_fraction_overflow_and_spoofed_factor --verbosity 2 --noinput`；`core_review/backend-moq-tests.log` |
| 真实 Chrome、最终构建、精确提交 CI | 本代理未执行，交根任务整合验收 | 已更新既有 ISS022 真实浏览器用例与专属 seed，不将文件存在说成浏览器已通过。 |

后端测试显式 `APP_STAGE=development`，`DATABASE_URL=sqlite:////workspace/scratch/845e333a0b4f/core_review/moq-test.sqlite3`，`MEDIA_ROOT=/workspace/scratch/845e333a0b4f/core_review/media`。Django 实际创建并销毁独立内存测试数据库 `file:memorydb_default?mode=memory&cache=shared`，迁移成功至 0130；不访问真实业务数据。

新增 8 个 MOQ 组件用例覆盖：低/等/高于 MOQ，分行同源合计，不同来源不混算，0.01 件真实短缺，零/缺失/无效阈值（参数化三项），加载中/失败/重试；同时断言 0.58 箱的行内折合展示。仅 DOM 与组件行为测试，不用重复写一遍算法替代被测实现。

## 本代理最终文件清单

1. `frontend/src/views/PurchaseOrderPage.vue`：整数百分位比较、折合数量显示格式化、一条已核实中文提示。
2. `backend/seed_iss022_browser.py`：MOQ58、100件箱，制造真实浮点边界。
3. `frontend/browser-tests/iss022-moq-real.spec.js`：0.57/0.58 箱，验证草稿警报、正式下单与低量例外留痕。
4. `frontend/tests/purchase-moq-precision.spec.js`：新增实际组件行为回归。
5. `frontend/tests/purchase-editor-receipt.spec.js`：唯一“折合”展示断言同步两位小数。

既有文件逐字节替换以保留行尾，PurchaseOrderPage 原有 61 个单独 LF 保持 61；只在新增计算块增加 7 个 CRLF。未改后端业务服务、数据库迁移、台账或发布脚本。文件 SHA256/Git blob 见同目录 `moq-change-manifest.json`，根任务仍需在最后汇总前重算最终哈希。

## 交接建议

- 保留 3bb 已验证业务主体，接收上述最小修补和另两组审查代理确认的项；不要合并所有远端分支。
- 根任务维护发布源码清单的更新，加入 MOQ 行为不变量；祖先提交存在不能防止后续回退，纯字符串存在也不能替代行为测试。
- 对 MOQ 继续沿用 ISS-022 记录新增发现与验证，不凭本代理局部测试宣告全部 Issue 关闭。
- 用户所说财务排版遗漏、部署实例身份、后续安装器脚本范围由根任务与财务代理核验，本报告不作越界结论。
