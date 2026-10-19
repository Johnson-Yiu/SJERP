# R1-FIN-P3-A 人民币实际资金统计与独立报表验收

日期：2026-10-19  
基线：`c895e1d0d758c1a9c158e940975689dc4b0ae0d6`  
范围：仅实现已确认人民币银行资金事实的只读统计、报表来源、CSV和页面展示；不修改P2-A资金计算、旧Transaction金额、历史数据或银行账户余额。

## 前置核实

P2-C精确基线的三项CI均为 SUCCESS（run `39221758795`）：[Backend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39221758795/job/117958451238)、[Backend PostgreSQL](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39221758795/job/117958451190)、[Frontend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39221758795/job/117958450918)。P2-C报告仍写明等待ChatGPT独立复审；本轮不把等待复审改写成关闭，也不改变ISS-105（OPEN）、ISS-108（BLOCKED）或118–120的状态。测试和页面均使用隔离数据库`.r1-fin-p3-a-isolated.sqlite3`及合成凭证，不连接真实业务库。

## 口径与实现

- 新API：`GET /api/actual-rmb-cash/`，返回`basis=bank_cash_confirmed_v1`、`date_basis=bank_date`、`coverage_status=registered_confirmed_only`和`coverage_configured=false`。仅查询`RmbCashEvent.status=confirmed`，再应用服务端资金可见性和模块权限过滤。
- 统计金额使用`bank_net_amount`，流入为正、流出为负；含扣手续费不再扣减，独立银行扣费作为独立事件统计一次。后端以`Decimal`聚合，旧`cash`来源仍从`Transaction.rmb_amount`提供账面人民币折算参考。
- 返回总流入、总流出、净流量、事件数、按`bank_date`月度趋势、按事件类型分类和逐笔事件摘要。CSV使用“银行实际人民币净额”标题，详情链接回`/rmb-cash-events?event=<id>`。
- 报表中心新增“银行实际人民币资金趋势”和“银行实际资金分类”预设及`actual_cash`数据源。财务概览新增独立“银行实际人民币资金”区域和CSV入口；旧“账面收支（人民币折算参考）”区域保留，未改变旧金额、URL、保存配置或API字段。
- 启用日期没有配置：页面明确显示“已登记银行资金汇总”，不推测未登记资金、期初/期末余额，也不称为利润、销售收入或银行账户余额。

## 实际业务操作矩阵

| 场景 | 证据类型 | 结果 |
|---|---|---|
| A 外币已收、结汇后确认 | FIXTURE_SETUP + REAL_UI_ACTION + REAL_API_OBSERVATION | 合成事件`P3A-FX-705`：USD60来源，银行净额CNY705、含扣手续费CNY5，confirmed后实际流入705。 |
| B 外币分次结汇 | MOCKED_TEST / P2-C回归 | P2-C资金服务回归覆盖分次来源；P3-A统计只读消费确认事件，不重新分配来源。 |
| C 同币种合并结汇 | MOCKED_TEST / P2-C回归 | P2-C服务和来源分配回归覆盖；统计按已确认事件逐笔聚合，避免根行/拆分重复。 |
| D 预收及后续核销 | MOCKED_TEST / P2-C回归 | 统计不访问PaymentPlan核销，不重复占用来源。 |
| E 银行净额与参考汇率差异 | REAL_UI_ACTION + REAL_API_OBSERVATION | 详情显示参考折算与银行净额分开；统计只取银行净额。 |
| F 含扣/独立银行扣费 | MOCKED_TEST / P2-C回归 | 含扣费用不再扣减；独立费用以独立事件计一次。 |
| G CNY直接收付 | MOCKED_TEST / P2-C回归 | 旧业务事件保持，只有新增且确认的RmbCashEvent进入本统计。 |
| H 待确认/已放弃 | AUTOMATED_TEST | `test_actual_cash_reporting`验证非confirmed不进入总额；页面只显示确认明细。 |
| I 跨月份银行日期 | AUTOMATED_TEST + REAL_API_OBSERVATION | 按`bank_date`筛选和月度分组；合成事件落在2026-10。 |
| J 旧账面折算并存 | REAL_UI_ACTION | 财务概览同时显示“银行实际人民币资金”和“账面收支（人民币折算参考）”，数值来源分离。 |
| K 权限/数据范围 | AUTOMATED_TEST + server implementation review | 统计接口先校验模块访问，再逐事件调用`cash.visible`；不可见批次不会参与聚合。正式RBAC仍不在本轮。 |
| L CSV/API一致 | AUTOMATED_TEST | 后端CSV与JSON共用同一确认事件集合和Decimal金额；测试核对705.00及标题。 |
| M 启用日期未配置 | REAL_API_OBSERVATION + REAL_UI_ACTION | `coverage_configured=false`，页面明确不代表全部公司实际资金，不显示余额。 |

## 数据库一致性

`DATABASE_VERIFICATION-after.json`记录隔离库前后核对：旧业务模型集合SHA256均为`cffe9cb0fa1346afccd16ee8ffee76a101d1279007cd0dbd7daf46955e0d7f6a`，`legacy_unchanged=true`；Transaction仍为9条，新增RmbCashEvent 1条（confirmed，银行净额705.00，含扣费5.00，来源USD60.0000），CashSourceAllocation 1条。没有迁移、没有重算Transaction.rmb_amount、没有修改PaymentPlan/AdvanceAllocation/Order/库存。

## 自动化结果

- Backend SQLite：`Ran 766 tests ... OK (skipped=13)`，原始输出见`backend-sqlite-full.log`。
- Node：136/136，见`node-unit.log`。
- Vitest：63 files / 633 tests passed（正确命令为`npx vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js`），见`vitest-full.log`。
- Playwright：155/155 passed（2 workers，真实隔离API代理），见`playwright-full.log`。
- Frontend Build：Vite SUCCESS，见`frontend-build.log`；仅保留既有大chunk warning。
- 新增后端统计测试2/2、前端统计单元/注册测试均包含在上述结果中。
- 本机没有独立PostgreSQL服务；P2-C精确HEAD的Backend PostgreSQL CI已SUCCESS，P3-A最终提交的三项CI需在push后按精确SHA复核。未把SQLite结果冒充PostgreSQL并发验收。

## 真实页面和原始证据

使用Codex内置浏览器（真实HTTP、隔离数据库）检查财务概览、报表中心切换到“银行实际人民币资金趋势”并查询、原始事件详情下钻；另保存1440/1280/1024财务概览截图及1440报表/事件详情截图。文件见`docs/uat-evidence/r1-fin-p3-a/`：

- `finance-dashboard-1440.png`、`finance-dashboard-1280.png`、`finance-dashboard-1024.png`
- `reports-center-1440.png`、`event-detail-1440.png`
- `REAL_API_OBSERVATION-actual-rmb-cash.json`及HTTP日志
- `DATABASE_VERIFICATION-after.json`及日志
- `fixture.json`、`synthetic-bank-voucher.json`、自动化原始日志

证据标签按`FIXTURE_SETUP`、`REAL_UI_ACTION`、`REAL_API_OBSERVATION`、`DATABASE_VERIFICATION`、`MOCKED_TEST`区分；没有用Mock截图代替真实页面。

## 新增/遗留问题

新增ISS-121：实际资金统计启用日期及“公司全部实际资金覆盖范围”尚未由财务负责人确认，因此本轮仅提供“已登记且已确认银行资金汇总”，不填写启用日、不推测期初/期末余额。状态为`BLOCKED`，不得自行关闭。ISS-105仍OPEN（历史统计口径及完整资金事实治理未完全关闭），ISS-108仍BLOCKED，其他Issue状态保持台账原值。P3-A完成后停止，不进入P3-B、RBAC、员工UAT或部署。

## 最终交付

代码与证据提交 SHA：`e951b65f5f5bdde75ce74de0bad9e052ded5810a`。该精确 HEAD 已推送 `master`，三项 CI 均 SUCCESS：

- [Backend job 117985145128](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39229926842/job/117985145128)
- [Backend PostgreSQL job 117985145243](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39229926842/job/117985145243)
- [Frontend job 117985145012](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39229926842/job/117985145012)
- [CI run 39229926842](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39229926842)

后续若仅回写本节文档，属于证据元数据提交，不改变代码、数据库或业务结论；独立复审前不得把本报告或ISS-121标为关闭。

## R1-FIN-P3-A-FIX-01 补修交付

基于精确基线 `470eb34e161d97f68ff8a1151870a6ab687f32ea`，本轮将旧财务概览与实际银行资金统计拆为独立请求，加入请求版本保护和独立错误/重试；实际资金 CSV 复用 `safe_csv` 保护银行参考号等可控文本。P2-A资金事实、旧账面折算参考、历史金额、核销、统计启用日期和权限策略均未改变。ISS-122、ISS-123登记为 `FIXED_PENDING_REVIEW`。完整补修矩阵、三视口真实截图、HTTP与自动化原始日志见[R1-FIN-P3-A-FIX-01补修验收](R1-FIN-P3-A-FIX-01-实际人民币资金统计安全补修验收.md)。
