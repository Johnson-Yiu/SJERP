# 统一集成测试日志

运行目录：`C:\Users\Johnson\.codex\worktrees\integration-039-037-040\森爵照明管理系统`

## 后端

| 命令 | 结果 |
|---|---|
| `python manage.py check` | 通过，0 issues |
| `python manage.py makemigrations --check --dry-run` | 通过，No changes detected |
| `python manage.py test crm.tests.test_integration_039_037_040` | 1/1 通过 |
| `python manage.py test crm`（临时 MEDIA_ROOT） | 856 通过，13 skipped，0 failed |
| ISS-039/037/040 定向测试 | 76/76 通过；权限、快照、成本分配、实际装箱录入与导出均覆盖 |

完整 Django 测试在默认 worktree `backend/media` ACL 下曾出现 1 个附件上传 PermissionError；未改目录权限，改用临时 `MEDIA_ROOT` 重跑后全套通过。测试输出中的 Bad Request/Internal Server Error 为主动覆盖的拒绝、权限、事务回滚路径。

## 数据库迁移

- 全新 SQLite：从头执行至 `0080_formal_party_snapshots`，通过。
- 已有 SQLite：从现有数据库副本升级，`0078`、`0079`、`0080` 均通过。
- `makemigrations --check` 无新迁移；未发现重复迁移或遗漏依赖。

## 前端

| 命令 | 结果 |
|---|---|
| `npm run test:unit` | 150/150 通过 |
| 相关 Vitest（采购成本、订单发货、实际装箱、采购工作台、筛选） | 5 files / 63 tests 通过 |
| 有效 Vitest 全量（排除两个既有基线问题文件） | 63 files / 622 tests 通过 |
| `npm run build` | 通过；仅有既有 bundle 大 chunk warning |

未排除的 Vitest 全量结果为 63 files passed、`detail-drawer-typography.spec.js` 无 Vitest suite、`phase2a-list-shell.spec.js` 的旧静态断言未包含现有 `/historical-orders`。两项均与本次三项集成无关。

## 真实 Chrome

当前集成服务以真实 Windows Chrome headless 加载实际订单 `SO-ISS040-D` 的装箱页，API 代理指向本集成分支的 Django 8123 服务：

- `chrome-integrated-desktop-1440.png`：桌面布局、Shipment 批次、实际装箱完成、导出 Packing List。
- `chrome-integrated-narrow-700.png`：窄屏布局、同一 Shipment、导出入口与箱明细可用。

ISS-039/037 的已保存 Chrome 证据仍分别位于对应 Issue 目录。原生 Excel Print Preview：**PRINT PREVIEW PENDING**。
