# PARTY-VERSION-CLOSEOUT-01：主体及版本核查

## 后续核查与最新结果

- 最终 SQLite 后端全量运行 1475 项，1389 项通过、86 项按条件跳过，退出码 0；[原始日志](logs/sqlite-full-release.log)。测试使用内存测试数据库和专属临时媒体目录，跳过项不算通过；真实 PostgreSQL 专项结果另列。此前提前停止和失败的运行均保留。
- 最终 PostgreSQL 17.10 一次性集群重跑 **73 项通过、0 跳过**，空库和 0108→0112 升级成功；受保护回退按预期拒绝，记录及迁移状态保留，集群和测试数据库清理完成。[测试](logs/pg17-final-all-source-stable/party-tests.log)、[升级/回退及清理](logs/pg17-final-all-source-stable/result.json)。覆盖 707 个源码及测试文件的[运行前](logs/pg17-final-all-source-stable/source-hashes-before.json)和[运行后](logs/pg17-final-all-source-stable/source-hashes-after.json)哈希一致，后者也与运行后文件一致；先前哈希变化的中间轮仍保留。
- 稳定业务代码的 PostgreSQL 17.10 专项共 73 项通过，无跳过；全新库及 0108→0112 升级、受保护回退拒绝、真实并发和临时资源清理均完成。[测试日志](logs/pg17-final-draft-tax-stable/party-tests.log)、[迁移和清理](logs/pg17-final-draft-tax-stable/result.json)。运行期间仅旧浏览器 spec 调整了正式化夹具，故整体源码清单哈希变化、脚本退出 1；[409 个后端文件前后与当前一致](logs/pg17-final-draft-tax-stable/hash-assessment.json)。随后已取得上方完整清单一致的成功重跑；不把该轮脚本退出码记为成功。
- 稳定源码前端 Node 全量 179 项、有效 Vitest 78 文件 741 项通过，[Node](logs/frontend-node-release.log)、[Vitest](logs/vitest-release.log)、[生产构建](logs/frontend-build-release.log)。正式报价税号只读的浏览器旧用例先真实标记报价已发送再断言，结果 [2 项通过](logs/chrome-tax-release.log)；草稿编辑由新增用例单独覆盖。
- 复现并修正销售订单国家来源：关联报价时使用保存报价的国家；历史报价国家未知时订单保持空值，不读取修改后的客户国家。无报价的新订单仍按既有规则读取主档。历史正式订单未改写。[修复前两项失败](logs/so-quote-country/before.log)、[36 项定向回归](logs/so-quote-country/targeted.log)。本包旧断言原要求法国，已调整为保存报价的德国；[旧断言失败记录](logs/so-quote-country/after.log)保留。
- 未审批修订阻断时 `mark-sent` 曾返回 500；已映射为 400。[失败记录](logs/quote-approval-guard-pg17/api-response-failure.log)、[修复后 13 项、其中 1 项 PostgreSQL 专用跳过](logs/guard-api-retry.log)。
- 两个合成认证账号以真实 Chrome 申请、独立审批和生成修订草稿，申请 HTTP 201、审批及应用 HTTP 200；桌面及 390×844 截图经人工查看：[申请](party-approval/request-desktop.png)、[审批](party-approval/approved-390.png)、[HTTP](party-approval/http-results.json)、[运行日志](logs/chrome-approval-final.log)。[原报价 XLSX](party-approval/synthetic-source.xlsx)与[新草稿 XLSX](party-approval/synthetic-child.xlsx)实际生成，[文件对账](logs/xlsx-approval-reconciliation.log)显示原版地址不变、新草稿为批准地址、税号及卖方一致。样本不含图片，不能据此声称图片覆盖；仅验证不同认证账号，不能证明自然人身份。
- 最新前端 Node 179 项、Vitest 78 文件 738 项通过；[Node 日志](logs/frontend-node-approval.log)、[Vitest 日志](logs/vitest-approval-full.log)、[生产构建](logs/frontend-build-approval.log)。[Django 检查](logs/check-approval-final.log)和[迁移一致性](logs/makemigrations-approval-final.log)通过。报价保存及 PI 预览 Chrome 2 项、SO/PO 页面 Chrome 4 项通过：[报价日志](logs/chrome-current-snapshot.log)、[SO/PO 日志](logs/chrome-current-orders.log)。前述订单页面测试仅检验可见快照与未知提示，不代表 SO/PO 完整资料已覆盖。
- 因发现销售订单国家漂移，已核对进程归属后终止旧源码上的全量回归；[部分日志](logs/sqlite-full-actual-final.log)保留，不计全量通过。最终源码的全量和 PostgreSQL 结果以随后追加的记录为准。
- 后续发现新报价草稿首次留空税号后无法在普通修订补填，已用隔离测试[复现](logs/draft-tax-revision/before.log)。因此再一次核对归属后终止了[第二个未完成的全量运行](logs/sqlite-full-final-stable.log)，保留日志、不计通过；无正式祖先草稿的安全修订及正式祖先保护已按下列证据补验。
- 草稿税号补修已落地：只有整条祖先链均为草稿且税号不是历史未知 `NULL` 时，普通修订才允许填写税号；锁定并重新检查祖先链，原版本不变。存在正式祖先、历史未知、根链不一致均拒绝。[PostgreSQL 17 专项 27 项通过](logs/draft-tax-revision/pg/party-service-concurrency.log)，包括祖先并发正式化和拒绝回退，运行前后源码哈希一致；[运行结果](logs/draft-tax-revision/pg/result.json)。原有迁移回退测试按 0112 更早拒绝的实际提示更新，仍核对结构和数据未变；[更新前的三项失败](logs/draft-tax-revision/backend.log)保留。
- 草稿税号及正式报价只读的真实 Chrome 2 项通过：[日志](logs/draft-tax-revision/chrome-fixed.log)、[桌面](logs/draft-tax-revision/chrome-fixed/draft-tax-revision/draft-1440.png)、[390px](logs/draft-tax-revision/chrome-fixed/draft-tax-revision/draft-390.png)。首次及重试分别失败，定位为详情层遮挡编辑器；采用局部层级修复并恢复原测试时限，[首轮](logs/draft-tax-revision/chrome-first.log)和[重试](logs/draft-tax-revision/chrome-retry.log)均保留。前端专项 [23 项通过](logs/draft-tax-revision/vitest.log)。

状态：**报价主体申请、独立审批、生成草稿及正式化保护已接线；整体仍未完成，须独立复审。** 基线 `bcdcb57545f121b8a4102f352c74008b47372035`；本分支的代码与证据须以实际提交及其树为准。本包记录的验证使用合成资料和隔离数据库，未接触真实业务库。ISS-037 不关闭；完整打印成品与分页仍按用户决定延期，不扩大到其他主体范围。CI 依仓库 2026-11-05 约定暂停，不计为通过。最终 PostgreSQL 和实际浏览器专项结果见下方；已完成的专项不代表本工作包全部主体与版本要求完成。

## 原有成果与现有消费者

当前代码确认已有空历史买方修订保留空值以及已保存报价的卖方、银行和模板资源冻结；没有重复实现。历史 `0012` 曾从迁移时主档产生部分报价快照，不能因此断言其是当时交易事实。`0080` 的订单和采购快照未从当前主档推测填充。接续记录有来源及审批线索，来源摘要并不证明原件真实性。

| 信息 | 报价及现有 PI API/XLSX | 销售订单 | 采购订单 |
|---|---|---|---|
| 对方名称、地址、联系人、电话、邮箱 | 各字段存于报价版本，PI API/XLSX 读取版本值；新报价预填、修订继承；缺失关键买方时拒绝正式输出 | 确认时冻结六项客户信息；关联报价时来自保存报价，国家未知不以主档补填 | 下单时冻结五项供应商信息 |
| 对方国家 | 本轮新增报价保存时国家快照及报价 API 输出；旧报价为未知，不回填；目前 PI/XLSX 没有消费新字段 | 关联报价时按保存报价捕获，旧订单不回填；无报价的新订单沿用确认时主档口径 | 未发现国家快照 |
| 我方名称、地址、联系人、电话、邮箱、银行 | 通过报价模板资源按版本保存并供 PI API/XLSX 消费；资源缺失或校验失败拒绝替代 | 未发现完整我方主体快照 | 未发现完整我方买方快照 |
| 买方税号 | 本轮新报价可选文本快照，已保存 PI API/XLSX 读取；新模板使用保存值。旧报价未知为 `NULL`，不回填；沿用旧模板的修订不能假定旧打印模板显示税号 | 未见完整结构化税务注册快照 | 未见完整结构化税务注册快照 |
| 双方独立账单/收货地址及收件人、其他税务注册信息 | 未见完整结构化历史快照 | 未见完整结构化历史快照 | 未见完整结构化历史快照 |

SO/PO API 同时可能返回当前主档与独立历史快照；当前名称不能作为历史事实。以上是对源码及既有消费者的核对，不表示所有正式文件均已覆盖；未发现可用以证明完整 SO/PO 双方主体正式文件的现有导出入口，未另建导出体系。

## 本轮增量与边界

- `0109_quote_buyer_country_snapshot` 为新根报价捕获国家，普通修订和订单触发的报价修订沿原版本继承。旧记录保留 `NULL`；客户不可查看时 API 隐藏。已保存快照的普通模型保存拒绝覆盖，有快照时迁移拒绝回退。数据库管理员或直接 SQL 不受模型层保护，不能将其称为数据库级防篡改。
- `0111_quote_buyer_tax_id` 对新报价允许可选文本税号，保留前导零；明确未填保存空字符串，迁移前旧报价保持 `NULL`。普通修订及订单触发的修订继承；无正式祖先的新草稿链可以按上述规则通过修订更正，其余普通修订不得更改。已有任何非 `NULL` 值时拒绝回退。PI API/XLSX 消费保存值；新模板可显示，已冻结旧模板不会被改写，旧模板沿用时不能据此声称所有输出都显示税号。
- 确认普通模型 `save()` 原可在正式报价、SO、PO 上原地覆盖主体字段；隔离复现和三项失败断言见 [复现](logs/formal-guard-before.log) 与 [修复前测试](logs/formal-guard-test-before.log)。新增模型层检查及行锁，阻止普通保存直接改写正式主体身份及已保存快照；草稿及无关字段更新继续允许。该保护不拦截原始 SQL、`QuerySet.update()` 或有权限者先绕开业务生命周期更改状态，不等于数据库防篡改。为保留数量变更既有回归，仅将其合成测试的主体事实移至正式订单创建时设置，没有修改数量业务代码。
- 主体申请及审批服务可关联报价、销售单或采购单，保存原始和拟议快照、原因、依据、变更类型、来源可信度、指纹，以及通过 Django 认证会话取得的发起人、审批人；禁止自批、重复批准及基准或审批内容改变后批准。服务复用模块权限与客户数据范围，不改变开发超级管理员开关。可区分的真实认证会话是申请和审批的前提，匿名开发身份不能冒充真实员工。`0110` 在受保护主体事实存在时拒绝回退。
- **报价 API 和界面已接线**：`GET/POST /api/quotes/{id}/party-change/` 读取基准、申请及来源或提交申请，`approve/` 独立审批，`apply/` 将已批准的同一法律主体资料更正应用为既有报价版本树中的新草稿；批准本身不自动创建或正式化报价。申请／审批者不同；生效检查权限、客户身份、基准、来源及审批指纹和来源单据，并在事务中创建应用记录。重复调用有一致性校验；旧申请缺少客户或来源指纹时不能直接应用。报价详情展示申请、审批、生效账号及时间，提供人工“主体未变”确认；系统不自动核实法律主体。匿名开发身份展示认证提示。实际真实员工身份、独立审核及最终集成验收仍待完成。
- **原绕过的历史事实与当前保护**：修复前 APIClient 曾复现已发送报价经普通修订更改地址、联系人、电话和邮箱后再次发送，申请和审批均为 0；原版未被覆盖。[原始复现及当时源码哈希](logs/ordinary-revision-approval-probe/api-client-raw.log)保留，不能代表当前源码行为。当前 `quote_party_approval_guard` 在报价修订进入 `sent`／`accepted` 和订单确认相关路径检查最近正式祖先；主体不同须有完整、匹配的独立审批及应用记录，未变主体可沿既有版本链处理。保护为应用／模型层规则，不等于阻止直接 SQL 或所有绕行路径。**已有 HTTP 边界失败证据**：一次 APIClient 运行中保护拒绝未审批修订，但 `mark-sent` 返回 500 而测试期望 400，[失败日志](logs/quote-approval-guard-pg17/api-response-failure.log)；现已将校验异常映射为 400，修复后独立回归见上方“后续核查与最新结果”；历史失败不删除。
- `0112` 增加报价应用记录、申请与客户及来源指纹关联，并在已有受保护事实时拒绝回退；PostgreSQL 对应用记录设置追加保护。`replacement` 可分类记录，不能通过报价更正流程应用或生成新草稿，法律主体替换如何生效仍待用户决定。没有拒绝／撤回及同基准重新申请的完整流程；SO/PO 尚无对应主体生效版本和消费链。现阶段来源可信度只允许未知或未核验，生成版本可追溯来源，但批准不代表历史原件真实或已核实；历史未知的国家／税号不能由应用流程自动升级。申请／审批与应用层保护不等于对所有数据库直接 SQL 的防篡改。
- 发现税号字段引入前的报价主体申请可能在批准后读取时误判基准变化；申请批准和只读校验现在按保存时的字段集合一致验证。旧申请的缺失税号保持缺失，不回填、不重算其历史指纹；未知或不完整的其他字段集合仍拒绝。
- 其余税务注册、独立账单及收货资料、SO/PO 双方完整快照和版本消费仍未完成；也未实现法律主体替换的正式生效、文件生成及完整审核链。本轮不将这些缺口算作打印延期，不把当前主档作为历史事实。

## 测试、证据及未完成项目

| 检查 | 实际结果与边界 | 证据 |
|---|---|---|
| SQLite 后端全量首轮 | 发现 1390 项，80 项跳过；两个类的 `setUpClass` 因 PATH 未找到 OpenSSL 报错。该轮启动后源码仍在开发，不能作为最终代码全量通过。 | [原始日志](logs/sqlite-full.log) |
| SQLite 后端全量第二轮 | 指定本机 OpenSSL 后发现 1423 项，1341 通过、82 跳过；运行期间迁移保护和模型保存保护仍在修改，不视为最终代码的全量结果。 | [原始日志](logs/sqlite-full-final.log) |
| SQLite 后端过期运行 | 一次后续全量在模型保护落地前启动；确认进程归属后主动停止以释放资源，保留部分日志。该轮未完成、不计通过。 | [部分日志](logs/sqlite-full-sealed.log) |
| SQLite 后端兼容修复前运行 | 又发现旧字段集批准后读取不一致，需要修改服务；确认进程归属后停止该过期运行，保留部分日志，不计通过。 | [部分日志](logs/sqlite-full-latest.log) |
| SQLite 后端旧税号来源复核前运行 | 随后发现旧申请若目标税号已由未知变为已填，也必须拒绝，需再次补修；确认进程归属后停止该过期运行，保留部分日志，不计通过。 | [部分日志](logs/sqlite-full-verified.log) |
| SQLite 后端主体生效接线前运行 | 确认普通报价修订可绕过审批后，继续实施同主体报价生效路径；为避免旧代码全量结果被误认成最终结果，核对归属后停止并保留部分日志。 | [部分日志](logs/sqlite-full-ultimate.log) |
| OpenSSL 失败类单独重跑 | 显式使用本机 Git 自带 OpenSSL，两个测试模块的 15 项通过；这不能替代最终代码的后端全量重跑。 | [原始日志](logs/openssl-rerun.log) |
| Django 检查 | 当时的代码执行 system check 和 `makemigrations --check --dry-run` 均通过；后续又加入报价审批 API、正式化保护和 0112，不代表最终代码已验。 | [system check](logs/check-final.log)、[迁移模型检查](logs/makemigrations-final.log) |
| SQLite 国家、主体服务及既有快照回归 | 中间版本发现 46 项、44 通过、2 项 PostgreSQL 专项跳过；后续代码变化须另行重跑。 | [原始日志](logs/sqlite-final-targeted.log) |
| SQLite 主体及报价定向中间轮 | 增强跨迁移拒绝保护后发现 94 项，92 通过；两项真实 PostgreSQL 并发用例按设计跳过。包含国家、税号、审批基础、回退与既有报价回归；不代表后续报价应用及正式化保护已验。 | [原始日志](logs/sqlite-latest-targeted.log) |
| 模型保存保护及交叉回归首轮 | 修复后三类单据保护、正式快照、数量变更、订单生命周期和历史接续发现 57 项，56 通过、1 项 PostgreSQL 专用跳过；后续扩展的字段及并发断言须再跑。 | [原始日志](logs/formal-guard-after.log) |
| 主体保护及迁移定向中间轮 | 28 项中 27 通过、1 项 PostgreSQL 行锁测试按设计跳过；该并发项在当时 PostgreSQL 17 的 66 项回归中实际通过。后续应用代码不属于此结论。 | [原始日志](logs/final-guard-regression.log) |
| PostgreSQL 17.10 新库及升级中间轮 | 专属随机端口和临时集群，空库全迁移、0108→0109→当时最新迁移成功；两项独立真实数据库连接的同基准申请/同申请审批竞争均各有且仅有一次成功，不代表后续 0112 已在该轮验证。 | [集群及迁移结果](logs/final/result.json)、[并发测试](logs/concurrency/party-tests.log) |
| PostgreSQL 拒绝破坏性回退 | 已有申请时 0110→0109 拒绝、原申请保留；已有报价国家快照时 0109→0108 拒绝、原快照及迁移状态保留。 | [申请拒绝](logs/final/0110-request-rejection.log)、[申请核对](logs/final/0110-request-verify.log)、[快照拒绝](logs/final/rollback-rejection.log)、[快照核对](logs/final/rollback-verify.log) |
| PostgreSQL 跨多迁移回退首轮 | 加入 0111 后从最新状态回退至 0108，0109 保护虽拒绝，但 0111/0110 已先撤销，当前 ORM 随后因缺少列报错；该轮失败，不能写成完整回退保护通过。该次使用 Python 3.14/Django 6.0.6，并非锁定环境。 | [拒绝日志](logs/final-tax/rollback-rejection.log)、[后续读取失败](logs/final-tax/rollback-verify.log)、[运行结果](logs/final-tax/result.json) |
| PostgreSQL 锁定环境首轮 | CPython 3.12.16/Django 6.0.9；受保护国家快照的跨迁移拒绝后，0111、0110、0109 和 ORM 可读性保持。但定向测试有 3 个权限测试错误；运行前后服务和测试源码哈希发生变化，不能当作稳定代码结果。另一个 0110 独立库的申请夹具因 auth 表迁移不完整失败，尚须重跑。 | [运行结果](logs/pg312-final/result.json)、[测试错误](logs/pg312-final/party-tests.log)、[夹具错误](logs/pg312-final/0110-request-seed.log)、[回退后核对](logs/pg312-final/rollback-verify.log)、[运行前源码哈希](logs/pg312-final/source-hashes-before.json)、[运行后源码哈希](logs/pg312-final/source-hashes-after.json) |
| PostgreSQL 锁定环境主体保护定向 | PostgreSQL 17.10、CPython 3.12.16/Django 6.0.9，66 项通过、无跳过；包含主体保存保护、草稿并发确认、并发申请/审批、权限、税号及数量交叉回归。新库迁移和 0108→0111 升级通过。0111→0108、0110→0108 和有申请的 0110→0109 均在首个受保护迁移前拒绝，记录与迁移状态保留；此轮之后追加了旧税号字段集兼容补修。 | [测试日志](logs/pg312-followup/party-tests.log)、[运行结果](logs/pg312-followup/result.json)、[最新回退拒绝](logs/pg312-followup/rollback-rejection.log)、[最新回退核对](logs/pg312-followup/rollback-verify.log)、[0110 申请拒绝](logs/pg312-followup/0110-request-rejection.log)、[当时源码哈希](logs/pg312-followup/source-hashes-after.json) |
| PostgreSQL 旧税号兼容中间轮 | 28 项通过，但服务及测试源码在运行期间变化；此轮不能当作最终代码证据。 | [测试日志](logs/pg312-legacy-tax/party-service-concurrency.log)、[运行前哈希](logs/pg312-legacy-tax/source-hashes-before.json)、[运行后哈希](logs/pg312-legacy-tax/source-hashes-after.json) |
| PostgreSQL 旧税号兼容当时定向 | 隔离 PostgreSQL 17.10、锁定 Python 环境，29 项全部通过、无跳过；包括旧字段集在批准和读取时保留未知，税号由未知变为空或非空时拒绝，以及三类主体保护、并发竞争和迁移回退。该轮报告的 17 个文件运行前后及当时比对一致；后续增加了报价应用及正式化保护，不代表当前完整源码已验证。 | [测试日志](logs/pg312-legacy-tax-final/party-service-concurrency.log)、[运行结果](logs/pg312-legacy-tax-final/result.json)、[源码哈希](logs/pg312-legacy-tax-final/source-hashes-after.json)、[当时源码比对](logs/pg-final-source-match.log) |
| 真实 Chrome 首轮 | 桌面 PI 预览与 XLSX 曾生成；窄屏步骤因单个测试总时限耗尽而失败。第二次在隔离 Django API 身份检查阶段失败，未执行浏览器断言。首轮草稿 XLSX 的文档元数据不是合成值，未归档；后续样本须先使用合成元数据。两次失败不能记作窄屏通过。 | [首轮日志](logs/chrome-real.log)、[重试日志](logs/chrome-retry.log) |
| 真实 Chrome 正式报价重跑 | 两项通过：真实 HTTP 标记已发送、修改合成客户主档、重开原报价并创建修订；桌面 1440×900 和窄屏 390×844 PI 预览显示合成买卖方及保存税号。实际 XLSX 两份的 B3/B6/I3 与 API/截图一致，税号为文本，作者元数据合成且自定义属性为空；不涉及系统打印。 | [模型保护后重跑日志](logs/chrome-final-quote.log)、[此前重跑日志](logs/chrome-tax-sanitized.log)、[桌面截图](party-version/saved-pi-1440.png)、[窄屏截图](party-version/saved-pi-390.png)、[桌面 HTTP](party-version/http-1440.json)、[窄屏 HTTP](party-version/http-390.json)、[XLSX 对账](logs/xlsx-reconciliation-final-current.log)、[桌面文件](party-version/synthetic-saved-quote-1440.xlsx)、[窄屏文件](party-version/synthetic-saved-quote-390.xlsx) |
| 真实 Chrome 订单与采购 | 4 项通过，桌面与 390×844 均打开工作台；合成订单故意缺失客户快照，页面提示“历史主体未记录”；已下单采购显示保存供应商名称。增强文本断言和模型保护后重跑通过。测试不代表双方完整资料或主体更正流程已覆盖。 | [最新日志](logs/chrome-final-order-purchase.log)、[此前日志](logs/chrome-orders-final.log)、[订单窄屏](party-order-purchase/order-390.png)、[采购窄屏](party-order-purchase/purchase-390.png)、[订单桌面](party-order-purchase/order-1440.png)、[采购桌面](party-order-purchase/purchase-1440.png) |
| 真实 Chrome 税号表单 | 2 项通过：新建报价税号字段在桌面和 390×844 可输入，修订字段只读并继承保存税号；本轮没有通过 UI 提交新报价。此前代理一次截图目录配置失败的原始日志未保存，仅有工具输出，不将其伪造为文件。 | [最新日志](logs/chrome-final-tax-ui.log)、[此前日志](logs/chrome-tax-ui.log)、[桌面截图](quote-tax-ui/quote-tax/editor-1440.png)、[窄屏截图](quote-tax-ui/quote-tax/editor-390.png) |
| 前端 Node 全量首轮 | 179 项中 178 通过、1 项隔离运行器并发启动 120 秒超时取消；不能算全量通过。 | [原始日志](logs/frontend-node.log) |
| 隔离运行器单独重跑 | 17 项中 16 通过、同一并发启动用例 120 秒超时取消；未通过，原因尚需进一步定位。 | [重跑日志](logs/frontend-node-runner-retry.log) |
| 前端 Node 全量再跑 | 在减少并发任务后重跑，179 项全部通过、0 跳过；此前两次超时仍保留，不能据此断言已修复所有环境下的运行器性能。 | [原始日志](logs/frontend-node-final.log) |
| 报价前端 Vitest 定向 | 四个现有报价、销售及未保存修改相关文件，68 项通过。 | [原始日志](logs/vitest-quote.log) |
| 前端 Vitest 全量首轮 | 77 文件的 715 项通过，但 `customer-ux.spec.js` 的 worker 启动超时，出现 1 个未处理错误、进程退出 1；不能记作全量通过。 | [原始日志](logs/vitest-full.log) |
| 前端 Vitest 失败文件重跑 | 单独重跑 `customer-ux.spec.js`，10 项通过；不以单文件结果替代全量。 | [原始日志](logs/vitest-customer-retry.log) |
| 前端 Vitest 全量重跑 | 使用单 worker 重跑有效 Vitest 测试，78 文件、725 项全部通过；`detail-drawer-typography.spec.js` 是 Node test 文件，由 Node 测试运行器覆盖。首轮错误仍保留。 | [原始日志](logs/vitest-full-retry.log) |
| 前端构建 | 税号 UI 修改后的生产构建通过；未代替浏览器或业务回归。 | [最终构建日志](logs/frontend-build-final.log)、[中间构建日志](logs/frontend-build.log) |
| 报价申请及应用 SQLite 定向中间轮 | 27 项中 25 通过、2 项跳过；日志记录未认证请求和自批拒绝。该轮不替代后续正式化保护及最终源码的全部回归。 | [原始日志](logs/quote-approval-target.log) |
| 报价审批前端 Vitest 中间轮 | 5 个文件、86 项通过；只代表该日志对应时点，不能推断此后 UI 调整均已覆盖。 | [原始日志](logs/vitest-approval-target.log) |
| 报价申请、审批及草稿生成 Chrome 首轮 | 一项通过，日志记录两个合成认证会话、申请 201、审批 200、应用 200，以及原版／新版本和 XLSX 请求；这是首轮证据，不代表当前最终 UI、权限及错误状态均已验。 | [原始日志](logs/chrome-approval-first.log) |
| 报价正式化保护 PostgreSQL 中间轮 | 隔离 PostgreSQL 17.10 定向 25 项通过，含应用及并发保护；该轮运行前后列出的 8 个文件哈希一致，不证明所有最终 API/UI 文件或后续修改一致。 | [测试日志](logs/quote-approval-guard-pg17/party-service-concurrency.log)、[运行结果](logs/quote-approval-guard-pg17/result.json)、[运行前哈希](logs/quote-approval-guard-pg17/source-hashes-before.json)、[运行后哈希](logs/quote-approval-guard-pg17/source-hashes-after.json) |
| 未审批修订正式化的 API 错误映射 | 独立 APIClient 测试未通过：模型保护抛出校验异常，`mark-sent` 返回 500，断言期望 400；保存事实和对外错误映射须分别核对。该日志为失败证据，不计通过。 | [失败日志](logs/quote-approval-guard-pg17/api-response-failure.log) |
| 最新 PG / 浏览器集成 | PostgreSQL 17 稳定源码 73 项通过；真实 Chrome 报价审批、草稿税号和正式税号只读已执行，参见文首逐项说明。 | [PG](logs/pg17-final-all-source-stable/party-tests.log)、[审批](logs/chrome-approval-final.log)、[草稿](logs/draft-tax-revision/chrome-fixed.log)、[正式税号](logs/chrome-tax-release.log) |

隔离测试中临时启用 RBAC 的覆盖仅用于验证权限拒绝，没有开启正式 RBAC。两套合成登录会话证明的是不同认证账号，不证明真实员工的实名归属或账号未共用；默认开发姓名也没有作为审批人。正式报价两张截图属于随后重跑，覆盖了同名的首轮桌面截图；首轮失败事实以原始日志为准。服务端真实 HTTP 与 Django APIClient 结果分开；`beforeprint` 和打印对话不属于本轮范围。

上述三组浏览器重跑发生在主体模型保护之后、旧税号字段集的主体申请校验补丁之前；当时所测页面和报价 API 未接入该主体申请服务，因此这些截图不能表述为在最终完整源码树上重新执行的证据。

## 环境与命令

工作树来自上述固定基线；锁定 Python 环境为 CPython 3.12.16、Django 6.0.9，`pip check` 无冲突，[16 个锁定版本逐项相符](logs/python-lock-retry.log)。首次使用独立 `packaging` 模块检查时因环境未安装该模块失败，保留[失败日志](logs/python-lock-check.log)，随后仅用标准库核对精确版本，没有安装额外依赖。SQLite 后端命令均设置 `APP_STAGE=development`、`DATABASE_URL=sqlite:///:memory:` 和本任务独立临时 `MEDIA_ROOT`；Django 测试使用自己的隔离数据库。使用的主要命令如下，原始输出和跳过项以表中日志为准：

```text
python manage.py test crm --noinput --verbosity 1
python manage.py test crm.tests.test_quote_buyer_tax_id crm.tests.test_quote_buyer_country_snapshot crm.tests.test_party_version_service crm.tests.test_party_version_migrations crm.tests.test_party_version_concurrency crm.tests.test_party_version_current_baseline crm.tests.test_quotes --verbosity 2 --noinput
python manage.py check
python manage.py makemigrations --check --dry-run --noinput
node scripts/run-isolated-browser-tests.mjs --business-test party-version-snapshot-real.spec.js
node scripts/run-isolated-browser-tests.mjs --business-test party-order-purchase-real.spec.js
node scripts/run-isolated-browser-tests.mjs --business-test quote-buyer-tax-id.spec.js
node node_modules/vitest/vitest.mjs run tests/quote-editor-availability.spec.js tests/quote-list-ux.spec.js tests/sales-safety.spec.js tests/unsaved-changes.spec.js --environment jsdom --maxWorkers=1
npm run build
```

浏览器运行器创建随机端口、专属 SQLite 和媒体目录并核验服务身份，结束后清理其标记的临时资源；`ISOLATED_TEST_PYTHON` 指向同一锁定解释器。PostgreSQL 脚本在一次性目录启动本机已有的 17.10 二进制、核验数据目录和新建库；脚本和各阶段原始记录位于 `logs/`，不连接共享数据库。测试结果不等于生产身份、生产数据或部署权限验收。

## 后续集成注意事项

新增 `0109`、`0110`、`0111`、`0112` 接在本基线迁移链之后；并行分支如使用同号需由集成方按实际图创建合并迁移，不改写已发布历史。`models.py`、`serializers.py`、`views.py`、报价主体服务／API、DTO、模板及表单可能与其他主体或打印分支冲突，不能整文件覆盖；数量变更测试仅提前设置合成订单原始主体快照，合并时需保留其原有业务断言。报价申请、审批和草稿应用已接入现有版本树，仍须完成最终集成验收；SO/PO 双方资料、有效版本和历史来源可信度传递仍未完成。公共台账由协调任务维护，建议保留 ISS-037 `NEEDS_VERIFICATION` 并记录本报告及未完成项。

既有 0110／0111 回退证据仅适用于各自已测迁移图；0112 也定义了受保护事实的逆向预检，仍须在最终 PostgreSQL 迁移图中核实。未来迁移可能先于本包迁移逐项撤销；集成时必须验证迁移图和运维回退前置检查，不能将已有结果泛化为任意迁移链的整体原子回退。

| 优先级 | 未完成项及验收条件 |
|---|---|
| P1 | 报价同主体更正的申请、独立批准及关联既有报价修订的草稿应用已实现；补充正式化、权限、连续更正、并发、幂等和回滚的完整跨单据验收，补齐拒绝／撤回及同基准重申流程。法律主体替换目前仅记录、不得应用，其生效方式等待用户决定。SO/PO 对应有效版本及原版回看尚未实现。 |
| P1 | 完整补齐双方名称、地址、联系方式、独立账单/收货地址、收件人及税务注册快照，并让已有 API、预览和现有文件消费者读取对应版本；不强制所有国家填写税号。 |
| P1 | 接通历史接续的来源、原件依据和可信度，不将未知升级为已核实；核实旧 `0012` 产生值的来源。报价应用已在事务内复核并保留来源／审批指纹，需验证旧申请兼容、正式化及消费者；批准不等于历史已核实。 |
| P1 | 对主体申请、审批和应用持久化保护做数据库层面独立审查。现有 Django 模型／QuerySet 限制不能阻止数据库直接 SQL；0112 对 PostgreSQL 应用记录增加追加保护，不等于全部主体事实具备数据库级防篡改。报价公共入口已接入，须完成完整权限、目标数据范围和生产环境独立复验。 |
| P2 | 对沿用旧模板的历史修订明确税号与新旧模板资源的消费边界；不重写冻结资源、不把旧模板空白当作实际无税号。 |
| P2 | 隔离浏览器运行器并发启动两次超时仍需在空闲环境定位；首次 Chrome 环境失败和历史截图均不替代最终范围测试。GitHub CI 因额度暂停，待用户恢复后按最终集成提交复验。 |

## 只读核查：报价独立账单及收货资料

**未完成，不能宣称覆盖。** 当前报价只有一组买方地址和联系人；`shipping_details` 是运输说明，不能认定为独立收货地址。独立账单地址、收货地址及收货收件人尚无完整的保存、修订、审批及正式输出覆盖。本项与用户决定延期的打印完整成品及分页验收是两件事；本项并非打印延期。

- 拟采用独立字段并区分历史未知 `NULL` 与明确留空；旧报价不得从现有买方地址、联系人或当前主档推断、回填。新单如提供“同买方”操作，应由用户明确选择并保存当时的值。
- 普通和订单触发修订须继承已保存值；正式更正是否需要独立审批须按字段业务属性决定。旧申请字段集及已有来源、结果指纹须保留原版本验证，新字段不能使历史审批失效或将未知升级为已核实。
- 当前 PI 打印内容及两套 XLSX 的卖方、银行、模板、配置和摘要随报价冻结，现有模板仅有一组买方地址/联系人位置。新增字段需明确新模板版本及旧报价修订选用策略；不得改写冻结资源或在字段已保存但模板无法展示时静默声称输出完整。
- 待业务确认：现有买方地址/联系人含义；收货人是否需要公司、电话、邮箱和国家；三项是否必填、账单抬头及税号是否独立；哪些变更须审批；旧模板修订如何输出；以及是否传递到 SO、出货、装箱和财务单据。
- 验收须覆盖历史 `NULL`、明确留空、新单、普通/订单触发修订、审批与旧指纹兼容、权限隐藏，以及保存版 PI 和实际 XLSX 的新旧模板输出；前端改动还须完成自动回归及真实 Chrome 视觉验证。以上为方案与待决边界，尚未实施或验收。

隔离运行器日志中仅对随机生成、运行结束即失效的测试令牌进行了脱敏；HTTP 状态、错误、结果及失败上下文保留。运行 `redact_ephemeral_test_tokens.py` 可复现同一脱敏规则。
