# D — ISS-052 CSV 大小限制与解析失败审计

- 统一基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`
- 新分支：`codex/r1-iss052-csv-limit-bd324-20261030`
- 来源工作树：`codex/r1-iss052-csv-limit-failure-audit-20261029`，原 HEAD 与统一基线相同；仅迁移该任务的设置、视图和测试差异。

## 验收

使用 `backend/requirements.lock` 锁定依赖、一次性 SQLite 测试库和隔离 MEDIA_ROOT。

- `crm.tests.test_safe_csv_import`：23 项通过，0 失败。
- 覆盖文件大小上限、非法编码、缺失表头、失败批次审计和解析失败不得产生业务数据副作用。
- Django system check：通过。
- `makemigrations --check --dry-run`：无未生成迁移。

日志位于 `logs/`：`locked-dependencies.log`、`system-check.log`、`makemigrations-check.log`、`csv-limit-audit-tests.log`。

未连接生产服务；未运行 GitHub Actions。
