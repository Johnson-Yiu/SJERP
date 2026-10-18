# R1-FIN-P1 现有财务统计口径澄清验收

日期：2026-10-18。基线：`ad3a08ebd47ad4b94ffe8f6ebfed5f083b9ac57e`。

本轮只澄清既有统计的名称与说明，不实现银行实际人民币到账统计。ISS-105保持OPEN，等待后续业务决定及另行授权；本轮代码与视觉结果待ChatGPT独立复审。

## 前置与隔离

完整读取[P0准备](R1-FIN-P0-财务统计口径确认及实施准备.md)、[原审查](R1-FIN-AUDIT-01-财务统计与结汇兼容性审查.md)、问题台账、AGENTS及相关模型、finance/profit/reporting/views/序列化、页面和测试。基线三项CI均SUCCESS：[Backend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39135593292/job/117699334407)、[Backend PostgreSQL](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39135593292/job/117699334243)、[Frontend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39135593292/job/117699334384)，均对应上述SHA。

从最新origin/master建立`.worktrees/r1-fin-p1`隔离工作区；主工作区的历史未提交修改保留。真实页面使用独立SQLite `r1-fin-p1-isolated.sqlite3`、Django 8136、Vite 5206；没有使用主工作区业务库。为避免执行本轮未授权迁移，从上一轮已知可销毁合成库以SQLite只读backup复制，并核对唯一客户代码FUP02-C。额外合成流水由现有服务创建，不直接修改余额；见[准备脚本](uat-evidence/r1-fin-p1/setup_fixture.py)及fixture.log。真实页面只读取、打开/取消表单和导出，没有提交收付款。

## 统一口径

> 账面人民币折算参考：已确认流水按既有人民币金额及流水汇率汇总，包含原币为CNY的既有流水；不代表银行实际到账、已完成结汇或银行账户余额。流水发生日期不等同于银行到账日。

| 区域 | 本轮修改 | 保持不变 |
|---|---|---|
| 财务概览 | 合同销售额、账面收入/支出/净收支（折算参考）；区分当前待结与未核销、预计利润；月度及分类标题、空状态、导出名 | 数值、期间、当前余额范围、合同/预收预付折算算法 |
| 财务流水 | 原币收付款说明、人民币折算参考列、页面小计、流水发生日期、参考折算汇率及单位说明 | 提交请求、汇率默认、输入精度、保存/重试/核销/退款逻辑 |
| 应收应付计划 | 汇总按合同汇率折算参考；登记表单流水发生日期/参考汇率，明确不表示结汇或银行到账 | 原币核销、金额及余额、权限 |
| 报表中心 | cash来源名称、日期说明、指标选择、图表与表格表头、默认预设标题和导出表头 | source=cash、预设ID、查询参数、行/总额/比较及筛选规则 |
| 经营概览/共享流水显示 | 直接引用同一cash口径说明，关联人民币列名同步 | 销售、订单利润、库存成本及其他来源算法 |
| API | finance-dashboard新增cash_basis；cash catalog/data新增basis/version，替换展示label/note | 所有旧键、类型、URL、权限与数据范围 |
| CSV | 两类标题、说明与人民币参考列名一致；概览首行追加说明列 | 数据行金额、分类、日期位置、顺序、服务器文件名、CSV安全转义 |

新增元数据：`basis=book_rmb_reference`、`version=1`。概览`cash_basis`还提供`date_basis=transaction_date`、`includes_cny=true`及note。非cash报表不增加cash元数据。前端保留旧API无cash_basis时的口径说明fallback；旧保存的cash自定义标题不重写，其下恒显新的参考口径。cash-trend/cash-category ID及本地保存结构不变。

`income_rmb`、`expense_rmb`、`net_cash_rmb`、`rmb_amount`等API键为兼容保留，不能仅按英文键推断为银行事实。CSV展示标题有意改变，依赖旧中文标题逐字解析的外部脚本应更新；本仓库报表配置/导出请求不依赖这些标题。服务端CSV文件名保持原值，概览浏览器下载名改为账面收支参考。

## 金额、记录与计算验证

同一合成库在修改前、修改后运行只读[capture.py](uat-evidence/r1-fin-p1/capture.py)，保存原始API JSON及两类CSV，再由[verify.py](uat-evidence/r1-fin-p1/verify.py)使用Decimal精确比较。Django APIClient属于真实应用API的进程内观察，不冒称浏览器HTTP；另有8136实际HTTP原始响应及状态记录。

| 指标 | 修改前 | 修改后 |
|---|---:|---:|
| income_rmb | 7988.0 | 7988.0 |
| expense_rmb | 391.9034 | 391.9034 |
| net_cash_rmb | 7596.0966 | 7596.0966 |
| 合同销售额 | 12780.0 | 12780.0 |
| 预计订单利润 | 12780.0 | 12780.0 |
| 当前应收折算 | 1704.0 | 1704.0 |
| 当前应付折算 | 7100.0 | 7100.0 |

月度、分类、预收预付、其他指标、cash/sales/profit报表的行/总额/同期/变化及全部流水JSON精确一致；两类CSV逐个数字单元格一致。全部CRM模型按主键排序的记录快照SHA256前后均为：

`c53801801f2a7732ee2ed56f5677c100664c0e8756a6245a212ddbb6a976a561`

详见before.json、after.json、verification.log及before/after CSV。真实HTTP：概览JSON、概览CSV、cash CSV均200，原始文件和Content-Type/Content-Disposition/哈希见[http-observations.json](uat-evidence/r1-fin-p1/http-observations.json)。UI显示两位小数是既有格式；原始四位金额没有截断或改写。

新增后端Decimal用例另覆盖USD收入10×7.123456、CNY100、EUR10×7.8既有0值fallback、USD支出2.34对应16.6689及作废流水排除，准确得到收入249.2346、支出16.6689、净额232.5657、合同189。fallback仅验证现状，本轮不修算法或认定历史数值正确性。

models、migrations、services/finance、services/profit及其他业务服务均未修改。reporting聚合/记录生成及Transaction序列化金额计算未改；仅增加口径元数据或展示标签。不存在新银行事实、精度变更、历史补写、结汇核销或会计政策变更。

## 真实操作与截图

操作明细与限制见[ui-operations.md](uat-evidence/r1-fin-p1/ui-operations.md)，原图索引/尺寸/哈希见[screenshots.json](uat-evidence/r1-fin-p1/screenshots.json)。截图均来自隔离真实API页面，未使用mock；自动浏览器测试单独标记MOCKED_TEST。

| 分类 | 操作 | 观察 |
|---|---|---|
| FIXTURE_SETUP | 复制已知合成库、现有服务新增CNY/USD/EUR及作废记录 | 准备数据不作为UI业务验收 |
| REAL_UI_ACTION | 内置浏览器及Chrome打开财务概览 | 合同/预计利润/应收应付/账面参考分开；CNY与日期说明可见 |
| REAL_UI_ACTION | 打开财务流水、新增记账后取消 | 原币/参考人民币列及参考汇率说明正确；没有记账写入 |
| REAL_UI_ACTION | 旧标题cash配置打开报表、导出CSV | 旧查询和自定义标题有效，新的来源/指标/表头/note清楚；CSV生成反馈正确 |
| REAL_UI_ACTION | Chrome应收计划登记表单打开后取消 | 日期与汇率说明一致，原币待结40未变 |
| REAL_UI_ACTION | Chrome经营概览滚动到账面收支 | 相同说明和金额，无实际银行资金暗示 |
| REAL_API_OBSERVATION | 实际HTTP GET两个CSV及概览 | 200，原始响应留档 |
| DATABASE_VERIFICATION | 全部CRM记录快照、API/CSV Decimal比较 | 无记录、金额变化 |
| MOCKED_TEST | Vitest/Playwright无权限/旧响应/旧配置/失败及尺寸回归 | 与真实UI证据分别报告，不将模拟当作真实银行业务 |

Chrome初期导航/CDP截图曾超时，最终恢复：通过原生截图接口保存真实Chrome可见区域，内置浏览器保存全页补充。没有伪造精确视口或把自动化mock截图混为真实页面。原图已人工检查文字、表头和布局。

## 自动回归

| 套件 | 本地结果 | 原始证据 |
|---|---|---|
| Backend SQLite | 740项，OK，10 skipped | backend-sqlite.log；skip为既有环境相关分支 |
| 新增后端针对性 | 3项PASS | backend-targeted.log |
| Node | 132项PASS | node.log |
| Vitest | 63文件633项PASS | vitest.log |
| 最后文案/导航回归 | 9项及新增口径3项PASS | frontend-final-targeted.log、frontend-report-final.log |
| Playwright | 全量147项PASS；最终表头增强后2项PASS | playwright.log、playwright-final-targeted.log |
| Typography | 1项PASS | typography.log |
| Frontend Build | PASS，既有大chunk提醒 | build.log、build-final.log |
| Backend PostgreSQL | 本地无PG实例，不伪报本地通过；由最终HEAD GitHub任务执行 | 最终交付CI链接 |

新增用例覆盖：精确金额及CNY包含、两类CSV表头/note/原值、元数据兼容、非cash不受影响、旧API fallback、流水汇率默认值、旧自定义cash查询和有符号金额、图表/选择/表格标签及1440/1024无主区域溢出。现有全量权限与财务重试测试继续执行，无新增账号或RBAC开关变更。

## 遗留与交付边界

1. **ISS-105 OPEN**：缺少银行实际人民币资金/结汇事实，本轮仅消除现有公开统计的误称，不宣称彻底修复。不自动执行P0待决政策或P2开发。
2. **ISS-107 P2/BLOCKED**：模型rmb_amount verbose_name及历史迁移仍有旧称；API键和用户自定义标题为兼容保留，已提供清晰口径说明。后续需明确授权后评估元数据迁移；不得重写历史迁移或金额。本轮扫描公开运行页面/报表旧误称只剩模型元数据。
3. 现有四位小数、拆分尾差、0值fallback、合同/流水多汇率和历史来源不明仍按原审查保留。本轮一致性不等于证明银行实收或历史业务正确。
4. 新文案与原图尚待独立代码和视觉复审；其他Issue状态保持，不进入正式RBAC、员工UAT或部署。

本报告、原图、原始测试日志、API/CSV和脚本同提交推送master。最终完整SHA及该精确HEAD的Backend、Backend PostgreSQL、Frontend运行URL/结论记录在最终交付消息及审查包`FINAL-DELIVERY.md`；推送前本地测试不代替精确HEAD CI。报告所引用基线CI仅为前置核验，不作为本轮最终CI。
