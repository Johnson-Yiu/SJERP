# R1-FIN-P3-A-FIX-01 证据目录

本目录保存实际人民币资金统计安全与容错补修的原始证据。

- `real-browser-*.png`：隔离 SQLite、真实 HTTP 和真实 Chromium 的财务概览截图，分别对应 1440、1280、1024 视口。
- `real-browser-http.log`：真实浏览器请求的状态记录，数据来自隔离合成数据库，不连接真实业务库。
- `playwright-resilience.log`：实际资金接口失败、独立重试和日期竞态的浏览器回归输出。
- `backend-actual-cash-fix.log`：实际资金 CSV 公式注入及交易权限回归输出。
- `vitest-finance-reference-basis.log`：财务概览失败隔离与过期响应回归输出。

故障注入场景使用 Playwright 路由模拟 HTTP 失败/延迟，仅用于验证前端容错；正常数据场景通过 `127.0.0.1:8103` 隔离 Django API 与 `127.0.0.1:5194` Vite 代理执行。
