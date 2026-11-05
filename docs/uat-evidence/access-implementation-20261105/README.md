# ACCESS-IMPLEMENTATION-02

基线 `81cb56c18e6183b357af5b9845a4d56d6e6dd96b`，沿用 `codex/access-readiness-20261105`。原始调查及失败保存在 [ACCESS-READINESS-01](../access-readiness-20261105/README.md)，不改写为历史通过。本轮未启用日常环境 RBAC、未建立真实员工账号，不修改公共台账。

## 改动和边界

- ERP API 新增 `GET /api/session/csrf/`、`POST /api/session/login/` 和 `POST /api/session/logout/`，复用 Django 的密码认证、会话轮换、停用账号判断和 CSRF。失败采用统一文案，登录/退出响应禁止缓存；原 `current-operator` 继续提供当前会话。前端新增登录页、同源返回路径检查、401 后重新登录及退出操作，不把密码或会话标识写入 localStorage。开发超级管理员仍由既有服务端判断。
- `AccessRoleViewSet` 对更新、删除和专用矩阵动作在事务中锁定角色，并拒绝修改保留的最高角色；`RolePermissionViewSet` 对关联最高角色的写入也锁定并拒绝。普通角色矩阵先完整验证再写入，审计记录前后权限；审计失败使事务回滚。普通角色创建和更新的审计失败均受事务保护。
- 在 `module_for_request` 中仅对 Django 路由解析出的格式后缀进行规范化，保留未知模块拒绝、Context/审计和动态权限分支。财务 API 仅补充路由 `format` 参数处理，并确保后缀凭证上传仍使用流式限制。35 路径逐条前后分类见 [suffix-results.json](suffix-results.json)：29 条模块识别修复、2 条原 500 修复、1 条原正常受控、1 条审计实体参数受控、2 条 API 根入口受控。
- 无数据库迁移；新增后端认证路由和前端 `/login`。部署时须为同源反向代理、HTTPS、session/CSRF cookie、受信来源和静态文件配置做目标环境验证。新增登录入口当前没有单独的登录限速/锁定机制，内测前须由目标环境安全方案补齐并验证，不能直接宣布生产就绪。

## 当前实测

- [SQLite 权限定向](logs/sqlite.log)：56 项通过；后续 [安全和审计专项](logs/security-matrix-audit.log) 17 项、1 项 PostgreSQL 行锁条件跳过；[带后缀的流式超限测试](../../../backend/crm/tests/test_access_implementation.py)对两类凭证上传均返回 413。
- [PostgreSQL 17 权限专项](logs/postgres.log)：58 项通过；后续 [行锁和审计专项](logs/postgres-cleanup-retry.log) 13 项通过并清理。一次 [完整定向测试](logs/postgres-final.log)60 项断言通过但测试线程留下连接导致测试库销毁失败，整体退出 1；修复测试线程连接关闭后另行复验，不能把失败那次记为通过。
- 随后对新增角色创建审计回滚的 [PostgreSQL 安全专项](logs/postgres-audit-final.log) 14/14 通过，包含真实行锁并发，临时集群清理完成。
- [PostgreSQL 会话撤权专项](logs/postgres-revoke.log)15/15 通过，包含真实登录后权限撤销和用户停用；仅使用合成账号及临时集群。
- [最终 PostgreSQL 安全专项](logs/postgres-last.log)15/15 通过，包含最高角色权限行拒绝及行锁并发，任务集群清理完成。
- [PostgreSQL 数据范围回归](logs/postgres-scopes.log) 129/129 通过，覆盖既有客户、销售、采购、共享采购、财务、附件及审计测试，临时集群清理完成。
- [PostgreSQL 格式后缀范围专项](logs/postgres-suffix-scope.log) 2/2 通过，验证客户自有范围与越权 404、财务 CSV 导出权限和内容；对应 SQLite 财务专项也通过。
- [前端 Vitest](logs/vitest.log) 78 文件、725 项通过；[生产构建](logs/build.log)通过，保留大包警告。Node 全量 178 项通过、1 项并行工作树隔离测试超时；[单项复跑](logs/node-concurrency-retry.log)仍超时，两个运行均保留，不增加时限或声称全量通过；后端全量完成后[单项复跑](logs/node-concurrency-after-backend.log) 1/1 通过，约 60 秒，不能据此确定前两次超时原因。
- 会话过期处理修改后的 [Node 安全定向](logs/frontend-security-unit.log) 8/8 和 [前端 RBAC 定向](logs/frontend-rbac-final.log) 11/11 通过；[最新生产构建](logs/build-verified.log)通过，仍有大包警告。
- 两次 SQLite 全量初次尝试未配置本机 OpenSSL 路径，运维回执测试初始化失败；[失败日志一](logs/backend-full.log)、[失败日志二](logs/backend-final.log)保留。使用 `OPS_TEST_OPENSSL` 指向现有工具后，[全量重跑](logs/backend-complete.log) 1416 项、81 项按条件跳过，结果 OK，测试数据库已销毁。
- 隔离 Chrome 登录测试使用合成普通账号、独立 SQLite/媒体/端口，从 ERP 登录页实际输入密码；覆盖错误密码、成功登录、退出和 localStorage 检查。首轮 390px 因测试查找不存在的菜单名称超时（[日志](logs/browser.log)），改用页面实际菜单控件后 [两视口通过](logs/browser-retry.log)，保留失败。
- [会话丢失首轮](logs/browser-complete.log)发现隔离开发阶段启用受限权限时匿名 API 返回 403 而非 401，导致原先仅处理 401 的页面未跳转。已在 403 时重新读取会话，仅在确实未登录且不是开发身份时提示过期；有身份但缺权限的 403 仍保留。后续真实浏览器复测结果单独记录。
- [最终 Chrome 会话复测](logs/browser-verified.log)4/4 通过：桌面和 390px 真实登录、错误密码、退出、已认证无权限 403、越权 Context 和真实合成私有附件 404；清除本次浏览器 cookie 模拟会话丢失，验证过期提示；外部返回地址不离开原站。真实后端 session 过期另由 Django 测试覆盖，不将清 cookie 冒充目标环境超时验收。[桌面登录截图](browser-verified/browser/evidence_dir/login-desktop.png)、[390px 登录截图](browser-verified/browser/evidence_dir/login-narrow.png)已人工检查。

## 未覆盖和上线门槛

本包不代表全站 389 条模式及每个动态动作/对象范围均已验收。仍需逐模块完成真实账号及权限变更即时性、导出、私有附件、代理和浏览器过期状态；本地并行工作树测试先前的 120 秒超时原因尚未确认，后端回归结束后单项复跑通过。正式目标环境须验证登录限速/锁定、安全日志、TLS、cookie、CSRF trusted origins、员工生命周期、会话失效、密钥和反向代理；测试配置不能当作生产启用授权。

仅测试进程使用受限配置；不关闭 Issue，不部署、不合并 master。按用户要求提交 `[skip ci]`，不运行 GitHub Actions。

日志中的本次隔离运行临时令牌已脱敏；`*.raw.gz` 保留脱敏后的原始输出字节，文本版本仅移除行尾空白。所有浏览器资料和数据库均为合成数据。
