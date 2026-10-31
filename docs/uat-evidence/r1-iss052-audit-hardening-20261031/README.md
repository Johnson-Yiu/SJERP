# R1-ISS052-AUDIT-HARDENING-02

## 范围

- 基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`
- 分支：`codex/r1-iss052-audit-hardening-20261031`
- 实现提交：`ab9ce886094a065766a24b35d9b82c7a7c0fd067`
- 本轮整合 CSV 大小限制、HTTP 413、CSV 导入审计追溯，并补强数据库追加保护和迁移回退安全。

未连接真实业务数据库、未启用正式 RBAC、未部署、未触发 GitHub Actions、未创建 PR、未合并 master、未关闭 Issue。

## 来源提交与集成谱系

| 来源 | 精确来源 SHA | 本分支集成提交 | 说明 |
|---|---|---|---|
| d08 的直接父依赖 | `a6c5b56a00326234681399a3405efa2117198f76` | `403f4a30d914e9e888dde2de261357d3c05deab7` | d08 直接基于该提交；保留 CSV 限制与解析失败批次审计的前置实现。 |
| 流式 CSV 大小限制 | `d08ca625ac6beeec51ecc14eb92c97da0ea6f63b` | `1c9a86aedd928ad450276ad54b5db561740f8385` | 有界读取和超限停止处理器。 |
| 真实 HTTP 413 | `8cff96af9f1f2e09dcbc0a29f361017ee23ffb75` | `66ffa7be3cc861ef911cafe6c8c0b5feb3d17006` | d08 的后继；保留三入口 HTTP 413 测试和已有真实 Chrome 证据。 |
| CSV 导入审计追溯 | `f2b7fd6487459be69be687ccfeab09e7947df995` | `2f5b7a332e18c4d389cf832e015eaca3c623728f` | 新增 0093、PreviewAudit、操作人/重试/批次/行记录追溯和前端失败重试上下文。 |
| 本轮审计加固 | — | `ab9ce886094a065766a24b35d9b82c7a7c0fd067` | 新增 0094、PostgreSQL 原始 SQL 测试、迁移回退保护与关联回归。 |

所有提交消息包含 `[skip ci]`。集成按父依赖、d08、8cff、f2b7 顺序进行。d08 与固定基线之间存在未指定父提交，因此保留其父提交而不是只 cherry-pick 子补丁。审计提交独立从基线分出，与已集成上传代码重叠；冲突位于 `backend/crm/views.py` 和 `backend/crm/tests/test_safe_csv_import.py`。合并后统一 CSV 读取异常结构，保留 streaming reader、SHA/可靠行语义、audit preview link、HTTP 413 状态与 source 的测试；没有删除断言或放宽上传上限。前端 `ImportPage.vue` 的重试预览上下文和 Vitest 断言也保留。

## 数据库保护与回退

| 表 | UPDATE/DELETE | TRUNCATE |
|---|---|---|
| `CSVImportBatch` | 0091 PostgreSQL 行级触发器 | 0094 PostgreSQL statement 级触发器 |
| `CSVImportRowAudit` | 0091 PostgreSQL 行级触发器 | 0094 PostgreSQL statement 级触发器 |
| `CSVImportPreviewAudit` | 0093 PostgreSQL 行级触发器 | 0094 PostgreSQL statement 级触发器 |

0094 的回退前置检查在三个审计表任一存在记录时抛出 `RuntimeError`，因此标准迁移回退不会先移除最后一层 TRUNCATE 保护，也不会继续到删除审计历史的旧建表迁移。空表回退允许并可再正向迁移。模型/QuerySet 层现有 UPDATE/DELETE 防护继续保留。PostgreSQL 触发器运行期执行未在本轮验证；见下方限制。

## 审计关联核对

- 预览审计记录文件 SHA（仅完整文件）、实体、入口、状态、真实已认证用户（匿名预览允许为空）、失败原因和可靠解析行数；不保存 CSV 正文。
- 执行失败和成功批次通过 `CSVImportBatch.preview` 指向相应预览；行级审计通过 `CSVImportRowAudit.batch` 指向其批次。
- 失败后重预览通过 `retry_of_batch` 指向原失败批次；成功批次与失败批次分别追加，不覆写历史。审计操作日志包括批次、预览、行记录关联元数据。
- 正式执行要求从数据库可核实的认证用户；不把开发超级管理员展示名或未保存用户对象伪装成真实操作人。
- 成功业务写入、批次、行审计和操作日志处于一个事务。模拟成功行审计写入失败后，业务数据及成功审计整体回滚；失败批次单独原子写入。
- 新增回归覆盖 oversized execute 的有效预览与操作人关联；无完整文件时不写部分 SHA 或伪造行记录。

## 测试与证据

实际命令、运行数据库、退出结果和重要警告见[测试日志](logs/test-results.md)。全量 Django 使用 Django test runner 创建的内存 SQLite；隔离环境未连接真实业务数据库。

既有真实 HTTP 413/Chrome 证据作为 8cff 来源保留，未冒充为本轮重新截图：

- [来源真实 Chrome 截图](../r1-iss052-http-413-bd324-20261031/screenshots/chrome-csv-upload-413.png)
- [来源原始日志包](../r1-iss052-http-413-bd324-20261031/logs.zip)
- 本轮集成分支重新执行 Django LiveServer 三入口 HTTP 413 回归，具体命令与通过数量见 `logs/test-results.md`。

## 未完成 / 待后续核验

- **POSTGRESQL_VERIFICATION_PENDING**：本轮测试连接 `sqlite:///:memory:`，PostgreSQL 专项按 `connection.vendor` 跳过。已添加原始 SQL UPDATE、DELETE、TRUNCATE 对三张表的测试，但没有 PostgreSQL 实际执行证据。需在专用隔离 PostgreSQL 测试库运行该测试和 0091/0093/0094 迁移验证；不得连接真实业务库。
- **BROWSER_RETEST_NOT_RUN**：真实 Chrome 413 截图来自精确来源 8cff；集成分支本轮未重新启动 Chrome。新后端代码的三入口响应、临时文件为空及数据库无业务写入已由隔离 LiveServer 测试核对。
- 前端构建仍有主 JS chunk 超过 500 kB 的既有警告；与本轮审计保护无关，未改性能拆分。
- ISS-052 保持 `FIXED_PENDING_REVIEW`。本轮未关闭 Issue，等待独立审查及 PostgreSQL 验收。
