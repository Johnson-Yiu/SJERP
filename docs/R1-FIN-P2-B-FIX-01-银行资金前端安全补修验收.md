# R1-FIN-P2-B-FIX-01 银行资金前端安全补修验收

日期：2026-10-19  
基线：`47c9f20ad4e9643c22c62bc93e4ffcb0a38d905f`  
范围：仅修复银行资金前端预览、未保存保护、来源人工核实和异步来源请求；不改变 P2-A 资金计算、历史金额、核销、报表来源或权限策略。

## 1. 独立审查发现与修复

| Issue | 根因 | 本轮处理 | 状态 |
|---|---|---|---|
| ISS-110 | 预览成功后修改金额、日期、手续费、来源或凭证仍可沿用旧结果登记 | `CashEventPage.vue` 对完整规范化请求生成稳定指纹；深度变更立即清除预览，登记前再次比较；服务端仍重新校验 | `FIXED_PENDING_REVIEW` |
| ISS-111 | 预览调用 `markClean`，未登记输入被当作已保存 | 预览不再清洁表单；只有登记、查询、确认或放弃完成后清洁。24小时本地快照恢复请求键、表单和来源分配，不保存银行登录凭据 | `FIXED_PENDING_REVIEW` |
| ISS-112 | 选择来源时自动发送 `verified=true`，缺少逐条人工核实 | 每条来源增加核实勾选；未逐条核实不能预览/登记；登记后复核摘要要求显式确认，已确认事件只读 | `FIXED_PENDING_REVIEW` |
| ISS-113 | 币种切换时旧来源请求可能覆盖新结果 | 请求序号、AbortController、币种一致性检查和失败保留输入；旧响应被丢弃 | `FIXED_PENDING_REVIEW` |
| ISS-114 | 历史全量记录为139通过/8失败，原因未分类 | 原8项在当前精确工作区单独复现为8通过；最终完整套件和新增用例通过，保留历史日志待独立复核 | `NEEDS_VERIFICATION` |

ISS-105 仍为 `OPEN`，ISS-108 仍为 `BLOCKED`，ISS-109 仍为 `FIXED_PENDING_REVIEW`；本轮没有关闭任何 Issue。

## 2. 实际操作矩阵

| 步骤 | 证据类型 | 结果 |
|---|---|---|
| 隔离 SQLite 迁移、合成客户/订单/两笔 USD 来源、合成银行账户与凭证 | `FIXTURE_SETUP` | 仅使用 `r1-fin-p2-b-fix-01-isolated.sqlite3` |
| 新建、选择两条来源、填写 USD100/CNY705、凭证和账户 | `REAL_UI_ACTION` | 真实 Chromium + Vite/API 页面完成 |
| 未逐条核实直接预览 | `REAL_UI_ACTION` / `REAL_API_OBSERVATION` | 页面提示“请逐条核实来源流水后再预览”，无预览请求写入 |
| 两条来源分别核实后后端预览 | `REAL_UI_ACTION` / `REAL_API_OBSERVATION` | HTTP 预览成功，来源合计 USD100、银行净额 CNY705，额度未占用 |
| 修改银行净额 705→706 | `REAL_UI_ACTION` | 旧预览立即消失，提示“旧预览已失效”；重新预览后才可登记 |
| 登记待确认草稿 | `REAL_UI_ACTION` / `REAL_API_OBSERVATION` | 返回稳定事件编号和请求键；完整审查摘要显示日期、参考号、凭证、账户、净额、手续费、原币总额及逐条分配 |
| 不勾选最终核对 | `REAL_UI_ACTION` | “确认银行凭证”保持禁用 |
| 勾选最终核对并确认 | `REAL_UI_ACTION` / `REAL_API_OBSERVATION` | 事件变为已确认；详情无覆盖/删除入口 |
| 刷新草稿 | `MOCKED_TEST` | 既有请求键和金额由本地临时快照恢复；真实页面流程的请求键回查保留原入口 |
| 币种快速切换、旧请求延迟返回 | `MOCKED_TEST` | 旧 USD 响应不能覆盖当前 CNY 来源；新增 Playwright 用例通过 |

真实截图和 HTTP 状态见 [`docs/uat-evidence/r1-fin-p2-b-fix-01/`](uat-evidence/r1-fin-p2-b-fix-01/)。1440 视口包含新建、来源选择、核实拒绝、预览、失效、待确认、确认和确认后列表；1280/1024 包含真实列表与详情。所有图片均由真实 Chromium 访问隔离 API 生成，不使用 mock 截图冒充页面证据。

## 3. 数据库核对

`database-after.json` 显示隔离库含 2 个合成订单、4 条原有交易、2 个银行资金事件和 4 条来源分配。两次资金事件分别由 USD30+70 来源组成，结汇只新增 `RmbCashEvent` 与 `CashSourceAllocation`，没有新增客户收款、应收核销或库存记录。首个合成订单的历史快照在 `fixture-legacy-before.json`；后端测试另验证旧模型哈希和旧四位金额未改变。

## 4. 自动回归

| 检查 | 结果 | 原始日志 |
|---|---:|---|
| Node `npm run test:unit` | 134/134 PASS | `node-unit.log` |
| Vitest 完整 jsdom（排除单独 Node typography） | 63 文件、633/633 PASS | `vitest-full.log` |
| Vitest 交易单位 | 4/4 PASS | `vitest-trade-units.log` |
| Vitest Phase2A 页面回归 | 22/22 PASS | `vitest-phase2a-list-shell.log` |
| 定向银行资金 Playwright | 4/4 PASS | `playwright-cash-events.log` |
| 完整 Playwright（最终代码） | 151/151 PASS | `playwright-full.log` |
| Backend SQLite | 764 PASS、13 SKIP、0 FAIL | `backend-sqlite.log` |
| Frontend Build | PASS，2003 modules；保留既有大 chunk 警告 | `frontend-build.log` |
| Backend PostgreSQL | 本地 BLOCKED | `backend-postgresql.log` |

完整套件覆盖原147项基础用例及本轮4项银行资金用例。历史139/8日志仍保存在上一轮证据目录；本轮原8项定向复现全部通过，没有删除或跳过失败测试。当前环境没有隔离 PostgreSQL 服务，`DATABASE_URL`/`POSTGRES_URL` 为空且无 docker/psql，因此没有连接任何真实数据库；PostgreSQL 结果必须以精确 HEAD 的 CI 为准。

## 5. 精确 HEAD CI

本轮推送后的精确 HEAD 为 `f4c1f1ede6eb74ada2fc19daa4ea14a28d363d2a`，GitHub Actions 运行 `39208527003` 已完成，三个 job 均为 SUCCESS：

- [Backend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39208527003/job/117916532420)
- [Backend PostgreSQL](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39208527003/job/117916532143)
- [Frontend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39208527003/job/117916532208)

运行总览：[CI #39208527003](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39208527003)。CI 包含后端 SQLite、PostgreSQL、Node/Vitest、Chromium 布局回归及构建；GitHub 记录的 Node.js 24 强制运行和 Ubuntu 迁移提示属于环境注记，不是失败。

## 6. 遗留边界

- P2-A 的 Decimal、来源额度、事务和后端权限校验未改；前端不自行计算或覆盖银行事实。
- ISS-108 的退款/更正和未知来源仍安全拒绝，未在本轮扩展业务规则。
- 本轮不改变既有财务统计口径，不开发 P2-C、正式 RBAC、员工 UAT 或部署。
- 等待 ChatGPT 对代码、真实截图、隔离数据库和精确 HEAD CI 的独立复审；`FIXED_PENDING_REVIEW` 不自行转为 `CLOSED`。
