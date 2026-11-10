# H1 历史商品归档与 SKU 关联

## 基线与交付边界

- 仓库 Johnson-Yiu/SUNJACK-ERP。分支 `codex/history-product-sku-linking-01`，独立 worktree `.worktrees/history-product-sku-linking-01`。
- 本轮核实 D2 本地对象及远端 `codex/history-completion-fixes-02` 均为 `3e925910d43647e58c1f0512c2ccc6371adeb874`。核实的远端 master 为 `25405e1b25ff8a218b67883acf489ada8a53e146`。
- 本轮查看了 `AGENTS.md`、`PROJECT_ISSUES.md`、`PROJECT_PHASES.md`、`REVIEW_PROTOCOL.md`、D2 历史分类与中文更正表单代码，以及历史预检、归档、资金、库存和接续的现有入口。财务分支远端可见 `96ad680c7b0cd154914046bcbe63de23fb8e64e3`，未取得 A2 冻结交付回执。
- 独立模块提交 `26867e84`。共有文件适配和最终业务源码 `7eeae5de4feaaafbbcd4c1574acb88ecbfeec9b0`。后继交付提交只归档证据。
- GitHub Actions `NOT_RUN`，提交使用 `[skip ci]`。未部署、未导入生产资料、未合并 master。A2/E1/E2 工作区和公共台账由原任务继续维护。

## 入口、权限与数据范围

| 入口 | 允许的操作 | 拒绝或降级 |
| --- | --- | --- |
| 历史工作簿预检、审核、执行 | 原有历史预检及管理员审核。商品缺少正式 SKU 可归档，仍核验来源、数量、币种、金额、主体、去重及凭证 | 无权限、重复来源、无效明细或未审核执行被拒绝 |
| `GET /api/import/history-products/`、`targets/`、`export/` | 经认证并通过历史资料、SKU 权限。按来源、批次、商品、日期、状态或目标编码查询 | 沿用历史申请可见范围，停用 SKU 不出现在目标选择器 |
| `POST /api/import/history-products/preview/`、`apply/` | 管理员预览与提交。改绑、解绑和标记待核实须有原因 | 不同目标冲突、规格单位冲突、过期、越权和并发版本变化均阻止整批写入 |
| 历史订单列表、详情和 `GET /api/reports/historical/?grouping=original\|linked` | 保留原文、历史分类、数量单位与订单合计。按正式 SKU ID 归集。进入 `/skus?detail=<id>` | 沿用销售数据范围及主档权限。历史商品明细不进入正式商品、利润或资金分摊报表 |
| 履约接续 | 核实的关联进入独立申请和复核，正式 SKU 与关联版本进入指纹 | 未关联、待核实、停用或单位规格冲突时阻断。变更关联使引用该行且未执行的接续须重新申请。已执行事实保留 |

- 迁移 `0129_historical_product_linking` 依赖 D2 的 `0128_merge_release_integration`，建立历史事实、当前关联和请求回执。迁移 `0130_history_product_candidate_rules` 建立来源限定候选规则。原有来源身份和正式明细 SKU 约束保留。
- 新档以 `HistoryTakeoverSourceRecord` 的稳定来源身份关联独立历史明细。旧档保留原目标并由历史读取适配层读取。已有承接来源身份的旧行可以在关联页处理，历史手工录入且没有承接来源身份的行保留原先的 SKU 关系和读取方式。成本、规格等缺失字段仍为空，归集不读取当前成本。候选规则使用来源系统、业务类型、原编码、规格和单位作为作用范围，只提出候选。
- 共有文件适配涉及历史预检、工作簿模板、执行及运营接续，Order/Purchase 模型金额与序列化、历史报表、路由和相邻回归，以及历史资料页、历史订单页和销售/采购详情。D2 冻结分类逻辑和中文更正表单保留。

## 验证命令

- SQLite 使用独立默认内存测试库及专属媒体目录。运行 `backend/manage.py test crm.tests.test_history_products crm.tests.test_history_takeover crm.tests.test_historical_orders crm.tests.test_history_import_preflight crm.tests.test_history_operational_contracts crm.tests.test_history_operational_inventory crm.tests.test_history_operational_finance --noinput`，78 项通过、9 项 PostgreSQL 专项或环境条件跳过、0 失败。见 [sqlite.log](sqlite.log)。
- PostgreSQL 17 用现有 PostgreSQL 二进制启动专属回环临时集群。执行 `python docs/uat-evidence/history-product-sku-linking-01/run-postgres.py --postgres-bin <本机 PostgreSQL 17 bin>`。脚本用 D2 旧明细验证前向升级，并在 Django 新建测试库执行事务、并发、审计保护和接续测试。前向升级保留旧明细、来源标识和 70 元订单金额，新库专项 31/31 通过。见 [postgresql-final.log](postgresql-final.log)。
- 前端执行 `npm ci --offline --no-audit --no-fund`、`node --test src/views/HistoryOrdersPage.test.js src/components/OrderDetailModal.test.js`、`npx vitest run src/components/HistoryProductLinking.test.js` 和 `npm run build`。Node 12/12，真实挂载的组件测试 3/3，构建成功并报告既有大包体提示。
- 在独立 SQLite 合成库 `h1-browser-fixture.sqlite3` 执行 `backend/manage.py migrate --noinput`，由 [seed-browser.py](seed-browser.py) 导入合成来源。后端绑定 `127.0.0.1:8398`，Vite 绑定 `127.0.0.1:5398`，设置专属媒体目录及 CSRF 来源。浏览器用既有忽略配置的本机验收账号。运行 `node docs/uat-evidence/history-product-sku-linking-01/check-browser.mjs`。
- Chrome 156 原生网页缩放 100% / 125%，物理视口 1366 / 1440 / 390。核查长名称换行、弹窗滚动、保存按钮位置、两个独立会话产生的真实 409，以及一次注入 503 后真实保存。检查 `/skus?detail=<id>` 导航和历史分析的关联归集。见 [Chrome 测量结果](chrome-checks.json)、[冲突截图](chrome-390-conflict.png)、[重试截图](chrome-390-retry.png) 和 [实际下载 CSV](history-products.csv)。125% 视口另存全幅原生截图。CSV 共四条，已关联与待关联各两条，SHA-256 为 `06606ad2790cf7abfc5e21e3c2dfc1e6a04e01503199aa6bea087ff4e42d46ee`。附件均为合成资料。
- 尝试记录。早期 SQLite 旧测试仍断言新归档写正式明细，更新为断言独立存储且原约束保留。第一次 PG 缺 psycopg，随后改用现有 Django 6.0.9 / psycopg 3.3.6 环境。首次成功启动的 PG 回归发现旧接续并发夹具缺少显式 SKU 关联，修复后 31/31。Chrome 早期夹具缺少测试 Host，后续遇到 CSRF 来源端口错配和选择器严格模式断言，已修正。浏览器扩展载入未能运行，最终通过独立 Chrome 原生设置的“网页缩放”验证。两份原属 Node runner 的旧前端用例误用 Vitest 后改用正确 runner。

## 待独立复审与待集成

- 独立复审关注旧档读取、来源和目标权限、候选规则作用域、锁序、审计回滚以及重试和接续审批失效。当前范围不关闭既有历史问题。
- A2 提供已推送冻结 SHA 后，核对迁移叶、共有文件及财务恢复修复，接收 H1 与 A2，再在同一最终候选运行适用后端全量、前端全量与构建，并补验实际受影响的 E1/E2 入口。
- 公共台账待合入内容。PROJECT_ISSUES 登记 H1 独立源码、源码范围证据和待独立复审事项。PROJECT_PHASES 登记 H1 依赖 A2 冻结和最终同 SHA 验收。整合后更新两处，保留现有 Issue 状态。
