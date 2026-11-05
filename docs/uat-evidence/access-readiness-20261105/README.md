# ACCESS-READINESS-01：身份与权限准备

基线 `bcdcb57545f121b8a4102f352c74008b47372035`；工作树 `codex/access-readiness-20261105`。本包仅新增测试、清单与报告；生产权限、登录、配置和共享台账未修改。结论：**内测身份入口及全站逐入口数据范围仍未完成验收，不能启用正式 RBAC。**

## 身份与会话

`backend/config/urls.py` 只挂载 Django admin 与 `/api/`；`backend/crm/urls.py` 提供 `session/current-operator/`，未发现 ERP 业务登录/退出 API，前端也未发现对应登录页或退出入口。专属测试对 `/api/login/`、`/api/logout/`、`/api/session/login/`、`/api/session/logout/` 验证无路由；这不能证明不存在所有可能的外部身份系统。内测前需设计 ERP 登录、退出、会话恢复/过期提示、CSRF 初始化、停用后实时生效及直接 API 拒绝，并分别验收。

测试进程使用 `force_login` 生成**合成 Django 会话**：已登录读取客户 200、无 CSRF 写入 403、退出/过期/停用后 401；不是业务登录或目标环境会话通过。生产阶段启动时 settings 选择 `SessionAuthenticationWithChallenge`，仅在已初始化的开发 settings 上覆盖 `APP_STAGE` 不会重建该类。首次 [SQLite](logs/sqlite.log) 和 [PostgreSQL](logs/postgres.log) 各 3 个探针原始失败为匿名返回 403；修正测试显式使用生产认证类，[SQLite 五项复测](logs/session-sqlite-retry.log)通过。保留失败，不据此宣称发现生产绕过。

## 入口与数据范围核查矩阵

[可执行 URL 清单](inventory.py)生成的 [389 条 URL 模式](api-inventory.json)包含格式后缀重复，列出视图、router 方法/动作、声明的模块、路径默认模块及待复核原因。`nominal_empty_query_lookup` 对 router 方法以合成路径、匿名身份、空查询调用当前模块/动作映射，仅为静态候选，不是对该入口发出 HTTP 请求。它不是逐入口通过证明：`scope_status` 均明确 `NEEDS_RUNTIME_REVIEW`；函数视图、动态属性、嵌套 Context、查询参数导出、附件和动作的最终判定须追踪运行时分支。35 条模式没有静态路径映射是**待检查项**，并非 35 个已确认漏洞。重新生成：`python docs/uat-evidence/access-readiness-20261105/inventory.py`，设置隔离 `DATABASE_URL=sqlite:///:memory:`。

| 入口 | 现有判定与本轮证据 | 仍需核查 |
|---|---|---|
| 列表、详情、搜索 | `permissions.py` 的模块/动作及 `sales_scope.py`；本人、部门、部门树、全部范围和无权 404 的既有 API 测试见 SQLite 日志 | 逐模块和边界账号的每个路由、搜索字段与分页 |
| Context/关联 | `CONTEXT_MODULES` 与关联对象范围；客户、产品、SKU、供应商、采购范围测试 | 清单中全部 entity 类型、被删除/历史对象、间接关联 |
| 写入和动作 | `ModuleActionPermission` 与动作覆盖映射；采购和销售跨范围写入拒绝测试 | 逐动作的授权、事务失败回滚和权限变化后立即生效 |
| 导出/报表 | `action_for_request` 将受支持导出识别为 export；财务和报表已有拒绝/授权测试 | 各导出格式、异步任务和实际文件内容的跨范围泄漏 |
| 附件/凭证 | `file_access.py` 经认证并结合记录、模块及范围；客户附件/SKU/证书和财务普通角色测试 | 所有文件类型、直链/反代及目标存储 ACL |
| 财务与共享采购 | `finance_closeout_api.py` 的动态 `permission_module` 和 action map；普通财务角色的查看/创建/更新/导出，以及共享采购与销售范围测试 | 全局财务授权与历史数据、凭证及其他交叉模块的完整矩阵 |
| 最高角色和审计 | `effective_permission_matrix`；既有最高角色只读/API、合成已认证账号的操作者及审计事务测试；开发匿名身份不生成正式审计 | 真实员工账号、角色变更/停用、实际 UI/API 全矩阵及独立验收 |

## 实际执行

CPython 3.12.16，依赖使用现有锁定环境；每项使用合成账号、隔离数据库，测试中才覆盖受限设置。SQLite 首次 129 项：125 通过、3 个测试初始化失败、1 个 PostgreSQL 条件跳过；五项会话复测通过。真实 PostgreSQL 17 由 [run_postgres.py](run_postgres.py) 复制既有二进制并创建随机临时集群，首轮 129 项 126 通过、3 个相同初始化失败；结果和清理以日志为准。该首轮不能标为全通过。

修正后 [SQLite 全量定向复跑](logs/sqlite-final.log)129 项，128 通过、1 项 PostgreSQL 专属跳过；[PostgreSQL 会话专项](logs/session-postgres-retry.log) 5/5 通过，[PostgreSQL 完整定向复跑](logs/postgres-final.log)129/129 通过、零跳过，临时集群均已清理；保留首次错误的原始日志。`pip check`、Django check 和 `makemigrations --check --dry-run` 通过。

浏览器与 API 分开：使用隔离启动器和独立 SQLite/媒体/端口，Playwright 自带 Chromium（不是以当前输出标签冒称 Chrome）[6/6 场景](logs/browser.log)通过；授权、越权、不存在客户在 1440 和 390px 的 [截图与 HTTP 日志](browser/browser/iss055-customer-404/)保留。夹具用 Django admin 登录创建合成 session，审计关闭；这不构成 ERP 登录或真实身份审计验收。日志中的一次性隔离令牌已脱敏。

浏览器及首次 PostgreSQL 文本日志去除行尾空白；对应 `.log.gz` 保存调整空白前的字节，浏览器日志在压缩前已脱敏。

复现命令：`python backend/manage.py test crm.tests.test_access_readiness_20261105 crm.tests.test_functional_rbac crm.tests.test_sales_data_scope crm.tests.test_procurement_data_scope crm.tests.test_supplier_context_scope crm.tests.test_finance_data_scope crm.tests.test_finance_integration_permissions crm.tests.test_audit --verbosity 2`；设置临时 MEDIA_ROOT 和 `DATABASE_URL=sqlite:///:memory:`。PostgreSQL 用 `python docs/uat-evidence/access-readiness-20261105/run_postgres.py --postgres-bin <PG17-bin>`；脚本自建并清理临时集群，不能指向现有数据库。浏览器命令为 `node scripts/run-isolated-browser-tests.mjs --business-test iss055-customer-404-real.spec.js`，在 `frontend` 执行并设置隔离 Python 和证据目录。

## 实施优先级

1. **内测前必须实施**：ERP 真实登录/退出与 CSRF、停用及会话过期流程；按 389 条模式归并实际入口，补齐明确模块、动作、对象范围、附件和导出授权；对真实账号写入不可伪造操作人并验证权限撤销立即生效。建议范围为独立身份入口、`backend/crm/permissions.py`、各未覆盖视图及前端登录/错误状态；不在本审查中修改。
2. **可内测期处理、不得影响安全边界**：角色管理的非阻断易用性、已授权操作提示、权限变更可读性；ISS-095/096 已有接受范围及 ISS-097 的历史证据需独立核对，不重复实现。
3. **目标环境验证**：真实用户生命周期、HTTPS/cookie/CSRF、跨组与全局财务真实数据范围、代理直链及私有媒体 ACL、审计留存和权限回收。应用超级管理员不是数据库或 OS 管理员。

未关闭 ISS-003/051/055/095/096/097；未改变开发超级管理员，不创建真实员工，不运行 GitHub Actions，不将本次结果扩大为全站通过。

## 续查：35 个格式/根入口与最高角色

### 已复现：最高角色可经通用 API 改写（内测前修复）

隔离 SQLite 和 PostgreSQL 中，拥有 `admin` 角色的非 Django 超级用户对 `/api/access-roles/<superadmin-id>/` 发送 `PATCH {"code":"synthetic-mutated"}` 得到 **200**；Django 超级用户同样得到 200。数据库内最高角色代码随之变化，仅被授予该角色的合成用户 `has_all_permissions` 从 true 变为 false。`TestCase` 在隔离库中回滚，未接触真实角色或用户。参见 [SQLite 失败和观测](logs/format-role-final.log)、[PostgreSQL 失败和观测](logs/format-role-postgres.log)。

`backend/crm/views.py` 的 `AccessRoleViewSet.permission_matrix` 只保护专用矩阵动作；通用角色更新路径使用 `AccessRoleSerializer`，未见同等的最高角色代码保护。建议下一轮在服务端统一保护内置最高角色的代码、停用和删除等入口，并补普通权限管理员、Django 超级用户、直接 API、事务和审计回归；本包不改生产权限实现。

### 已复现：格式后缀的授权不一致和财务 500

[逐条 35 路径请求结果](suffix-route-results.json)列出匿名、无权限普通用户、具有全部模块权限的普通用户、Django 超级用户四种身份，仅执行 GET；记录是合成空数据的 HTTP 结果，不等于全部动作或对象范围验收。四类结果分别为：32 条 `403/403/403/200`（含两个 API 根入口）；1 条合同变更 `403/403/200/200`；2 条财务入口 `403/403/500/500`。匿名与无权限用户在本矩阵没有获得 200。

其中授权普通用户 `/api/customers/` 为 200、`/api/customers.json` 为 **403**；`module_for_request` 对首段带 `.json` 的路径未映射到 `customers`，高权限用户则先通过全权限判断。建议统一使用解析后的路由/视图模块而不是将格式后缀作为模块名，并保留无权限拒绝与原有数据范围测试。两个财务后缀返回 **500**：`FinanceCloseoutViewSet.list()` 和 `RmbCashEventViewSet.list()` 不接受 router 传入的 `format` 参数；建议在保留认证及既有契约的前提下处理后缀或明确取消支持，并单独验证。这些是可用性/兼容性缺陷，当前证据不证明未授权数据泄露。

### UI/API 与边界

隔离 Django/Vite 的真实 Chromium 页面复测 [桌面](role-browser-retry/browser/evidence_dir/highest-role-desktop.png)和[窄屏](role-browser-retry/browser/evidence_dir/highest-role-narrow.png)：API 返回 24 个模块，页面 144 个权限勾选全部选中且禁用；专用矩阵接口拒绝修改（400）。两项通过仅覆盖开发身份下页面和该专用动作，不能覆盖上面的通用 PATCH 缺陷或真实员工会话。首次逐一读取复选框触发 30 秒总超时（[日志](logs/role-browser.log)）；复跑采用一次 DOM 读取并逐项断言全部 144 个状态，不增加超时或删除断言，[复跑日志](logs/role-browser-retry.log)为 2/2 通过。日志中本次临时隔离令牌已脱敏。

本轮新专项在 SQLite 与 PostgreSQL 各运行 6 项：3 项观测通过、3 项保护性断言失败；失败是上述两个缺陷的回归信号，没有 skip 或改成通过。其余 354 条 URL 模式的各动态动作、所有关联/文件/导出路径以及真实账号和目标环境仍未逐项完成；之前 129 项通过与这次局部发现均不代表全站验收。公共台账交协调线程处理，等待独立审查后再安排修复。
