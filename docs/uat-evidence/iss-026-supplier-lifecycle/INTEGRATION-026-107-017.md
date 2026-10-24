# ISS-026 / ISS-107 / ISS-017 统一集成验收

日期：2026-10-24

统一基线：`71ec4a4c2d860b9944624a1434d9d7580e9a6d38`

集成分支：`codex/integration-026-107-017`

状态：`FIXED_PENDING_REVIEW`，未合并 `master`，未关闭 Issue。

## 成果来源与迁移

| 任务 | 远端分支 | 精确成果 SHA | 远端核对 |
|---|---|---|---|
| ISS-026 | `codex/iss-026-supplier-lifecycle` | `3625f472b028146c062823990322de32a98759a1` | `git ls-remote` 可见 |
| ISS-107 | `codex/iss-107-finance-labels` | `60df1b045c06c7f2146b44e4a60866b1786024cc` | `git ls-remote` 可见 |
| ISS-017 | `codex/iss-017-private-files` | `c5fc1c11b9728655a363a4f2a5ba0544584a8d07` | `git ls-remote` 可见 |

按指定基线建立独立 Worktree 后，按任务逐项 cherry-pick：

- ISS-026 集成提交：`523d9fa`（来源 `3625f472...`）。
- ISS-107 集成提交：`52bb644`（来源 `60df1b045...`）。
- ISS-017 集成提交：`8c53a67`（来源 `c5fc1c11...`）。
- 迁移汇合提交：`e30c7fc`，新增 `crm.0082_merge_iss026_iss107_iss017`，无业务操作。

三个源提交均直接以统一基线为父提交。冲突仅有一个：`docs/PROJECT_PHASES.md` 的两个追加段落发生文档冲突，已保留 ISS-026 与 ISS-107 的完整记录；模型、API、前端和迁移文件没有代码冲突。没有覆盖、删除或改写已发布迁移。

## 迁移验收

三条并行叶节点均依赖 `crm.0080_formal_party_snapshots`：

- `0081_supplier_lifecycle`
- `0081_transaction_rmb_reference_label`
- `0081_product_certificate_private_file`

新增无操作 merge migration `0082_merge_iss026_iss107_iss017`，保留三条历史路径。结果：

- 全新 SQLite：`0001` 至 `0082` 顺序迁移通过，`makemigrations crm --check --dry-run` 为 `No changes detected`。
- 既有 SQLite：先迁移至 `0080`，再升级至三个 `0081` 和 `0082`，通过。
- 回滚/重放：从 `0082` 回退至 `0080` 成功，再次迁移至 `0082` 成功。
- `showmigrations crm`：`0078`、`0079`、`0080`、三个 `0081` 和 `0082` 均为 `[X]`。

本地完成的是 SQLite 新库、既有库升级和回滚/重放；PostgreSQL 的 GitHub CI 源任务运行均为失败状态且没有可用步骤日志，因此不能把本地结果写成 PostgreSQL/生产迁移通过。

## 业务与权限交叉验收

### ISS-026

源分支既有专项证据保留在 `README.md`：无历史交易和有历史交易供应商的直接删除均为 405；停用/恢复写入审计；停用后不进入新采购候选，历史采购、付款、联系人、供应来源和快照仍可读取；ISS-039 成本分配和 ISS-037 历史主体快照没有被改写。集成后后端全量回归仍通过。

### ISS-107

账面人民币折算参考与银行已确认人民币净额继续分开。既有金额、汇率、Transaction API 键、CSV 字段、旧 `source=cash` 报表配置和 ISS-048 统计/权限逻辑未改写。既有证据批次保持账面参考 `USD 100 × 7.1 + CNY 250 = ¥960.0000`，银行确认净额 `¥705.00`，源任务记录的前后金额哈希保持一致。Chrome 截图见 `docs/uat-evidence/r1-fin-p1/`。

### ISS-017

后端定向权限测试覆盖未登录、越客户、证书、SKU 图片、报价图片、跟进附件、缓存响应和直接 URL；证书外部 URL 被拒绝，合法采购跨销售权限由既有测试保留。应用代码测试不能替代目标部署的 Nginx/CDN/对象存储代理安全审查；该部署边界仍明确保留在源证据 README 中。

## 自动化、构建与浏览器

| 检查 | 结果 |
|---|---|
| Django 全量 | `Ran 862 tests ... OK (skipped=13)`；最终集成测试环境无 system check 问题 |
| 集成定向后端 | 55/55 通过；覆盖供应商生命周期、财务参考口径、实际资金/共享报表和功能 RBAC |
| Node 单元 | 151/151 通过 |
| 有效 Vitest 全量 | 64 files，645/645 通过；排除仓库已有 `detail-drawer-typography` 项，遵循 CI 配置 |
| 交易单位定向 Vitest | 4/4 通过 |
| 生产构建 | Vite 2009 modules 成功；仅保留既有大 chunk warning |
| Chrome 桌面/窄屏 | 真实 Chrome channel 执行 25 个选定用例；供应商、财务口径、报表权限、证书/HS 页面覆盖 1440/1280/1024/700/390。首轮 22 个通过，3 个只因历史用例截图路径不能写入受管 Worktree；同一 3 个受影响用例已在写入权限修正后重跑通过，未出现业务断言失败 |

本轮生成/更新的截图包括：

- `../iss-017-private-files/certificate-desktop.png`
- `../iss-017-private-files/certificate-narrow.png`
- `../iss-067-report-permission/employee-old-url-1440.png`
- `../iss-067-report-permission/employee-authorized-source-1440.png`
- `../iss-067-report-permission/employee-old-url-700.png`
- ISS-107 财务页面/报表/流水的 Chrome 截图及 CSV/API 快照保留在 `../r1-fin-p1/`。

为使全量后端测试与 ISS-017 规则一致，修正了旧测试中把外部证书 URL 第二次 PATCH 断言为 200 的一处断言；现在断言 400、错误字段存在、证书名称/文件链接/有效期不变。这是测试一致性修正，不是业务逻辑变更。修正后的该测试及 Django 全量均通过。

## GitHub CI 与剩余风险

三个源提交对应的 GitHub CI 均已核对为 `failure`，分别是运行 `40066297225`（ISS-026）、`40056744016`（ISS-107）和 `40056435147`（ISS-017）；作业均在可见步骤前失败，不能据此宣称源任务 CI 通过。集成分支推送后的 CI 结果以远端运行记录为准。

仍未完成或不能由本轮证明的事项：

1. 没有目标生产代理、CDN、对象存储和正式账号，ISS-017 的部署级直链/缓存/跨客户安全验收仍待独立安全环境。
2. 本地未运行 PostgreSQL；SQLite 迁移升级/回滚不能替代 PostgreSQL 并发与部署迁移验证。
3. 浏览器权限用例使用隔离 fixture/mock API；真实 Django 权限由 APIClient/后端测试覆盖，不能把本地开发超级管理员或 mock 浏览器冒充生产代理安全验收。
4. 三个源任务及集成状态均保留 `FIXED_PENDING_REVIEW`，等待统一独立审查；本轮不合并 `master`、不关闭 Issue。
