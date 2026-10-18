# R1-A-FUP-01 财务重试安全验收

日期：2026-10-18。基线：`f9a9cfb076f581ecb1e2f758b2284fe4dcf525fd`，最新 origin/master 建立独立工作区 `.worktrees/r1-a-fup-01`；主工作区未提交修改不动。

## 结论与根因

ISS-004保持FIXED_PENDING_REVIEW；新增ISS-104为P1 / FIXED_PENDING_REVIEW，等待ChatGPT独立代码及原始截图复审。ISS-001继续BLOCKED，本轮不实施FUP-02；ISS-005/006/054既有范围和状态不变。

旧 `useUnsavedChangesGuard({data:()=>null})` 比较恒定快照，无法识别编辑；首次请求已提交但响应丢失后，虽然同表单编号稳定，关闭重开会静默丢失编号，存在跨表单重复记账风险。原R1-A对应保护通过结论撤回。

修复 `TransactionPage.vue`：比较完整form、订单查询和已选订单；初始化结束后markClean；关闭/取消/遮罩/路由统一进入guard；busy期间禁止关闭、新建重置、修改和重复提交。编号首次提交生成，重试不变，页面显示只读编号。明确校验拒绝与无响应、408、5xx及编号冲突区分；结果不明确保持提示，后续400不能消除前次不确定性。重复编号拒绝不认定为本次成功。主动放弃时显示编号、重复风险及“已记录编号，放弃表单”。成功才清理基线并关闭。

通用guard只增加可选confirmOptions，其他页面默认提示不变。未修改财务服务、唯一约束、核销次序、会计政策、历史单据或余额；不启用RBAC或创建员工账号。

## 操作及证据矩阵

证据目录：[原始记录](uat-evidence/r1-a-fup-01/ui-operations.md)。IAB真实操作，Chrome补充视觉检查；localhost5198→故障代理8128→真实Django8129；数据库独立 `r1a-fup01-isolated.sqlite3`，无真实业务数据。

| 场景 | 分类与结果 | 原始证据 |
|---|---|---|
| A 空白新建取消 | REAL_UI_ACTION：直接关闭无误报；MOCKED_TEST同样通过 | ui-operations.md；transaction-safety.spec.js |
| B 修改后取消/关闭/路由 | REAL_UI_ACTION取消及Chrome关闭有确认；网络异常后路由也有风险确认；遮罩完整矩阵为MOCKED_TEST | 01、06原图；ui-operations.md；Vitest |
| C 保存中所有入口 | MOCKED_TEST：受控pending验证字段、按钮、遮罩、路由、重复提交、beforeunload；不冒充真实网络UI验收 | Vitest、Playwright新增用例 |
| D 未写入拒绝→修正重试 | REAL_UI_ACTION + REAL_API_OBSERVATION：USD合同误选EUR，400；保留编号/订单/金额/汇率/备注/错误，修正USD及21后201，同编号 | 07、08原图；transport-events.jsonl |
| E 提交后响应丢失 | REAL_UI_ACTION + REAL_API_OBSERVATION：其他期间费用USD12.34，真实后端201提交，代理只丢响应，客户端网络失败 | 02原图；transport_proxy.py；transport-events.jsonl |
| F 同号重试拒绝 | REAL_API_OBSERVATION + DATABASE_VERIFICATION：同号400，所有流水/计划逐行一致，不自动报成功 | database-after-lost-response.json、database-after-retry.json；database-retry-check.log |
| G 失败后关闭风险 | REAL_UI_ACTION：取消提示原FIN编号及另建风险；路由相同保护 | 03原图；ui-operations.md |
| H 放弃关闭后继续编辑 | REAL_UI_ACTION：返回核对，原编号及完整输入/错误保留，无新POST | 03原图；ui-operations.md |
| I 成功后下一笔 | REAL_UI_ACTION：成功关闭，下一笔新编号 | 05、08原图；原始HTTP |
| J 同额真实两笔付款 | REAL_UI_ACTION + DATABASE_VERIFICATION：两笔其他期间费用USD2.34，FIN编号不同，各201，各CNY16.6689 | 05原图；database-final.json |

FIXTURE_SETUP：迁移全新数据库；脚本仅创建合成客户、SKU和USD500订单用于D，未改余额。真实UI动作与fixture分开，见fixture-setup.log。E/F/G实际使用无合同期间费用，未依赖模拟API；有合同拆分重放沿用原后端回归覆盖，不宣称本轮真实UI再次覆盖所有分配分支。

## 数据库与金额更正

[最终数据库快照](uat-evidence/r1-a-fup-01/database-final.json)：4条有效流水，结果不明重试不新增；两笔同额付款均保留；订单客户收款USD21，剩余应收479，履约状态仍confirmed。流水原币、汇率、本位币及关联均保留服务端值。比较为逐行JSON及服务端Decimal断言，不以页面两位小数判断账务精度。

原R1-A报告两处笔误改为：USD12.34×7.123456=CNY87.9034；USD2.34×7.123456=CNY16.6689。原始历史database-final.json两条账务本来正确，未修改该文件，SHA与匹配行及Decimal复核见[历史金额核对](uat-evidence/r1-a-fup-01/historical-amount-verification.json)。另以只读SQLite连接核对原数据库两条实际记录，见historical-database-readonly.json，未写入历史库。

## 自动化与完整结果

新增Vitest 10个表单安全测试，后端3个真实API/数据库回归，Playwright1个受控请求及浏览器离开用例。后端覆盖同号不写入、明确拒绝后原号修正、同额两笔不同编号允许，以及Decimal精度。旧R1-A计划拆分/事务回滚测试继续运行。

完整结果及原始日志见本目录：backend-sqlite.log、node.log、typography.log、vitest.log、playwright.log、playwright-targeted.log、build.log。Node121、额外typography1、Vitest620、既有Playwright139通过；新增浏览器1项通过；SQLite729项通过（10项跳过），完整Playwright最终140项结果见playwright-final.log。PostgreSQL通过最终HEAD GitHub CI运行，不将SQLite替代PG。最终提交SHA、三项CI完整URL/结果与CI原始数据随交付汇总及ZIP提供；本报告所在提交即修复提交，避免自引用SHA。

## 范围与遗留限制

浏览器beforeunload使用原生通用提示，浏览器不允许自定义风险文案；表单内持续显示编号/核对提示。Chrome手动reload未取得原生弹窗可观测证据，不记为视觉通过；事件及真实Chromium原生dialog由自动浏览器用例补验。保存中关闭不执行，但用户强制终止浏览器仍非应用可阻止行为。

本次保护不等于全站exactly-once：用户明确记录编号并主动放弃后仍须按编号核对；跨刷新自动恢复、多个标签或外部渠道重复业务识别不在本轮范围。不得按相同金额粗暴去重。无权限沿用既有服务端及前端权限，未改变开发超级管理员约定。

原始截图未经修改，HTTP含真实状态与合成请求/响应，传输故障脚本只影响隔离代理。ZIP含截图、操作、数据库/日志证据与最终交付汇总，供独立审查。交付后停止，不关闭Issue，不进入R1-B、员工UAT、正式RBAC或生产部署。
