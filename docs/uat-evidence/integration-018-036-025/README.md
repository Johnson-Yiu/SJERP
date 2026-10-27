# INTEGRATION-018-036-025｜ISS-018、ISS-036、ISS-025 集成验收

日期：2026-10-27

统一基线：`7951ecb8c6196f773128ad5978bfcd0a5b30c6b5`

集成 Worktree：`C:\Users\Johnson\.codex\worktrees\integration-018-036-025\森爵照明管理系统`

集成分支：`codex/integration-018-036-025`

## 来源与提交

按 ISS-018 → ISS-036 → ISS-025 顺序集成，三条来源 HEAD 均已成为集成 HEAD 的祖先，功能提交和证据提交没有遗漏：

| 任务 | 来源分支 | 来源 HEAD |
|---|---|---|
| ISS-018 | `codex/fix-iss018-restore-edge-cases` | `21812b7c1190540a7214d4b77518ede31221180a` |
| ISS-036 | `codex/fix-iss036-invalid-snapshot` | `80a93559852d9d679c86d71250549261c7c2bbd1` |
| ISS-025 | `codex/iss025-report-visual-evidence` | `1480429338d0fc6de20384ea77a43e969a2b7de4` |

集成提交：

- `b58af55`：ISS-018 备份恢复及报告路径安全。
- `47c97d8`：ISS-036 不可拆分单位与异常快照校验。
- `ef9b457`：ISS-025 客户状态报表映射及视觉证据。

## 冲突与代码核对

- ISS-018 → ISS-036：仅 `docs/PROJECT_PHASES.md` 冲突；保留 ISS-018 与 ISS-036 两侧完整阶段记录。
- ISS-036 → ISS-025：仅 `docs/PROJECT_PHASES.md` 冲突；保留 ISS-018、ISS-036、ISS-025 全部记录。
- `backend/crm/serializers.py` 的 ISS-036 与 ISS-025 修改自动合并；复核确认 `CustomerSerializer.status_display`、客户状态映射，以及 `ShipmentPackageSerializer` 的 factor-one、不可拆分整数倍和异常快照歧义处理同时存在。
- `docs/PROJECT_ISSUES.md` 的三项最新状态和来源证据均保留；没有新增迁移，未覆盖 ISS-018/036/025 历史记录。

## 本地测试日志

后端定向：

```text
python manage.py test crm.tests.test_iss018_backup_recovery crm.tests.test_actual_packing crm.tests.test_issue_025_status_labels --verbosity 1
Ran 60 tests in 5.886s
OK (skipped=3)
```

全量 Django：首次使用 Worktree 默认 `backend/media` 时，`crm` 984 项出现 1 个环境错误，唯一堆栈为 Windows ACL 拒绝创建附件目录；没有代码断言失败。使用隔离临时 `MEDIA_ROOT` 重跑：

```text
MEDIA_ROOT=<temporary-isolated-directory> python manage.py test crm --verbosity 1
Ran 984 tests in 406.957s
OK (skipped=18)
```

检查与迁移：

```text
python manage.py check
System check identified no issues (0 silenced).

python manage.py makemigrations crm --check --dry-run
No changes detected in app 'crm'
```

迁移检查有本地既有 SQLite `unable to open database file` RuntimeWarning，但退出码为 0、没有生成迁移。未执行生产 PostgreSQL。

前端：

```text
npm run test:unit
156 passed, 0 failed

npx vitest run --environment jsdom tests --exclude tests/detail-drawer-typography.spec.js
Test Files 67 passed (67)
Tests 661 passed (661)

npm run build
2018 modules transformed; built successfully
```

首次 `npm run test:unit` 因 Worktree 没有 `node_modules` 而报 `axios` 缺失；仅在本地用 `npm install --ignore-scripts --no-audit --no-fund --no-package-lock` 补齐依赖后通过。首次 Vitest 未指定 jsdom，78 项因 `document/localStorage` 缺失失败；按项目测试环境重跑后 661 项全部通过。上述首次失败均已保留为环境/命令记录，不标记为代码回归。

生产构建仅有既有大 chunk warning；没有运行浏览器自动化或连接生产环境。本轮未调用 GitHub Actions，集成提交使用 `[skip ci]`。

## 截图与既有真实证据路径

本轮只执行本地自动化，不新增浏览器截图；来源分支截图随集成保留：

- ISS-036：`docs/uat-evidence/iss036/chrome-invalid-indivisible-roll.png`、`docs/uat-evidence/iss036/chrome-success-indivisible-roll.png`。
- ISS-036-FIX-01/FIX-02：`docs/uat-evidence/iss036-fix01/chrome-invalid-factor-one.png`、`docs/uat-evidence/iss036-fix01/chrome-success-factor-one.png`、`docs/uat-evidence/iss036-fix02/chrome-invalid-factor-one.png`、`docs/uat-evidence/iss036-fix02/chrome-success-factor-one.png`。
- ISS-025-FIX-02：`docs/uat-evidence/review-iss025-status-consistency/screenshots/iss025-fix02-customer-status-report-desktop.png`、`docs/uat-evidence/review-iss025-status-consistency/screenshots/iss025-fix02-customer-status-report-mobile-390x844.png`。
- ISS-018：后端隔离恢复及结构化报告证据见 `docs/uat-evidence/iss-018-backup-recovery/README.md`，本轮没有伪造 UI 截图。

## 延期与未关闭事项

- ISS-018 继续 `BLOCKED` / `DEPLOYMENT_VERIFICATION_PENDING`：真实 PostgreSQL、生产私有媒体卷、POSIX/NTFS ACL、加密异地副本、自动任务/告警、RPO/RTO 和部署恢复演练未验证。
- ISS-036 继续 `FIXED_PENDING_REVIEW`：冲突历史交易单位快照的归属/优先级仍需业务确认；生产 PostgreSQL、真实物流数据和正式员工场景未验收。
- ISS-025 继续 `FIXED_PENDING_REVIEW`：真实员工权限、生产数据库和全量业务数据抽查仍待 `BUSINESS_VERIFICATION_PENDING` / `DEPLOYMENT_VERIFICATION_PENDING` 验证。

本轮未合并 `master`、未关闭 Issue、未部署生产环境，等待统一独立审查。
