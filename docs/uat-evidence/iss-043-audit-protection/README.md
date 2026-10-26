# ISS-043 重要业务操作日志防篡改验收

日期：2026-10-26
基线：`f12b591cb90d6a5d8ebfedf1c559703377c92d84`
分支：`codex/iss-043-audit-protection`
规则原文：`C:\Users\Johnson\Desktop\SUNJACK-ERP_B8E5A1A7E599AEE6B4A7E4A48C%85_2026-10-24\新增议题逐项移交\ISS-043_重要业务操作日志防篡改.md`

## 先行审查与复现

基线代码确认 `OperationLogViewSet` 为 `ReadOnlyModelViewSet`，所以 API 的 POST/PATCH/DELETE 已返回 405；`OperationLogSerializer` 全字段只读并对采购、财务、订单敏感快照按数据范围脱敏。基线 `OperationLogAdmin` 只有 `readonly_fields`，未覆盖 `has_delete_permission`，后台超级管理员仍会获得默认删除权限；`OperationLog` 模型也没有阻止实例 `save/delete`、QuerySet `update/delete` 或 PostgreSQL UPDATE/DELETE。

基线定向命令：

```text
python manage.py test crm.tests.test_audit crm.tests.test_shared_report_templates --verbosity 1
Ran 10 tests in 34.941s — OK
```

这次复现确认的是应用后台/ORM 和数据库层的真实缺口，不修改任何既有审计行或其他任务分支。

## 本轮补修

- `OperationLog` 的实例 `save/delete`、QuerySet `update/delete/bulk_update` 均拒绝历史行修改；新增记录仍只由业务审计 hook 追加。
- Django admin 对 OperationLog 明确禁止新增、修改、删除；普通用户和应用超级管理员没有后台写入口。
- 新增 `crm.0088_operationlog_append_only`：仅 PostgreSQL 创建拒绝 UPDATE/DELETE 的触发器；新增 `crm.0089_operationlog_operator_protect`，避免删除操作人时通过 `ON DELETE SET NULL` 改写历史审计；SQLite 不冒充生产防篡改验证。
- 非开发环境 `AUDIT_LOG_ENABLED` 默认开启，显式关闭会 fail fast；开发环境继续按 `AGENTS.md` 保持关闭。
- 增加 PostgreSQL 运行账号最小权限和独立维护 runbook；不执行真实生产授权、不公开任何数据库或媒体目录。

## 自动回归

命令：

```text
python manage.py test crm.tests.test_audit --verbosity 2
Ran 8 tests in 8.429s — OK (skipped=1)
```

覆盖结果：

| 场景 | 结果 | 证据 |
|---|---|---|
| 认证业务操作写入操作者、对象、前后快照 | PASS | `test_authenticated_operator_records_operation_with_snapshot` |
| 业务事务异常时审计随事务回滚 | PASS | `test_audit_row_rolls_back_with_business_transaction` |
| 普通应用 ORM 实例/API QuerySet 改写和删除 | PASS | `test_application_orm_cannot_mutate_or_delete_historical_rows` |
| 删除操作人不改写历史身份 | PASS | `test_operator_deletion_cannot_rewrite_historical_identity`；0089 `PROTECT` |
| Django 后台超级管理员新增/修改/删除 | PASS | `test_admin_is_read_only_even_for_superuser` |
| REST API 写入路径 | PASS，均 405 | `test_api_exposes_only_read_methods` |
| PostgreSQL 原始 SQL UPDATE/DELETE 触发器拒绝 | `PENDING` | 本机无 PostgreSQL 客户端/服务；测试在 PostgreSQL job 中执行 |

迁移链在隔离 SQLite 测试库完整应用至 `0089`，系统检查通过；`makemigrations --check --dry-run` 无变化。PostgreSQL 触发器测试会在 `connection.vendor == "postgresql"` 时执行，SQLite 结果不计入生产安全验收。

全量回归日志：

```text
python manage.py test --verbosity 1
首次运行：938 tests，因 Worktree 的既有 backend/media Windows ACL 在附件上传测试写入时失败（环境问题，未修改该目录）。
使用临时 MEDIA_ROOT=C:\Users\Johnson\AppData\Local\Temp\sunjack_iss043_media 重跑：
Ran 938 tests in 490.124s
OK (skipped=14)
System check identified no issues (0 silenced).
```

前端回归日志：

```text
npm run test:unit                         153 passed, 0 failed
npx --no-install vitest run tests ...     67 files / 657 tests passed, 0 failed
npm run build                             passed (Vite production build)
```

staging 配置安全探针：设置 `APP_STAGE=staging`、`AUDIT_LOG_ENABLED=false` 导入 settings 失败并报 `AUDIT_LOG_ENABLED must be true outside development.`；未连接或修改生产数据库。

GitHub Actions 原始状态：代码提交 `fe11fc3042dc1470182f724bdb1fe5813facb5e6` 对应 [run 40317433830](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/40317433830)，0089 补修后的最终提交 `b142d4252c3d120d41e8b323bc1af417d0a58a49` 对应 [run 40318972037](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/40318972037)；两次整体均为 `failure`，`backend`、`backend-postgres`、`frontend` 均在约 2 秒后失败且 `steps=[]`。因此本次 CI 没有执行 PostgreSQL 触发器测试，不能把它标记为通过；不修改账户、额度或工作流绕过该状态。

## 浏览器与视觉证据

本轮没有修改业务页面布局或可见业务文案。Chrome Use 已连接本 Worktree 的隔离 Vite/Django 服务（`28432 → 28431`），打开标记 SKU 的库存详情并切换到“SKU 操作日志”：桌面和 `390×844` 窄屏均只展示日志面板，没有新增、修改、删除控件；开发环境开关关闭时显示明确的开发环境提示。窄屏现有关联记录页签保持横向滚动，这是本轮记录的既有布局观察，没有扩大安全补修范围。

截图：

- [桌面操作日志](operation-log-desktop.png)
- [390px 窄屏操作日志](operation-log-narrow-390.png)

截图由 Chrome Use 生成并复制到本目录；没有把内置浏览器或 API 测试冒充 Chrome 通过。

## 未覆盖 / PENDING

- 未连接真实生产 PostgreSQL，未修改真实角色权限；运行账号的实际 `UPDATE`/`DELETE` 拒绝、继承角色检查、触发器存在性、备份恢复演练均为 `PENDING`。
- 未执行特殊维护流程；runbook 要求独立 DBA 身份、工单号、备份、带工单 `application_name` 和额外维护审计，不提供应用绕过 API。
- 未引入外部审计平台、区块链或多级审批；未改 ISS-021/ISS-026 的操作历史和业务核心计算。
