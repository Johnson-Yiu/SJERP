# ISS-029 测试记录

基线：`b3559f3bf83b967d06166bd409b00fc92e4e5902`。分支：`codex/iss-029-quote-recipient-snapshot`。运行代码及证据随本分支提交，最终 SHA 由交付消息和远端分支绑定。测试日期 2026-10-25，报告整理 2026-10-26。

| 命令 | 真实结果 | 日志 |
|---|---|---|
| `python manage.py test crm.tests.test_quotes crm.tests.test_quote_revision_tree crm.tests.test_formal_party_snapshots --verbosity 1` | 72 项，OK；54.510s | 初轮终端输出，后续全量包含同批用例 |
| `python manage.py test crm --verbosity 1` | 881 项，OK，skipped=13；649.573s | `backend-full.log` |
| `npx vitest run tests/quote-editor-availability.spec.js --environment jsdom` | 20 项通过 | `frontend-focused.log` |
| `npx vitest run tests --exclude tests/detail-drawer-typography.spec.js --environment jsdom` | 65 文件、652 项通过 | `frontend-vitest.log` |
| `npm run test:unit` | 151 项通过 | `frontend-node.log` |
| `npm run build` | 2009 modules，成功；既有 500kB chunk 提示 | `frontend-build.log` |
| `npx playwright test --config playwright.iss029.config.js --reporter=list` | 真实 Chrome，1 个完整 A/B 业务场景通过，51.9s；总 2.4m（含启动） | `chrome-live.log` |
| `python manage.py check` | 0 issues | 本轮终端输出 |
| `python manage.py makemigrations crm --check --dry-run` | No changes detected | 本轮终端输出 |
| `python manage.py migrate --check` | 退出 0；隔离库已迁移 | 本轮终端输出 |
| `python .../verify_exports.py` | 三个实际 XLSX 与 DB 四字段及版本号一致 | `export-reconciliation.json` |

`tests/detail-drawer-typography.spec.js` 使用 node:test，不是 Vitest suite；未将无效 suite 当成通过项。Django 全量含既有权限、数据范围、正式快照及迁移保护测试；其 13 个跳过项保持原有数据库/并发环境限制，没有宣称 PostgreSQL 验收。

真实 Chrome 没有拦截或模拟 API，使用服务端开发身份与独立 SQLite；权限拒绝通过 Django TestCase 中的隔离受限身份覆盖，不修改应用的开发权限配置。详情见 `README.md` 的逐项矩阵。
