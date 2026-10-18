# R1-FIN-P2-B 银行结汇及人民币实际资金前端验收

日期：2026-10-19。基线：`b79af36dc7140507ef210ea61437dd579ba8de8b`。本轮只开发人民币实际资金前端，复用R1-FIN-P2-A后端API；不修改旧财务统计来源、Transaction/PaymentPlan金额、核销、报表、权限策略或历史记录。ISS-105继续OPEN，ISS-108继续BLOCKED，ISS-109继续FIXED_PENDING_REVIEW。交付后停止等待ChatGPT独立代码和视觉复审，不进入P2-C、正式RBAC、员工UAT或部署。

## 前置与隔离

基线精确HEAD的三项CI均为SUCCESS：

| 检查 | 结果 | URL |
|---|---|---|
| Backend | SUCCESS | [job 117726240523](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39144762344/job/117726240523) |
| Backend PostgreSQL | SUCCESS | [job 117726240492](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39144762344/job/117726240492) |
| Frontend | SUCCESS | [job 117726240331](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39144762344/job/117726240331) |

使用独立工作区 `C:\Users\Johnson\.codex\worktrees\r1-fin-p2-b\森爵照明管理系统`、独立数据库 `backend/r1-fin-p2-b-isolated.sqlite3`、合成客户/订单/收款流水及合成银行凭证。数据库脚本拒绝已有Customer记录，且明确断言资金事件初始为0；未连接真实业务数据库。受控账户仅为 `SYNTH-FX-01` 与 `SYNTH-CNY-01`，凭证文件标记为 `SYNTHETIC_BANK_VOUCHER_NOT_REAL`。

## 实现范围

- 新增 `CashEventPage.vue`，提供银行资金事件列表、状态筛选、搜索、只读详情和来源快照展示。
- 新建事件分为“事件与银行金额 / 银行凭证与受控账户 / 来源分配”三步表单；先调用后端 `/preview/`，预览成功后才能登记待确认草稿，再单独确认凭证。
- 事件编号与稳定请求键在表单初始化时生成并持续保留；保存结果不明时显示回查入口，禁止静默生成新键。
- 来源可用额度由后端返回；未知额度显示“待核对”并禁用选择。历史来源若保留四位小数，要求用户按币种精度明确填写，前端不自动舍入或截断。
- 确认、放弃和详情均为只读/留痕操作。确认后不提供覆盖或删除入口；放弃要求原因并保留来源和凭证快照。
- 在财务概览、财务流水和主导航增加人民币资金入口；原有概览及报表金额没有接入新事件。
- 新增Node单测与Playwright UI流程回归；更新侧栏回归预期。

## 实际业务操作矩阵

| 分类 | 操作 | 结果与证据 |
|---|---|---|
| FIXTURE_SETUP | 新建USD100订单、两笔USD30/70应收计划和30/70拆分流水；建立合成银行账户与凭证文件 | `fixture.json`、`fixture-legacy-before.json`、`synthetic-bank-voucher.json` |
| REAL_UI_ACTION | 在真实内置浏览器打开 `/rmb-cash-events`，填写CNY705净到账、参考汇率7.100000、账户、银行参考号和凭证SHA；选择两笔来源 | 页面显示来源分配30.00+70.00；旧四位候选被要求人工输入 |
| REAL_API_OBSERVATION | 点击“后端预览” | HTTP 200；页面显示“来源合计 USD 100.00，银行净额 CNY 705.00”；预览不占额度 |
| REAL_UI_ACTION | 登记待确认草稿，点击关闭/放弃，填写放弃原因 | 列表显示“已放弃”；页面提示保留审计留痕，未伪造银行回款 |
| REAL_UI_ACTION | 重新登记同一合成来源，预览后确认银行凭证 | 列表和详情显示“已确认”、CNY705.00、USD100.00、两条来源快照 |
| REAL_API_OBSERVATION | 确认返回后刷新列表并打开详情 | 已确认事件只读；参考折算CNY710.00与差额-5.00标为“仅供信息对照” |
| REAL_API_OBSERVATION | 使用已确认事件的原稳定请求键重放，并用同键改银行参考号制造冲突 | 原请求返回HTTP 200且事件数仍为2；改内容返回HTTP 409，未增加流水或资金事件；见 `idempotency-observation.json` |
| DATABASE_VERIFICATION | 查询订单、计划、原始Transaction、RmbCashEvent和CashSourceAllocation | 订单/计划/原流水保留；2个事件（1 cancelled、1 confirmed）和4条来源快照；无第二笔客户收款、无重复核销 |
| MOCKED_TEST | Playwright中控制API响应验证预览→登记→确认界面序列 | `frontend/browser-tests/cash-events-p2b.spec.js`，1 passed |

金额、币种、受控账户和权限校验仍由P2-A服务端完成；前端的合计仅作操作提示，不能替代后端Decimal预览。未开发银行账户余额、自动导入、自动汇兑损益或更正/退款解锁流程。

## 页面与视觉证据

真实浏览器内置标签完成了待确认、放弃、重新登记和确认流程。隔离页面截图在 [截图清单](uat-evidence/r1-fin-p2-b/SCREENSHOTS.md)；列表与详情分别按1440、1280、1024视口保存。截图等待业务内容加载完成后采集，详情页显示银行净额、原币来源、手续费、参考差异、请求键和来源快照。

截图文件：

- `real-ui-list-1440.png`、`real-ui-detail-1440.png`
- `real-ui-list-1280.png`、`real-ui-detail-1280.png`
- `real-ui-list-1024.png`、`real-ui-detail-1024.png`

## 自动化与回归

- `npm run test:unit`：134 passed。
- `npm run test:trade-units`（Vitest + jsdom）：4 passed。
- `npm exec vitest run tests/phase2a-list-shell.spec.js`：22 passed；新页面Node单测随 `test:unit` 执行，2 passed。
- `npm run test:browser -- browser-tests/cash-events-p2b.spec.js --reporter=line`：1 passed；该用例标注为MOCKED_TEST，真实数据库流程以本报告REAL_UI_ACTION/REAL_API_OBSERVATION/DATABASE_VERIFICATION为准。
- 完整 `npm run test:browser -- --reporter=line`：139 passed、8 failed。失败集中在既有财务重试、R1-A履约应收和R1-FIN-P1统计口径用例，未触及本轮新增页面；原始完整日志保留在 `test-browser-full.log`，本轮新增用例单独通过。
- `npm run build`：SUCCESS。构建仅有既有大chunk提示。
- `python manage.py test`：764 passed、13 skipped（隔离SQLite）；P2-A资金后端测试和既有财务回归未修改。输出含 `P2A-DATABASE_VERIFICATION`，旧记录哈希前后相同，来源使用量和银行净额为Decimal值。

直接执行未带项目环境的 `npm exec vitest run` 会把需要jsdom的历史测试按Node环境执行并出现 `document is not defined`；项目定义的Vitest命令为 `test:trade-units`，该命令已通过。该环境差异不改变Node单测、定向Vitest、Playwright新用例或生产构建结果。

## 兼容、权限与遗留

- 继续复用 `development_superadmin_enabled()` 的开发身份；没有启用正式RBAC或创建员工账号。后端权限/数据范围没有被前端绕过，列表详情由服务端统一返回。
- 不可见来源或未知额度不显示金额，前端不把未知值当作0；受控账户未配置时后端确认会安全拒绝并保留待确认状态。
- 不支持的更正、退款来源不明、已确认事件作废和额度自动释放仍按P2-A安全拒绝，登记ISS-108 BLOCKED，不在本轮扩大。
- ISS-105仍OPEN：本轮没有把银行事实混入财务概览、cash报表或CSV，也没有宣称人民币实际统计已切换。
- 最终提交SHA及该精确HEAD的Backend、Backend PostgreSQL、Frontend CI URL在交付消息中绑定；本报告的基线CI链接用于前置门槛核对。

## 证据目录

`docs/uat-evidence/r1-fin-p2-b/` 包含：合成fixture、凭证及SHA256、数据库前后JSON、后端/前端日志、截图、截图脚本和操作说明。所有记录均为隔离合成数据，未包含真实银行凭据或业务秘密。
