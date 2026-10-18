# R1-A-FUP-02-FIX-01 独立审查补修验收

日期：2026-10-18。基线origin/master `7faafcf142827ee4e94aa1aaa8d04e68e77e3726`；从该基线新建隔离工作区`.worktrees/r1-a-fup-02-fix-01`。主工作区未提交修改和业务库均保留。本轮仅处理用户指定的表头串改与无有效计划误导提示。ISS-001保持FIXED_PENDING_REVIEW；表头回归按AGENTS要求新登记ISS-106待复审；其他已有Issue状态不变。

## 根因与受控修改

1. DocumentPage同时渲染报价、订单两个表格，前轮修改将两处“状态”均替换为“履约状态”。本轮只将quote-table恢复“状态”；共享组件测试从订单切报价再切订单，保证两种表头分别正确。
2. 有效应收计划为空时，既有outstanding_amount派生0；no_plans虽然未称“已结清”，但orderTasks只检查正余额，导致completed显示“当前没有待处理事项”，详情和列表也将未知待收显示0。本轮不改该历史金额计算或写入规则，而在展示层区分未知与确认余额。
3. 新增纯函数receivableNeedsReview，仅对非草稿/非取消、合同额已知且非零且派生状态no_plans/review返回true。工作台生成“应收计划待核对”只读待办，链接本单应收；当前待收显示“待核对”，隐藏财务百分比。它优先于数值余额，不把异常计划的0或其他数字当作确定待收。
4. OrderSerializer追加SerializerMethodField `receivable_state`，复用既有order_receivable_state，只返回动态状态，用于列表未知余额提示。这是只读API字段，非数据库字段，无迁移或结清状态存储。财务和流水查看权限均满足才返回，权限不足返回None；列表金额列和详情卡片/任务/入口仍要求两项查看权限。
5. 完成履约及收付款服务、有效计划筛选、Decimal余额/逾期算法、统计口径、权限入口与数据范围未改。零合同额、草稿、取消仍沿用原规则；completed不会重现采购/发货操作。无财务权限的空待办提示仅限“可查看的履约待办”，不作财务完成结论。

## 真实业务流程与证据

使用全新可销毁SQLite：r1a-fup02-fix01-isolated.sqlite3。真实内置浏览器执行业务，Chrome复核修改页面。原始点击步骤、分类、环境、首次测试偏差均见[ui-operations.md](uat-evidence/r1-a-fup-02-fix-01/ui-operations.md)。

| 场景 | 当前结果 | 证据 |
|---|---|---|
| USD500订单、全部发货、收340、欠160、完成履约 | 真实发货201、收款201、完成200；completed仍显示待收160、部分收款、逾期与本单应收入口 | 真实HTTP及浏览器实读、before/after_complete；02仅加载截图 |
| 再收160 | 应收页面登记201，重开订单已收500/余额0/款项已结清，无虚假收款待办，履约仍completed | 03原图、settled.json |
| 退款40 | 财务流水退款201，重开订单净收460/待收40，待办及逾期恢复，履约仍completed | 04原图、refunded.json |
| 历史非零completed无计划 | 只读显示核对待办；回款“应收计划待核对”、当前待收“待核对”；列表亦显示核对提示；没有补建计划或改历史记录 | 01/05/06原图、fixture及快照比较 |
| review状态 | 受控API自动化验证明确核对提示、不显示确认零金额或财务百分比、不重现履约操作 | Node、Vitest、Playwright，分类MOCKED_TEST |
| 财务权限不足 | 后端分别拒绝finance/transactions后派生状态与金额None；前端恶意未屏蔽数据亦不显示金额卡/核对任务/应收入口，列表金额列隐藏 | 后端8项、Vitest、Playwright；08模拟权限原图 |
| 报价/订单表头 | 真实Chrome分别读取“状态”/“履约状态”；共享组件双向切换回归 | 06/07原图、order-overview-ux测试 |
| 零金额/草稿/取消 | Node状态矩阵保持既有行为；后端特殊状态测试保留 | orderOverview.test.js、backend-targeted-final.log |

FIXTURE_SETUP不算业务UI已验收。历史无计划样本模拟导入记录，初始即completed且无计划，不删除正常单据或改余额来制造案例；本轮不裁定缺失历史流水的完成合法性。无权限/review/网络失败及重复点击为MOCKED_TEST，不冒充正式员工或真实异常账务。

## 数据库一致性与金额

[verify_database.py](uat-evidence/r1-a-fup-02-fix-01/verify_database.py)只读取原始JSON，以Decimal精确断言：完成履约前后PaymentPlan、Transaction、Shipment、InventoryMovement、InventoryReservation逐行相等；应收160保留。再收160余额0、退款40余额40，completed不变。历史无计划订单及其空计划/流水全程不变。主订单原币净收USD460；既有汇率7.1下人民币参考净额3266仅为原口径核对，不称实际银行人民币到账。原始金额、汇率、rmb_amount、计划核销均见快照与HTTP响应，未改R1-FIN-AUDIT-01方案或财务统计口径。

## 自动化与执行结果

原始日志均在[证据目录](uat-evidence/r1-a-fup-02-fix-01/)。最终代码的完整结果以精确提交GitHub三项CI及其原始日志为准，不能用前轮CI代替。

| 检查 | 本地结果 / 日志 |
|---|---|
| Backend SQLite全量 | 首轮736通过、10跳过；追加只读列表状态测试后最终全量见backend-sqlite-final.log（737项）；定向8项通过 |
| Backend PostgreSQL | 本地无实例；最终精确HEAD的GitHub PostgreSQL17任务执行完整测试，交付列出该任务结果与URL |
| Node | 131通过，node-final.log；typography独立1项通过 |
| Vitest | 62文件630项通过，vitest-final.log；最后无权限空待办文案调整后定向8项通过 |
| Playwright | 显式5204隔离服务完整145项通过；最后权限场景补图及提示后定向5项通过 |
| Build / Django check / migration check | 通过；无模型迁移。Build保留既有chunk>500kB警告，不影响构建 |

保留首轮错误日志：Playwright误复用旧5195服务产生6失败/139通过，修正为专用config后145通过；定向测试夹具带detail路由打开不完整报价详情，出现未处理错误，修正夹具无detail路径后通过。没有删除失败记录或将错误轮次宣称PASS。

## 原图与交付追溯

01历史无计划（内置浏览器）；02完成后加载过程（不作为欠160结果截图）；03结清；04退款欠40；05真实Chrome历史核对卡；06真实Chrome订单表头及未知金额列；07真实Chrome报价表头；08模拟权限Playwright截图。JPEG/PNG均保留原始字节；证据清单含SHA256。HTTP日志仅合成业务数据，不含授权头或真实财务秘密。

本报告的Git提交即本轮代码/证据提交，以`git log -1 --format=%H -- docs/R1-A-FUP-02-FIX-01-独立审查补修验收.md`取得精确SHA。最终交付附该SHA、绑定该headSha的Backend / Backend PostgreSQL / Frontend任务URL及结果；GitHub保存CI原始日志，复审ZIP同时附精确提交文件和CI元数据，避免文档自引用SHA造成再次改变HEAD。推送仅fast-forward master，不强制覆盖。

## 遗留与停止条件

ISS-001及ISS-106均待ChatGPT独立代码、图片和数据库证据复审，不自行关闭。历史无计划如何由业务人工核对仍需实际业务负责人处理，本轮不给未知欠款补造金额或计划。其他已有Issue、人民币统计/银行结汇、正式RBAC、员工UAT和部署均不在本轮；不进入R1-B。最终精确HEAD三项CI成功后停止等待独立审查。

截图限制：02在重载瞬间捕获，未显示业务结果，已明确重命名为loading-only；未用模拟画面或改库复造。欠160完成的真实操作及结果仍有HTTP/数据库原始证据，独立审查需评估该单张结果截图缺口，不扩大截图验收。
