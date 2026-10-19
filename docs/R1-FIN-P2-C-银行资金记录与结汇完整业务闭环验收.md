# R1-FIN-P2-C 银行资金记录与结汇完整业务闭环验收

日期：2026-10-19  
基线：`9cd57800ce524d8e0ead90f245215ac4153cf144`  
范围：使用隔离 SQLite、合成业务记录和真实 Chromium 完成银行资金事实/结汇闭环验收；只修复本轮发现的前端安全边界，不改变 D01–D08、历史财务金额、应收应付核销、库存或既有参考统计。

## 1. 前置核对

基线精确 SHA 的 GitHub Actions run `39213776600` 三项均为 SUCCESS：

- [Backend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39213776600/job/117932817861)
- [Backend PostgreSQL](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39213776600/job/117932817973)
- [Frontend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39213776600/job/117932818072)
- [Run overview](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39213776600)

本轮隔离库为 `backend/r1-fin-p2-c-isolated.sqlite3`，未连接真实业务数据库。合成凭证为 `SYNTHETIC_BANK_VOUCHER_NOT_REAL`，SHA256 为 `89a84663e486a3a14a6ece97bc2ac9038703e60aeaa4189f302f6264a79519fc`。

## 2. 本轮缺陷与修复

| Issue | 根因 | 处理 | 状态 |
|---|---|---|---|
| ISS-118 | 旧版 localStorage 草稿可保留凭证引用、SHA256 和人工核实说明；仅按新白名单读取不足以清除旧原文 | 恢复安全字段后立即以当前版本白名单覆盖快照；敏感字段不落本地且恢复后要求重新填写 | `FIXED_PENDING_REVIEW` |
| ISS-119 | 现有后端要求独立银行手续费关联 `fee_for`，但页面没有可操作的已确认结汇事件选择 | 增加最小已确认结汇事件选择；仍由后端校验关联、额度、权限和事务 | `FIXED_PENDING_REVIEW` |
| ISS-120 | 浏览器数字输入把 `87.60` 序列化为 JS 数字 `87.6`，触发服务端 Decimal 精度拒绝 | 资金净额和手续费在请求体中按规范化字符串发送；后端精度规则不变 | `FIXED_PENDING_REVIEW` |

没有修改 P2-A 后端金额计算或历史数据；ISS-105 保持 OPEN，ISS-108 保持 BLOCKED，ISS-109–117 及其他旧 Issue 状态不变。

## 3. 真实业务操作矩阵

| 场景 | 结果 | 证据类型 |
|---|---|---|
| A. 外币来源 USD60，含扣手续费 CNY3，银行净额 CNY423 | PASS；原币来源仅分配一次，参考差额 -3.00 | `REAL_UI_ACTION` / `REAL_API_OBSERVATION` / `DATABASE_VERIFICATION` |
| B. 同一 USD100 来源分 60/40 两次结汇 | PASS；两笔确认事件分别 CNY426/CNY284 | 真实页面截图及隔离库 |
| C. USD30+70 合并结汇 | PASS；来源不重复占用，银行净额 CNY700，参考差额 -10.00 | 真实页面截图及隔离库 |
| D. 预收款后续核销 | PASS；预收分配保持独立，结汇不重复核销 | 隔离库 `AdvanceAllocation` 对比 |
| E. 银行净额与参考汇率差异 | PASS；差异仅信息展示，不覆盖银行净额 | 真实API/详情 |
| F. 含扣手续费及独立银行扣费 | PASS；独立扣费选择已确认结汇事件，净额合计按方向统计 | 真实页面截图及隔离库 |
| G. CNY 直接收付款 | PASS；CNY金额按银行事实登记 | 真实页面截图及隔离库 |
| H. 待确认草稿确认/放弃 | PASS；历史4位小数来源可预览，放弃后为 cancelled，未产生客户收款 | 真实页面截图及API |
| I. 结果不明/请求键回查 | PASS（稳定请求键回查与同内容重试）；实际断网窗口沿用既有安全回归，未伪造网络成功 | API状态与前端回归 |
| J. 重复、超额及争用 | PASS；同键同内容返回既有结果、同键异内容409、超额409；PostgreSQL并发由精确HEAD CI覆盖 | API及CI |
| K. 已结汇来源退款/作废/替代 | PASS；均安全拒绝400，不释放已确认额度或覆盖原事实 | 真实API |
| L. 历史4位小数、JPY零位 | PASS；历史 `12.3401` 未舍入，JPY `0.1` 被拒绝 | API/数据库 |
| M. 权限、范围和异常输入 | PASS（开发超级管理员范围内的服务端拒绝/数据保护）；正式RBAC场景 BLOCKED，未获授权启用 | 既有后端测试及400响应 |
| N. 刷新、返回、恢复、取消、再次操作 | PASS；真实截图覆盖列表三视口、预览、待确认、确认、放弃；稳定请求键不变 | `REAL_UI_ACTION` |

H 场景为证据采集重试两次，数据库中有 2 条 cancelled 草稿；没有额外 confirmed 事件、客户收款或来源重复分配，报告明确保留该事实。

## 4. 数据库与财务一致性

`verify_p2c.py` 的隔离库结果：10 条原始 Transaction、6 条 PaymentPlan、9 条 RmbCashEvent（7 confirmed、2 cancelled）、10 条 CashSourceAllocation。确认银行净额按方向净额为 CNY `2203.00`；A/C 的参考差异分别为 `-3.00` 和 `-10.00`，不改变实际银行净额。

来源剩余量：`P2C-USD-A-40=40.0000`、历史4位来源 `P2C-USD-HIST-4DP=12.3401`，已确认来源其余为 `0.0000`。预收 `P2C-USD-ADV` 的 `AdvanceAllocation=20.0000` 保持不变。原有模型快照 SHA256 前后均为 `41f898001fcdcb54c39eac2c2a4b4d1db57a3fccce04acbee9c889b5281c0447`，证明 Transaction、PaymentPlan、Order 等旧记录未被结汇覆盖或批量舍入。

## 5. 自动化和环境结果

| 检查 | 结果 | 原始日志 |
|---|---:|---|
| Node `npm run test:unit` | 134 PASS | [`node-unit.log`](uat-evidence/r1-fin-p2-c/node-unit.log) |
| Vitest 完整 jsdom | 63 文件、633 PASS | [`vitest-full.log`](uat-evidence/r1-fin-p2-c/vitest-full.log) |
| Vitest 交易单位 | PASS | [`vitest-trade-units.log`](uat-evidence/r1-fin-p2-c/vitest-trade-units.log) |
| 定向资金 Playwright | 8 PASS | [`playwright-cash-events.log`](uat-evidence/r1-fin-p2-c/playwright-cash-events.log) |
| 完整 Playwright | 155 PASS | [`playwright-full.log`](uat-evidence/r1-fin-p2-c/playwright-full.log) |
| Backend SQLite | 764 PASS、13 SKIP、0 FAIL | [`backend-sqlite.log`](uat-evidence/r1-fin-p2-c/backend-sqlite.log) |
| Frontend Build | PASS | [`frontend-build.log`](uat-evidence/r1-fin-p2-c/frontend-build.log) |
| Backend PostgreSQL | 本机无服务/配置；以最终精确HEAD CI核验 | [`backend-postgresql.log`](uat-evidence/r1-fin-p2-c/backend-postgresql.log) |

本地 PostgreSQL 阻塞原因仅为环境未提供服务或连接配置；没有把 SQLite 结果冒充 PostgreSQL。P2-A 的 PostgreSQL 并发测试和本轮最终 HEAD 的 Backend PostgreSQL CI 是并发与数据库兼容性的正式证据。

## 6. 原始截图和文件清单

证据目录为 [`docs/uat-evidence/r1-fin-p2-c/`](uat-evidence/r1-fin-p2-c/)，包含 A/B/C/D/F/G/H 的预览、待确认、确认/放弃截图，1440、1280、1024 列表截图，合成凭证、fixture、HTTP观察、数据库验证和所有测试日志。截图由真实 Chromium 等待业务内容加载后保存；`README.md` 标注了 `FIXTURE_SETUP`、`REAL_UI_ACTION`、`REAL_API_OBSERVATION`、`DATABASE_VERIFICATION`、`MOCKED_TEST` 和 `BLOCKED` 的边界。

## 7. 未解决问题与停止边界

- ISS-105 仍为 OPEN：本轮新增事实没有混入既有财务概览或报表，不宣称P3实际资金报表完成。
- ISS-108 仍为 BLOCKED：退款/更正/来源解除等未批准业务政策继续安全拒绝。
- ISS-118–120 等待 ChatGPT 独立代码、业务和视觉复审，不自行转为 CLOSED。
- 正式RBAC、员工UAT、生产部署、完整银行账户余额、自动汇兑损益和P3均未启动。

最终精确 HEAD、三项 CI URL 和结果以本报告提交后的交付记录为准。
