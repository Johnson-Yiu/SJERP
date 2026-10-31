# ISS-042-DEV 测试记录

## 后端

- `python manage.py test crm.tests.test_shared_report_templates --verbosity 1`：7/7 通过。
- `python manage.py test crm.tests.test_reporting --verbosity 1`：32/32 通过。
- `python manage.py test --verbosity 1`：799/799 通过，跳过 13 项，SQLite 全量测试完成。
- `python manage.py test crm.tests --verbosity 1`：22/22 通过（项目当前自定义测试发现范围）。
- `python manage.py makemigrations --check --dry-run`：通过，`No changes detected`。
- Python Django 导入 `crm.report_templates`：通过。

原始输出：`backend-shared.log`、`backend-reporting.log`、`backend-targeted.log`、`backend-all.log`、`backend-migrations.log`。

## 前端

- `npx vitest run tests/reports.spec.js tests/shared-report-templates.spec.js --environment jsdom`：2 files / 7 tests 通过。
- `npx vitest run tests/r0f2-overview-reports.spec.js --environment jsdom`：1 file / 15 tests 通过。
- `npm run test:unit`：143/143 通过。
- `npm run build`：通过；Vite 仅报告既有主入口 chunk 体积提示。

原始输出：`frontend-targeted.log`、`frontend-overview.log`、`frontend-unit.log`、`frontend-build.log`。

## 真实 Chrome

- `npx playwright test browser-tests/shared-report-templates.spec.js --workers=1`，`PLAYWRIGHT_CHANNEL=chrome`：1/1 通过。
- `npx playwright test browser-tests/overview-reports.spec.js --workers=1`，`PLAYWRIGHT_CHANNEL=chrome`：15/15 通过。
- 共享模板测试使用独立 manager/employee browser context：管理者创建和发布，普通用户跨 context 使用、刷新看到更新、取消发布后不可用、删除后个人 localStorage 图表仍保留。

原始输出：`browser-shared.log`、`browser-overview.log`。

## Runner 限制

直接运行全量 `npx vitest run --environment jsdom` 会把仓库中使用 Node `node:test` 的 `src/**/*.test.js` 当作 Vitest 文件，产生既有的 `No test suite found` 失败；另有一项旧 `phase2a-list-shell` 路由基线断言不属于本轮。未修改无关测试以掩盖该 runner 差异，使用项目标准 `npm run test:unit` 与本轮定向 Vitest 验证。
