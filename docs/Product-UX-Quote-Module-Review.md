# Product UX Review — Module 2：Quote Management

## 范围与接受门槛

基线：`0df25bbc5ef70614762e1d64c49fb63891a80918`，CI #154 backend / backend-postgres / frontend 全部 SUCCESS。
本次只调整报价列表、树交互、筛选与路由连续性。QuoteEditorModal、QuoteDetailModal、后端生产代码、模型、迁移、全局样式均未修改。
编号、修订编号、历史不可变模型、状态规则、转订单、库存可用量、销售规则、预估装箱、交易单位、导出及财务语义保持原实现。
实现与真实 UI UAT 已完成；最终 HEAD 三项 CI 全部 SUCCESS 且独立 ChatGPT 评审通过后，才可宣布本轮 Quote Management UX-FROZEN。当前独立评审待完成；不冻结全 ERP，不开始下一模块。

## 原问题与决策

- 原已接受金额直接累加不同币种 total_amount 再标为 USD，数学上无效。已完全移除 acceptedAmount 及其卡片，没有前端换汇或当前汇率换算；单条报价继续显示原币金额。
- 四张卡片为报价项目（当前结果 parent_quote 为 null 的根报价数）、报价版本（当前结果全部原始与修订记录）、进行中（draft + sent）、已接受（accepted 版本数）。
- 原根行只展开甚至无修订时无动作。现在任何报价行或号码点击均打开该准确 ID 的详情；专用 Chevron 按钮使用 click.stop，只展开/收起，不打开详情，Enter 亦阻止向行冒泡。
- 原 status/customer/ordering 为本地 ref，刷新丢失。现在三个状态派生自 route.query；默认空 status/customer、ordering=-updated_at。
- 原客户下拉源于当前报价结果，随筛选缩水。现复用客户主数据 customers，页面进入时独立加载，单实例缓存请求；编辑器 options 加载复用同一客户请求。

## 路由规则

支持 `/quotes?status=sent&customer=2&ordering=-quote_date`。
控件通过普通 router.push 更新对应 key，保留其他 query 和 hash。只有 route 数据签名 watcher 触发筛选数据重载，不叠加 change load。
重置移除 status/customer/ordering，恢复默认排序；不移除 detail/create/edit/returnTo 或其他上下文。沿用清空本地瞬时搜索；若没有 URL 筛选变化但搜索已清空，仅补一次 load。
直接挂载与浏览器刷新从 route 恢复三个控件，并向后端传相同筛选；客户主数据选项独立于结果。
详情开关复用既有 DocumentDetail 路由工具，保留筛选。
Module 1 客户精确工作台 RouterLink、普通历史 push 与浏览器 Back 保持不变。

## 真实 UI UAT

2026-10-07，使用内置 Browser 技能，未使用 Computer Use 或 API/DB/shell 数据写入捷径。
使用现有 UAT 报价，没有创建、保存、变更状态或删除任何业务记录。

| UAT | 结果 | 实际证据 |
| --- | --- | --- |
| UAT-QUOTE-001 | PASS | 全部结果：报价项目 42、版本 45、进行中 17、已接受 26；无已接受金额 USD 卡 |
| UAT-QUOTE-002 | PASS | 点击有修订的原始报价号码 SJ20260930DE001（行冒泡，非眼睛按钮），打开原始 ID 1 |
| UAT-QUOTE-003 | PASS | 专用展开/收起按钮展示/隐藏修订；无详情 dialog，URL 不含 detail |
| UAT-QUOTE-004 | PASS | 点击修订 SJ20260930DE001-1，准确打开 ID 2 |
| UAT-QUOTE-005 | PASS | 选已发送，URL status=sent；刷新保持，唯一结果 SJ20260930CA001，状态已发送 |
| UAT-QUOTE-006 | PASS | 选择 UAT-R1 CSV Test Customer（ID 2），URL customer=2；刷新客户选择保留 |
| UAT-QUOTE-007 | PASS | 新到旧报价日期，URL ordering=-quote_date；刷新排序选择保留 |
| UAT-QUOTE-008 | PASS | 已发送仅有客户 2 的一条结果，但下拉仍有全部 12 个客户，包括不在结果中的 Alpha ID 1 |
| UAT-QUOTE-009 | PASS | active status/customer/ordering 下打开 ID 10，detail=10 与三个筛选共存；关闭仅移除 detail，列表仍一条 CNY 310.00 报价 |
| UAT-QUOTE-010 | PASS | 客户 ID 1 → 报价 SJ20261002DE003 → 打开报价工作台 `/quotes?detail=40`；浏览器 Back 返回 `/customers?detail=1` 同一客户 |

临时数据及清理：没有新增或修改业务数据，无需清理。
截图：本任务 visualizations 目录 `quote-ux-filter-uat.png`；筛选后卡片 1/1/1/0，单行金额 CNY 310.00。

## 自动化与回归

新增 `tests/quote-list-ux.spec.js` 7 项，子场景覆盖混币情况下纯数量卡片、根/版本/进行中/接受数量、两类根行、修订行、专用展开、直接 URL 与重新挂载、三个筛选的 URL/API 参数、单次请求、detail/其他上下文保留、重置保留 create/edit/returnTo、客户主数据独立。
更新 DocumentPage Node 源码断言：route computed、任何行打开准确详情、不存在 acceptedAmount/旧卡。
更新原路由测试 customer 参数为 URL 字符串，客户变化后等待导航完成再改变排序；业务筛选与树排序断言继续保留。
完整前端测试含 Module 1 customer-ux 的工作台/返回回归，报价状态动作与 PI 官方 totals、编辑器、交易单位、转订单、采购与装箱等既有验证。
后端 full suite 验证既有 Quote 生命周期、修订、导出、库存等规则；未通过真实 UI 改变 UAT 报价状态来验证写操作。

| 检查 | 本地结果 |
| --- | --- |
| backend full suite | 562 项，OK（10 项 PostgreSQL 专用测试本地跳过） |
| makemigrations --check --dry-run | No changes detected |
| frontend Node | 111 项 PASS |
| Node-only typography | 1 项 PASS |
| frontend Vitest | 25 文件 / 190 项 PASS |
| frontend build | PASS，既有块体积提示 |
| git diff --check | PASS |

## CI 与评审状态

实现提交 CI 待推送后核对记录。包含 CI 记录的最终文档提交也必须独立核对其 HEAD 的三个作业。
最终 SHA、最终工作流号与三个结论记录在最终交付报告；不提前声称未完成的 CI 通过。
独立 ChatGPT 评审尚未收到，当前不宣布 UX-FROZEN。
正常 commit/push，不 force push、reset 或远程历史 rebase；非快进即停止。
