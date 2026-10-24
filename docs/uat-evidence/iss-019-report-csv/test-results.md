# ISS-019 测试记录

## 后端

- `python manage.py test crm.tests.test_reporting crm.tests.test_functional_rbac crm.tests.test_shared_report_templates --verbosity 1`：77/77 通过，system check 无问题。
- `python manage.py test --verbosity 1`：863/863 通过，13 项按项目现状跳过；第二次执行使用独立 `backend/media` 测试目录，消除了 managed worktree 的媒体写入权限错误。
- `python manage.py check`：通过。
- `python manage.py migrate --check`：通过（对隔离 ISS-019 evidence SQLite）。
- `python manage.py makemigrations crm --check --dry-run`：`No changes detected`。
- 本地 Django HTTP 下载：`GET /api/reports/data/?...&export=csv` 返回 200；下载文件 549 bytes、前缀 `EF BB BF`，SHA-256 与 `report-sales-customer.csv` 相同。

## 前端

- `npm run test:unit`：151/151 通过。
- `npx vitest run tests --exclude tests/detail-drawer-typography.spec.js --environment jsdom`：64 个文件、645/645 通过。
- `npx vitest run tests/reports.spec.js --environment jsdom`：5/5 通过。
- `npm run build`：Vite 8.2.0，2009 modules，生产构建通过；保留既有大 chunk warning。
- `PLAYWRIGHT_CHANNEL=chrome npx playwright test browser-tests/overview-reports.spec.js --workers=1`：16/16 通过，覆盖 1440、1280、1024、700；新增未提交筛选不影响导出用例通过。

仓库的 `frontend/src/**.test.js` 中有 41 个 `node:test` 文件。直接 `npx vitest run` 会将它们误当作 Vitest 文件并报告 `No test suite found`；本轮按项目现有双 runner 约定分别用 `npm run test:unit` 和排除唯一 `frontend/tests/detail-drawer-typography.spec.js` 的有效 Vitest 集合验证，未把 runner 混用输出计入业务失败。

## 权限回归

新增后端用例：报表 `view=false`、`export=true`、销售来源 `view=true` 时，普通 API 和 CSV API 均为 403。既有 `view=true`、`export=false` 的 CSV 403、来源/维度权限拒绝和共享模板当前权限复核仍全部通过。
