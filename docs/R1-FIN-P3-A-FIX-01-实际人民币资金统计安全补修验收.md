# R1-FIN-P3-A-FIX-01 实际人民币资金统计安全补修验收

日期：2026-10-19  
基线：`470eb34e161d97f68ff8a1151870a6ab687f32ea`  
范围：财务概览实际资金接口容错、日期请求竞态、实际资金 CSV 文本安全。  
边界：不修改 P2-A 资金事实/结汇计算、旧 Transaction 金额、核销、历史数据、统计启用日期或 D01–D08 口径。

## 判定

本轮两个缺陷均已在隔离环境完成最小修复并有自动回归和真实页面证据，状态按台账登记为 `FIXED_PENDING_REVIEW`，等待 ChatGPT 独立代码、财务口径和视觉复审。ISS-105 继续 `OPEN`；ISS-108、ISS-121 继续 `BLOCKED`，未关闭其他 Issue。

## 根因与修复

### 财务概览独立容错（ISS-122）

原 `FinanceDashboardPage.vue` 用 `Promise.all` 同时等待 `/finance-dashboard/` 与 `/actual-rmb-cash/`。实际资金接口失败时，旧财务概览也进入失败态；日期快速切换时，旧响应可能写入新期间。

修复将旧概览请求和实际资金请求拆开：旧概览保持原错误/重试行为，实际资金拥有独立加载、错误和“重新加载”入口；启动新期间时清空旧实际资金，避免把旧期间金额当作当前期间。`loadVersion` 保护旧概览响应，`actualCashVersion` 保护实际资金响应、错误和加载状态。启动顺序先建立旧概览请求，保持既有 API mock/调用契约兼容；服务端仍重新返回完整统计结果。

### CSV公式注入保护（ISS-123）

`backend/crm/actual_cash_api.py` 原先直接把银行参考号和事件文本写入 CSV。现改为复用 `crm.reporting.safe_csv`，保护说明、表头、事件编号、类型、方向、银行参考号和汇总标签。危险前缀会增加单引号，正常银行参考号仍保持可读；JSON API、数据库原文和报表中心既有金额/字段不改变。报表中心已有 CSV 同样复用该保护函数，本轮增加实际资金端点回归以证明边界。

## 实际操作矩阵

| 场景 | 证据类型 | 结果 |
|---|---|---|
| 正常隔离财务概览 | `FIXTURE_SETUP` + `REAL_UI_ACTION` + `REAL_API_OBSERVATION` | 合成确认事件 `P3A-FX-705`，银行净额 ¥705.00；旧账面折算参考同时显示，未混入实际资金。 |
| 实际资金接口返回失败 | `MOCKED_TEST` + Playwright | 旧概览仍显示合同/账面指标；实际资金区域显示接口错误与独立重试。 |
| 独立重试恢复 | `MOCKED_TEST` | 点击实际资金区域“重新加载”后返回 ¥705.00，旧概览不重新依赖实际资金接口。 |
| 快速切换日期 | `MOCKED_TEST` + Playwright | 延迟旧期间响应返回后不覆盖新期间 ¥200.00；当前区域只保留新日期。 |
| 真实三视口页面 | `REAL_UI_ACTION` | 1440、1280、1024 均加载实际资金区域、银行事件明细和旧账面参考区域。 |
| CSV危险文本 | `REAL_API_OBSERVATION` + Backend test | `=HYPERLINK(...)` 导出为单引号保护文本；正常事件编号保留；API/数据库原文未改。 |
| 权限不足 | `AUTOMATED_TEST` | 实际资金 JSON 与 CSV 均返回 403；不泄露金额或事件。 |
| 报表中心CSV | `CODE_REVIEW` + 既有回归 | 继续使用 `safe_csv`；本轮未改变报表统计来源或金额。 |

## 数据与口径核对

- 实际资金仍只统计服务端 `status=confirmed` 的 `RmbCashEvent.bank_net_amount`，按 `bank_date` 汇总；含扣手续费不重复扣减。
- 本轮未新增模型、迁移、银行账户余额、结汇计算或启用日期配置。
- 正常真实 HTTP 日志记录：`/api/actual-rmb-cash/` 和 `/api/finance-dashboard/` 在 1440/1280/1024 均为 200；页面实际流入 ¥705.00、事件 `P3A-FX-705`、银行参考号 `SYNTH-BANK-REF` 一致。
- 不可见来源的聚合保护和现有服务端权限未改；实际资金权限测试覆盖 API 与 CSV 两条入口。

## 自动化结果

- Backend SQLite：768 tests，skipped=13，`OK`。
- Backend actual cash 定向：4 tests，`OK`（恶意参考号、权限 JSON/CSV、现有报告）。
- Node：136/136 passed。
- Vitest：63 files / 635 tests passed，命令为 `npx vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js`。
- Playwright：157 passed（含本轮实际资金接口失败/重试和日期竞态 2 项）。
- Frontend Build：Vite SUCCESS。
- 本机未启动独立 PostgreSQL 服务；Backend PostgreSQL 需以最终精确 HEAD 的 GitHub CI 为准，未将 SQLite 结果冒充 PostgreSQL。

## 证据清单

目录：[docs/uat-evidence/r1-fin-p3-a-fix-01](uat-evidence/r1-fin-p3-a-fix-01/)

- `real-browser-finance-1440.png`、`real-browser-finance-1280.png`、`real-browser-finance-1024.png`：真实隔离 API/数据库页面。
- `real-browser-http.log`：三视口 HTTP 状态及银行资金区域文本。
- `backend-sqlite-full.log`、`backend-actual-cash-fix.log`：后端完整及定向日志。
- `vitest-full.log`、`node-unit.log`、`playwright-resilience.log`、`playwright-full.log`、`frontend-build.log`：前端自动化和构建原始输出。
- `capture_real_browser.mjs`：截图采集脚本，未访问真实业务数据库。

## 遗留与审查边界

ISS-121 的统计启用日期和全公司覆盖政策仍待财务负责人决定；本轮不填日期、不推测期初/期末余额。ISS-105、ISS-108、ISS-121 不因本轮代码或测试通过而关闭。页面控制台仍可见既有 RouterLink/Transition 警告，它们不阻断本轮数据加载，未扩大为本轮业务修改。

## 最终交付

实现提交：`5c66574bec80301c61d64d4c0cdf4862d8fc8fcf`。

该精确 HEAD 的 GitHub Actions 三项 CI 均为 SUCCESS：

- [Backend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39247654695/job/118043416984)
- [Backend PostgreSQL](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39247654695/job/118043417446)
- [Frontend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39247654695/job/118043417390)

运行总览：[master CI 39247654695](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39247654695)。本节为验收证据回写，不改变实现代码、财务口径或历史数据；完成后停止等待 ChatGPT 独立复审，不进入 P3-B、正式 RBAC、员工 UAT 或部署。
