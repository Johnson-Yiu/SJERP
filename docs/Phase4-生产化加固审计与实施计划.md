# Phase 4A — 生产化加固审计与实施计划

审计分支：`phase-04a-production-readiness-audit`  
审计基线：`master` / `907a3991dadde19a31cbe02f27d0c5b789405c51`  
审计日期：2026-09-27  

本轮只读审计并新增本文件，未修改 models、serializers、views、services、frontend、settings、requirements、migrations，未连接或迁移任何生产数据库，未改变 Phase 3B UAT 数据。

## 1. Executive summary

当前系统可以继续作为 development 环境运行，但还不能直接作为 production 部署。主要阻断项是：

1. `backend/requirements.txt` 没有 PostgreSQL driver；`dj_database_url` 能解析 PostgreSQL URL，但运行时没有可保证的 DB driver。
2. `REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES` 为 `AllowAny`，绝大多数业务 ViewSet 和 action 没有后端鉴权。
3. 没有应用登录、登出、current-user 登录链或前端登录页；`/session/current-operator/` 只是状态展示接口。
4. `DEVELOPMENT_SUPERADMIN=true`、`RBAC_ENFORCEMENT=false`、`DEBUG=true`、`ALLOWED_HOSTS=*` 和 secret fallback 均不适合生产。
5. `AccessRole`/`RolePermission`/data scope 字段已建模，但业务 QuerySet 没有统一数据范围过滤。
6. 审计 hook 覆盖了不少 CRUD 和关键动作，但默认关闭，且 append-only 只由 API 只读视图保证，没有数据库级不可修改约束。

本轮没有确认业务逻辑 bug；结论是生产化配置、认证、权限、数据库和运维能力尚未完成。

## 2. Current state and production configuration

| 项目 | 当前代码/默认值 | development 合理性 | production 风险 | production 建议 | 是否必须改代码 |
|---|---|---|---|---|---|
| `DJANGO_SECRET_KEY` | env；缺省 `dev-only-change-me` | 可用于本地 | 固定 secret 可伪造 session/签名 | 必须由 secret manager 注入，缺失即拒绝启动 | 启动检查或部署脚本 |
| `DJANGO_DEBUG` | 缺省 `true` | 便于调试 | traceback、静态/媒体调试暴露 | `false` | 仅环境变量；建议增加 fail-fast |
| `APP_STAGE` | env；按 DEBUG 默认 development | 正确标识本地 | 可能误以为生产已切换 | 明确设为 `production` | 环境变量 |
| `DEVELOPMENT_SUPERADMIN` | 缺省 `true` | 无账号时便于 UAT | 未关闭即绕过权限 | `false` | 环境变量；建议启动阻断 |
| `RBAC_ENFORCEMENT` | 缺省 `false` | 保持当前开发契约 | 业务 API 不受角色权限保护 | `true` | 环境变量并完成权限实现 |
| `AUDIT_LOG_ENABLED` | 缺省 `false` | 避免本地写日志 | 关键动作没有审计证据 | `true` | 环境变量；前提是有真实认证 |
| `DEFAULT_OPERATOR_NAME` | `Johnson` | 空用户开发展示 | 伪造操作人/审计归属 | 不作为身份来源 | 环境变量/代码校验 |
| `ALLOWED_HOSTS` | 缺省 `*` | 本地多地址方便 | Host header 攻击面扩大 | 仅生产域名/内网地址 | 环境变量 |
| `CORS_ALLOWED_ORIGINS` | 缺省 localhost:5191、127.0.0.1:5191，credentials 开启 | 本地 Vite 合理 | 生产域名、cookie 跨站策略需显式收紧 | 只列生产前端 origin | 环境变量 |
| DRF 默认权限 | `AllowAny` | 当前开发可直接使用 | CRUD 和 action 可被匿名调用 | 全局 `IsAuthenticated`，再按 action 放行 | 必须改配置/权限 |
| `DATABASES` | `dj_database_url`，缺省 SQLite | 单机开发简单 | 无 PostgreSQL driver；SQLite 锁语义不同 | staging/production PostgreSQL | requirements + 环境 |
| `STATIC_ROOT` | `backend/staticfiles` | 可本地 collectstatic | 需由 Nginx/持久卷提供 | 独立 release/static volume | 部署配置 |
| `MEDIA_ROOT` | `backend/media` | 本地文件方便 | 单机磁盘、备份和多实例不安全 | 持久卷或对象存储 | 部署；后续可改 storage |
| CSRF | middleware 已启用，未配置 production trusted origins | 本地同源/开发可用 | HTTPS、跨域 session 提交需明确配置 | trusted origins、secure cookie、HTTPS | 配置/部署 |
| HTTPS/cookie | 未显式设置 redirect、proxy header、secure cookies、HSTS | 本地无需 | 明文或代理误判，session/cookie 暴露 | Nginx TLS + secure/httponly/samesite + HSTS | 配置/部署 |
| password validators | `AUTH_PASSWORD_VALIDATORS=[]` | 测试账号方便 | 弱密码无阻止 | 启用 Django validators | settings |

当前开发环境的 superadmin 约定必须保留到 production 设计完成前，但不能被当作 production authentication。

## 3. PostgreSQL readiness audit

### 3.1 三档矩阵

| 项目 | 结论 | 证据/风险 |
|---|---|---|
| PostgreSQL driver | **BLOCKER** | `requirements.txt` 只有 `dj-database-url`，没有 `psycopg`/`psycopg2`；全新环境不能仅按现有 requirements 可靠连接 PostgreSQL |
| DATABASE_URL 解析 | **SAFE WITH DRIVER** | `dj_database_url.config()` 已使用标准 URL 配置；默认仍回落到 SQLite |
| 原生 SQL/SQLite 专用 SQL | **SAFE（初步）** | 审计 backend 未发现业务 raw SQL、`sqlite3`、PRAGMA 或 SQLite 方言依赖；仍需 staging 实测 |
| ORM 查询/聚合 | **SAFE WITH TEST** | 主要使用 Django ORM、Subquery、Coalesce、Case、JSONField；需在 PostgreSQL 跑完整测试和关键报表核对 |
| JSONField | **SAFE WITH TEST** | Django JSONField 用法可跨数据库；需核对空值、键类型和索引计划 |
| Decimal/金额 | **SAFE WITH TEST** | DecimalField 定义明确；迁移后必须逐笔核对金额、汇率、成本分配 |
| transaction.atomic | **SAFE WITH TEST** | 关键编号、履约、财务服务广泛使用 atomic；SQLite 不等价模拟并发锁 |
| select_for_update | **RISK** | 关键服务使用锁，但 SQLite 下锁语义不足；必须在 PostgreSQL staging 做并发测试 |
| unique/conditional constraints | **SAFE WITH TEST** | 模型使用 UniqueConstraint，包括条件唯一约束；需执行迁移并检查历史脏数据 |
| NULL/排序/大小写 | **RISK** | PostgreSQL 与 SQLite 的 NULL 排序、文本比较和排序规则可能不同；列表、国家、SKU/编码搜索需回归 |
| bulk_create/bulk_update | **RISK** | 业务使用 bulk 操作，需核对默认值、信号、返回主键和约束失败时的事务行为 |
| 时间与时区 | **SAFE WITH TEST** | `USE_TZ=True`、`Asia/Shanghai`；必须以 UTC 存储/接口序列化为准在 staging 验证 |
| 自增 sequence | **RISK** | SQLite integer id 与 PostgreSQL sequence 行为不同；导入后必须校准并验证下一个编号 |

因此 PostgreSQL readiness 当前为：**1 个明确 blocker，多个需要 staging 验证的风险，无已确认的 SQLite-only 业务 SQL blocker**。

### 3.2 SQLite → PostgreSQL migration strategy（不在本轮执行）

1. **开发**：继续保留 SQLite，保持快速本地 UAT；不把 SQLite 锁行为当作并发保证。
2. **staging**：创建与 production 同版本的 PostgreSQL，安装明确版本的 `psycopg`，运行所有 migrations 和完整回归。
3. **schema**：冻结 release，备份 SQLite，执行 `showmigrations`/`makemigrations --check`，在 staging 应用全部 migration。
4. **data**：使用受控 Django 数据迁移/导出导入工具，不用手写 SQL 猜字段；先导入基础资料，再导入交易和快照，保留外键顺序。
5. **media**：迁移 `MEDIA_ROOT` 下 SKU image、QuoteItem image_snapshot、FollowUp attachment；逐文件保留路径、大小、SHA256。
6. **sequence**：对所有自动编号表检查 `MAX(id)` 与 PostgreSQL sequence，另行核对客户、产品、报价、订单、采购编号业务 sequence。
7. **row count**：迁移前后按模型输出 count；重点模型包括 Customer、SKU/SKUVersion、Quote/QuoteItem、Order/OrderItem、Purchase/Receipt、Shipment/Movement、Transaction/PaymentPlan、OperationLog。
8. **业务校验**：逐项校验订单/采购/收发货数量、库存 actual/reserved/available、PaymentPlan settled/remaining、Transaction split/allocation、采购成本分配和 Quote revision 链。
9. **切换**：staging smoke/UAT 全绿后短暂停写，执行最终增量、校验、切换 Nginx/Gunicorn 到 production DB。
10. **rollback**：保留旧 SQLite 只读备份与 PostgreSQL pre-cutover backup；在校验失败时切回应用版本/DB endpoint，不在生产库中“向前修复”未知数据。
11. **backup drill**：上线前完成一次 PostgreSQL restore 到隔离环境，并验证 media 与 DB 可共同恢复。

## 4. Authentication audit

| 能力 | 状态 | 证据/结论 |
|---|---|---|
| Django User model | IMPLEMENTED | 使用 Django auth user，EmployeeProfile 与用户一对一关联 |
| SessionMiddleware/AuthenticationMiddleware | IMPLEMENTED | settings 已启用 |
| 应用登录 endpoint | MISSING | `crm/urls.py` 没有 login/token/JWT endpoint；只有 Django admin 的默认登录 |
| 前端登录页 | MISSING | router 无 login route；主应用直接加载工作台 |
| current-user | PARTIAL | `/api/session/current-operator/` 返回展示状态，不建立身份、不签发凭据 |
| logout | MISSING | 未发现应用 logout route 或前端 logout flow |
| session expiration | PARTIAL | Django 默认机制存在，但未配置 production timeout、rotation、强制失效策略 |
| CSRF | PARTIAL | middleware 存在；无 production trusted origins/secure-cookie 验证 |
| credential transport | MISSING/PARTIAL | 没有明确应用登录凭据传输；现有 API 可匿名访问 |
| frontend route guard | MISSING | `router.beforeEach` 只处理 modal 路由，不检查认证 |
| API 401 handling | MISSING | Axios 主要做重试和错误消息，无统一跳转登录/刷新 session |
| production authentication | MISSING | development superadmin 不能替代真实登录/RBAC |

结论：认证链为 **PARTIAL（Django 基础组件存在）但业务登录为 MISSING**。

## 5. RBAC and data-scope audit

### 5.1 RBAC maturity

成熟度：**模型和配置 UI 已存在，后端业务 enforcement 未完成（Level 1 / not production-ready）**。

已确认的后端保护只有：

- `PermissionAdminOnly`：AccessRole、RolePermission 写操作在 `RBAC_ENFORCEMENT=true` 时保护。
- `HSCodeMaintenancePermission`：HS code 非安全方法需要管理员。
- `QuoteExportPermission`：报价导出在非 development superadmin 时检查认证和 quotes export permission。
- `OperationLogViewSet`：读取要求 `IsAuthenticated`。

绝大多数其它 ViewSet/APIView 没有显式 permission_classes，因 DRF 默认 `AllowAny` 而可匿名调用。前端按钮隐藏或 `OrganizationPage` 的可编辑状态不是安全边界。

### 5.2 Business module matrix

`Backend enforced?` 描述当前真实后端，不把 UI 行为当权限；`Frontend hidden?` 仅表示是否存在展示层提示。

| Module | Read | Create | Update | Delete | Export | Special Action | Backend enforced? | Frontend hidden? | Data scope enforced? |
|---|---|---|---|---|---|---|---|---|---|
| Dashboard | AllowAny | — | — | — | — | summary | No | No | No |
| Customer | AllowAny | AllowAny | AllowAny | AllowAny | — | insights | No | No | No |
| Contact | AllowAny | AllowAny | AllowAny | AllowAny | — | — | No | No | No |
| FollowUp | AllowAny | AllowAny | AllowAny | AllowAny | — | attachments | No | No | No |
| Quote | AllowAny | AllowAny | AllowAny | AllowAny | export protected only | revise/accept | Partial | Partial | No |
| Order | AllowAny | AllowAny | AllowAny | AllowAny | — | confirm/cancel/packing/shipment | No | Partial | No |
| Purchase | AllowAny | AllowAny | AllowAny | AllowAny | — | allocation/receipt/payment/reversal | No | Partial | No |
| Inventory | AllowAny | AllowAny | AllowAny | AllowAny | — | manual adjustment | No | Partial | No |
| Supplier | AllowAny | AllowAny | AllowAny | AllowAny | — | preferred source | No | Partial | No |
| Product | AllowAny | AllowAny | AllowAny | AllowAny | — | SKU plan/candidates | No | Partial | No |
| SKU | AllowAny | AllowAny | AllowAny | AllowAny | — | image/packaging/trade unit | No | Partial | No |
| Category | AllowAny | AllowAny | AllowAny | AllowAny | — | reorder/attributes | No | Partial | No |
| Transaction | AllowAny | AllowAny | AllowAny | AllowAny | — | allocation/void | No | Partial | No |
| PaymentPlan | AllowAny | AllowAny | AllowAny | AllowAny | — | settle | No | Partial | No |
| Finance Dashboard | AllowAny | — | — | — | — | reporting | No | No | No |
| Cost Allocation | AllowAny | — | update action | — | — | preview/save | No | Partial | No |
| Organization | AllowAny | AllowAny | AllowAny | AllowAny | — | units/positions | No | Partial | No |
| Employee | AllowAny | AllowAny | AllowAny | AllowAny | — | role assignment | No | Partial | No |
| Permission | authenticated/admin write when enabled | protected write when enabled | protected write when enabled | protected write when enabled | — | permission matrix | Partial | Partial | No |
| Audit | authenticated read | — | — | — | — | operation log filters | Read only | No | No |

### 5.3 Data scope

`AccessRole.default_data_scope` 和 `EmployeeProfile.data_scope_override` 支持 `all/department_tree/department/self` 选项，但当前审计未发现统一的 QuerySet scope service 或在 Customer owner、FollowUp owner、Quote、Order、Transaction、Purchase、Supplier 查询中按用户范围过滤。当前结论：**字段/设计存在，实际数据范围 enforcement 为 MISSING**。

## 6. Special-action permission audit

| Action | Backend permission now | Frontend-only risk |
|---|---|---|
| Quote export | `QuoteExportPermission`（development bypass；RBAC off 时已认证用户可导出） | production 仍需统一认证和角色策略 |
| Quote revise / accept | No dedicated backend permission | Yes |
| Order confirm / cancel / complete | No dedicated backend permission | Yes |
| Supplier allocation | No dedicated backend permission | Yes |
| PO create/update | No dedicated backend permission | Yes |
| Receipt / receipt reversal | No dedicated backend permission | Yes |
| Shipment / shipment reversal | No dedicated backend permission | Yes |
| PaymentPlan settle | No dedicated backend permission | Yes |
| Transaction create / void | No dedicated backend permission | Yes |
| Advance allocation | No dedicated backend permission | Yes |
| Cost allocation | No dedicated backend permission | Yes |
| ContractChange approve | No dedicated backend permission | Yes |
| Inventory manual adjustment | No dedicated backend permission | Yes |

这些 action 的业务不变量仍由 service 校验，但不等于身份/角色权限保护。

## 7. Audit trail audit

`AuditTrailMixin` 为普通 create/update/delete 提供 hook；`record_operation()` 仅在 `AUDIT_LOG_ENABLED=true` 且 request user authenticated 时写入。当前 development 默认关闭，因此下表的 AUDITED 表示“代码 hook 存在”，不表示当前环境已经产生审计记录。

| Action | 状态 | 依据/缺口 |
|---|---|---|
| Quote create | PARTIAL | mixin；受 audit 开关影响 |
| Quote revise | AUDITED | 代码显式记录 revision |
| Quote accept | PARTIAL | 普通 update hook；无独立动作语义核对 |
| Quote export | MISSING | 未发现导出 operation log |
| Order create/status | PARTIAL | mixin + 部分确认动作；取消/完成需统一动作审计 |
| Supplier allocation | AUDITED | 显式 record_operation |
| PO CRUD/payment/receipt/reversal | AUDITED | mixin 与显式 action logs |
| Cost allocation | AUDITED | 保存前后 summary 写 metadata |
| Shipment/Shipment reversal | AUDITED | 确认/装箱/冲销有显式日志 |
| Payment / advance allocation | PARTIAL | 关键支付/核销有日志，需统一检查失败和主体信息 |
| Transaction void | PARTIAL | action 有日志路径，但需统一 root/child/allocation metadata |
| SKU change | PARTIAL | mixin 覆盖普通写，图片/包装为显式 custom |
| SupplierSKU change | PARTIAL | mixin + preferred action；停用/来源变更需审计规范 |
| Packaging change | AUDITED | SKU packaging save 有显式日志 |
| TradeUnit change | PARTIAL | mixin 覆盖 CRUD，需确认停用等语义 |
| Permission change | AUDITED | mixin/permission matrix hook，但 `RBAC_ENFORCEMENT` 可关闭 |
| User/Role change | PARTIAL | role write 受管理员 permission；Employee/组织写路径需统一保护 |
| ContractChange approve | AUDITED | 显式审批日志；approve UI 仍有 Phase 3B gap |

### 7.1 Immutability

`OperationLogViewSet` 是 `ReadOnlyModelViewSet`，admin 也把字段设为 readonly，能阻止正常 API/admin 表单修改。但 `OperationLog` 没有数据库 trigger、禁止 UPDATE/DELETE 的数据库权限或不可变 append-only 表策略。具备数据库写权限的操作者仍可改删记录，结论为 **PARTIAL / HIGH risk**。

## 8. Production security checklist

| 等级 | 当前发现 | 处理方向 |
|---|---|---|
| CRITICAL-01 | secret fallback `dev-only-change-me` | 缺失时 fail-fast；secret manager 注入 |
| CRITICAL-02 | DEBUG 默认 true | production 明确 false，并禁止启动时沿用默认 |
| CRITICAL-03 | DRF 默认 AllowAny，业务写 API 无全局认证 | 先启用认证，再逐 action 配权限 |
| CRITICAL-04 | development superadmin 默认 true、RBAC 默认 false | production 配置强制关闭，并完成真实权限矩阵 |
| HIGH-01 | `ALLOWED_HOSTS=*` | 收紧到生产域名 |
| HIGH-02 | 无显式 HTTPS redirect/proxy/cookie secure/HSTS 配置 | 在 TLS 代理和 Django 两侧配置并测试 |
| HIGH-03 | 无应用登录、登出和前端 route guard | Phase 4C |
| HIGH-04 | password validators 为空 | 启用强度、常见密码、长度验证 |
| HIGH-05 | CORS 默认本地 origin 且 credentials 开启，生产策略未声明 | 显式生产 origin、CSRF trusted origins |
| HIGH-06 | media 在 DEBUG 下由 Django 直接服务，生产存储/访问策略未定义 | Nginx/object storage、内容类型和权限策略 |
| MEDIUM-01 | 无统一 request ID/结构化 logging/health check | Phase 4G |
| MEDIUM-02 | 上传类型/大小策略未形成全局 policy | 限制图片、附件、导入和导出资源 |
| MEDIUM-03 | 本地 media 与 DB 没有已验证的联合备份 | backup/restore drill |
| LOW-01 | frontend build 有 chunk-size warning | 性能 backlog，不是本轮安全 blocker |

CRITICAL findings：**4**。HIGH findings：**6**。本轮只记录，不修复。

## 9. File and media storage

| 数据 | 当前 | production 方案 |
|---|---|---|
| SKU images | `MEDIA_ROOT` 本地文件 | 持久卷起步；多实例时迁移对象存储 |
| QuoteItem image_snapshot | 本地 immutable snapshot 文件 | 与 QuoteItem 一起备份；禁止被当前 SKU 图片覆盖 |
| FollowUp attachments | 本地 media | 持久卷/对象存储，按客户和权限控制下载 |
| PI templates | repository `templates/` | 版本化发布资产，发布包只读 |
| XLSX export | 生成后下载/内存流 | 不依赖本地临时目录；如需留档再设计受控存储 |

先不接 S3/OSS。Phase 4 初始部署使用持久 media volume + 独立备份，确认多实例需求后再切对象存储。

## 10. Backup and disaster recovery

适合当前 10–20 人、低并发系统的初始方案：

- PostgreSQL 每日完整备份，保留 30 天；至少每周复制到独立位置。
- 若业务可接受最多 24 小时数据损失，RPO=24h；若收款/库存要求更严，启用 WAL/PITR，将 RPO 降至 15 分钟以内。
- media 每日增量、每周完整备份，保留与 DB 同周期；备份中记录 SHA256/文件数量。
- RTO 目标 4 小时：新建 DB、恢复最近备份、恢复 media、启动 app/Nginx、执行 smoke。
- 每月在隔离环境做一次 restore drill；验证 row count、金额、库存、Quote snapshot、附件可读性。
- rollback 依赖“上一版应用 + 上一个 DB backup + media backup”，不依赖生产现场手工删除数据。

## 11. Deployment architecture

| 方案 | 优点 | 风险/成本 |
|---|---|---|
| A. 单 VPS（Nginx + Vue static + Gunicorn + Django + PostgreSQL） | 最简单、成本低 | DB 与 app 同主机故障域、备份更重要 |
| B. app/DB 分离自管 | 故障域更清晰 | 运维和网络复杂度增加 |
| C. 单 VPS app + managed PostgreSQL | 仍低复杂度，DB 备份/升级/恢复更可靠 | 有 managed DB 费用、需配置网络 |

推荐 Phase 4 初始架构：**C**。一台小型 VPS 运行 Nginx、Vue 静态文件、Gunicorn/Django；使用 managed PostgreSQL；media 先用持久卷并独立备份。只有出现容量、合规或多实例需求再拆 app/worker 或对象存储。

## 12. Logging and monitoring minimum

当前 settings 未定义完整 `LOGGING`、request ID、health endpoint 或 backup heartbeat。最小生产集合：

1. Gunicorn/Nginx/Django 结构化 access/error log，按天轮转并限制磁盘占用。
2. 每个请求生成 request ID，响应和异常日志关联。
3. `/health/live`（进程）和 `/health/ready`（DB 查询）分开。
4. 监控 5xx、登录失败、权限拒绝、数据库连接、磁盘/媒体容量、备份成功时间。
5. 前端统一显示 request ID/错误编号，不把 traceback 展示给用户。
6. 每日备份成功告警；超过保留窗口或磁盘低于阈值告警。

不引入 Redis/Celery/大型 observability stack，除非监控量和异步任务实际超过单机能力。

## 13. Concurrency and transaction audit

| 对象 | 当前保护 | PostgreSQL 风险/下一步 |
|---|---|---|
| Quote root number | atomic + `select_for_update` + unique date/country | staging 并发压测；导入后校准 sequence |
| Quote revision | root/counter `select_for_update` | 验证重复 revision 和历史 legacy suffix |
| Order/Purchase numbers | serializer/业务编号需逐项核对 | 必须确认是否有统一 sequence/unique constraint |
| Receipt/Shipment/movements | fulfillment service atomic/锁 | staging 并发收货、发货、冲销，检查库存不变量 |
| Transaction/advance | finance service atomic/锁 | staging 并发核销/void，验证 split/allocation ledger |
| Cost allocation | service atomic + version checks | 并发保存 preview/save 需验证 stale version |
| Unique constraints | 多处 Django UniqueConstraint | migration 前扫描历史重复，PostgreSQL 应用约束前清理 |

SQLite 开发库不能证明 row-level lock 下的并发安全；所有关键动作必须在 PostgreSQL staging 使用并发测试。

## 14. Existing Phase 3 gaps retained

- `UI COVERAGE GAP-01`：ContractChangeRequest approve 正常 UI 入口仍不完整，Phase 4 归入权限/审批 hardening，并同时补 UI completeness；本轮不实现。
- `UX ISSUE-01`：published SKU schema 与分类模板变更提示不一致。
- `UX ISSUE-02`：非整包装错误 toast 显示 `[object Object]`。
- Phase 3C deferred invariants 已封版；本轮只审计其生产部署前的认证/权限/数据库前置条件。

## 15. Phase 4 roadmap

| 阶段 | 目标 | 改动模块 | 前置依赖 | 风险 | 测试/完成标准 | migration | 影响业务数据 |
|---|---|---|---|---|---|---|---|
| 4A Audit | 形成真实风险基线（本轮） | docs、审计报告 | Phase 3C seal | 误把模型当 enforcement | review 完成、无生产代码改动 | 否 | 否 |
| 4B PostgreSQL readiness | driver、staging DB、迁移演练 | requirements、settings profile、ops scripts | 4A blocker 清单 | 锁/排序/序列/历史脏数据 | staging migrations、308+ regression、row-count/金额/库存校验、restore drill | 可能已有 migration，不新增业务字段 | staging copy；production cutover 需计划 |
| 4C Authentication | 登录、登出、session/CSRF、401、route guard | auth endpoints、frontend auth、settings | 4B staging；账号/组织基线 | 锁死现有 UAT、凭据泄露 | unauthenticated 401、login/logout、expiry、CSRF、browser smoke | 通常否；可能新增 auth profile 字段 | 不删除业务数据 |
| 4D RBAC + data scope | 后端 action permission 和 QuerySet scope | permissions、viewsets、scope service、frontend hints | 4C identity | 越权/误过滤 | module/action matrix、cross-user scope tests、UI smoke | 可能角色/权限 seed migration | 角色映射需审计 |
| 4E Audit trail | 关键动作完整、可追溯、append-only | audit service、DB permissions、operation log | 4C/4D | 性能、隐私、日志缺失 | action coverage、tamper/retention、failure atomicity | 可能 audit schema/trigger | 只追加日志 |
| 4F Production security/config | secret、DEBUG、host、TLS、cookies、upload policy | settings/deploy config | 4C | 配置错误造成不可用 | `check --deploy`、TLS/CSRF、upload limits、error leakage | 否 | 否 |
| 4G Deployment/backup/recovery | 可部署、可恢复、可观测 | Nginx/Gunicorn/backup/health/logging | 4B、4F | restore 不完整、media 丢失 | backup/restore、RPO/RTO、5xx/disk alerts | 否 | 备份/切换需窗口 |
| 4H Production smoke/UAT | 真实生产前验收 | browser UAT、runbook、release checklist | 4C–4G | 业务数据和权限误操作 | login、CRUD、quote/order/PO/inventory/finance、rollback drill | 否 | 只用受控测试数据 |

推荐顺序不是机械并行：先解决 4B driver/staging，再做 4C 身份，随后 4D 权限/数据范围，4E 审计，最后 4F–4H 部署与生产验收。

## 16. Blocking and non-blocking issues

### Blocking before production

- `BLOCKER-PG-DRIVER-01`：requirements 未声明 PostgreSQL driver。
- `BLOCKER-AUTH-01`：应用登录、登出、session/401/route guard 缺失。
- `BLOCKER-RBAC-01`：业务 API 默认 AllowAny，special actions 无统一后端权限。
- `BLOCKER-SCOPE-01`：数据范围字段存在但没有 QuerySet enforcement。
- `BLOCKER-SECURITY-01`：secret/DEBUG/superadmin/RBAC 默认值可导致开发配置进入生产。
- `BLOCKER-DR-01`：DB + media 联合 backup/restore 尚未演练。

### Non-blocking for this audit, still required before launch

- `RISK-AUDIT-01`：OperationLog API 只读但无 DB append-only 约束。
- `RISK-POSTGRES-01`：锁、NULL/排序、bulk、sequence 需 staging 验证。
- `RISK-MEDIA-01`：local media 尚无对象存储/多实例方案。
- `UI COVERAGE GAP-01`、`UX ISSUE-01`、`UX ISSUE-02`：Phase 3 已知非本轮修复项。

## 17. Audit evidence and regression

- master 已 fast-forward 到 `907a3991dadde19a31cbe02f27d0c5b789405c51`，未发生额外业务代码变更。
- PostgreSQL readiness 结论基于 settings/requirements/ORM/migrations/services 的静态审计；未安装 PostgreSQL、未迁移数据库。
- 本轮审计分支只新增本文件。
- Phase 3C 已有本地回归：后端 `308/308 PASS`；前端 unit `61/61`、node-only `1/1`、Vitest `31/31`、build PASS。Phase 4A 提交后将再次执行完整回归。
- GitHub Actions API 当前因本机 GitHub CLI token 失效无法读取 Run ID；不得将本地结果冒充远程 CI 状态，推送后需补查并确认 backend/frontend 全绿。

