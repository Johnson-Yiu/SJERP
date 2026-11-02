# R1 PostgreSQL 认证契约测试修正

- 分支：`codex/r1-postgres-auth-contract-20261102`
- 基线：`9f0e59ea4e31778e0944bdac8cff858d0cfd9fa2`
- 测试代码提交：`3a79e1a68988aa2099159d9f393f22766280f68f`
- 范围：测试断言和测试专属认证配置；生产认证、权限逻辑、默认操作员名均未更改。

## 修改摘要

将七个匿名请求的预期状态码从 403 改为 401：`test_functional_rbac.py` 五处、`test_order_quantity_adjustments.py` 一处、`test_quotes.py` 一处。所有已认证但没有业务权限的 403 断言保持不变。

DRF 视图在模块导入时缓存认证类，运行中仅 `override_settings(REST_FRAMEWORK=...)` 不会切换已构造视图的认证器。为使 SQLite 测试与 staging 使用同一认证语义，相关测试方法临时将目标 DRF viewset 或函数包装视图指定为 `SessionAuthenticationWithChallenge`；patch 仅在测试方法期间生效。

`test_follow_up_subject_optional_and_current_operator_available` 显式设置 `DEFAULT_OPERATOR_NAME="Johnson"`，没有改变生产默认值。

## 验证

执行环境为 CPython 3.14.5、Django 6.0.6、DRF 3.17.2。业务回归使用 `DATABASE_URL=sqlite:///:memory:` 和每次新建并在结束时删除的临时 `MEDIA_ROOT`；没有连接仓库数据库或业务数据库。

相关后端测试命令：

```powershell
python manage.py test crm.tests.test_functional_rbac crm.tests.test_order_quantity_adjustments crm.tests.test_quotes crm.tests.BusinessFlowTests.test_follow_up_subject_optional_and_current_operator_available
```

结果：131 项通过、0 失败；Django system check 通过。

其他验证：

- `python manage.py check`：通过。
- `python manage.py makemigrations --check --dry-run`：通过，未检测到迁移变化。
- 使用 `APP_STAGE=staging`、PostgreSQL URL 及非空临时部署配置只导入设置、不连接数据库：数据库 engine 为 PostgreSQL，`REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES` 为 `crm.authentication.SessionAuthenticationWithChallenge`。
- `git diff --check`：通过。

## 验收边界与后续动作

本机无 PostgreSQL 客户端、Docker 或本地 PostgreSQL 服务（5432 未监听），因此实际 PostgreSQL 测试无法执行，状态为 `BLOCKED`。staging 配置加载检查和 SQLite 测试不等于 PostgreSQL 集成验证；后续应在专用 staging/PostgreSQL 环境重跑上述命令。

提交消息带 `[skip ci]`，未触发 GitHub Actions；未创建 PR、未合并 master、未部署、未修改业务数据库或关闭 Issue。ISS-051 保持 `BLOCKED`。
