# R1-REPAIR-CONSOLIDATION-01 集成验收

日期：2026-10-28
固定基线：`054bd82518039a5bc0e0c14234964a14d7fbbfd8`
集成分支：`codex/integration-r1-repairs-20261028`

## 集成来源与完整性

| 内容 | 远端分支 | 集成前核实的精确 HEAD |
|---|---|---|
| R1-REPAIR-03 | `codex/repair-history-recipient-typography` | `c3739e77562c5dd8995228d5c3e7375a6728d316` |
| R1-REPAIR-04-FIX-01 | `codex/repair-browser-navigation-timeouts` | `e20f8a7bc506c299644b6c828c9b5574ee688f46` |
| R1-REPAIR-05 | `codex/fix-iss055-chinese-404` | `9c5f1f821cfc1b436f5fffe0b681991fa056b34d` |
| R1-REPAIR-06-FIX-01 | `codex/repair-playwright-isolation` | `5ad252c537dfb0b3f95150e76e471c9fe3fd0a99` |
| R1-REPAIR-07 | `codex/repair-orders-390-layout` | `58541e94918e2d912c2b75d2371a8d625e1fc9d4` |
| final-cross-module-ux | `codex/repair-final-cross-module-ux` | `45df13b8fd229427229a58d64d0ae2bec30a00cb` |
| supplier-purchase-ux-r2 | `codex/repair-supplier-purchase-ux-r2` | `64fb397aa065062e192ceb30040421f59b63a08c` |

七个指定版本分别按 non-fast-forward merge 集成；合并后检查文件差异、提交祖先关系与业务逻辑，没有来源版本被静默替换，也没有新增数据库迁移。

供应商分支 `codex/repair-supplier-purchase-ux-20261028` 的远端 SHA `fe1cc16c3950e256fa564ea4508e08414ae8810b` 与 R2 非祖先关系。对其 `iss075-payment-terms-real.spec.js` 独有差异逐项检查后，仅保留两条 Google Fonts 外部请求路由拦截，以避免字体网络不稳定；没有删除、放宽 ISS-075 的业务断言，也没有合并其余提交。

## 冲突与兼容性检查

- 七次合并均无文本冲突；未用单一分支覆盖 `PROJECT_ISSUES.md`、`PROJECT_PHASES.md` 或验收材料。
- 合并后仅增加集成本轮的状态核实、历史记录和验收索引；既有台账/阶段记录保留。
- 来源差异中没有数据库迁移。集成后 `makemigrations --check --dry-run` 通过。
- 无业务财务、采购、MOQ、付款计划、权限或历史数据规则修改。ISS-075 仍保留“新采购单不隐式生成固定付款计划、历史显式计划保留”的约束。
- 集成专用的少量测试夹具调整仅用于让允许列表内的浏览器测试安全使用 R1-06 隔离 runner；不增加通用 seed 参数，也不修改产品业务代码。

## 综合回归

除表中说明的 RBAC 前置条件外，均在固定集成分支与本地隔离环境执行。隔离浏览器流程为每次运行分配独立 API/Vite 端口、SQLite、`MEDIA_ROOT` 和 run identity，并验证 Vite `/api` 代理目标后再运行测试。

| 范围 | 结果 |
|---|---|
| Django system check | 通过 |
| Django migrations check | 通过；未发现未生成迁移 |
| Django 全量测试 | 1,000 项发现；982 项通过、18 项按套件标记跳过、0 失败 |
| Django 隔离 runtime 定向测试 | 10/10 通过 |
| Node 单元测试 `npm run test:unit` | 169/169 通过 |
| Node detail-drawer typography | 1/1 通过 |
| Vitest | 66 个文件、657 项通过 |
| trade-unit Vitest | 1 个文件、4 项通过 |
| R1-06 runner 自测 | 13/13 通过，覆盖错误代理、端口冲突及并行隔离等拒绝/隔离路径 |
| Playwright 隔离基础冒烟 | 1/1 通过，直接 API 与 Vite 代理身份一致 |
| Playwright 全量浏览器文件 | 31 个 spec、189 项通过、0 失败 |
| 前端生产构建 | 通过；主 JS 1,126.05 kB，gzip 393.59 kB；保留大于 500 kB chunk 警告 |
| `git diff --check` | 集成实现提交和最终交付差异均通过 |

另对真实隔离 API 场景复测：ISS-022 MOQ 1/1、ISS-075 付款快照 1/1、历史订单 02/03 各 2/2、ISS-029 收件人快照及 XLSX 1/1。全量浏览器文件已包含这些 spec。ISS-055 的真实员工/RBAC 浏览器 spec 未执行：它要求正式员工会话及启用的 RBAC，本轮不得启用正式 RBAC；没有用本地 mock 结果替代。相关 Django 范围测试和前端中文错误映射单测纳入本轮回归。

Vitest 首次使用 `npx vitest run tests ...` 时，Vitest 将 `tests` 解析为文件名筛选而扫描了 Node/Playwright 基础设施目录，造成 2 个非 Vitest suite 收集错误；改用 `--dir tests` 后正确范围为 66 文件、657 项全通过。首次 Django 全量测试继承到父进程 `AUDIT_LOG_ENABLED=0`，触发 11 个部署安全校验失败；在同一隔离 DB/MEDIA_ROOT、移除该继承覆盖后重跑 1,000 项通过（18 skipped）。两次初始日志均保留，作为环境/命令选择记录，不计作集成回归缺陷。

## 真实浏览器证据

本轮截图由 Chromium/Chrome 浏览器实际运行 Playwright 生成；涉及 API 的场景使用本轮隔离 SQLite 和合成资料。截图/诊断共 79 个文件：51 张 PNG、25 个 JSON、3 个 XLSX。

| 场景 | 可核查证据 |
|---|---|
| ISS-022 供应商 MOQ 草稿、低 MOQ 提醒、例外原因、取消保留草稿及正式下单 | [`screenshots/iss022/`](screenshots/iss022/) |
| ISS-075 不显示固定付款规则、新采购单为空付款快照、历史计划保留 | [`screenshots/iss075/`](screenshots/iss075/) |
| 历史订单详情/收件人快照 | [`screenshots/history-02/`](screenshots/history-02/)、[`screenshots/history-03/`](screenshots/history-03/) |
| Quote 收件人快照、版本编辑、PI/XLSX 导出核验 | [`screenshots/iss029/`](screenshots/iss029/) |
| 订单 390/700/1024/1440 布局及 DOM 尺寸 | [`screenshots/orders-390/`](screenshots/orders-390/) |
| 供应商 UI、Finance/Inventory/Reports 导航与细节、路由修复 | [`screenshots/supplier-ui/`](screenshots/supplier-ui/)、[`screenshots/r1-repair-04/`](screenshots/r1-repair-04/) |

原始命令输出位于 [`logs/`](logs/)，包括 Django、Node、Vitest、构建、隔离 runner、每个全量 Playwright spec 和定向真实 API spec 日志。来源任务的原始截图和报告仍保存在各自验收目录中，索引见 [`../INDEX.md`](../INDEX.md)。

## Issue 状态与遗留验收缺口

- ISS-022、ISS-029、ISS-055、ISS-075：保持 `FIXED_PENDING_REVIEW`，等待独立代码/业务/视觉复审，不关闭。
- ISS-041：仍为 `Enhancement / BLOCKED（延期）`；本轮浏览器证据不代表整个 Enhancement 已完成。
- ISS-003：真实员工会话、正式组织树与启用 RBAC 的 UI/API 权限矩阵未验收；开发超级管理员机制未改。
- ISS-002：不属于本轮修复来源，既有 Pillow 11.3.0 风险与 Python 依赖锁定缺口仍需单独处理。
- ISS-052：不属于本轮修复来源；审计日志关闭时的导入操作者/行级持久审计缺口仍待补验。
- ISS-058：本轮构建数字仅为包体复测，不构成真实用户性能改善证据。
- ISS-055 浏览器级真实员工权限证据仍需在获授权的隔离 RBAC 环境补测；本轮未改变权限设置。

## GitHub Actions 与 11 月 1 日待办

按要求没有触发或重试 GitHub Actions；本地回归不代表 CI 成功。11 月 1 日对推送后的精确最终 SHA 手动核对现有 `backend`、`backend-postgres`、`frontend` 三个 job：记录每个运行链接及结果；若因额度、付款或外部启动错误阻塞，保留 Actions 页面原始错误，不以本地结果替代。不得在该日期前启动 CI。

本轮未合并 master、未部署、未启用正式 RBAC、未操作实际业务数据库、未关闭 Issue。测试使用的隔离 SQLite/MEDIA_ROOT 由 runner 仅清理本次标记的临时资源。
