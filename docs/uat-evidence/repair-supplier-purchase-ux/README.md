# 供应商与采购浏览器回归修复验收

## 范围与基线

- 固定基线：`054bd82518039a5bc0e0c14234964a14d7fbbfd8`
- 实际独立分支：`codex/repair-supplier-purchase-ux-20261028`
- 目标分支 `codex/repair-supplier-purchase-ux` 已被另一独立 worktree 占用；本轮从指定基线创建了不覆盖既有工作树的同基线独立分支。
- 本轮未修改 `master`、`PROJECT_ISSUES.md`、`PROJECT_PHASES.md`，未触发 GitHub Actions，未部署。

## 结论

本轮未确认供应商或采购业务产品缺陷。8 项失败均可由证据解释：6 项是 ISS-075 退出供应商固定付款规则后仍保留的过时浏览器断言，ISS-022 的固定端口运行受到其他 worktree 数据污染，ISS-075 的截图阶段受到可选外部字体网络请求阻塞。

没有重新引入 `payment_terms_config` 编辑器、固定付款规则筛选或供应商比例输入框；没有改动 MOQ 例外审批、正式下单二次核验、历史付款计划或供应商备注后端规则。

## 失败分类与依据

### 已确认的过时测试断言

`frontend/browser-tests/supplier-ux.spec.js` 的以下断言与当前 ISS-075 验收契约冲突：

1. 三个视口要求供应商编辑器出现 `.terms-description` 及“已保存采购保留原快照”。当前供应商编辑器只维护付款条款备注，不渲染供应商固定付款计划编辑器。
2. 创建供应商后读取 `state.posts[0].payment_terms_config.map(...)`。当前普通供应商保存请求不提交该兼容字段。
3. 查找供应商编辑器中的“比例 % 1”输入框并校验固定付款比例。当前比例编辑器已从供应商常规前端退出；采购单仍保留逐单付款条件编辑器。
4. `termsMode=custom` 期望供应商筛选只剩 1 行。当前供应商筛选只支持搜索和可供分类，旧 `termsMode` 不再是有效固定付款规则筛选；分页仍按页面大小显示 25 行。
5. 从供应商关联入口新建采购单时期望自动填充 50% 比例。当前采购单付款条件默认为空，页面明确提示“未协商时可暂不设置”。

证据：ISS-075 历史验收记录明确要求保留旧数据库字段和兼容能力，但从供应商常规列表、编辑和筛选页面移除固定规则；采购单付款条件逐单协商，未协商时不生成应付计划。

因此本轮只更新测试 mock 与断言，使其核对当前 API/UI 契约；没有 skip 或删除测试。

### ISS-022 固定端口运行不是产品缺陷

原固定端口 `54127` 上已有其他 worktree 的 Django 进程。请求 `/api/purchase-orders/?page=1` 返回了外部数据库数据，重跑时列表出现 4 行而不是隔离场景预期的 2 行。该运行不作为验收证据，也没有终止其他任务进程。

在新端口 `54227` + Vite `54228`、全新 SQLite 数据库和独立媒体目录上重跑，场景通过 `1 passed (13.6s)`。真实请求包括：创建 201、正常下单 200、低于 MOQ 两次拒绝 400、填写例外原因后下单 200、状态筛选 200；`noHorizontalOverflow=true`。

### ISS-075 截图等待是测试环境可靠性问题

固定端口的真实页面能够加载，但截图阶段曾停在 `waiting for fonts to load...` 直至 120 秒；服务器日志显示页面请求均为 200，页面快照已显示供应商列表、空付款条件采购草稿和历史付款计划，没有 API、迁移或采购工作流错误。

本轮在 ISS-075 浏览器测试中仅拦截 `fonts.googleapis.com` 和 `fonts.gstatic.com` 的可选请求，让浏览器使用产品已配置的 fallback 字体；没有改动产品 CSS。未增加测试超时。新端口 `54274` + Vite `54275` 隔离运行通过 `1 passed (6.8s)`。

## 实际浏览器证据

### ISS-022 MOQ

- [浏览器请求日志](./iss022/browser-log.json)
- [Playwright 报告](./iss022/playwright-repair-report.json)
- [隔离迁移日志](./iss022/migration-isolated.log)
- [隔离服务器日志](./iss022/server-isolated.err.log)
- [低于 MOQ 例外确认](./iss022/05-low-moq-exception-dialog.png)
- [例外记录持久化](./iss022/07-moq-exception-persisted.png)
- [窄屏采购列表](./iss022/09-narrow-purchase-list.png)

### ISS-075 付款条件

以下 `iss075-rerun` 文件是字体拦截修正后的成功重跑证据；迁移、种子和服务器日志与该隔离 SQLite 场景一并归档：

- [浏览器请求日志](./iss075-rerun/browser-log.json)
- [Playwright 报告](./iss075-rerun/playwright-repair-report.json)
- [隔离迁移日志](./iss075-rerun/migration-isolated.log)
- [隔离服务器日志](./iss075-rerun/server-isolated.err.log)
- [供应商列表：无固定规则入口](./iss075-rerun/01-supplier-list-no-fixed-rule.png)
- [新采购单：空付款条件](./iss075-rerun/02-new-po-empty-payment-terms.png)
- [历史采购单：保留付款计划](./iss075-rerun/03-history-po-payment-plan.png)
- [窄屏供应商列表](./iss075-rerun/04-narrow-supplier-list.png)

截图由 Playwright `channel: chrome` 生成，覆盖桌面和窄屏视口；ISS-022、ISS-075 均检查了横向溢出。

## 测试结果

### 后端

在全新 SQLite 测试数据库上执行迁移至 `crm.0089_operationlog_operator_protect`，迁移成功；ISS-022 和 ISS-075 隔离场景均使用独立数据库和媒体目录。

定向 Django 测试：`28 passed`，包括供应商付款条款显示、MOQ、采购付款条件、付款计划筛选和采购安全。

### 前端

- `npm ci --ignore-scripts --no-audit --no-fund`：通过。
- `npm run test:unit`：`156 passed`。
- `npm run test:trade-units`：`4 passed`。
- 供应商、采购工作台、采购安全、采购付款、付款条件及付款计划相关 Vitest：`7 files / 54 passed`。
- `npm run build`：通过；仅有既有大 chunk warning，没有构建错误。
- `supplier-ux.spec.js`：`8 passed (37.2s)`。
- ISS-022 隔离真实 Chrome：`1 passed (13.6s)`。
- ISS-075 隔离真实 Chrome：`1 passed (6.8s)`。

曾单独尝试把 `frontend/src/views/PurchaseOrderPage.test.js` 加入 Vitest，但该文件本身没有 test suite；相关有效的 7 个测试文件已单独重跑并全部通过，该文件未修改。

## 修改清单

- `frontend/browser-tests/supplier-ux.spec.js`：移除过时固定付款规则 mock，改为验证付款备注、无规则 UI、旧筛选参数不生效、空付款条件采购草稿和现有供应商数据校验。
- `frontend/browser-tests/iss075-payment-terms-real.spec.js`：仅为本地真实截图阻断可选外部字体请求，保持 fallback 字体和业务流程不变。
- 未修改 `frontend/browser-tests/iss022-moq-real.spec.js`；该场景在隔离端口和数据库上通过。
- 未修改后端业务代码、数据库迁移、MOQ/付款规则、采购状态或共享项目台账。

## 待后续补修与限制

- 当前两个正式 Playwright 配置仍使用固定开发端口；多 worktree 并行运行时可能发生端口和数据库污染。后续可单独安排测试基础设施任务改为动态端口/显式生命周期，本轮不扩大范围。
- 本轮按要求未运行 GitHub CI、PostgreSQL、生产代理安全验收，也未部署生产。
- 真实生产网络字体可用性未在本地回归中判定；本轮只确保字体不可用时页面仍能用 fallback 完成截图和业务操作。
- 开发环境使用统一开发超级管理员和本地 SQLite，不能替代生产账号、PostgreSQL 和代理层验收。
