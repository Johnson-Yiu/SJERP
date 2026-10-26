# ISS-051 验收记录

本目录记录代码级和隔离测试环境证据。未连接真实生产数据库、未生成生产密钥、未创建生产用户，也未将任何密钥写入日志或仓库。

实现提交：`d366224`（完整 SHA 由 Git 交付消息核对）。

## 当前结论

- 本地配置保护：通过。开发/生产配置快照、危险默认值拒绝、密钥不打印和 HTTPS/Cookie/HSTS 约束均有自动化覆盖。
- 开发环境兼容：通过。`python manage.py check` 和完整 Django 测试通过；开发超级管理员仍只由 `development_superadmin_enabled()` 控制。
- API 未登录/权限拒绝：通过。生产 SessionAuthentication 对受保护业务 API 返回 401 challenge；已登录但无模块权限返回 403；ISS-017 私有附件既有回归包含在完整后端测试中。
- Chrome Use 回归：通过开发环境只读检查。桌面默认视口和 `390×844` 窄屏客户管理页均可加载，路由、开发身份提示、客户列表和筛选区可见；本轮未提交表单或改写业务数据。
- 真实服务器、反向代理、生产 PostgreSQL、生产 Cookie/HTTPS 和密钥轮换：`DEPLOYMENT_VERIFICATION_PENDING`。

## 本轮命令结果

| 检查 | 结果 |
|---|---|
| `python manage.py check` | PASS |
| `python manage.py test` | PASS：916 tests，13 skipped，OK |
| 生产配置/拒绝不安全值定向测试 | PASS：15 tests |
| `python manage.py makemigrations --check --dry-run` | PASS：`No changes detected`；使用临时 SQLite，不新增迁移 |
| `npm run test:unit` | PASS：151/151 |
| 有效 Vitest（jsdom，排除仓库既有 typography 配置噪声入口） | PASS：656 tests / 67 files |
| `npm run build` | PASS：Vite 生产构建完成；保留既有大 chunk warning |
| Chrome Use | PASS：桌面及 `390×844` 窄屏只读回归；截图在本轮会话中采集 |

完整后端回归期间测试故意使用临时 `MEDIA_ROOT`，避免托管 Worktree 对默认媒体目录的 ACL 限制；该限制不属于应用失败。测试输出中的 Bad Request/Forbidden/Internal Server Error 是既有测试对拒绝路径、事务回滚和异常审计的预期请求日志，最终测试结果为 `OK`。

## 证据范围

- `backend/config/settings.py`：按环境解析配置并在生产启动时 fail fast。
- `backend/crm/authentication.py`：生产 SessionAuthentication 的 401 challenge。
- `backend/crm/tests/test_database_settings.py`：开发/生产数据库和安全默认值隔离测试。
- `backend/crm/tests/test_functional_rbac.py`、`backend/crm/tests/test_development_access.py`：现有 API 权限、开发身份和 ISS-017 私有附件保护回归。
- `frontend/src/router.js`、`frontend/src/accessControl.js`：现有权限状态路由守卫。

所有测试命令使用隔离数据库；报告只记录状态、数量、路径和哈希，不记录密钥、密码或数据库连接串。最终提交 SHA 在本目录所属提交及交付消息中记录。
