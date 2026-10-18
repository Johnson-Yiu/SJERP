# R1-A 核心业务历史 Issue 核实与修复

日期：2026-10-18（Asia/Shanghai）。范围仅 ISS-001、004、005、006、054。独立审查尚未发生，不关闭任何 Issue，不进入 R1-B、员工 UAT、正式 RBAC 或部署。

## 环境与基线

- 用户基线及真实远端 master：`48a2126b07670c5e228180d7e6ca100fa12dbb64`，已用 `git ls-remote origin refs/heads/master` 重新核对。
- 主工作区 master 为 `608c0194a44221a0ec758f23f8628998668a96c7`，存在大量历史未提交修改。全部保留；本轮在 `.worktrees/r1-a` 从指定基线创建独立 detached worktree，交付以 `HEAD:master` 快进推送，不覆盖主工作区分支或文件。
- 初次沙箱内 Git schannel 无凭据、CLI API 403；使用获准联网执行后远端与 Actions 查询成功，不再把此项列为阻塞。
- 基线 CI：[run 39046034965](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39046034965)，[Backend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39046034965/job/117434832675)、[PostgreSQL](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39046034965/job/117434832510)、[Frontend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39046034965/job/117434832706) 均 SUCCESS。
- 本轮服务明确设置 `DATABASE_URL=sqlite:///D:/Codex项目/森爵照明管理系统/.worktrees/r1-a/backend/r1a-isolated.sqlite3`；后端 `127.0.0.1:8126`，前端 `127.0.0.1:5196` 代理至该后端。主环境未设置 DATABASE_URL 时默认 `backend/db.sqlite3`，未拿主库做业务操作或清理。
- 身份保持 development superadmin；未创建员工账号、未打开正式 RBAC。migrate 仅针对全新专用库。脚本带数据库路径断言及空主数据保护；没有直接改业务余额。
- SQLite 自动化用 Django 独立测试库，不是 UI 合成库。PostgreSQL 由本轮精确提交 GitHub CI 的 PostgreSQL 17 服务完成；本机未配置独立 PostgreSQL，不伪报本地 PostgreSQL 验收。
- 已查阅 AGENTS、PROJECT_ISSUES、PROJECT_PHASES、REVIEW_PROTOCOL、R0-E1、Phase3 计划与 Round1 历史；旧 FAIL/PASS 均未直接当作当前判定。

## 逐项判定

| Issue | 当前判定 | 根因 / 改动 | 尚缺条件 |
|---|---|---|---|
| ISS-001 | BLOCKED：业务决定；已真实复现 | 全部发货、仅收 USD340 / 合同500 时可完成；计划保留160，工作台待办被完成状态短路。只分析，不改规则 | 业务负责人选择方案 A/B；随后补 UI/API 与历史兼容回归、独立复审 |
| ISS-004 | FIXED_PENDING_REVIEW，限定已覆盖范围 | 旧 USD 入口失败未复现；当前真实 USD 保存、拆分、预收与超额均可用。确认了不带流水号的请求重放风险，新增表单保存编号在重试期间保持不变，复用已有唯一约束；保存中禁止关闭/离开/修改 | 全站通用幂等协议、跨刷新或新表单恢复、真实并发冲突与提交后断网仍未完整验收；不据此宣称 exactly-once |
| ISS-005 | FIXED_PENDING_REVIEW，主闭环证据补全 | 无销售订单的两 SKU 采购从创建、确认、收货到付款完成；无供货来源明细也走既有合法路径。未修改采购服务或政策 | 采购保存网络失败的真实 UI 重试、同 SKU 多来源的全部组合、独立复审 |
| ISS-006 | NEEDS_VERIFICATION：已补核心正常/拒绝证据 | 现有事务服务在已覆盖场景未见余额缺陷；原流水、反向流水、数量及预留已核对。没有为了通过测试修改服务规则 | 全部网络失败、并发到货/冲销竞态、更多历史异常样本未完成真实 UI 验收，不关闭 |
| ISS-054 | FIXED_PENDING_REVIEW | 收货成功反馈 receiptSuccess 与冲销 notice 独立保存；冲销未清旧反馈。打开及提交冲销时清理旧成功/错误，失败不显示成功，成功只显示冲销结果 | ChatGPT 独立审查截图、代码及测试 |

首次发现、原始失败及原关闭条件继续保留于 PROJECT_ISSUES 原行，本报告为新增核实记录。没有批量变更其它历史 Issue。

## 真实操作矩阵

所有 REAL_UI_ACTION 均操作专用 SQLite，使用 Codex 内置浏览器；补充 Chrome 操作单独注明。脚本和测试不是 UI 替代品。

| 标签 | 场景 / 操作 | 结果及证据 |
|---|---|---|
| FIXTURE_SETUP | 空库迁移；两供应商、SKU、包装、交易单位、客户；USD500 草稿、10pcs 期初库存 | seed_isolated.py、fixture.log、migrate.log；订单确认、发货和记账不是脚本代做 |
| REAL_UI_ACTION | 供应商→不关联订单→选两个 SKU→USD/7.2→2卷×10m×USD12.5/m，加5m×USD3/m→保存→确认 | PO-2026-00001，合同 USD265；第一 SKU 自动匹配 GB 来源，第二 SKU 无来源；HTTP POST 201 / place 200 |
| REAL_UI_ACTION | 第一次收1卷10m→冲销；第二次再收10m→冲销 | 部分到货→已下单；原记录与反向记录都保留；iss054-before/after.jpg |
| REAL_UI_ACTION | 冲销后重新收20m，再收第二 SKU 5m | completed；2卷=20m，基础单位成本12.5；iss005-paid.jpg / database-checkpoint.json |
| REAL_UI_ACTION | 采购付款100 USD/7.15，再付165 USD/7.2 | 应付79.5+185.5全部结清；现金流水按跨计划拆分为100、85.5、79.5，合计265，本位币1903；不是三次付款 |
| REAL_UI_ACTION | USD500订单确认→10pcs全部发货→财务“新增记账”输入340 / 7.25→完成 | 已收340、欠160仍可完成；工作台待办消失，回款卡仍160；iss001-completed-unpaid.jpg |
| REAL_UI_ACTION | 完成后调整尾款到期日为2026-10-17→仅看逾期 | 350计划、190已核销、160待收仍显示“已逾期”；只通过合法日期调整 UI，未改金额；iss001-overdue.jpg |
| REAL_UI_ACTION | 客户详情及财务概览回查 | 客户详情主要显示销售额/订单/流水，无独立客户应收总卡；不能把累计销售额误称实收；HTTP insights / finance-dashboard 可追溯160余额 |
| REAL_UI_ACTION | 新增记账→未分配预收款→无订单/计划→USD12.34 / 7.123456 | 成功，币种、客户、未核销额正确；本位币精确87.9034；iss004-no-plan.jpg |
| REAL_UI_ACTION | R1A-REVERSAL 正常订单收520 USD/7.3，合同500 | 合同核销500，额外20转未分配预收，沿用现行政策；财务流水与 database-final.json 对照 |
| REAL_UI_ACTION | 第二张草稿确认→出库20m→回采购冲销原20m | HTTP400“实际库存不足以冲销”；没有新增反向流水；iss006-consumed-rejected.jpg |
| REAL_UI_ACTION | 该销售发货单冲销 | HTTP200，已发20→0、库存0→20、预留0→20；历史发货保留；iss006-shipment-reversed.jpg |
| REAL_UI_ACTION | 手工库存盘盈3pcs / 成本2.35→冲销 | HTTP201；新增-3pcs反向记录，原IM保留，净库存不变；iss006-manual-reversed.jpg |
| REAL_UI_ACTION | 第二SKU已收足后再收2m，明确确认“赠品”超到 | 已到7、剩余0、超到2；合同/应付仍265；iss006-overage.jpg |
| REAL_UI_ACTION | Chrome 冲销该超到，目视正确反馈 | 回到5m，超到历史仍2m且标已冲销；chrome-reversal-feedback.jpg |
| REAL_UI_ACTION | Chrome 对已结清订单再记客户收款1 USD | HTTP400；表单保留金额/订单，未显示成功；chrome-finance-rejected.jpg |
| REAL_UI_ACTION | 失败后取消、重开，合法未分配预收USD2.34 / 7.123456 | 成功；备注R1A post-fix Chrome，对应36字符FIN编号、本位币16.6689；新表单是新业务请求 |
| REAL_API_OBSERVATION | 相同预收请求不带流水号重放两次 | 201/201，各生成1笔：确认旧调用方式无法识别重试；replay-http.json，合成流水未删除 |
| REAL_API_OBSERVATION | 相同流水号重放两次 | 201/400，第二次0新增；唯一性拒绝，数据库状态不变；replay-http.json |
| DATABASE_VERIFICATION | 检查计划、原币/汇率/本位币、库存/预留/在途、正反流水和快照 | verify_database.py / final_verification.py；所有比较使用Decimal；database-checkpoint.json / database-final.json |
| MOCKED_TEST | 模拟保存中重复提交、响应丢失、重试同编号、拒绝后再成功、冲销反馈切换 | Vitest，不能称为真实断网 UI 验收 |
| MOCKED_TEST | 第二笔拆分写入故障、入库后预留重平衡故障 | 注入异常但执行真实DB事务，断言事务前后全部行相等；SQLite与PostgreSQL测试；不是实际网络事故 |
| BLOCKED / 未覆盖 | 真实提交后断网及跨刷新恢复、真实多客户端并发、任意历史坏数据、采购保存断网重试 | 保留缺口，不以139条模拟页面测试或旧Round1 PASS宣称完成全部业务验收 |

## 修复前后与兼容边界

ISS-054：PurchaseOrderPage.openReceiptReversal 清除 receiptSuccess/notice；submitReceiptReversal 在发请求前清旧 error/notice/receiptSuccess。正常返回才写冲销成功；拒绝时只保留错误。没有修改 fulfillment.py、采购状态算法、成本、权限、receipt或库存模型。

ISS-004：TransactionPage.save 首次提交生成 `FIN-<32位随机十六进制编号>`，失败后的同表单提交沿用它；既有 Transaction.transaction_no 唯一约束及 serializer 校验负责拒绝重复。重复编号返回时提示先查具体流水号。字段和关闭按钮保存中禁用，遮罩/重新打开/路由离开使用busy保护。未修改财务模型、分期核销顺序、超额预收拆分或汇率政策。历史流水无需迁移。

该修复是“同一次新增记账表单的重放防重”，不是服务端普适的幂等成功回放：其它客户端仍可不带编号发起不同请求；关闭失败表单/刷新后新建有新编号，需要人工核对可能已提交的现金。并发同编号在DB唯一约束下不会重复落账，但竞争时的友好响应仍需专门并发测试。没有用金额/客户/日期相同自动去重，因为两笔真实现金可以完全相同。

## ISS-001 两套可执行方案（只建议，未实施）

当前后端 complete_order 只要求shipped且所有明细已发足；实际是履约完成。Order.outstanding_amount按open应收计划计算，排除draft/cancelled但不排除completed。工作台任务生成对completed提前返回，导致提醒与账务分离；不是计划被删或自动结清。

| 影响面 | A：履约完成与财务结清分开（建议） | B：整单财务结清才能完成 |
|---|---|---|
| 前端 | 明确“履约状态”和“回款状态”；已完成仍显示欠款/逾期及催收入口 | 完成前显示需收清，按钮给出具体余额；拒绝后保留上下文 |
| 后端 | 保留完成动作现有发货条件，独立由有效计划计算财务状态；工作台先构建应收任务再处理终态 | complete事务锁订单与有效计划，验证已全部发货且剩余应收为零；UI隐藏不能代替服务校验 |
| 历史订单 | 不改历史status、不重写流水；回算派生结清状态，列出历史已完成欠款 | 不自动把历史completed改回shipped；先生成只读例外清单，业务决定如何标记和处理 |
| 报表 | 合同销售、实际现金、剩余应收分别统计，completed不等于cash settled | 完成指标将兼含履约与收款，历史口径须版本化；仍不得拿完成额替代现金额 |
| 应收 | 完成后持续催收和账龄，退款/调增后可重新欠款，无需改履约历史 | 完成后若退款/调增产生欠款，需决定是否重新打开订单或显示“完成后欠款”；禁止静默清计划 |
| 权限 | 复用当前开发superadmin；未来按正式设计分开履约操作和财务核销，不在本轮启用 | 同样复用现有入口；需决定是否允许审批例外、谁能处理历史例外，本轮不增角色或绕过 |

推荐A，因为现有“完成”服务已按履约实现，能保留历史履约事实并持续催收；这是待业务负责人确认的建议，不是已选政策。B也可实施，但需一并决定完成后财务变化、坏账/折让/退款及历史例外；不能由开发猜测。

## 数据库核对与报表边界

- USD500：150+190=340；150+350=500计划；剩余160；7.25下现金2465，按合同7.1折应收1136。订单完成只改变状态，没有新增财务流水或结清计划。
- 采购：20m×12.5+5m×3=265 USD；2卷×10m=20m。付款100×7.15+165×7.2=1903 CNY。分批付款拆3行是跨计划核销，不是重复记账。
- 最终库存：EXISTING实存20m、预留20、可用0、在途0；SECOND实存5m；PCS实存0。手工+3/-3、超到+2/-2、销售-20/+20各保留正反向历史。采购冲销反向流水数量/单位成本与原流水精确相等。
- 库存价值核对仅验证流水`quantity×unit_cost`及采购原币金额，不擅自将原币入库成本解释成跨币种会计存货估值；系统当前流水并无每行独立币种字段，进一步统一估值政策需要另行决定。
- 财务概览仍列出本订单160 USD应收；销售报表为合同金额，不代表实收；现金报表只使用confirmed实际流水。原始HTTP保留了金额字段的序列化形态，持久化账务断言使用Decimal，未拿float近似判定。
- http-initial.json中的context/customer及inventory地址404来自核对脚本路径写错，不是产品缺陷；改为源码声明的复数customers及inventory-detail后另留http-final.json，不删除初次观测。

## 自动化与独立验收

新增后端6项：独立采购/无来源及分批付款、消耗后拒绝/销售冲销/重复冲销、入库后故障回滚、USD拆分与非法金额、唯一流水号重放、第二拆分写入故障回滚。新增Vitest3项：冲销成功/失败反馈两分支、记账单飞/失败重试编号/新表单新编号。修正一条旧测试“前端不发送流水号”的过时预期。

本地最终结果：Backend SQLite 726项，OK（10项skip）；Node 121/121，独立Node版式1/1；Vitest 610/610；Playwright JSON 139/139、0 unexpected/0 flaky；Build成功（既有chunk size提示）。最终完整结果和命令保留在证据目录的原始日志及CI；最终HEAD、三项CI精确链接以交付记录为准。基线720后端/607Vitest不冒充新增后的最终测试数量。Playwright首次标准命令139项均输出ok但退出/报告曾延迟，首次文本日志未带总结；后续标准JSON重跑亦完成139/139、0 unexpected，不以中间文本推断结果；另用playwright.r1a.config.js连接显式隔离Vite服务完整重跑，结果以playwright-external.json为准。CI仍运行仓库标准playwright配置。

独立审查：等待ChatGPT。Codex的代码自检、真实浏览器目视、自动测试和GitHub CI均不是独立审查。本轮未将FIXED_PENDING_REVIEW转CLOSED。

## 证据与交付

原始证据目录：[uat-evidence/r1-a](uat-evidence/r1-a/README.md)，截图哈希/像素见manifest.json；HTTP状态见server.log、replay-http.json、http-final.json；数据库前段及最终读回见database-checkpoint.json、database-final.json；重跑脚本保留。

提交、最终精确CI结果在交付消息和GitHub该HEAD检查中记录；本文件不能包含自身提交哈希形成自引用。收到独立审查前停止本轮，不进入其它阶段。未覆盖及剩余风险按上表继续追踪，不能将本轮称为全系统无条件PASS。


## R1-A-FUP-01 复审更正（2026-10-18）

原文两处本位币笔误已改为 87.9034 和 16.6689；原始数据库证据正确，未修改历史流水。复审确认旧表单空快照无法识别修改，且结果不明确后关闭可能丢失稳定编号；旧“关闭/离开保护”结论撤回，不能作为验收通过依据。补修与真实提交后响应丢失证据见 [FUP-01](R1-A-FUP-01-财务重试安全验收.md)。原范围外分支仍按本报告保留，不宣称全站 exactly-once。
