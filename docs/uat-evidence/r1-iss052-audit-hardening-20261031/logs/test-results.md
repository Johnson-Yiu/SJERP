# R1-ISS052-AUDIT-HARDENING-02 测试日志

运行日期：2026-10-31。环境：Windows；Python 3.14.5；Django 6.0.6；Node 24.16.0；npm 11.13.0。Django 测试均显式设置 `DATABASE_URL=sqlite:///:memory:`，由 test runner 创建隔离 SQLite 测试库；未连接真实业务数据库。

## Django 定向回归

命令（工作目录 `backend/`）：

```powershell
$env:DATABASE_URL='sqlite:///:memory:'
$env:AUDIT_LOG_ENABLED='1'
python manage.py test crm.tests.test_safe_csv_import crm.tests.test_csv_upload_http_413 crm.tests.test_csv_import_audit_migration_rollback crm.tests.test_csv_import_audit_postgres -v 1
```

最终结果：`Ran 36 tests in 53.136s`，`OK (skipped=1)`，system check 无问题。35 项实际执行通过；1 项 PostgreSQL 原始 SQL 专项因 SQLite vendor 被明确跳过。覆盖 CSV 预览/正式执行/兼容端点的大小限制与 HTTP 413、解析失败、真实操作人、批次/预览/行审计关联、失败重试、审计写失败事务回滚、迁移空数据正反向及含数据回退拒绝。

集成期间第一次定向执行 35 项，曾有 1 项失败：旧的上传边界测试要求超限异常的 `digest is None`，统一异常类一度把“未知完整文件 SHA”转换成空字符串。已恢复原异常属性语义并增加有效预览关联的超限执行回归；最终 36 项定向结果如上。

## Django 全量回归

命令（工作目录 `backend/`）：

```powershell
$env:DATABASE_URL='sqlite:///:memory:'
$env:AUDIT_LOG_ENABLED='1'
python manage.py test -v 1
```

结果：`Ran 1041 tests in 707.003s`，`OK (skipped=20)`，即 1021 通过、20 跳过、0 失败；Django system check 无问题。测试输出中的预期 4xx/异常日志来自已有负向/故障注入用例；未出现失败汇总。全量测试附带输出的 P2A 数据库验证哈希前后相同，legacy 金额/分配记录未变。

## Django / 迁移检查

| 命令 | 结果 |
|---|---|
| `python manage.py check`（SQLite memory 配置） | PASS：`System check identified no issues (0 silenced).` |
| `python manage.py makemigrations --check --dry-run crm` | PASS：`No changes detected in app 'crm'` |
| `test_empty_audit_tables_allow_reverse_and_forward_migration` | PASS：空审计表允许回退 0094 到 0093，再正向迁移恢复 0094。 |
| `test_reverse_is_refused_while_any_audit_history_exists` | PASS：存在 Preview/Batch/Row 记录时回退被拒，迁移记录及三类审计行保持。 |
| 新增 PostgreSQL raw SQL UPDATE/DELETE/TRUNCATE 测试 | SKIPPED：当前测试连接 vendor 是 SQLite；未声称 PostgreSQL 通过。 |

## 前端相关回归

| 命令 | 结果 |
|---|---|
| `npm ci --offline` | PASS：添加 227 packages，审计 228 packages，0 vulnerabilities；npm 报现有 `glob@10.5.0` 和 `lucide-vue-next@1.0.0` 弃用警告。 |
| `npm exec -- vitest run tests/import-preview-state.spec.js --environment jsdom` | PASS：1 文件 / 1 测试。 |
| `npm run test:unit` | PASS：171 通过、0 失败、0 跳过；Node test runner 用时约 81.67 秒。 |
| `npm run build` | PASS；主 JS 1,128.12 kB（gzip 394.27 kB）；保留 Vite >500 kB chunk 警告。 |

本轮 Chrome 未重新启动；8cff 来源中已有真实 Chrome HTTP 413 截图和 `logs.zip`，在本轮报告中标记为“继承来源证据”，不作为本轮新截图。

## 差异与边界检查

- `git diff --cached --check`：代码提交前及报告/台账文档提交前均 PASS，无空白错误。
- 未运行 GitHub Actions；所有新提交包含 `[skip ci]`。
- PostgreSQL 数据库触发器实际执行、生产代理行为、正式 RBAC、真实业务数据均未验证。
