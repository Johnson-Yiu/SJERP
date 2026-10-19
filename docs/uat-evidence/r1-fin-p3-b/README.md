# R1-FIN-P3-B 原始证据

本目录只收录隔离 SQLite、合成业务数据和 `127.0.0.1:8104/5195` 真实服务产生的证据。

- `FIXTURE_SETUP`：`p3b-fixture-summary.json`、`p3b-db-snapshot.json`。
- `REAL_API_OBSERVATION`：`p3b-actual-*.json`、`p3b-events.json`、`p3b-report-actual.json`、`p3b-report-actual.csv`、`p3b-legacy-dashboard.json`。
- `DATABASE_VERIFICATION`：`p3b-db-snapshot.json`、`p3b-rejection-check.json`；后者记录关联银行事件时作废/退款拒绝及前后哈希。
- `REAL_UI_ACTION`：`p3b-finance-1440/1280/1024.png`、`p3b-report-actual-1440.png`、`p3b-rmb-cash-events-1440.png`，以及真实浏览器 HTTP/可见文本日志。
- `AUTOMATED_TEST`：Backend 全量/定向、Node、Vitest、Playwright、Build 原始日志。
- `BLOCKED`：本机没有 PostgreSQL 服务，因此真实 PostgreSQL 并发在本机未执行；最终 GitHub PostgreSQL CI 作为交付门槛。真实网络超时注入未对隔离服务实施，既有容错回归结果保留在报告中。

未将隔离数据库文件、银行凭证或任何真实业务数据提交到仓库。