# H2 历史商品关联补修

工作分支为 `codex/history-product-linking-fixes-02`。已审基线为 `43067137d0fba04b0be055e449e55a06dba6d208`。产品冻结在 `e01d2f0c2a65320b47bd8e1fe9ecf5ca2a021391`。测试使用独立数据库、媒体目录、合成资料和本机验收账号。GitHub Actions 为 `NOT_RUN`。

## 复现与修复

| 项目 | 复现 | 修复与断言 |
|---|---|---|
| 订单行与履约行 | 用历史编码 HIST-A 建销售明细和发货行，导入前先后选择正式 SKU | 原始身份与人工确认身份分开比较。同源同目标通过，异目标阻断。清除需明确选择并填写依据，原始编码仍为 HIST-A。 |
| 规格核实 | 对空白原规格直接关联，或填写不同功率、无依据、目标规格也为空 | 支持明确记录补核规格及依据。仅归一化已列明单位前的空白，区分 24 W、24 kW 与不同基础单位。续办时重查当前关联版本的核实审计及正式规格。 |
| 下次导入候选 | 先保存已核实规则，再导入同来源和原始身份的新单 | 显示编码、商品名、规格、单位、来源及依据。选择只预填关联表单，提交前仍需填写依据。停用、待核实、已改规格的旧规则不会成为可选候选。 |
| 关联审计 | 批量关联、改绑、解绑、待核实及审计写入失败 | 追加记录动作、来源、前后 SKU 快照、核实规格、依据、身份和时间。开发身份按既有策略记为非实名。审计失败回滚整个关联批次，重试按原请求返回。 |
| 金额舍入 | 50 条数量 1、单价 0.335 的销售明细。H1 预览返回 16.75 | 销售有效行金额沿用单据货币舍入。预览、CSV、分析的商品金额为 17.00，单据金额含运费 10 和折扣 5 后为 22.00。原单价及原始快照保留。 |
| 历史分析乱序 | 让初次请求晚到，再快速切换关联口径和原文口径 | 初次、刷新、日期及口径切换共享同一个请求序号。回包只在序号仍有效时生效。等待和错误期间不展示旧口径结果，关闭工作区后忽略旧回包。 |
| 未知 SKU 的归档盘点 | 归档盘点后查不到正式 SKU，或已复核后改绑 | 关联入口展示原始编码和正式 SKU。改绑使待复核或已复核且未执行的盘点申请失效。只有重新走原申请、双人复核和启用后才入库存基准，原盘点和已执行事实保留。 |
| 迁移降级 | H1 中创建归档、链接、候选规则和审计引用后降级至 0128 | 在删除结构前拒绝降级，验证引用及各表数据完整。空库可降级，再前向升级。 |
| 列表查询 | H1 过滤后的 500 来源查询执行 505 条 SQL | 数据库先过滤及分页，再按明细类型批量读取。50 条和 500 条的每页查询次数相同，断言不超过 8。相同筛选的总数、第一页和 CSV 一致。 |

[H1 基线复现原始结果](h1-baseline-repro.log) · [统一 24W 的身份比较单独复现](h1-identity-repro.log)

正常关联的回归同时核对 SKU 数量、历史分类、国家、成本快照、库存、资金及付款计划。库存基准的新增来自原审批链执行，关联和改绑本身不产生基准。历史销售及采购续办测试仍检查原幂等、审计、回滚及并发约束。

## 修改文件

- 后端历史业务与 API 位于 `history_products.py`、`history_product_api.py`、`history_import_preflight.py`、`history_takeover.py`、`history_takeover_api.py`、`history_operational_inventory.py` 和 `history_operational_contracts.py`。
- 迁移修改 `0129_historical_product_linking.py` 与 `0130_history_product_candidate_rules.py` 的逆向保护。前向为无操作的检查点，既有迁移状态和数据不重写。
- 前端修改 `HistoryProductLinking.vue`、`HistoryOrdersPage.vue`、`HistoryPreflightPage.vue`、`HistoryTakeoverPage.vue`。回归包含后端历史测试、历史页面 Vitest 及独立 Chrome 用例。可按 `git diff --name-only 43067137d0fba04b0be055e449e55a06dba6d208 e01d2f0c2a65320b47bd8e1fe9ecf5ca2a021391` 查文件全路径。

## 运行记录

H1 复现使用指定源码的独立归档副本，注入本轮回归断言以保留旧失败。最早 SQLite 定向试跑中，9 条旧续办用例使用两个空规格，已修正合成夹具并继续验证原业务断言。PG 首次在 Windows 沙箱启动受限，获批后第二次启动和停止正常，但仓库虚拟环境缺少驱动。最终使用本机 Python 3.14、Django 6.0.6、psycopg 3.3.6 和 PostgreSQL 17.11。运行日志省略浏览器临时隔离令牌并清理行尾空格。浏览器首次进入候选界面后，脚本因名称与编码顺序断言停止。后续 Chrome 显示候选已选择并保存，但普通商品预览按钮在选中 SKU 后仍禁用。复现确认 Vue 将空字符串判为启用 disabled 属性，已改成显式布尔值。首次单次 HTTP 503 注入被应用自动重试恢复，取证脚本改为覆盖初次请求及五次自动重试。

[旧 SQLite 夹具失败](sqlite.log) · [PG 启动受限](postgres.log) · [PG 缺驱动](postgres-isolated.log) · [Chrome 按钮超时](chrome.log) · [Chrome 按钮禁用](chrome-final.log) · [Chrome 单次故障注入](chrome-verified.log)

| 检查 | 通过 | 失败 | 跳过 | 证据 |
|---|---:|---:|---:|---|
| SQLite 历史定向 | 72 | 0 | 7 | [最终日志](sqlite-final.log)，跳过项依赖 PostgreSQL。 |
| PostgreSQL 17 历史定向 | 33 | 0 | 0 | [最终日志](postgres-final.log)，包含并发锁、线程退出、测试库删除和临时服务停止。 |
| 历史页面 Node | 6 | 0 | 0 | [日志](frontend-node.log) |
| 历史页面 Vitest | 19 | 0 | 0 | [日志](frontend-vitest.log) |
| 前端构建 | 1 | 0 | 0 | [日志](frontend-build.log) |
| 真实 Chrome 历史业务 | 1 | 0 | 0 | [完整记录](chrome-accepted.log) |

数据库测试运行时的 HEAD 为 `c980bf69c763206f4465172c0a865ca98d51c573`。此后至产品冻结的差异仅在前端及测试脚本，`git diff c980bf69 e01d2f0c -- backend` 为空。PostgreSQL 停机后只剩默认的 1、4、5 数据库目录，已移除本包临时集群。

## Chrome 与下载证据

使用真实 Google Chrome `156.0.8078.80`、1440×900、100% 缩放和已认证的本机验收账号。浏览器运行 HEAD 为 `a90beef504df546c8b2fd1e4a0de126230eaff97`，相对产品冻结仅改浏览器断言。候选选择、预览冲突、人工补核、保存审计、口径切换和下载均使用隔离后端。分析故障通过 Playwright 注入六次 HTTP 503，手动刷新回到真实后端。迟到初始请求及快速切换由 Vitest 控制请求顺序复现。

- [候选与适用依据](candidate.png)
- [缺少规格时的冲突](missing-specification-conflict.png)
- [填写核实规格和依据后的预览](verified-specification-preview.png)
- [保存后的审计快照](audit-detail.png)
- [按关联 SKU 归集](linked-analysis.png)
- [重试耗尽后的提示](analysis-error.png)
- [手动恢复后的历史原文](original-analysis-recovered.png)
- [浏览器元数据](chrome-checks.json)

实际下载的“历史商品明细.csv”包含四条合成明细。核对 A1 原规格仍为空、正式 SKU 为 B、金额 50.00 CNY。销售商品合计 200.00 CNY，采购商品合计 15.00 USD。文件 SHA-256 为 `4b399dc70358315d5c7c8f7db88b244b7058ce025fe5c061557fcd950976bb95`。[原始下载](history-products.csv)

## 后续待验

全量数据库、前端和通用浏览器验收由 A3 在集成冻结候选上执行。正式部署环境、实际媒体权限、异地备份与调度，以及真实历史资料的质量和导入仍需按发布流程验收。
