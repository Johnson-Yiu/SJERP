# R1-FIN-P2-C 证据目录

本目录只保存隔离数据库、合成客户/订单/流水、合成银行凭证、真实浏览器操作、HTTP响应、数据库前后对比和自动化测试日志。凭证文件明确标记为 `SYNTHETIC_BANK_VOUCHER_NOT_REAL`。

证据分类：

- `FIXTURE_SETUP`：仅建立合成数据，不等同于UI验收。
- `REAL_UI_ACTION`：真实Chromium访问隔离API的页面操作。
- `REAL_API_OBSERVATION`：真实本地HTTP状态与响应。
- `DATABASE_VERIFICATION`：隔离SQLite/PostgreSQL记录和不变量核对。
- `MOCKED_TEST`：仅用于竞态/断网等无法稳定复现的界面回归，不代替真实写入证据。
- `BLOCKED`：外部环境或未批准业务政策导致的安全拒绝。
