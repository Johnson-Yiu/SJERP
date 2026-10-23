# ISS-042-FIX-01 测试记录

## 后端

- `python manage.py test crm.tests.test_shared_report_templates --verbosity 1`：8/8 通过。
- `python manage.py test crm.tests.test_reporting --verbosity 1`：32/32 通过。
- SQLite 全量 `python manage.py test --verbosity 1`：800/800 通过，跳过 13 项。
- `python manage.py makemigrations --check --dry-run`：`No changes detected`，本轮不新增迁移。

日志：`backend-shared.log`、`backend-reporting.log`、`backend-all.log`、`backend-migrations.log`。

## 前端和浏览器

- `npx vitest run tests/reports.spec.js tests/shared-report-templates.spec.js --environment jsdom`：7/7 通过。
- `npm run test:unit`：143/143 通过。
- `npm run build`：通过；仅有既有 chunk 体积警告。
- 真实 Chrome `browser-tests/shared-report-templates.spec.js`：1/1 通过，包含 mock 409 刷新提示、跨会话、个人图表兼容和截图。
- 既有报表中心 Chrome 回归 `browser-tests/overview-reports.spec.js`：15/15 通过。

日志：`frontend-targeted.log`、`frontend-unit.log`、`frontend-build.log`、`browser-shared.log`、`browser-overview.log`。

直接全量 Vitest 的仓库既有 runner 混用问题仍单独保留：Node `node:test` 文件被 Vitest 收集时会产生 `No test suite found`，不将其写成“全量 Vitest 通过”。
