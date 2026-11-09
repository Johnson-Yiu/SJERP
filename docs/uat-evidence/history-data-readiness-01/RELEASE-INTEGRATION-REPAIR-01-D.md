# RELEASE-INTEGRATION-REPAIR-01 D 包复验

基于 c90cacaa99a468d92dd61c41437834c5d8acb094，复用原包提交 4d205ece04204e2f8d915ca9ba7707ac86532be7 的补丁。原验收记录保留，本次结果不覆盖原记录。

- 后端：`python manage.py test crm.tests.test_formal_party_snapshots crm.tests.test_historical_orders crm.tests.test_history_import_preflight crm.tests.test_history_takeover crm.tests.test_reporting crm.tests.test_sales_order_import --verbosity=1`：98 项，3 跳过，其余通过，隔离 SQLite。
- 前端：`npm exec --no -- vitest run tests/sales-order-import-ux.spec.js tests/history-takeover.spec.js tests/import-ux.spec.js --reporter=dot`：23 项通过；输出含测试环境 RouterLink 和导航警告。
- `python manage.py makemigrations --check --dry-run crm`：无变化；`git diff --cached --check`：通过。
- 前端复验使用原历史准备工作树的已安装 node_modules；首次 npx 因隔离环境 npm 缓存权限失败，未计入通过结果。
- 本次未执行 Chrome 视觉验收、实际文件下载、PostgreSQL、最终跨包迁移、CI 或生产数据验证。来源包的 Chrome 限制保持原记录；下载清单可查，但相关文件未随来源提交纳入 Git，最终候选须重新保存实际下载证据。
- 迁移 0123 依赖 c90 的 0122，仅增加空历史维度快照，无数据回填。最终集成须处理与 B/A 的迁移汇合，验证新库与升级路径。
