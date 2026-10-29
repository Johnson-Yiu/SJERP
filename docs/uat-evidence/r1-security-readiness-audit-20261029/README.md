# R1-SECURITY-READINESS-AUDIT-01 安全与生产就绪检查报告

日期：2026-10-29

固定基线：`54e715bdc568b80ba624186fecd866550676cf38`

分支：`codex/audit-security-readiness-20261029`

工作树：`C:\Users\Johnson\.codex\worktrees\audit-security-readiness-20261029\森爵照明管理系统`

## 结论摘要

本轮仅审计和取证，没有修改产品代码、依赖锁、CI、权限开关或业务数据。

当前代码和隔离回归证明了若干应用层安全边界，但不足以宣称生产就绪：

1. ISS-002 的当前源码已包含 `Pillow==13.0.0`、精确 Python 运行时锁和前端 `package-lock.json`；前端当前 `npm audit`（含开发依赖和仅生产依赖）均为 0 个漏洞。但本机只有 Python 3.14.5，实际导入环境不是锁定环境，Python 3.12 不可用；Python 官方公告复核也被本机外部 TLS/认证阻断，因此保持 `NEEDS_VERIFICATION`。
2. ISS-003 的服务端权限、客户数据范围、跨模块脱敏和共享采购的最小销售订单候选在隔离合成账号测试中通过；真实员工、正式组织树、生产数据库和真实浏览器会话仍未验证，不能扩大为内测通过。
3. ISS-017 的应用层媒体入口是认证 API，仓库没有把 `MEDIA_ROOT` 暴露为 Django `/media/` 路由；但仓库没有目标 Nginx、CDN、对象存储或反向代理配置，生产直链/缓存边界仍未证明。
4. ISS-018 的联合归档、媒体清单、SHA256 校验和原子恢复目前只对 SQLite/本地媒体实现并在隔离测试通过；代码明确对非 SQLite 数据库 fail-closed，真实 PostgreSQL、加密异地副本、定时任务、告警和 RPO/RTO 未验证。
5. ISS-043 的 ORM/admin 追加写保护、PostgreSQL UPDATE/DELETE 触发器迁移和非开发审计 fail-fast 已存在；本机无 PostgreSQL，运行账号实际权限、角色继承、表所有者边界和维护留痕未验证。
6. ISS-051 的生产配置拒绝路径在隔离测试中通过，但当前仓库只有 Django SessionAuthentication 和 `/admin/` 登录，没有业务前端登录、退出或业务会话建立接口；除非部署另有已审查的 SSO/反向代理认证，本项存在代码级生产就绪阻断。
7. ISS-052 的 CSV 导入会使用当前请求权限校验，但 `_preview_import`/`_apply_import_rows` 直接调用导入行逻辑，没有创建导入批次、操作者、行级 before/after 或持久化 OperationLog；这是已确认的审计证据缺口，不应把导入成功当作审计通过。

## 检查矩阵

风险等级含义：P1 表示进入生产/内测前必须补齐或取得明确的环境证据；P2 表示有条件风险，需在目标环境或后续专项中完成；PASS 仅表示当前代码/隔离证据通过，不代表生产通过。

| Issue | 当前证据 | 风险 / 阻断条件 | 下一步 |
|---|---|---|---|
| ISS-002 依赖与安全公告 | `backend/requirements.txt` 直接锁定 9 个包，其中 `Pillow==13.0.0`；`backend/requirements.lock` 为 15 个精确 pin，包含 Django 6.0.9、DRF 3.18.3、Pillow 13.0.0、psycopg 3.3.6 及传递依赖。`frontend/package-lock.json` 为 lockfileVersion 3，生产/开发依赖均有解析版本。当前 npm registry 的 `npm audit --json` 与 `npm audit --omit=dev --json` 均报告 `total=0`。 | P1 / `requirements.lock` 的生成说明是 Python 3.14，目标声明为 CPython 3.12+；本机实际环境为 Python 3.14.5、Django 6.0.6、DRF 3.17.2、Pillow 11.3.0，不能代表仓库锁定运行时。Python 3.12 不存在，`py -3.12 --version` 无可用运行时；`pip-audit` 未安装。PyPI、Django RSS 和 GitHub Advisory API 的官方公告抓取因本机 TLS/认证失败，未形成当前公告快照。npm 还提示 `glob@10.5.0` 与 `lucide-vue-next@1.0.0` deprecated；这不是 npm audit 报告的漏洞，但属于维护风险。 | 在隔离 Python 3.12/目标生产镜像中按 lock 安装并运行 `pip check`、`pip-audit`/官方 advisory 对照；确认 Pillow 13 的图片、缩略图和 XLSX 路径兼容后再更新台账状态。不得把当前全局环境或 0 个 npm advisory 当作完整 Python 安全结论。 |
| ISS-003 权限、数据范围、跨模块关联 | `crm.permissions.ModuleActionPermission` 在 RBAC 模式下按服务端模块/动作矩阵拒绝未授权请求；`sales_scope.py` 实现 self/department/department_tree/all；订单、报价、客户关联、财务和附件路径使用范围查询。采购成本归属候选只返回销售订单 ID、编号和状态，不返回客户名称；这是现有共享采购规则的受控例外。隔离后端定向回归 146 项通过（5 项 PostgreSQL/平台条件跳过）；其中包含 functional RBAC、销售/采购/财务范围和共享采购测试。 | P1 环境阻断，不是本轮已复现的应用层缺陷。真实员工账号、正式组织树、正式角色分配、生产 PostgreSQL、跨部门真实数据、导出和真实 Chrome 会话未验证。开发身份仍由 `development_superadmin_enabled()` 控制，不能用它替代员工验收。 | 在获授权的隔离 staging 建立非开发账号，覆盖列表/详情/搜索/导出/嵌套 context/附件/动作及正常共享采购路径；逐项保存 HTTP、数据库和浏览器证据。保持开发超级管理员约定，不在本轮切换正式 RBAC。 |
| ISS-017 私有媒体与直链边界 | `config/urls.py` 只挂载 `/api/` 和 admin；`crm/urls.py` 的媒体入口为 `/api/media/<path>`。`file_access.py` 按附件所属客户、报价图片、SKU 图片和证书模块权限查找，并返回 `Cache-Control: private, no-store` 与 `nosniff`。模型文件 URL 由 `protected_media_url()` 生成 API 路径，不返回 FileField 的公开 URL。隔离权限/私有存储测试通过。 | P1 部署阻断。仓库没有真实 Nginx、CDN、对象存储或反向代理 ACL；无法证明代理不会把 `MEDIA_ROOT`、对象存储 key 或旧缓存直链公开。当前本地测试不能证明生产缓存、回源和权限策略。 | 运维在隔离 staging/生产用未登录、越客户范围、无模块权限、旧缓存和已知文件路径实测；确认没有 `alias/root` 指向私有媒体卷，且对象存储/CDN 采用私有回源与受控缓存。 |
| ISS-018 DB+媒体备份恢复 | `backup_recovery.py` 要求 `--quiesced`，把数据库、媒体、配置和 manifest 放入一个归档，恢复前核验数据库 SHA256、SQLite integrity check、媒体逐文件 SHA256，并在新目录原子切换；媒体 manifest 拒绝符号链接。`crm.tests.test_iss018_backup_recovery` 在本轮选定测试中通过，Windows ACL 仍按代码标记为待外部核验。 | P1 部署阻断。代码 `_assert_sqlite()` 明确只接受 SQLite；没有实际 PostgreSQL dump/快照适配器、生产媒体卷、独立故障域加密副本、systemd/计划任务、失败告警、磁盘/inode 告警和 RPO/RTO 证据。`age`、`psql`、`pg_dump` 本机不可用/未验证。 | 运维提供同一恢复点的 PostgreSQL + 私有媒体归档、加密异地副本、恢复结果、金额/库存/附件关系核对、权限/密钥恢复和告警/RPO/RTO 记录；不得用 SQLite 演练替代。 |
| ISS-043 审计日志与防篡改 | `AuditTrailMixin` 与各业务自定义动作调用 `record_operation()`；OperationLog ORM QuerySet、实例和 admin 禁止修改/删除；迁移 0088 在 PostgreSQL 安装 UPDATE/DELETE 触发器，0089 使用 `PROTECT` 保留操作人身份；非开发环境关闭 `AUDIT_LOG_ENABLED` 会 fail fast。`crm.tests.test_audit` 等定向测试包含 8 项审计回归，当前选定后端回归总体 146 项通过。 | P1 部署阻断。PostgreSQL 原始 SQL 触发器测试因本机没有 PostgreSQL 跳过；没有生产运行账号 `UPDATE/DELETE/TRUNCATE` 拒绝、角色继承、表所有者/超级用户隔离、备份恢复或独立维护账号留痕证据。应用层/触发器不能限制数据库所有者或超级用户。 | DBA 在目标版本 PostgreSQL 按 `docs/deployment/ISS-043-PostgreSQL审计防篡改.md` 实测运行账号和继承角色，保存权限查询、拒绝响应、触发器存在性、审计备份及受控维护记录。 |
| ISS-051 密钥、DEBUG、开发身份、认证 | `settings.py` 在 staging/production 拒绝 DEBUG、开发超级管理员、关闭 RBAC、关闭审计、弱/默认 secret、通配符/空 ALLOWED_HOSTS、HTTP CORS/CSRF 来源、非 PostgreSQL 和不安全 Cookie/HTTPS/HSTS；生产 API 使用 SessionAuthentication challenge。配置/环境隔离测试 20 项通过。 | P1 代码+部署阻断：仓库只有 `admin/` 和 SessionAuthentication，没有业务登录/退出 API、前端登录页或 SSO 集成。`frontend/src/router.js` 直接加载当前权限状态，没有认证入口。若没有外部已审查的认证层，生产员工无法通过 ERP 业务界面建立受控会话。真实 secret、HTTPS、反向代理、Cookie、生产 PostgreSQL 和实名账号也未验证。 | 在进入内测/生产前明确并实现/接入一种受审查的业务认证路径（Django session login/logout 或正式 SSO），补充 CSRF、失败尝试限制、停用账号即时失效和真实 staging 会话证据；由运维保存 secret/HTTPS/代理配置审计。不得在开发环境伪造登录或关闭现有开发身份约定。 |
| ISS-052 CSV 操作者、批次、行级审计 | `import_csv_preview` 和 `import_csv_execute` 做文件 hash、预览 token、状态快照、事务写入和权限检查；导入订单被明确拒绝，避免绕过报价/库存/收款计划。现有隔离 UI/API/数据库证据证明四类导入成功与失败原子性。 | P1 代码级审计缺口：`_apply_import_rows()` 直接调用 `_import_row()`，`_preview_import()` 也直接调用 serializer 保存并回滚，当前路径没有 `record_operation()`、ImportBatch 模型、操作者快照、批次号、行级 before/after 或错误行持久证据。开发配置 `AUDIT_LOG_ENABLED=false` 且请求 `authenticated=false` 时 OperationLog 为 0；即使生产审计开关打开，当前导入代码也不会自动补齐这些字段。 | 另行设计并验收 CSV 导入审计批次/行模型或等价不可变审计事件：记录真实认证操作者、文件 hash、实体、批次、行号、业务主键、before/after、结果和错误；在审计开启的隔离 staging 用真实测试账号验证，并确认历史资料不被覆盖。不要在开发身份上伪造正式审计人。 |

## 代码级问题与环境/授权阻断分界

### 已确认的代码级就绪问题

- ISS-051：没有业务登录/退出/会话建立实现；`SessionAuthentication` 只验证已经存在的 Django session。Django admin 的登录页不等于 ERP 员工业务认证方案，仓库也没有 SSO/反向代理认证契约。
- ISS-052：CSV 导入写路径没有导入批次和行级审计事件，也没有调用 `record_operation()`。权限校验、preview token 和事务原子性不能替代审计证据。

本轮不直接修改上述代码，因为用户要求本任务形成审查矩阵，不改变认证、审计或业务规则；两项应作为后续独立修复任务处理。

### 需要运维/授权/真实环境证据的问题

- Python 3.12 运行时、目标镜像依赖安装和 Python advisory：当前机器不存在 3.12，且官方公告抓取被 TLS/认证阻断。
- 生产 PostgreSQL、DB 运行账号与角色继承、审计触发器、备份恢复和加密异地副本：本轮没有连接，也没有生产凭证。
- 私有媒体的 Nginx/CDN/对象存储/反向代理权限边界、缓存和持久卷 ACL：仓库没有目标配置。
- 真实 HTTPS、Cookie、secret、实名员工账号、组织树和跨账号 Chrome：本轮只使用隔离 SQLite/临时媒体与合成账号。

## 可复核测试证据

所有后端测试使用临时 SQLite 和临时 `MEDIA_ROOT`，没有连接生产数据库；环境变量仅存在于命令进程中。

### 后端

```text
python manage.py check
System check identified no issues (0 silenced).

python manage.py makemigrations --check --dry-run
No changes detected
```

迁移检查同时出现 `RuntimeWarning: unable to open database file`，原因是托管 worktree 默认数据库路径 ACL；没有把该警告当作数据库迁移 PASS，定向测试使用临时 SQLite。

```text
python manage.py test crm.tests.test_functional_rbac crm.tests.test_sales_data_scope crm.tests.test_procurement_data_scope crm.tests.test_finance_data_scope crm.tests.test_iss047_private_storage crm.tests.test_audit crm.tests.test_iss018_backup_recovery crm.tests.test_safe_csv_import --noinput --verbosity 1
Ran 146 tests in 304.443s
OK (skipped=5)
```

配置和开发身份边界：

```text
python manage.py test crm.tests.test_database_settings crm.tests.test_environment_isolation crm.tests.test_development_access --noinput --verbosity 1
Ran 20 tests in 8.753s
OK
```

### 前端锁、审计和构建

在临时镜像 `C:\Users\Johnson\AppData\Local\Temp\sunjack-security-readiness-20261029-runtime-v3\frontend` 按当前 `package-lock.json` 执行 `npm ci --ignore-scripts --no-audit`；原工作树直接创建 `frontend/node_modules` 因 ACL 返回 `EPERM`，没有修改原工作树。

```text
npm run test:unit
tests 169
pass 169
fail 0
duration 72164 ms

npm run build -- --configLoader runner --outDir <temporary-dist>
2018 modules transformed
built successfully in 2.30s
index-CfM8L8T7.css       387.31 kB / gzip 63.57 kB
index-BvEkI8Kz.js       1,126.67 kB / gzip 393.68 kB
```

构建警告：Vite 提示部分 chunk 超过 500 kB；npm 安装提示 `glob@10.5.0` 和 `lucide-vue-next@1.0.0` deprecated。没有运行 `npm audit fix`、依赖升级或任何自动修复。

```text
npm audit --json
metadata.vulnerabilities: total=0, low=0, moderate=0, high=0, critical=0

npm audit --omit=dev --json
metadata.vulnerabilities: total=0, low=0, moderate=0, high=0, critical=0
```

### Python 环境证据

```text
python=3.14.5
django=6.0.6
djangorestframework=3.17.2
Pillow=11.3.0
python -m pip check
No broken requirements found.

py -0p
-V:3.14 * C:\Python314\python.exe
pip-audit=NOT_INSTALLED
```

`pip check` 只证明当前全局环境内部没有声明冲突，不能证明 `requirements.lock` 的安全性或运行兼容性；当前环境没有安装仓库锁定的 Django/DRF/Pillow 版本。

## 外部公告复核边界

本轮原计划读取以下官方来源：

- [Pillow PyPI](https://pypi.org/project/Pillow/)
- [Pillow GitHub Security Advisories](https://github.com/python-pillow/Pillow/security/advisories)
- [Django security releases](https://www.djangoproject.com/weblog/)
- [Django REST framework Security Advisories](https://github.com/encode/django-rest-framework/security/advisories)
- [npm audit documentation](https://docs.npmjs.com/cli/v11/commands/npm-audit)

当前机器对 PyPI、Django RSS 和 GitHub Advisory API 均返回 TLS/认证失败；搜索服务也返回 429。故本报告只把 npm registry 的当前 `npm audit` 结果记录为本地观测，不把 Python advisory 写成“无漏洞”。下一步必须在可访问官方源的受控环境复核，并保存公告日期、受影响范围和修复版本。

## 交付边界

- 没有连接生产数据库、生产媒体、CDN 或反向代理。
- 没有部署、启用正式 RBAC、修改真实业务数据或修改 CI 工作流。
- 没有更新共享 `docs/PROJECT_ISSUES.md` / `docs/PROJECT_PHASES.md`。
- 本分支没有创建 PR；提交应使用包含 `[skip ci]` 的 commit message，避免触发 GitHub Actions。
