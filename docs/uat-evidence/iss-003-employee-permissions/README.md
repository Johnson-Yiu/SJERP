# ISS-003 员工权限与数据范围隔离验收

## 本轮结论

- 基线：`46353a5436637832f5adadb7bdef6b45cdeada23`
- 分支：`codex/verify-iss003-employee-permissions`
- 工作树：独立托管 Worktree（未修改其他工作树）
- 日期：2026-10-27
- 结论：本轮隔离 API/服务端范围回归通过；ISS-003 不关闭，仍为 `BLOCKED`。
- 本轮未修改业务代码、开发身份配置或 RBAC 配置；只新增本报告并更新既有项目台账。

本轮使用合成用户、合成客户和隔离 SQLite。没有连接生产数据库，没有使用真实员工账号，没有启用当前开发环境的开发超级管理员，也没有把默认开发姓名当作正式审计操作人。

## 权限与数据范围矩阵

测试夹具在 `crm.tests.test_sales_data_scope`、`test_procurement_data_scope`、`test_finance_data_scope` 和 `test_functional_rbac` 中创建独立用户及角色。用户名称仅为隔离测试标识，不代表正式员工账号。

| 隔离身份 | 数据范围 | 合成组织 | 预期可见客户 | 结论 |
|---|---|---|---|---|
| `scope-a` | `self` | 销售部 | 仅本人负责客户 A | 通过 |
| `scope-manager` | `department` | 销售部 | 销售部客户 A、B | 通过 |
| `scope-tree` | `department_tree` | 销售部及下级团队 | 销售部客户 A、B 与下级团队客户 | 通过 |
| `scope-all` | `all` | 全部有效组织 | 全部合成客户，包括未归属客户 | 通过 |
| `rbac-readonly` | 有效角色但未授予目标模块动作 | 仅合成组织 | 无目标模块业务访问 | 通过拒绝路径 |
| 匿名请求 | 无身份 | 不适用 | 无业务数据 | 通过拒绝路径 |

服务端 `effective_data_scope()` 按有效角色的最宽范围和员工覆盖值计算；`development_superadmin_enabled()` 仍是开发身份唯一入口。本轮测试用 `APP_STAGE=development`、`DEBUG=false`、`DEVELOPMENT_SUPERADMIN=false`、`RBAC_ENFORCEMENT=true`，因此合成员工走正式权限执行分支。

## 覆盖场景与实际结果

### 1. 模块权限、列表、详情和搜索

- 未登录访问客户 API 被拒绝（当前 DRF 配置实际返回 HTTP 403）。
- 缺少 `view` 的模块不会因已有其他模块权限而放行；客户、采购单、付款计划、SKU、交易等缺少模块权限的入口均按模块拒绝。
- `self`、`department`、`department_tree`、`all` 四种范围的客户列表结果与组织关系一致。
- 联系人、跟进、报价、订单、发货及客户关联 Context 复用客户范围；无权客户的列表结果为空，详情、关联 Context 和越权动作按当前接口契约返回 404。
- 搜索不会扩大授权集合；采购单搜索中的销售订单号只有在销售订单范围内才进入可搜索字段。
- 客户、联系人、跟进、报价和订单的跨范围创建、更新、客户改绑及报价修订均被拒绝，原记录保持不变。

### 2. 导出、报表和财务 API

- 报表屏幕查询要求 `reports.view` 及对应来源模块查看权限。
- CSV 导出额外要求 `reports.export`；只有查看权限不能导出。
- 报表屏幕总额和 CSV 合计复用同一范围查询；跨客户数据不会通过分组、详情或导出出现。
- 财务计划、交易流水、资金分配和财务概览按销售客户范围过滤；采购/公共费用等无销售客户归属的共享业务保持既有规则。
- 财务关联客户、订单、采购单、付款计划及原始流水的创建、改绑、冲销会同时检查模块权限和数据范围。

### 3. 共享采购业务与跨模块脱敏

- 采购人员可以在具备采购修改权限的情况下处理必要的共享采购成本归属，即使没有销售订单查看权限；这是受控共享业务路径，不等同于获得销售客户资料权限。
- 成本归属返回的销售关联仅保留采购分配需要的受控识别信息；采购单序列化器在没有销售订单范围时清除订单详情和关联订单列表，并设置 `sales_link_restricted`。
- 没有财务与流水查看权限时，采购单不会返回已付/未付金额；没有供应商权限时，供应商名称、地址、联系人和邮箱快照会被清除。
- 缺少订单查看或更新权限不会阻止无销售订单的独立采购，也不能借成本分配接口读取客户、报价、利润或财务明细。
- 采购来源候选在缺少采购查看权限时去除历史采购来源和采购价格；供应商候选、订单商品分配和生成采购草稿分别检查供应商、订单、SKU、采购模块权限。
- 操作日志关联快照对无权员工脱敏；原始数据库审计记录不被测试用户修改。

### 4. UI 路由守卫与开发身份边界

已审查 `frontend/src/accessControl.js`、`frontend/src/router.js` 和既有 `frontend/tests/functional-rbac.spec.js`：前端根据服务端 `/session/current-operator/` 矩阵隐藏无权模块并将手工打开的无权路由导向访问受限页；权限不足不能只依赖前端隐藏，服务端 API 仍是最终边界。

本轮未修改前端文件，也未将模拟 UI 结果冒充真实员工浏览器验收。独立 Worktree 未安装 `frontend/node_modules`，尝试直接复用其他工作树依赖时因当前工作树配置无法解析依赖且 Vite 无法写入临时配置文件而停止；因此本报告不宣称真实员工 Chrome UI 已通过。现有 UI 受限路径仍需在获得正式隔离员工账号和可运行的 staging 前端后复核。

## 测试命令与结果

以下命令均在本 Worktree 的 `backend` 目录执行，数据库为隔离 SQLite，媒体目录为隔离临时目录；没有使用生产连接串。

```powershell
$env:APP_STAGE='development'
$env:DJANGO_DEBUG='false'
$env:DEVELOPMENT_SUPERADMIN='false'
$env:RBAC_ENFORCEMENT='true'
$env:DATABASE_URL='sqlite:///C:/Users/Johnson/.codex/visualizations/2026/10/23/01a16909-d780-7433-8b85-36b37254f61c/iss003-audit.sqlite3'
$env:MEDIA_ROOT='C:/Users/Johnson/.codex/visualizations/2026/10/23/01a16909-d780-7433-8b85-36b37254f61c/iss003-media'
python manage.py test crm.tests.test_functional_rbac crm.tests.test_sales_data_scope crm.tests.test_procurement_data_scope crm.tests.test_finance_data_scope crm.tests.test_reporting --noinput
```

结果：`131` 项通过，`0` 失败。测试覆盖模块权限、匿名拒绝、四种数据范围、列表/详情/搜索、跨范围写入、报价导出、报表 CSV、采购成本分配、财务流水、跨模块脱敏及正常共享采购路径。

```powershell
python manage.py check
```

结果：`System check identified no issues`。

```powershell
python manage.py makemigrations --check --dry-run
```

结果：`No changes detected`。

另用全新的隔离 SQLite 执行 `python manage.py migrate --noinput`，从初始迁移连续应用至 `crm.0089_operationlog_operator_protect`，全部迁移成功。

还验证了配置 fail-closed 边界：`APP_STAGE=production` 配合 `DJANGO_DEBUG=true` 被拒绝；`APP_STAGE=production` 配合 `DEVELOPMENT_SUPERADMIN=true` 也被拒绝。命令使用的是一次性测试环境变量，未写入仓库或日志。

曾尝试 `python manage.py test crm --parallel 4 --noinput`，Django 发现 984 项后在克隆 SQLite 测试数据库阶段报 `sqlite3.OperationalError: unable to open database file`，没有进入测试断言；这属于托管 Worktree 路径/SQLite 并行克隆环境限制，不作为代码 PASS 或 FAIL。定向单进程回归是本轮实际通过依据。

前端有效 Vitest/Chrome 真实员工 UI 本轮未运行，不将其写成通过；原因和后续条件见下节。

## 拒绝路径、通过路径与边界判断

| 类型 | 例子 | 实际判断 |
|---|---|---|
| 权限不足 | 无 `customers.view` 访问客户；无 `reports.export` 导出 CSV；无 `purchases.view` 读取采购单 | HTTP 403 或相应模块拒绝；不是数据范围问题 |
| 数据范围不足 | `self` 范围账号请求其他员工客户的详情、报价、订单、附件或财务流水 | 列表过滤为空，详情/动作按接口返回 404/拒绝；不泄露对象存在性或字段 |
| 正常共享业务 | 采购员处理采购单成本归属、独立采购、收货和共享库存 | 仅开放采购职责所需字段；销售客户、报价、利润和资金明细仍按模块/范围脱敏 |
| 需真实部署/员工验证 | 正式会话、真实组织树、生产 PostgreSQL、生产反向代理和真实业务数据 | 本轮不伪造 PASS，继续登记为待验证 |

## 未覆盖与后续条件

- `ISS-003` 仍为 `BLOCKED`：本轮证明的是隔离合成账号的服务端 API/范围边界，不是正式员工内测完成。
- 真实员工账号、正式组织树、真实跨部门数据和 Chrome 页面流程仍需用户明确进入内测并提供隔离 staging 账号后执行。
- 真实 PostgreSQL、部署层认证会话、Nginx/HTTPS、私有文件直链和生产基础设施权限不在本轮范围；不得用 SQLite/开发身份替代这些证据。
- 前端 `functional-rbac.spec.js` 已作为代码审查依据，但本轮未在该 Worktree 重跑；后续前端依赖可用后，应与服务端同一隔离账号执行桌面及窄屏 UI 回归。
- 本轮没有发现能够在当前代码和测试中明确证明、且可安全最小修复的权限缺陷，因此没有修改业务代码，也没有扩大任何角色权限。

## 交付边界

- 未修改 `DEVELOPMENT_SUPERADMIN`、`RBAC_ENFORCEMENT` 或任何正式权限策略。
- 未连接生产数据库、未使用真实员工账号；本轮未主动运行或查询 GitHub CI，最终提交使用 `[skip ci]`。
- 未合并 `master`，未关闭 ISS-003，交付后等待独立审查。
