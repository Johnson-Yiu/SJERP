# 合成核心闭环：真实 HTTP 验收

集成起点为 `4388947d70d26bca66ca0bfc76b2383a2fc0d404`；当前复核 HEAD 为 `0914002b5d8b3c848b1a78d2cc6e0419764d9053`。coreHTTP 拒绝用例及 `Supplier.code="RV"` fixture 修正已包含在该提交；主审启动 PG 专项后 backend 冻结，当前无 backend 工作树改动。测试文件：`backend/crm/tests/test_review_core_http.py`。

## 之前的实际执行（新增拒绝用例前）

`logs/core-http-rbac-20261104.log`：2 项通过、0 失败、0 跳过，98.105 秒；SQLite 隔离测试数据库，Django LiveServer 实际 HTTP，请求由 `http.client` 发出。开发超级管理员关闭，RBAC 和审计开启。正向使用合成 Django superuser 的有效 session，并发送 CSRF cookie/header；登录 session 由测试夹具建立，不代表 ERP 业务登录入口或普通员工角色验收。

报价、订单、采购、收货、发货、应收应付及流水状态变更均调用业务 HTTP 端点，不绕过 serializer 制造正式业务单据。客户、SKU、供应来源等仅为隔离参考夹具。

| 范围 | 实际检查 |
|---|---|
| 销售及文件 | 报价保存、接受、转订单、订单确认、保存重开；下载实际 XLSX 并验证客户/产品/数量/金额内容；实际 CSV 与报表数据对应 |
| 资金旧支持范围 | 应收和应付计划、结算、无效金额拒绝、流水作废及余额恢复；新账户资金规则尚未集成，不能扩大为退款新规则验收 |
| 采购及部分履约 | 分配供应来源、生成采购、取消和重新生成、账期、下单、部分收货及部分发货 |
| 拒绝与冲销 | 超量发货拒绝、已有履约取消拒绝、已消耗收货冲销拒绝；先冲销发货再冲销收货，最终取消采购和销售 |
| 原子性和操作人 | 拒绝前后库存、预留、单据、付款和审计快照保持一致；所有成功操作审计关联当前合成 session 用户，不把默认开发姓名当实名 |

实际响应的 SHA256、状态码、UTF-8 解析依据及拒绝响应原始字节记录在日志。下载原文件与数据库前后快照位于 `artifacts/http-rbac-20261104/`，文件摘要在各 manifest 中。此前失败及修正迭代日志、旧范围成功日志均保留，不能代替本次结果。

## 尚未扩大认定的范围

- PostgreSQL 17 上运行本新增测试的结果待实际执行。
- Chrome 中逐步完成整条业务闭环尚未完成；自动 HTTP 结果不能代替视觉验收。
- 该测试使用进程内临时数据库，快照是合成记录导出，不是生产备份恢复证据。
- 正式员工鉴权、部署私有媒体 ACL、外部银行凭证、新资金服务、历史承接与运维联合恢复须分别验收。

## 权限拒绝、CSRF 与财务范围补充（开发侧交叉自查）

只读核对版本：`ce74f8b7cf6cd1e1e4e8f50141d9fc38e86c3903`。本节是开发侧覆盖核对，不是独立 ChatGPT 复审或权限验收。

### coreHTTP 当前覆盖边界

- `backend/crm/tests/test_review_core_http.py` 的 `setUp` 创建隔离合成 superuser，再用 `Client.force_login` 建立 session；`_request` 对每个请求都发送该 session cookie、CSRF cookie 和有效 `X-CSRFToken`。因此两项通过只证明合成 superuser 在 `DEVELOPMENT_SUPERADMIN=false`、`RBAC_ENFORCEMENT=true`、`AUDIT_LOG_ENABLED=true` 下能走正向业务路径。
- 本轮新增真实 HTTP 拒绝用例：不带 session、有效 session 缺少 CSRF header、错误 CSRF token、以及仅有报价查看权的合成非 superuser 尝试新建报价。四条拒绝请求均断言 Quote、业务数据库快照和 OperationLog 与请求前一致。它仍未验证 `/api/current-operator` 或 ERP 业务登录入口；无报表查看权的数据源拒绝也未覆盖。不得据此宣称真实员工登录或普通员工身份验收。
- 财务正向范围仅为旧 `PaymentPlan`/`Transaction` 路径：销售应收与采购应付计划、结算、零金额拒绝、流水作废及计划余额恢复。没有调用 `/api/rmb-cash-events/`，也没有验证银行事实确认、待确认事件、重复识别、手续费关联、退款/更正或新资金统计口径。
- 当前代码已有 `RmbCashEvent` 路由、`cash_api.py` 与 `services/cash_events.py`；这表示相关代码存在，不表示功能已经完整集成或经过 coreHTTP 验收。ISS-105/ISS-108 的专项结论仍以 [Issue 矩阵](ISSUE-MATRIX.md) 和对应财务证据为准。原“新账户资金规则尚未集成”在本报告中应理解为未纳入本 coreHTTP 闭环验收，不应解释为仓库中完全没有相关代码。

### 关闭这些覆盖缺口所需的可执行证据

| 缺口 | 可执行场景与通过条件 | 当前结论 |
|---|---|---|
| 未认证拒绝 | 真实 LiveServer 对不带 session 的 `POST /api/quotes/` 拒绝，并核对 Quote、业务快照及 OperationLog 不变。当前本地认证配置返回 403；部署 challenge 配置可返回 401。 | SQLite 定向回归已覆盖；PG17 定向复跑待主审安排 |
| RBAC 受限拒绝 | 合成非 superuser 员工仅有 `quotes.can_view`，带有效 session/CSRF 对 `POST /api/quotes/` 得到 403，且 Quote、业务快照及 OperationLog 不变。无 `reports` 权限时 `/api/reports/data/` 的数据源拒绝仍未覆盖。 | 报价新建拒绝已覆盖；报表数据源拒绝未覆盖。通过只证明合成角色权限路径，不证明真实员工登录入口 |
| CSRF 拒绝 | 已认证 session 分别省略 `X-CSRFToken`、发送错误 token；两者均为 403，且 Quote、业务快照及 OperationLog 不变。 | SQLite 定向回归已覆盖；PG17 定向复跑待主审安排 |
| 旧财务路径在 PostgreSQL 17 | 对最终 SHA 执行 `backend/manage.py test crm.tests.test_review_core_http`；PG17 日志须记录通过/失败/跳过并核对该运行的文件及快照证据。 | 本轮本地 SQLite 3/3；主审 PG1199 记录为 3 errors、30 skipped，详情仍在提取，不能记为通过，需在 PG17 上复跑 |
| 新资金规则与退款更正 | 单独核对 `crm.tests.test_cash_events`、`crm.tests.test_cash_duplicate_review`、`crm.tests.test_actual_cash_reporting` 的 PostgreSQL 17 实际结果及其断言/报告；如需宣称真实 HTTP 闭环，还须有 LiveServer HTTP 请求和数据库/资金事实前后证据。不得用 coreHTTP 的 PaymentPlan/Transaction 结果替代这些专项验收。 | coreHTTP 未覆盖；专项状态依各自证据，不在本节判定 |

本轮测试变更仅限原 HTTP test 文件，不修改 Issue 台账；不把合成 superuser 的 `force_login` 视为登录、员工身份或权限验收通过。

### Supplier 合成 fixture 更正及本轮定向结果

- 更正先前关于国家字段的推测：`Supplier.country` 是 `max_length=100` 且默认值为“中国”；触发 PostgreSQL `varchar(2)` 错误的是 `Supplier.code`（“供应商二字代码”，`max_length=2`）。测试 fixture 已改用 `code="RV"`，country 保持模型默认值；未修改业务模型。
- 修正后曾使用本包 `.tmp/review-integration-python/Scripts/python.exe` 执行 `backend/manage.py test crm.tests.test_review_core_http --verbosity 1`，设置开发超级管理员关闭、RBAC 与审计开启，SQLite 进程内隔离数据库；交互终端显示 3 项通过、0 失败、0 跳过（132.142 秒）。该轮 stdout 未重定向到文件；在本包 logs 与工作树文件中均未找到其原始日志，因此不能提供或声称已归档该轮原始日志。本机没有可安全使用的隔离 PostgreSQL URL，此结果不验证 PostgreSQL varchar 约束。
- 上述 3/3 轮的终端输出显示拒绝响应：当前本地认证配置下匿名、缺失 CSRF、错误 CSRF、受限角色四条路径均为 HTTP 403；测试逐条核对业务快照、报价记录和 OperationLog 未新增或变化。合成员工及 superuser session 仍不代表 ERP 业务登录或真实员工身份验收。

## 最终日志归档与 backend 冻结

- 随后保存的完整定向运行日志为 `logs/core-http-final-20261104.log`，SHA256：`0b2da695ad0ebee2811733282cae6982eb0abfc5837390902cf99812bd237236`。该日志实际记录 3 项测试、1 项失败（111.218 秒），**不能作为 3/3 通过证据**。
- 失败发生在 `test_purchase_partial_fulfillment_reversal_cancel_and_atomic_failures_over_http.tearDown`：`test_http_auth_csrf_and_rbac_denials_have_no_business_or_success_audit` 与采购用例都被测试证据命名逻辑分到 `procurement-manifest.json`，后一个测试因拒绝覆盖既有 manifest 而失败。HTTP 拒绝路径本身返回预期 403；销售用例通过。证据目录 `artifacts/http-final-20261104/` 已保留，采购 manifest 与两份采购快照不构成完整同轮 manifest 证据。
- 因此，3/3、132.142 秒结果确有当时终端输出，但其原始日志文件不存在；可复核的最新原始日志是上述 3 测试/1 失败文件。PG1199 仍记录 3 errors、30 skipped，主审正在提取原因；不得标为通过。
- 冻结确认：HEAD 为 `0914002b5d8b3c848b1a78d2cc6e0419764d9053`，本轮之后未改 backend；PG 专项进行中。本文档为获准的报告更新，不改变测试代码或台账。

## 后续已核实结果（替代上节“最新”状态，不删除失败历史）

证据命名前缀已分别设为 denials、procurement、sales，避免两场景覆盖同一 manifest。`logs/core-http-prefix-unique.log` 实际 3/3、107.906 秒；随后启用完整合成数据库保存的 `logs/core-http-with-database-snapshots.log` 实际 3/3、103.842 秒，0 失败/跳过。

`artifacts/http-with-database-snapshots/` 包含三份完整 SQLite 文件、逐场景 manifest、HTTP 请求响应摘要、业务前后快照和实际 XLSX/CSV。三库 integrity_check 均为 ok，文件摘要保存在各自 manifest；不是实际业务数据库。真实一次性 PostgreSQL 17 的 a866c29 专项 42/42 亦包含这三个真实 HTTP 场景，原先 Supplier.code 超长已修正；旧失败结果不再作为当前状态。

财务来源合入后的完整后端运行 `logs/backend-full-c1937da.log` 再次执行三个 HTTP 场景且通过；全套1249、1189通过/60跳过，不等于后续全部来源的最终版本。
