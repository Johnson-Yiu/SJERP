# ISS-052 CSV 导入审计修复验收

## 范围与边界

- 基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`
- 分支：`codex/r1-iss052-import-audit-fix-20261031`
- 仅调整 CSV 导入预览/执行审计关联、开发验收和对应前端重试上下文；不改导入字段映射、校验规则或业务写入规则。
- 验证使用 CPython 3.12.16、Django 测试数据库和专用临时 SQLite/媒体目录；未连接用户业务数据库，未改动任何业务记录。
- 保留开发超级管理员配置，不启用正式 RBAC。正式导入仍要求可在配置用户表中查到的已认证真实用户作为操作人；开发身份、未保存用户对象不会被伪装为审计人。

## 实现与审计关系

- 新增只追加的 `CSVImportPreviewAudit`，记录预览 UUID、类型、完整文件 SHA-256（无完整文件时为空）、真实操作人（匿名预览时为空）、入口、状态、解析行数、校验错误及失败原因。不存储 CSV 正文。
- `CSVImportBatch.preview` 将正式执行批次关联到其签名预览；历史批次保持 `NULL`，没有回填或重写。
- 解析失败、执行失败和成功均创建各自的新批次。无法可靠解析行时只写批次级失败，不伪造行审计。可可靠识别的行错误以 `CSVImportRowAudit.batch` 关联所属批次。
- 签名凭证关联预览记录；预览 SHA、实体和签名均需一致。失败后重新预览可携带 `retry_of_batch_id`，服务端只接受同一实际操作人、同一实体的失败批次。对同一预览的重复执行尝试也以 `previous_attempt_batch_id` 留下链路。
- 成功时业务变更、批次、行审计和操作日志处于同一个原子事务；任一审计写入失败会回滚业务写入。失败批次、行审计和失败操作日志同属一个原子事务；预览记录与其操作日志也在同一事务内。
- 新预览审计只映射至既有 `imports` 日志模块，不启用或扩展正式 RBAC。SQLite 下由模型/查询集阻止修改和删除；迁移另为 PostgreSQL 安装数据库触发器。

## 核验结果

### 业务流程与审计数据

执行命令（工作目录 `backend/`，运行环境 CPython 3.12.16）：

```powershell
python manage.py test crm.tests.test_safe_csv_import crm.tests.test_audit crm.tests.test_dashboard_import crm.tests.test_sales_data_scope.SalesDataScopeTests.test_customer_import_rejects_out_of_scope_code_and_defaults_new_owner --verbosity 1
```

结果：**48 项通过，1 项跳过**。跳过项是 `test_postgres_trigger_rejects_raw_update_and_delete`，测试明确要求 PostgreSQL；SQLite 不能证明 PostgreSQL 触发器行为。单独的安全 CSV 导入套件亦通过 23 项。

用例核对内容包括：空文件、非法 UTF-8、缺表头/必要字段/数据行的失败批次与原因；完整 SHA-256；无可靠行数据时没有行记录；失败批次和错误行的外键关系；有效操作人、未保存用户拒绝、匿名正式执行拒绝；预览校验失败不产生正式导入批次；成功的新增/更新审计；失败后重预览与重试关联；不同操作人/实体不能借用失败批次；批次、行记录和预览审计不可更新/删除；业务更新与审计日志写入失败时的事务回滚；现有 Dashboard CSV 导入和数据范围回归。

合成验收数据断言了以下关系与结果：失败批次 `operator_id` 指向真实测试用户；解析失败批次 `preview_id` 指向原预览；行错误的 `batch_id` 指向失败批次；重试预览的 `retry_of_batch_id` 指向原失败批次；成功重试另建 `succeeded` 批次，原 `failed` 批次及错误行仍存在且未被覆盖；客户数据只在成功事务中变化。原始 CSV 内容不进入审计表。

### 数据库迁移正反向检查

使用新建的临时 SQLite `audit-migration-roundtrip.sqlite3`，不复用任何已有数据库：

1. 对空库执行完整 `manage.py migrate --noinput`，所有迁移（含 `0093_csv_import_preview_audit`）成功。
2. 插入合成用户、预览审计、批次和行审计各一条。
3. 回退到 `crm.0092_merge_fulfillment_and_csv_audit`：新增预览表和批次预览外键列被移除；原有批次及行审计计数仍为 **1/1**。
4. 再次正向迁移：预览表和外键列恢复；既有批次/行仍为 **1/1**，旧批次预览外键为 `NULL`。

回退新建表迁移会移除该新表中的预览审计数据，这是回退建表迁移的预期结果；因此如需在已写入真实预览审计的环境回滚，应先按部署运维流程备份/导出这些新增审计记录。该回退没有删除或重写迁移前既有的导入批次和行审计。

### Django 检查

- `python manage.py check`：通过，无系统检查问题。
- `python manage.py makemigrations --check --dry-run`：通过，`No changes detected`。
- 测试数据库为 Django test runner 创建的内存 SQLite；迁移方向测试使用上述专用临时 SQLite。均使用 CPython 3.12.16。

### 前端

- `npx vitest run tests/import-preview-state.spec.js tests/import-ux.spec.js --environment jsdom`：**2 个文件、7 项通过**。覆盖执行失败后重预览携带原失败批次 ID，以及选择不同文件时清除旧重试关联。
- `npm run build`：通过。构建器报告主 JS chunk 超过 500 kB；产物显示主入口 JS 1,128.12 kB（gzip 394.27 kB）。这是现有体积告警，本任务未做无关性能改动。
- `npm run test:unit`：**未全通过**。并行工作树基础设施测试 `two independent worktree runtimes can start concurrently without sharing ports or data` 在约 96 秒后失败，输出为临时 Django API `fetch failed` / `Django API identity check failed`。该用例位于现有 Playwright 隔离基础设施，本任务未改其代码；相关导入 Vitest 定向测试已通过。此失败作为遗留项保留，不以定向通过替代全量失败。

## 遗留与限制

- PostgreSQL 触发器运行时行为未在本地 SQLite 环境验证；现有 PostgreSQL 专项测试被明确跳过。部署前/数据库环境具备后应在 PostgreSQL 上补跑。
- 本地前端全量 Node 测试存在上述隔离基础设施失败；需在独立复测中定位其端口/服务身份探测原因。
- 预览审计的保留期限和行级审计查询授权仍按既有验收待确认事项处理，本次未扩展保留策略或权限范围。
- 未触发 GitHub Actions；未创建 PR、合并、部署或关闭 Issue。
