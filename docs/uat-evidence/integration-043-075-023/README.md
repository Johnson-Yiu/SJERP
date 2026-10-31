# ISS-043 / ISS-075 / ISS-023 统一集成验收

日期：2026-10-26
统一基线：`f12b591cb90d6a5d8ebfedf1c559703377c92d84`
集成分支：`codex/integration-043-075-023`

## 集成范围

按 ISS-043 → ISS-075 → ISS-023 顺序，在独立 Worktree 中移交已审查成果：

- ISS-043：`dea057ce0c98fc32da44b72999beb4af78a58176`，包含 0088 append-only 和 0089 operator `PROTECT`。
- ISS-075：`771307b19667256453c7c22ebf60256ffd2a26dd`，取消常规采购隐式付款条件回填，保留显式历史计划。
- ISS-023：`c6a1415437fb2a020ec31d655fe8ce274aa93912`，保护人工 Sales Model、历史空型号和 SKU 版本快照。

三项均已完整集成。Git cherry-pick 依次纳入 ISS-043 的 4 个历史提交、ISS-075 的 1 个提交和 ISS-023 的 1 个提交；没有整文件覆盖。`serializers.py`、`PROJECT_ISSUES.md`、`PROJECT_PHASES.md` 没有未解决文本冲突，自动合并后逐段核对，保留两项业务逻辑。0088 依赖 0087，0089 依赖 0088，未复制或改写既有迁移历史。

## Chrome Use 证据

浏览器使用隔离 SQLite、Django `54174` 和 Vite `54175`（`vite.iss075.config.js` 代理到隔离后端）：

- SKU 管理：桌面和 390×844 窄屏均可见；窄屏导航收起后标题、指标、搜索和页面入口仍可用。
- 采购管理：桌面和 390×844 窄屏均可用；3 个无付款阶段 PO 显示 0.00 / 100.00，历史 `ISS075-HISTORY-01` 显示两阶段 500/500 应付计划。
- 历史 PO 付款页：供应商付款金额、已付/未付、两行付款计划和状态均显示一致。
- 组织与权限页：开发身份仍通过既有开发超级管理员入口显示；没有修改正式 RBAC 或创建正式账号。
- Chrome 控制台：上述页面未捕获 error/warning。

截图：

- [SKU 桌面](screenshots/sku-desktop.png)
- [SKU 窄屏 390×844](screenshots/sku-narrow-390x844.png)
- [采购桌面](screenshots/po-desktop.png)
- [历史付款计划](screenshots/po-payment.png)
- [采购窄屏 390×844](screenshots/po-narrow-390x844.png)

## 边界与延期台账

- ISS-043 真实 PostgreSQL 运行账号、角色继承、触发器现场拒绝、备份恢复和特殊维护留痕未执行，保留 `BLOCKED` / `DEPLOYMENT_VERIFICATION_PENDING`。
- ISS-075 无付款阶段 PO 与真实业务财务数据的跨模块抽查未执行；本地自动化和隔离数据通过，保留 `BUSINESS_VERIFICATION_PENDING`，不表示发现代码缺陷。
- ISS-023 真实 SKU 主数据的型号完整性抽查未执行，保留 `BUSINESS_VERIFICATION_PENDING`；不批量改写旧 SKU。
- ISS-023 窄屏菜单收起可用性已通过，不登记为未修复事项。
- 本机 PostgreSQL 未监听；远端 CI 必须以最终精确 SHA 另行核对。未连接生产数据库、未部署、未生成或写入真实密钥。

所有延期/环境待验说明只登记在现有 `docs/PROJECT_PHASES.md` 与 `docs/PROJECT_ISSUES.md`，没有创建第二套 Issue 清单。ISS-043、ISS-075、ISS-023 均保持未关闭，等待统一独立审查。
