# ISS-097 超级管理员权限显示一致性

日期：2026-10-26
基线：`8b2b5c19e517addd9604b239211e199a789b739e`
分支：`codex/iss-097-admin-permissions`
规则原文：`C:\Users\Johnson\Desktop\SUNJACK-ERP_B8E5A1A7E599AEE6B4A7E4A48C%85_2026-10-24\新增议题逐项移交\ISS-097_超级管理员权限呈现与有效权限一致.md`

## 核实结论

历史 `superadmin` 模板有 24 条存储权限记录，其中 `reports`、`suppliers`、`purchases`、`packaging`、`trade_units`、`hs_codes`、`finance` 等新增模块可能没有有效勾选；这不是服务端授权缺失。`has_all_permissions()` 和 `effective_permission_matrix()` 对内置 `superadmin` 及开发超级管理员均按服务器规则返回全部 ERP 模块和动作。

因此确认的是“保存模板与实际有效权限不一致导致界面误导”的显示缺陷，不确认越权或服务端拒绝缺陷。本轮没有回写历史模板，也没有扩大普通角色授权。

## 最小修复

- `AccessRoleSerializer` 增加 `has_all_permissions` 和 `effective_permissions` 元数据；内置最高业务角色以服务端模块矩阵生成全部有效权限，普通角色仍使用已保存的 `permissions`。
- `OrganizationPage.vue` 对最高角色按有效矩阵显示全选，并显示“包含全部ERP业务权限，不受普通勾选项限制。此最高角色不可修改；下方勾选反映实际生效权限。”；复选框继续只读。
- 没有新增迁移、没有补写 `RolePermission`、没有改变 `development_superadmin_enabled()`、审计保护或正式 RBAC 执行规则。

## API 与数据库证据

隔离 SQLite：`C:\Users\Johnson\.codex\visualizations\2026\10\23\01a1690a-0a0e-7b72-826e-17ae19ef53e2\iss097-ui.sqlite3`。全新迁移完整应用至 `0089`，没有修改用户数据库。

对当前 Worktree 的本地 API `http://127.0.0.1:8127/api/organization/overview/` 实测：

| 字段 | 结果 |
|---|---|
| `role.code` | `superadmin` |
| `has_all_permissions` | `true` |
| `effective_permissions` | 24 个模块 |
| 6 个动作是否全部有效 | 是 |
| 历史存储模板的无勾选模块 | `finance, hs_codes, packaging, purchases, reports, suppliers, trade_units` |

测试还删除了历史 `reports` 存储行后重新读取 API；API 仍返回完整 24 模块有效矩阵，并确认该存储行没有被接口偷偷补写。

## 自动化验证

```text
python manage.py test crm.tests.test_functional_rbac.FunctionalRBACApiTests.test_superadmin_effectively_gets_every_module_and_action crm.tests.test_functional_rbac.FunctionalRBACApiTests.test_superadmin_overview_exposes_effective_matrix_without_rewriting_template --verbosity 2
2 tests — OK

python manage.py test crm.tests.test_functional_rbac crm.tests.test_development_access --verbosity 1
Ran 39 tests — OK；system check 无问题

vitest run tests/organization-access-ux.spec.js tests/functional-rbac.spec.js --environment jsdom --maxWorkers=2
2 files / 23 tests — PASS

node --test --test-reporter=dot
exit 0

vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js --maxWorkers=2 --reporter=dot
67 files / 658 tests — PASS

vite build
2012 modules transformed — PASS
```

前端全量 Vitest 保留既有 mock 路由和未解析指令警告，但没有失败；生产构建的既有大 chunk 提示也未因本轮引入新错误。

## 真实 Chrome 视觉核验

Chrome Use 连接当前 Worktree 的隔离服务：前端 `http://127.0.0.1:5291/organization`，后端 `http://127.0.0.1:8127`。桌面视口实际观察到：

- 页面显示“包含全部ERP业务权限，不受普通勾选项限制”；
- 显示 `24 / 24 个模块`；
- 当前可见矩阵的六类动作均为选中状态；
- 矩阵复选框均为禁用，不能通过普通勾选修改最高角色；
- 未显示旧的“当前身份只能查看”误导文案；
- 页面仍明确开发身份和数据范围仅为应用内权限，不把它描述为服务器或数据库管理员。

截图：[`iss097-chrome-desktop.jpg`](iss097-chrome-desktop.jpg)。

普通员工、销售员、采购员和财务员工使用现有 RBAC 受限角色夹具及后端 API 回归覆盖：普通角色仍按存储权限矩阵工作，缺少模块查看权限时接口拒绝，未增加数据范围。没有创建或冒充真实员工账号；正式员工会话和生产部署仍按 ISS-003、ISS-051 的原有风险登记等待后续授权验收。

## 风险与边界

- `P1 / DEPLOYMENT_VERIFICATION_PENDING`：本轮未连接生产 PostgreSQL、反向代理或服务器账号；ERP 超级管理员不等同于基础设施管理员的边界仍由 ISS-051 保留。
- `P1 / BUSINESS_VERIFICATION_PENDING`：没有真实创始合伙人及普通员工账号，本轮用隔离 RBAC 夹具核对会话/接口边界，不将其冒充正式员工 UAT；ISS-003 保持原状态。
- ISS-043 审计防篡改实现及其部署前风险未修改。

本轮不关闭 Issue、不合并 `master`、不改变正式权限方案，等待独立审查。
