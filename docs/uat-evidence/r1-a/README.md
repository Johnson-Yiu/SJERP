# R1-A 原始证据

所有业务记录均为专用SQLite合成数据。脚本准备≠UI验收；自动页面测试多数mock API，不能当真实业务证据。

- REAL_UI_ACTION：下列原图，IAB及Chrome实际操作步骤见[报告](../../R1-A-核心业务历史Issue核实与修复.md)。图片是直接截图字节，未编辑；尺寸/格式/哈希见manifest.json。
- FIXTURE_SETUP：seed_isolated.py、fixture.log、migrate.log。
- REAL_API_OBSERVATION：server.log、replay-http.json、http-final.json；http-initial.json保留首次脚本路径错误及404，不据此判断产品缺陷。
- DATABASE_VERIFICATION：database-checkpoint.json、database-final.json及对应只读脚本。
- MOCKED_TEST：Vitest、Playwright（mock业务API）及后端故障注入；后端API测试在真实独立测试数据库运行，但不是实际浏览器操作。
- BLOCKED/未覆盖：提交后断网、跨刷新恢复及真实多客户端并发详见报告。

- [chrome-finance-rejected.jpg](chrome-finance-rejected.jpg) · Chrome · 1905×912
- [chrome-finance-saved.jpg](chrome-finance-saved.jpg) · Chrome · 1905×912
- [chrome-reversal-feedback.jpg](chrome-reversal-feedback.jpg) · Chrome · 1920×919
- [chrome-reversal.jpg](chrome-reversal.jpg) · Chrome · 1920×919
- [iss001-completed-unpaid.jpg](iss001-completed-unpaid.jpg) · Codex In-app Browser · 1304×892
- [iss001-overdue.jpg](iss001-overdue.jpg) · Codex In-app Browser · 1304×892
- [iss004-no-plan.jpg](iss004-no-plan.jpg) · Codex In-app Browser · 1289×882
- [iss004-usd340.jpg](iss004-usd340.jpg) · Codex In-app Browser · 1289×882
- [iss005-paid.jpg](iss005-paid.jpg) · Codex In-app Browser · 1304×892
- [iss006-consumed-rejected.jpg](iss006-consumed-rejected.jpg) · Codex In-app Browser · 1304×892
- [iss006-manual-reversed.jpg](iss006-manual-reversed.jpg) · Codex In-app Browser · 1289×882
- [iss006-overage.jpg](iss006-overage.jpg) · Codex In-app Browser · 1304×892
- [iss006-shipment-reversed.jpg](iss006-shipment-reversed.jpg) · Codex In-app Browser · 1304×892
- [iss054-after.jpg](iss054-after.jpg) · Codex In-app Browser · 1304×892
- [iss054-before.jpg](iss054-before.jpg) · Codex In-app Browser · 1304×892
