# ISS-048 测试结果

| 类别 | 命令/范围 | 结果 |
|---|---|---|
| 后端下钻 | `crm.tests.test_finance_drill` | 7 passed |
| 财务/RBAC定向 | `test_finance`, `test_finance_data_scope`, `test_finance_reference_basis`, `test_actual_cash_reporting` | 65 passed |
| SQLite 全量 | `python manage.py test --keepdb`，临时 `MEDIA_ROOT` | 808 passed, 13 skipped |
| 前端 Node 单元/静态 | `npm run test:unit` | 143 passed |
| 前端财务 Vitest | `finance-reference-basis.spec.js`, `finance-contract-navigation.spec.js` | 12 passed |
| 完整 Vitest 尝试 | `npx vitest run --environment jsdom` | 63 passed；仓库将 42 个 Node `node:test` 文件同时匹配为 Vitest suite，因无 `describe/it` 报告失败；另有 1 个既有侧栏历史订单顺序断言失败，均与 ISS-048 无关，原始输出见 `frontend-vitest-full.log` |
| 前端生产构建 | `npm run build` | passed；仅保留既有大 chunk warning |
| 新财务 Chrome | `finance-drill.spec.js`，Chromium，1440/700 | 2 passed |
| 既有财务/报表 Chrome | finance reference/resilience、overview reports、ISS-041-B evidence | 21 passed；银行空链接保护后财务回归另 4 passed |

首次 SQLite 全量在工作树默认 `MEDIA_ROOT` 下有 1 个附件测试因 Codex C: 工作树 ACL 无法创建 `backend/media`；改用系统临时 `MEDIA_ROOT` 后全量通过。该环境性问题不涉及 ISS-048 业务逻辑。

前端项目的可执行 Node 单元入口是 `npm run test:unit`（143 passed），财务 Vue 交互通过定向 Vitest 12 项；没有把混合测试 runner 的全量 Vitest 失败伪报为本轮功能失败，也没有修改无关侧栏断言。

浏览器说明：Chrome 测试使用真实 Chromium；ISS-048 新增浏览器测试的 API 是 mock route，不能代替真实 Django 跨账号浏览器集成。真实后端权限/范围由 Django APIClient 定向测试覆盖；跨账号浏览器服务账号待集成环境提供。
