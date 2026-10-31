# 统一集成测试日志

日期：2026-10-26
分支：`codex/integration-043-075-023`

| 检查 | 结果 |
|---|---|
| 后端三项定向 | 117 项，跳过 1 项，OK；审计、付款条件/实际付款、SKU 型号/快照、合同和库存联动覆盖 |
| Django 全量 | 940 项，跳过 14 项，OK；临时 `MEDIA_ROOT` 隔离 Worktree ACL 后运行 |
| Node 全量 | `npm run test:unit`：154/154 pass |
| 有效 Vitest | `npx vitest run tests --exclude tests/detail-drawer-typography.spec.js --environment jsdom`：67 文件、657/657 pass；排除项为 Node 风格且无 Vitest suite 的现有文件 |
| 前端构建 | `npm run build`：pass；仅既有大 chunk warning |
| 迁移检查 | 全新 SQLite 完整迁移至 0089：pass；独立库先到 0087 再升级 0088→0089：pass；`makemigrations --check --dry-run`：No changes detected |
| Chrome Use | 桌面/390×844 SKU 与采购页、历史付款页、组织权限页：pass；控制台 error/warning：0 |
| PostgreSQL | 本机 `127.0.0.1:5432` 未监听，`DEPLOYMENT_VERIFICATION_PENDING` |
| CI | 推送后按最终 SHA 查询；若本地 GitHub CLI/凭据不可用，保留明确不可核对记录，不冒充通过 |

首次 Django 全量执行的唯一错误是托管 Worktree 默认 `backend/media` ACL 拒绝附件目录创建；改用临时 `MEDIA_ROOT` 后同一 940 项完整通过，未修改应用代码。

## 保护性回归结论

- OperationLog 的 ORM/admin/API 改删拒绝、业务操作审计、事务回滚和脱敏测试通过；PostgreSQL 原生触发器只在真实 PostgreSQL 环境补验。
- 空 `payment_terms_snapshot` 的 PO 不创建虚假付款计划；显式旧快照仍生成并显示原计划，未恢复默认 30/70。
- SKU 参数修改只刷新仍等于旧自动值的型号；人工型号、明确空型号、报价/订单/采购商品快照不被覆盖。
- 三项没有改变银行资金事实、历史单据主体快照或正式财务统计口径。
