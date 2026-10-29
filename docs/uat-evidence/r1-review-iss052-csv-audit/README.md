# R1 独立审查：ISS-052 CSV 导入审计与数据保护

## 结论

总体结论：**FIX REQUIRED**。当前实现为可解析、进入执行阶段的 CSV 建立了真实操作人关联、批次与行记录，并把业务变更和成功审计放进同一事务；失败执行会整体回滚，再独立保存失败批次。SQLite 定向回归和从 0089 到最新迁移的隔离升级通过。

本次发现两项需修复的缺口：

1. CSV 没有字节大小上限，读取时将整个文件载入内存；5,000 行限制不能限制单行/字段或总文件字节数。
2. 已认证的执行请求若在 CSV 读取/解析阶段失败，会直接返回 400，不产生批次审计；这使格式错误、空文件、错误表头、超行数等执行尝试无法追溯。

另有两项需明确验收：行级审计记录没有应用内直接读取接口；审计快照和错误信息的保留期限、备份访问范围没有在本轮代码中找到明确策略。PostgreSQL 触发器因本轮严格限定所有测试使用 SQLite 而未实际运行，标记 BLOCKED。

## 范围与约束

- 基线：bd324a8c3fb64af245c3afcabbd4301c84f7711c
- 审查分支：codex/r1-review-iss052-csv-audit-20261029
- 审查起点：指定工作树 HEAD 精确匹配基线，原工作区干净；审查期间只新增本目录报告和证据。
- 审查对象：后端 CSV 导入视图、模型、权限、OperationLog 读取路径、0091/0092 迁移和相关测试。
- 未修改产品代码、测试脚本、AGENTS.md、共享问题台账或阶段计划；未连接真实业务数据库、未使用 PostgreSQL、未运行 Chrome、未推送、未创建 PR、未触发 Actions、未部署。
- 测试用 SQLite 和 MEDIA_ROOT 均位于独立临时目录。Django 测试 runner 使用隔离 SQLite 测试库；测试用户和业务资料由测试事务创建。

## 审查矩阵

| 范围 | 分类 | 已核实事实 |
|---|---|---|
| 操作者来源 | PASS | 执行门禁要求 request.user 已认证且 AUDIT_LOG_ENABLED 为真；批次 operator 是用户外键并使用 PROTECT。匿名开发身份会被拒绝，不会伪造操作者。 |
| 导入权限 | PASS | DRF 默认权限是 ModuleActionPermission；导入路径映射到 imports，POST 映射为 import。RBAC 回归覆盖缺少 imports.can_import 时预览和执行均为 403。 |
| 批次/行级记录 | PASS（持久化） | 批次有 UUID、实体、SHA256、操作者、状态和计数；行审计有批次外键、CSV 行号、业务主键、结果、对象 ID 和唯一约束。 |
| before/after | PASS（执行路径） | 快照限于导入字段及对象 ID；成功更新保存前后快照，失败行保存 before、空 after。原始 CSV 文件正文不写入审计表。 |
| 成功/失败事务 | PASS | 成功业务写入、批次、行审计及 OperationLog 同属 transaction.atomic；异常回滚后另行保存失败批次。定向测试覆盖模拟写入异常并断言业务数据回滚。 |
| 失败行/部分成功 | PASS（全有或全无语义） | 预览有错误时不发执行 token；执行期发生任一写入失败会回滚整批，所有来源行记为 failed，不存在部分成功。failed_rows 等于整批未应用行数，只有具体异常行保存原始错误，其余行标记为批次未执行。 |
| 无法解析的执行请求 | FIX REQUIRED | 认证后的执行请求在 _read_import_csv 抛出 ValueError 时直接返回 400，不建立批次或行记录。读取失败与有效 CSV 执行失败的审计覆盖不一致。 |
| 文件资源限制 | FIX REQUIRED | _read_import_csv 先 upload.read() 全量读入内存；仅限制数据行数，不限制文件字节数。 |
| 敏感数据 | NEEDS VERIFICATION | 不持久化上传文件正文或原文件名；SHA256 和字段快照会保存。客户 address/notes、SKU cost_price、流水 amount/reference/notes 等字段可能进入 CSVImportRowAudit 和 OperationLog；错误文本可能包含输入值。需确认保留期限、备份访问和审计数据的最小读取权限。 |
| 行审计可读性 | NEEDS VERIFICATION | 当前路由没有 CSVImportBatch/CSVImportRowAudit 的只读查询端点。成功行可经对应实体 OperationLog 间接追踪；失败行明细仅落在 CSVImportRowAudit 表，应用用户无法通过本轮发现的 API 查询完整行结果。 |
| ORM 追加保护 | PASS（SQLite） | 自定义 QuerySet 拒绝 update/delete/bulk_update，模型实例拒绝更新/删除，批次/行外键为 PROTECT；测试覆盖 QuerySet update 与删除拒绝。 |
| PostgreSQL 触发器 | BLOCKED | 0091 仅在 PostgreSQL 安装 UPDATE/DELETE 触发器。本轮按要求只允许 SQLite 测试；实际 PostgreSQL DDL、触发器效果及数据库角色权限未验证。 |
| 迁移 | PASS（SQLite） | 独立 SQLite 从 crm.0089 升级到 crm.0092；0090、0091、0092 均已应用；makemigrations --check 无差异。SQLite 上 RunPython 按设计不创建 PostgreSQL 触发器。 |

## 发现详情

### F1 — FIX REQUIRED：无 CSV 字节上限

位置：[views.py:3446](../../../backend/crm/views.py#L3446)、[views.py:3465](../../../backend/crm/views.py#L3465)。上传内容在解析前被一次性读入内存；后续 5,000 行限制发生在完整解码和 DictReader 之后。一个或少数超大字段仍可造成高内存占用，行数上限不能缓解这一点。仓库搜索未发现 CSV 专用字节上限；实际反向代理限制未在本轮部署范围内验证。

建议：在全量读取前设置明确的最大字节数，或使用有界读取；超限时返回稳定 400，并增加单行超大字段和总文件超限回归。具体阈值由产品/部署容量决定。

### F2 — FIX REQUIRED：解析失败的执行请求没有批次记录

位置：[views.py:3337](../../../backend/crm/views.py#L3337)、[views.py:3347](../../../backend/crm/views.py#L3347)。执行入口先通过认证和审计门禁，随后读取文件；读取抛出 ValueError 时只返回 HTTP 400。此路径不会调用 _import_failure_response，因此没有 import_batch_id、CSVImportBatch 或 CSVImportRowAudit。有效 CSV 的无效凭证、过期凭证、预览状态冲突和写入异常则会建立失败批次。

建议：若 ISS-052 的审计定义覆盖所有已认证执行尝试，为无法解析的文件增加批次级失败记录；可在能读取原始字节时只留 SHA256，不保存正文；无法解码时不伪造行记录。非执行预览的校验错误可继续保持无写入，但应在验收定义中明确它不属于执行审计。

### F3 — NEEDS VERIFICATION：行审计记录缺少应用内查询路径

位置：[urls.py:73](../../../backend/crm/urls.py#L73)、[views.py:125](../../../backend/crm/views.py#L125)。路由提供模板、预览、执行，没有 CSVImportBatch 或 CSVImportRowAudit 的读取路由。OperationLog 只读接口可提供成功行的间接关联；失败行记录没有逐行 OperationLog，故完整失败原因和行结果只能直接查数据库。

建议：确认数据库直查是否为正式运维设计。若业务用户/审计员需要在应用内追溯，新增只读批次/行查询并复用 imports.view、实体数据范围和字段脱敏规则；不得扩大普通用户的审计读取权限。

### F4 — NEEDS VERIFICATION：审计副本的保留与隐私控制未定义

位置：[views.py:3085](../../../backend/crm/views.py#L3085)、[views.py:3125](../../../backend/crm/views.py#L3125)、[views.py:3538](../../../backend/crm/views.py#L3538)。CSVImportRowAudit 与 OperationLog 会保存选定业务快照；客户地址/备注、SKU 成本、交易金额和说明可能被复制，格式错误信息也可能包含用户输入值。没有发现 CSV 审计的保留或清理策略。追加保护会阻止普通 ORM 删除；数据库维护删除方式需要受控且有记录。

建议：明确审计记录保留期限、备份/运维读取权限和批准的归档/清理流程；确保行审计读取沿用业务数据范围及 serializer 脱敏。保持现有不落原始文件正文的做法。

### F5 — BLOCKED：CSV PostgreSQL 触发器未验证

位置：[0091_csv_import_audit.py:14](../../../backend/crm/migrations/0091_csv_import_audit.py#L14)、[0091_csv_import_audit.py:18](../../../backend/crm/migrations/0091_csv_import_audit.py#L18)、[0091_csv_import_audit.py:53](../../../backend/crm/migrations/0091_csv_import_audit.py#L53)。迁移通过 vendor 检查，仅 PostgreSQL 安装批次和行表的 UPDATE/DELETE 触发器。SQLite 升级成功只证实迁移图和模型表可用，不执行这段 DDL。本次运行中 CSV trigger 查询结果为空，符合 SQLite 分支预期。

现有 [test_audit.py:88](../../../backend/crm/tests/test_audit.py#L88) 的 PostgreSQL 专用测试针对 OperationLog，不是 CSVImportBatch/CSVImportRowAudit；本轮 1 项跳过对应 OperationLog 的 PostgreSQL 测试。下一步需在独立 PostgreSQL 临时库迁移后，对 CSV 两表做原始 SQL UPDATE/DELETE 拒绝验证，并确认应用数据库角色不能绕过触发器或修改迁移对象。当前 SQLite-only 授权边界下不执行该验证。

## 自动验证

工作目录：指定工作树的 backend 子目录。数据库 URL 明确指向 AppData 临时 SQLite 路径；MEDIA_ROOT 指向同一轮独立临时目录。没有读取或连接默认业务数据库。

运行结果原始摘要见 [targeted-tests.log](evidence/targeted-tests.log)：

- Django system check：通过。
- crm makemigrations --check --dry-run：无变更。
- 定向命令：python -B manage.py test crm.tests.test_safe_csv_import crm.tests.test_audit crm.tests.test_functional_rbac.FunctionalRBACApiTests.test_quote_export_and_import_actions_use_special_permissions --verbosity 1
- 27 tests，40.891 秒，OK，1 skipped，退出码 0。
- 被跳过项是要求 PostgreSQL 的 OperationLog 原生触发器测试；不构成 CSV PostgreSQL 触发器证据。

隔离迁移原始输出见 [sqlite-migrations.log](evidence/sqlite-migrations.log)。先迁移到 0089，再迁移全部最新版本；0090、0091、0092 均标记已应用，命令退出码均为 0。SQLite 触发器探针结果为 CSV_TRIGGER_NAMES=[]。

## 限制与后续

- 本轮没有修改产品代码、测试脚本或共享台账；本报告不改变 ISS-052 的共享状态。
- 没有执行真实 Chrome；本任务是后端代码与数据保护审查，不宣称本轮 UI 验收。
- PostgreSQL DDL/触发器、生产角色权限、审计留存策略及应用内行审计读取仍未验证。
- 本地提交只包含本目录报告和证据；不推送、不创建 PR、不触发 CI、不合并 master、不部署。
