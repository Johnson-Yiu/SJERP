# RELEASE-INTEGRATION-REPAIR-01 补验

2026-11-10。续用分支 `codex/release-integration-repair-01`，起点 `4c01d3be84663d9709b437a4b8fe825f993473d7`。[原验收记录](../release-integration-repair-01/README.md)和原下载文件继续保留。

## 本轮补齐

- 库存调整在发送前把原请求标识和完整提交写入当前浏览器标签页的会话存储，并按账号隔离。响应丢失时，关闭原工作区并重进后可重试原提交；已登记流水重放原结果，不再次入账。确定的业务校验失败允许更正；其他未确认结果继续保留。保护范围是同一浏览器标签页，关闭整个标签页或换设备无法读取这份会话存储。
- 财务概览与历史资料预检在真实 Chrome 的 1366×768、1440×900、390×844 下分别切换原生 100%／125%。由 Chrome 设置页切换，以设备像素比及 CSS 可视宽度复核。使用长客户名、长订单号、四条明细合成样本。390px 放大后有效宽度为 312 CSS 像素，已消除整页横向溢出；宽表仍可在容器内滚动。通过 Chrome CDP 保存原尺寸视口及主要按钮的截图。[测量记录](browser/sales-order-import-real.spec/native-zoom-results.json)。
- 产品证书 400 校验保留“证书名称”等业务字段提示，并保留未保存输入；500 错误仍显示通用提示。
- C 的真实隔离 PostgreSQL 17.11 [恢复演练](../attachments-recovery-hardening-01/final-candidate-pg17-20261110.md)和 [GPG/OpenSSL 加密、解密、签名、保留演练](../attachments-recovery-hardening-01/final-candidate-pg17-crypto-20261110.md)均通过。验证包括数据库和媒体、银行凭证文件、空媒体目录、损坏拒绝、真实锁竞争和审计保护；媒体写入栅栏为模拟，副本在本地。

## 回归命令与结果

- 在 frontend 运行 `npm run test:unit`：197/197 通过。
- 在 frontend 运行 `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js --maxWorkers 4`：87 个文件、818/818 通过。调整旧断言以继续覆盖明确关闭保护、业务字段、历史预检入口、实际付款汇率和幂等标识。
- 浏览器：使用已配置的隔离 codex 真实会话、`ISOLATED_CODEX_TEST_SUPERADMIN=1`、`ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT=docs/uat-evidence/release-integration-repair-01-followup`，运行 `node frontend/scripts/run-isolated-browser-tests.mjs --business-test sales-order-import-real.spec.js`，9/9 通过。包括库存真实写入后丢响应、关闭工作区后原提交重放，以及长证书名称由实际 API 拒绝且输入保留。
- SQLite 全量 `python manage.py test --noinput` 未通过：发现 1751 项，报告运行 1736 项，9 失败、47 错误、118 跳过。旧回退测试试图从合流后的数据库跨过 0120 不可逆保护，一些用例在注册恢复前已经撤掉新字段，引发后续共享库缺列。此外存在本地 Python 缺 PostgreSQL 依赖和旧接口断言。不得把全量结果写成通过，也未关闭这些测试或降低门禁；原三入口前向升级结果不受影响。

## 边界

- 正式目标的媒体 ACL、异地副本、调度和目标库真实历史资料未提供，尚未验收。正式部署、GitHub Actions 与完整打印和分页均未运行。
