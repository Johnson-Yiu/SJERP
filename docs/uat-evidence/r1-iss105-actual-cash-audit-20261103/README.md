# R1-ISS105-ACTUAL-CASH-AUDIT

审查日期：2026-11-03。审查源码 SHA：`8d3ca5faa16fb74de95dbc716f5556a5d51bbe79`。

分支：`codex/r1-iss105-actual-cash-audit-20261103`。本提交只增加本目录的审查材料，不修改业务代码、原测试、迁移、配置或共享台账，不访问业务数据库，不改变 Issue 状态。

## 1. 结论和历史成果边界

**部分实现，不能作为公司全量实际资金统计验收通过。** 已有结汇、人民币直接收付、独立银行手续费的人工确认事实；实际统计与账面折算分离、同请求重放、来源额度、权限和历史保护已有实现及测试。缺少内部转账排除、多字段银行重复识别、现金账户分类、启用基准余额、完整核对状态及待分类事实流程。

另外确认一个现有前后端契约差异：API 接受无结汇父事件的独立银行手续费，资金页面却强制要求关联结汇。这里只记录，不修复。

已阅读 `docs/R1-FIN-P3-B-财务统计最终业务闭环验收.md`、`docs/PROJECT_ISSUES.md` / `PROJECT_PHASES.md` 相关历史及旧 ISS-105 财务来源静态审计（2026-10-31 独立工作树）。旧验收明确不实现账户余额、启用日期或全量覆盖；本轮不能把这些既有范围声明误说成新回归，也不能用旧阶段 PASS 覆盖本次十项规则的缺口。

## 2. 逐项业务规则核对

| 规则 | 当前状态 | 当前证据及边界 |
|---|---|---|
| 1 内部转账不计公司流入/流出 | 未实现 | `models.py:1902` 仅三种资金类型；`cash_events.normalize:183` 拒绝 internal_transfer；`actual_cash_api._summary:71` 只按方向累加。合成内部转账若用可用的 cny_direct 表达，两端各100被计流入100/流出100，净额0，但毛流量错误。不是声称真实历史记录已被污染。 |
| 2 全部已核实人民币银行资金纳入并按性质分类 | 部分实现 | 支持有 confirmed Transaction 来源的三种事件，确认凭证和受控账户后计入；`validate_sources:227`、`normalize:209` 强制1–100条来源。缺少完整银行导入/覆盖清单，退款等不确定来源主动拒绝，只有 cny_direct 等粗分类；API 明示 registered_confirmed_only / coverage_configured=false。 |
| 3 外币收款参考、结汇人民币一次 | 已实现于支持路径 | `available:152` 扣 confirmed 分配；`confirm_event:291` 锁来源并重新验证。实际统计只读银行净额，不读 Transaction.rmb_amount，不创建第二笔业务收款；已有分次/合并结汇及旧表哈希测试。跨请求银行重复识别另见规则8。 |
| 4 独立手续费按银行事实处理 | 部分实现 | 后端要求独立 CNY bank_fee 来源，含扣费不再扣净额；关联父结汇时验证父事件无含扣费及账户一致。但前端 `CashEventPage.vue:188` 强制 fee_for，遗漏不属于结汇的真实独立银行扣费。 |
| 5 现金与银行分开 | 未实现 | 受控账户只有字符串白名单；没有 cash/bank 账户类型和分开报表。现有界面仅声称银行资金，未发现将一个已有现金账本显式混入的实现；缺的是可验证分类边界。 |
| 6 启用余额来自对账单、独立基准不算收入 | 未实现 | 无 opening_balance 模型/基准日期/对账单绑定；提交该类型400。API 不返回余额，前端明确不推测期初/期末。不能把普通收入代作期初。 |
| 7 账面折算不混实际人民币 | 已实现 | `actual_cash_api.py:66–100` 使用 confirmed 的 bank_net_amount / bank_date；`reporting.py:130–141` 同口径；`views._finance_cash:2375` 为独立旧参考路径；`FinanceDashboardPage.vue:184–195` 分区展示。测试故意改变 rmb_amount，实际统计不变。 |
| 8 六维重复识别 | 未实现（只有请求幂等） | event_no/request_key 唯一、同键同内容重放有效，但没有账户/日期/金额/币种/对手/摘要的候选重复判断；事件没有独立交易对手/银行摘要字段。探针同来源剩余额度内、同账户/日期/银行参考/金额换请求键可确认两次，合计200。合法同额两笔也必须允许，不能简单唯一金额。 |
| 9 流入/流出/净变动/余额/核对状态 | 部分实现 | API、财务概览、报表/CSV有前三项及明细；人工凭证确认 status 不是银行对账状态，未实现基准余额滚算及银行差异核对。明示不是余额，不冒充已完成。 |
| 10 未知性质保留待分类 | 未实现 | unknown 类型400，无待分类性质字段/队列。已有 pending 是凭证待确认，不等于性质待分类；原 Transaction 可能仍保留，但没有对应待分类银行事实流程，不能默认映射 cny_direct 后算作完成分类。 |

表内路径除前端外相对 `backend/crm/`；行号均对应审查 SHA，不是本报告提交的业务变更。

## 3. 按严重程度排序的问题和最小建议

### P1 CASH-01：内部转账缺少成对事实和公司毛流量排除

位置：`models.py:1896–1933`；`services/cash_events.py:157–223`；`actual_cash_api.py:71–100`；`reporting.py:130–141`。

探针 `test_intended_internal_transfer_has_no_supported_exclusion`：把合成的自有账户转出100/转入100表达为现有人民币直接收付，真实 API 返回 inflow100 / outflow100 / net0。显式 internal_transfer 被400拒绝。现有系统无法同时满足“完整收录银行事实”与“排除公司内部毛流量”。

最小建议：新增明确的账户归属及转账配对语义，保留账户级变动，公司级统计排除配对内部本金；手续费仍独立流出。未知历史不得自动配对或重分类，先人工核对。

### P1 CASH-02：请求幂等不等于真实银行重复识别

位置：`models.py:1898–1914`；`services/cash_events.py:262–287`；`actual_cash_api.py:71`。

探针 `test_same_bank_fact_different_request_keys_is_not_deduplicated`：同一200元来源被两次各分配100；账户、日期、币种、金额、银行参考号相同，换编号/键后均201并确认200，统计200。系统确实允许此状态；是否现实中重复付款须由银行凭证判断，本审查没有连接真实银行或业务库。原测试 `test_f_cny_direct_identical_amounts_are_distinct_real_events` 只证明合法同额交易允许，不覆盖六维候选重复。

最小建议：保留请求幂等，另外记录原始银行交易标识、交易对手及摘要，六维生成重复候选并核实/留痕放行；不得用“同日同额必须唯一”误伤合法收付。

### P1 CASH-03：资金覆盖和性质状态尚不完整

位置：`services/cash_events.py:133–149,183,209–223,227–246`；`actual_cash_api.py:136–150`。

只支持三类、有具体业务流水来源；退款、供应商退款、汇兑差异、替代链等不确定来源安全拒绝。没有待分类银行事实类型、全量核对清单或账户覆盖起点。`unknown` 返回400，不能把 pending 凭证状态当作待分类。

最小建议：在 ISS-108/ISS-121 政策确定后扩充可追溯银行事实/分类流程；未知性质明确保留，报表展示未分类覆盖差距。保留现有退款、更正 fail-closed，不为了“全部统计”绕过来源保护。

### P2 CASH-04：独立手续费前端额外要求结汇父事件

位置：`frontend/src/views/CashEventPage.vue:177–189` 的 `clientError`；后端 `services/cash_events.py:206–208,242–251`。

探针 `test_independent_bank_fee_api_does_not_require_fx_parent`：独立 CNY 手续费5、fee_for=null，API 创建201/确认200，报表流出5。源码明确在预览之前因未选父结汇返回错误。因此没有结汇的银行扣费不能走现有页面正常登记。

最小建议：允许不关联结汇的独立手续费，仍严格要求独立手续费来源、凭证、账户与人工确认；仅在选择关联时校验父事件。保留含扣费重复扣减保护。该前端结论为源码与真实 API 契约对照，**本轮未运行 Chrome，不宣称浏览器复现**。

### P2 CASH-05：现金分类、启用余额及核对体系缺失

位置：`models.py:1909–1928`；`config/settings.py:72`；`actual_cash_api.py:71–100,136–150`；`frontend/src/views/FinanceDashboardPage.vue:184–192`。

无账户类型、启用对账单基准、可核算余额/对账状态。最小建议依赖 ISS-121 先定义账户及启用基准，之后余额=基准+已确认变动，现金/银行分别展示，保留差异及更正凭证；不回写历史事实，不把启用余额计新流入。

### P2 CASH-06：凭证摘要是人工声明，操作审计为事件快照而非完整日志

位置：`services/cash_events.py:52–55,252–257,262–335`；`cash_api.py:47`；`audit.py:42–68`。

确认只检查 evidence_sha256 为64位十六进制、引用和说明非空；未把摘要与实际凭证文件计算绑定。创建/确认/放弃在事件中保存 actor 与时间/理由，但 ViewSet 不继承 AuditTrailMixin，也未调用 record_operation；signals 无资金事件通用审计钩子。探针在已认证、AUDIT_LOG_ENABLED=True 下创建并确认，OperationLog 增量0，同时事件 actor 快照存在。不是“完全无审计”，也不是文件 SHA 已验证。

开发身份复用统一入口，明确标注 development_superadmin / 非正式员工审批，不伪造真实操作人；该机制按要求保持。最小建议：需要正式验收时由受控凭证存储计算/绑定摘要，并在同事务追加状态操作日志；保留真实登录与开发身份区别。是否要求制单/复核分离应另行确认，不在本轮擅自增加权限政策。

## 4. 已有保护和测试覆盖

- `cash_events.access/source_visible/visible`（46/58/74）：财务操作权、财务查看与流水查看叠加；批次含无权来源则整批隐藏；关联归属改变也隐藏，不泄露快照。`CashPermissionsTests` 及 finance_data_scope 实际执行通过。测试使用局部权限设置，没有启用运行服务的正式 RBAC。
- `register_event:262` 事务创建事件和来源；唯一键重放同内容返回原结果，异内容409；`confirm_event:291` 在有序来源/往来方/事件锁下重新检查额度、快照和凭证；已确认再确认幂等。SQLite 不证明 PostgreSQL 锁语义，本轮3项并发测试明确跳过。
- `models.RmbCashEvent.save/delete:1933`、`CashSourceAllocation.save/delete:1961` 应用层禁止覆盖/删除；`guard_void/replacement/refund:338–356` 阻止危险历史改写。`correction_of` 字段存在但目前明确拒绝，不能误称更正已实现。
- `test_failure_after_event_creation_rolls_back_both_tables`、`test_confirm_failure_after_status_update_is_rolled_back` 验证事务回滚；旧表前后哈希相同。0077 为加法迁移，测试从0076迁移到0077并对比历史行及四位金额精度，本轮通过。未新增迁移。
- CSV：实际接口与报表中心使用同一 confirmed 银行净额、银行日期，CSV公式转义已有实测。旧 cash 来源仍是折算参考，不与 actual_cash 叠加。
- 前端已有双阶段预览/登记/核实、稳定请求键查结果、失败反馈、日期请求版本防竞态等源码回归；没有银行重复候选/转账排除/独立手续费无父事件的 UI 行为覆盖。Node测试不是浏览器视觉验收。
- 额外风险边界：模型 save/delete 保护并非数据库 append-only 触发器（0077仅金额/状态/分配唯一约束），不应把它宣传为能防任意直连SQL/QuerySet.update。本轮未对实际库做此操作，亦未据此声称现有API可绕过。

## 5. 本次真实执行结果、原始日志和复现命令

环境：Windows，`C:\Python314\python.exe` **CPython 3.14.5**、Django **6.0.6**、DRF **3.17.2**，非Python3.12，非干净锁定安装；测试基线代码未改。Node版本见日志。所有 Django 命令显式 `APP_STAGE=development`、`DATABASE_URL=sqlite:///:memory:`，运行测试库为 `file:memorydb_default?mode=memory&cache=shared`，MEDIA_ROOT使用每次新建的临时路径。只用合成资料、测试内存库，测试结束由 Django 销毁，不读取工作树 sqlite 文件。

| 执行 | 结果 |
|---|---|
| cash_events + actual_cash_reporting + finance_reference_basis + finance_data_scope + finance_retry_safety | 56项：53通过、3跳过、0失败（23.712s） |
| 本目录 probe_tests | 5项通过，0跳过/失败；“通过”表示确认现有缺口行为，不表示业务合规通过 |
| Node：CashEventPage / FinanceDashboardPage / financeBasis / reports registry | 8项通过，0跳过/失败 |
| Django check | 无问题 |
| makemigrations --check --dry-run | No changes detected |
| PostgreSQL并发 | 未执行；3项原因均为 `Real PostgreSQL locks required`，需独立隔离PG环境后续验收 |
| Chrome、全量后端/前端、生产构建 | 本次未执行，属于只读业务代码审查，不借用历史结果冒充本轮结果 |

原始输出打包在 [logs/raw-logs.zip](logs/raw-logs.zip)，包含 environment.txt、backend.txt、probes.txt、node.txt、node-version.txt、check.txt、migrations.txt。原始日志不改写，不含访问凭证。独立探针源码：[probe_tests.py](probe_tests.py)。日志包 SHA256 见 [logs/SHA256.txt](logs/SHA256.txt)。

在本工作树 backend 目录执行（每条检查退出码）：

```powershell
$env:APP_STAGE='development'
$env:DATABASE_URL='sqlite:///:memory:'
$env:PYTHONUTF8='1'
$env:MEDIA_ROOT=Join-Path ([IO.Path]::GetTempPath()) ('iss105-audit-'+[guid]::NewGuid())
C:\Python314\python.exe manage.py check
C:\Python314\python.exe manage.py makemigrations --check --dry-run
C:\Python314\python.exe manage.py test crm.tests.test_cash_events crm.tests.test_actual_cash_reporting crm.tests.test_finance_reference_basis crm.tests.test_finance_data_scope crm.tests.test_finance_retry_safety --verbosity 2
$env:PYTHONPATH=(Resolve-Path '../docs/uat-evidence/r1-iss105-actual-cash-audit-20261103').Path
C:\Python314\python.exe manage.py test probe_tests --verbosity 2
# frontend目录
node --test src/views/CashEventPage.test.js src/views/FinanceDashboardPage.test.js src/utils/financeBasis.test.js src/reports/registry.test.js
```

## 6. 依赖、冲突和下一轮建议

- ISS-108：退款、供应商退款、替代及凭证更正的来源政策影响已确认资金；不要解除现有保护来补统计。
- ISS-121：启用日期、账户覆盖和期初基准决定余额可核算性，须先定义后实施；不得猜测历史余额。
- ISS-122/123及既有财务权限/报表口径：保持 confirmed 来源额度、精度和含扣费规则；新增转账/分类应同时更新实际API、报表中心、概览及CSV，不能改变旧 cash 折算语义。
- ISS-052审计成果提供通用append-only经验，但CSV审计表保护不自动覆盖资金表，不应直接复用CSV状态或伪造导入批次。
- 本轮其余ISS-037/039是独立证据分支；采购成本归属不得生成新资金事件，主体快照不得按现主档反向重写资金来源历史。

建议优先处理 CASH-01/02，明确覆盖与分类模型后处理 CASH-03/05，独立最小修复 CASH-04；CASH-06 在正式审计验收前补齐。所有建议等待独立审查授权。本轮不触发GitHub Actions、不创建PR、不合并、不部署。
