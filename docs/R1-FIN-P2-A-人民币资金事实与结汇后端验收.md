# R1-FIN-P2-A 人民币资金事实与结汇后端验收

日期：2026-10-18至19（跨日执行，合成银行发生日固定为18日，不是正式启用日）。基线：`1b2ca0eb5b1947dd53f5ab995828dd33f514e0d4`。本轮仅后端、增量迁移、必要API、安全保护及回归；不开发前端结汇页面，不切换任何报表来源。ISS-105保持OPEN，交付后停止等待ChatGPT独立代码复审，不自动进入P2-B。

## 前置、权限及数据隔离

读取AGENTS、PROJECT_ISSUES、PROJECT_PHASES、REVIEW_PROTOCOL、R1-FIN-AUDIT-01、P0、P1及财务模型、服务、权限和测试。最新origin/master与指定基线一致。基线精确HEAD三项CI SUCCESS：[Backend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39139339195/job/117710334373)、[PostgreSQL](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39139339195/job/117710334636)、[Frontend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39139339195/job/117710334709)。

独立工作区`.worktrees/r1-fin-p2-a`从该远端建立，主工作区未提交内容保留，未重置/清理/强推。每次Django命令显式使用本工作区`backend/r1-fin-p2-a-isolated.sqlite3`；自动测试使用独立测试库。真实HTTP仅8138合成服务。未连接或修改真实业务数据库。

开发超级管理员继续由`development_superadmin_enabled()`统一判定。资金服务/API复用`user_can`、finance_scope、validate_finance_relations。权限矩阵仅在自动测试临时数据库中使用既有fixture和override_settings，不创建正式员工账号、不修改开发权限或启用正式RBAC。

## 已批准规则的实施边界

| 规则 | 本轮实施 |
|---|---|
| D01 | bank_net_amount为独立银行实际CNY净额；含扣手续费仅说明，不再次相减。独立扣费是独立事件，引用现有CNY bank_fee现金行及自己的银行凭证 |
| D02 | 登记pending与凭证人工确认分开；确认要求凭证引用、SHA256、人工核实说明及voucher_checked=true。业务流水confirmed不自动成为银行事实 |
| D03 | 不设启用日；API coverage_since=null，不生成统计覆盖承诺、不自动认证旧CNY流水。历史补证仅逐次明确登记/确认，不批量迁移 |
| D04 | 显式银行实际入账/扣款日期；不取流水日代填。不提供覆盖式更正；原记录、凭证、来源快照保留 |
| D05 | CNY/USD/EUR/GBP/HKD/AUD输入2位，JPY 0位；汇率6位；Decimal、显式ROUND_HALF_UP。超过规定小数位数的输入（含多余尾零）拒绝，旧4位字段与记录不舍入 |
| D06 | 有活动银行事件的源家族不能作废/替代；同往来方同币种有关联银行事件的退款因来源不明拒绝。已出现退款（包括历史作废退款）/替代关系的来源不能自动确认银行事实，不推断现金恢复 |
| D07 | 同币种分次、同币种多行合并及CNY直接收付；同批来源由人工确认来自同一受控来源账户。无完整账户余额/总账、无跨币自动匹配 |
| D08 | 银行净额不被参考汇率覆盖；只展示来源原币×既有汇率的参考差异，不生成汇兑损益或改变订单利润 |

银行凭证SHA256是人工核对的证据引用，不表示系统已从银行验证文件真伪或完成自动对账。API不接收网银密码、登录信息、任意额外字段，不提供凭证下载/上传代理；外部凭证库的访问与保存须后续明确授权。

## 模型与迁移

新增`RmbCashEvent`：唯一event_no/request_key、规范化request_hash/request_payload、类型、来源币种/原币金额、方向、bank_date、bank_net_amount、fee_mode/fee_amount、source_account/rmb_account受控标识、银行参考号、凭证引用/哈希/说明、可选quoted_rate、确认状态/时间、开发或真实认证身份的审计快照、correction_of及fee_for保护关系。

新增`CashSourceAllocation`：事件、具体Transaction行、原币使用量、币种与不可覆盖的源行快照。唯一约束(event,source)、正数约束及PROTECT关系。没有持久化“可用余额”字段；额度从现金行金额减去已确认事件的分配求得。保留4位来源承载能力，但新分配按币种最小单位严格校验。

事件/分配的金额和证据没有更新/删除API。模型save也拒绝覆盖已确认/已取消事件及既有分配；确认和放弃仅允许pending进入终态。数据库直接SQL/bulk update不属于业务接口，本轮不宣称具备生产数据库防篡改权限体系。

`0077_rmb_cash_events`仅CreateModel两表及其索引/约束/关系，没有RunPython、旧表AlterField或金额回写。fresh-migrate.log证明全新合成库从零迁移成功；迁移测试从0076种入12.3401/87.9034/已核销0.0001历史流水，迁移后全部旧模型记录逐条相等、新资金事实为0。该测试也在PostgreSQL CI执行。

账号标识由`RMB_CASH_ACCOUNT_IDS`环境配置允许列表控制；默认空列表会拒绝确认。示例仅隔离测试配置`SYNTH_FX,SYNTH_CNY`，不写真实账号、不自动开通正式账户。不配置账户也不妨碍旧业务。正式启用日、真实账户标识和凭证管理均未配置或代选。

## 事务、幂等与原业务保护

1. 规范化金额、汇率、日期、空值、来源顺序及凭证哈希，稳定请求键和事件编号唯一。同键同内容返回原事件（200），同键异内容或编号冲突409。并发唯一冲突后只在键、内容及权限均匹配时返回已有结果；不凭金额/日期/银行参考号相同去重真实两笔。
2. 草稿登记与来源行在同一事务创建；任一步失败全部回滚。pending不占用已结汇额度；多个草稿不能越过确认时的额度锁。
3. 确认与退款共用往来方锁域，包括历史只经订单/计划指向往来方的来源；按固定顺序锁往来方，再按根→子行顺序锁整个拆分家族，最后锁事件。确认后重算额度，校验状态、币种、方向、来源证据及快照。不同请求竞争同一来源不得超额，同事件重复确认不二次记账。
4. 每条现金行单独计数；root.amount不是整家族总额。合法30+70家族合计100，不再加一个root=100；重复列同一行直接拒绝。AdvanceAllocation及PaymentPlan核销不扣结汇额度、不被结汇修改。
5. finance.record_transaction仅加已关联资金事件的替代保护；void_transaction在任何余额写入前检查整个家族；record_contract_refund先锁往来方、检查同币种资金依赖，再沿用原退款算法。没有资金依赖的原收付款和无关往来方/币种的合法操作仍走原路径。
6. 退款、作废、替代或取消草稿不产生银行逆向事实。仅未确认草稿可有理由放弃并保留来源/凭证；它本来不占确认额度。已确认事件不允许取消、释放、改写或自动冲销。

资金登记/确认不调用record_transaction、原币核销或订单生命周期；不创建第二笔客户收款，不改AdvanceAllocation、采购、销售、库存、旧rmb_amount或任何既有报表计算。API参考差异仅信息，不是净利润或会计汇兑损益。

## API及权限矩阵

基础路径`/api/rmb-cash-events/`；金额返回字符串，bank_currency和fee_currency固定CNY，currency/amount表示来源原币。

| 方法/路径 | 权限及行为 |
|---|---|
| GET列表、/{id}/详情、/by-request-key/?request_key= | finance.view + transactions.view；全部来源/家族及费用父批次可见才返回整个事件，否则列表隐藏、详情/回查404，不返回全批金额供反推 |
| GET /sources/?currency=USD | 相同读权限及原业务数据范围；按具体现金行显示剩余候选额度，始终要求人工核实；未知/退款/替代关系用null和blocked_reason，不假定0或银行余额 |
| POST /preview/ | 读权限、规范化/来源校验，无写入、无额度占用；预览不代替银行确认 |
| POST基础路径 | 额外finance.create；建立pending事件及来源，201；同内容重试200；受保护的重复键不给不可见事件详情 |
| POST /{id}/confirm/ | 额外finance.update；仅接受`{"voucher_checked":true}`，不允许重传/覆盖草稿金额、凭证或来源 |
| POST /{id}/cancel/ | 额外finance.update；仅pending有理由放弃，保留快照；已确认拒绝 |
| PUT/PATCH/DELETE | 405，不提供直接覆盖删除 |

来源每条都检查相关customers/suppliers/orders/purchases查看权限与sales scope，包括家族中未直接分配的行；合并批次不能部分裁剪后泄露总额。费用事件还保护其父结汇批次。无导出及任意附件入口；不新增绕过权限的只读聚合接口。

最小登记示例及规范化结果见证据目录http-request-final.json/http-final-observations.json；只含合成账户和银行凭证。未来前端必须保存request_key，结果不明先回查；本轮未开发其UI或宣称跨刷新表单已实现。

## 场景与原始证据

| 场景 | 自动回归及不变量 |
|---|---|
| A/B | 收USD100仅核销原币，新增银行事件为0；确认净CNY705、含扣费5后，只新增资金事件/分配，旧业务与概览逐条相等 |
| C | 60、40两次确认，累计100；再0.01拒绝，不增加事件或占用 |
| D | 现有业务服务生成30/70拆分家族，再合并100；伪把root当100或重复root拒绝 |
| E | 含扣费5不再次减净705；独立CNY银行费须bank_fee来源及独立凭证，无含扣父批次才允许关联；710流入和5流出净705，不自动新增费用流水 |
| F | CNY收入/支出分别人工确认；相同金额/日期但不同请求与合法剩余额度能记录两笔真实事实 |
| G | 缺凭证、缺受控账户配置或未人工勾选均拒绝；保留pending，没有确认占用或历史改写 |
| H | 已确认/待确认关联源作废拒绝；已确认后退款/替代拒绝，所有余额和快照不变；无关退款仍可正常执行；未知来源不得自动结汇或释放 |
| I | 同键重试、回查、重复确认；异内容/事件编号冲突；保留取消草稿、禁止取消已确认事件 |
| J | PostgreSQL双连接并发60/60抢100只有一个确认、剩40；同键并发登记和同事件并发确认仅一事件/一分配；确认与作废/退款竞争不产生逆向事实 |
| K | 无财务/流水查看或写权限、跨客户不可见合并、缺订单权限家族整体拒绝；不泄露金额；NaN/Infinity/float/bool/负数/超限/超精度/类型异常拒绝 |
| L | 历史100.0001只分配100留下0.0001；JPY拒绝0.1分配；历史四位原值与核销不变；新参考展示1.005按HALF_UP为1.01，银行事实不被重算 |

自动测试同时包含“来源快照变化”“分配写入中异常”“确认状态写入后异常”故障注入，验证两表及确认占用安全回滚。模拟故障不作为真实银行证据，模拟数据修改仅建立异常历史fixture，不用于绕过校验让业务通过。

### 真实HTTP/数据库核对

`prepare_http_fixture.py`只接受指定的新合成DB并拒绝已有客户，不清库；通过既有服务建立USD100、30/70计划及合法收款家族。合成凭证文件明确标记非真实银行凭证。`verify_http.py`对8138发出13次真实HTTP请求：预览200且零事件、登记201、确认200、重试200、冲突409、超额409、作废/取消/更正400；原始请求/响应逐项留档。初版HTTP原始请求中的来源尾零格式保留为开发记录，最终严格2位示例另存http-request-final.json，不把旧输入格式当作最终可接受契约。

旧模型全部记录序列化前后SHA256均为：

`e677ab087f53e434f0f64b6c95ae96bfcc25563f08d9a2d94f9201ac88c2b7d5`

旧概览响应完全一致，仅多出1个confirmed银行事件和2条来源分配。原计划仍分别结清30/70，银行净额705.00，含扣费5.00只说明。最终安全增强后重启同一合成服务，再实际HTTP复测同键回查/确认及作废、退款、替代、取消拒绝，旧记录哈希和银行事件/分配条数仍一致，见http-final-observations.json、http-final-verification.log。

### 测试结果与分类

- **FIXTURE_SETUP**：新建合成库、服务层准备原业务、银行凭证合成文件，不等于真实银行对账或UI验收。
- **REAL_API_OBSERVATION**：8138真实HTTP状态与响应；Django APIClient测试另注明为进程内真实应用API，不是网络请求。
- **DATABASE_VERIFICATION**：legacy-before/after.json、全部旧模型哈希、迁移逐行对比及资金表精确值。
- **MOCKED_TEST**：仅故障注入和现有前端mock浏览器回归；PostgreSQL锁测试不mock数据库或锁。
- **BLOCKED**：实际更正/退款归属及零净额细则、正式启用日和正式账户/凭证配置未决定/未启用；本轮无真实银行资料，不声明上线可用。

本地SQLite全量762项OK（13 skipped，包含3项仅PG锁测试）；其后新增两项历史关联/家族权限边界，最终针对资金+原财务+数据范围74项OK（3项PG跳过）。最后精确HEAD的完整SQLite及PostgreSQL全部测试以GitHub最终运行验证，包含本轮24项新增测试。PostgreSQL测试输出`P2A_REAL_POSTGRES_CONCURRENCY`及`P2A_MIGRATION_VERIFICATION`原始JSON，不能用SQLite跳过结果代替。

本地Node132、Vitest633、Typography1及Build通过。Playwright原有147用例保留：首次Windows managed-webServer在147条逐项ok后清理未退出，记录不作为完整进程PASS；切换独立合成代理测试服务器后完整重跑，结果见playwright-final.log，最终CI亦运行标准配置全量。没有前端产品UI变更，按本轮明确要求不采集无意义截图；原前端视觉验收范围不因这些mock测试扩大。

初次开发针对性测试发现新建ORM对象未刷新时Decimal字段仍为字符串，返回展示失败；已在事务内刷新新事件，后续针对性回归通过。失败日志保留并与最终日志区分，不将失败批次记为PASS。

## 遗留、安全拒绝与交付

新增ISS-108 BLOCKED：已确认事件更正日期/反向资金来源/银行撤销凭证和额度解除策略仍未明确，零净额结汇及混合含扣与另扣费用归属也不代选；当前明确拒绝，不提供覆盖式更新或解锁接口。解除需财务负责人明确原银行是否实际撤回、更正记入哪个期间、具体来源分配及审批依据，再另行授权实现与PG回归。

ISS-105保持OPEN：本轮仅事实与安全后端，既有参考概览、cash报表、CSV、预计利润与库存成本均未改，新事件不混入任何旧统计。ISS-107及其他历史Issue状态保持；未实现银行余额、自动导入、自动汇兑损益、真实银行对账、正式RBAC或生产部署。

提交代码、0077增量迁移、回归、原始日志及数据前后证据到master。最终完整SHA、精确HEAD三项CI URL/结论及PG原始并发证据绑定最终交付消息与审查包FINAL-DELIVERY.md，避免把父提交CI冒充最终结果。仅当三项CI实际完成且PG并发验证通过后交付。随后停止，等待独立审查，不自动进入P2-B。


## 精确CI发现的跨日测试修正

首推`8706200632980c7e3a6a5e0b776e81fdac7e1613`，[Backend失败](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39144166262/job/117724498131)、[PostgreSQL失败](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39144166262/job/117724498049)，均执行764项、仅原有test_multi_plan_decimal_and_overdue失败。固定的第二期到期日18日在跨入19日后也逾期，真实结果485.32，测试错误地继续期待135.32。修正fixture显式today=self.day，第一期today-1、第二期today+1，并分别断言today部分逾期135.32、today+2全部逾期485.32。没有修改逾期业务算法、余额或金额。

登记ISS-109 FIXED_PENDING_REVIEW。原始ci-backend-initial-failed.log和ci-postgres-initial-failed.log保留，不称失败SHA已通过。该PG原始日志已实际输出三项`P2A_REAL_POSTGRES_CONCURRENCY`成功结果和PG迁移数据不变；仍须以补修后精确最终HEAD三项CI全部SUCCESS作为交付门槛。最终代码及新旧业务回归再次执行，结果见backend-final-with-date-fix.log与最终CI。此处为CI可靠性必要修正，不扩大财务业务规则范围。
