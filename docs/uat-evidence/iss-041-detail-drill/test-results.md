# ISS-041-B 测试结果

## 通过

- Backend：`python manage.py test crm.tests.test_reporting` → **32/32 passed**。
- 前端报表定向 Vitest：`node node_modules/vitest/vitest.mjs run tests/r0f2-overview-reports.spec.js --environment jsdom` → **15/15 passed**。
- 前端 Node 单元测试：`node --test` → **143/143 passed**。
- 前端生产构建：`node node_modules/vite/bin/vite.js build` → **SUCCESS**，Vite 8.2.0，2007 modules；仅有既有大 chunk warning。
- 报表中心真实 Chrome：`node node_modules/@playwright/test/cli.js test browser-tests/overview-reports.spec.js --config=playwright.config.js` → **15/15 passed**，覆盖 1440/1280/1024/700、旧保存配置、两级下钻、权限及原始明细。
- ISS-041-B 截图测试：`browser-tests/iss041b-evidence.spec.js` → **2/2 passed**。

## 未纳入本轮结论的环境项

直接执行前端全量 Vitest 会收集项目中使用 `node:test` 的 `src/**/*.test.js` 文件，产生 42 个 `No test suite found` 收集错误；另有既有 `tests/phase2a-list-shell.spec.js` 对当前基线导航预期不一致。本轮未修改这些无关测试；与本任务直接相关的 15 项 Vitest、143 项 Node 测试和报表浏览器套件均通过。

本机 PostgreSQL/CI 未在本轮启动；用户要求 CI 继续 PENDING，因此仅报告隔离 SQLite、本地前端构建和真实 Chrome 结果。
