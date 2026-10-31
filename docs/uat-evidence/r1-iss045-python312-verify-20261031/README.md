# R1-ISS-045 CPython 3.12 验收复核

日期：2026-10-31

来源分支：`codex/r1-iss045-qa-tools-bd324-20261031`

来源 HEAD：`4ddaa6b7bdd1a9f21443f687e4ff90f46aa02629`

复核分支：`codex/r1-iss045-python312-verify-20261031`

## 结论

使用真实 **CPython 3.12.16 x64** 完成旧脚本退役、隔离运行时、`seed_demo` 安全保护和完整后端回归。全量 Django 套件 **1028 项通过、19 项跳过、0 项失败**。允许路径只向本轮带隔离身份标记的临时 SQLite 写入；拒绝路径的临时目标没有被创建。未连接当前工作树默认数据库、共享业务数据库或生产数据库。

解释器为 Windows x64 uv-managed standalone CPython，位于独立临时目录；未使用系统 Python 3.14，未修改全局 PATH。依赖使用与 ISS-002 相同的独立 CPython 3.12 venv；A/B 两个来源工作树的 `requirements.txt` 和 `requirements.lock` 相同。B 工作树自身未修改依赖文件。

## 实际测试

测试期间 `APP_STAGE=development`，`DATABASE_URL`、SQLite 数据库和 `MEDIA_ROOT` 显式指向 `C:\Users\Johnson\AppData\Local\Temp\sunjack-cpython312-verify-20261031-a37d\iss045-*` 下的独立目录。Django 测试数据库由测试运行器创建并销毁。

| 命令 / 验证 | 结果 |
|---|---|
| `python manage.py check` | PASS，无系统检查问题 |
| `python manage.py makemigrations --check --dry-run` | PASS，`No changes detected` |
| `python -m unittest discover -s test_support -p "test_*.py" -v` | PASS，13/13 隔离运行时测试 |
| `python manage.py test crm.tests.test_environment_isolation crm.tests.test_legacy_qa_tools --verbosity 2` | PASS，12/12；包含两条旧业务流命令退役拒绝和 `seed_demo` 接受/拒绝边界 |
| `python manage.py test --verbosity 1` | PASS，1028 项运行、19 skipped、0 failures，`OK` |
| 隔离 SQLite 迁移后执行 `python manage.py seed_demo` | PASS；仅该隔离库新增合成数据：2 个产品、2 个订单、3 条交易流水 |
| `seed_demo` 指向未标记的独立临时 SQLite 探针 | PASS（安全拒绝）；返回 `CommandError` / exit 1，目标数据库文件没有创建 |

安全验证的关键路径：显式目标只有同时提供正确 run ID/token、`.sunjack-playwright-isolation.json` 标记、隔离根目录、数据库和 MEDIA_ROOT 且通过 `verify_isolated_runtime` 时才允许执行。未标记探针仍在系统临时目录中，仅为合成文件名，从未设置为共享业务库地址。

全量测试过程中的 HTTP 400/403、预期模拟异常及 19 个 skip 均由各自测试触发；Django 最终汇总为 `OK (skipped=19)`，没有失败或错误。全量运行还输出 P2A 数据库与迁移只读核验摘要，`legacy_unchanged=true`、`all_legacy_rows_equal=true`。

## 边界与遗留风险

- `seed_demo` 成功仅证明带标记临时 SQLite 的安全入口和合成演示数据路径，不代表其直接 ORM 写入可作为真实业务流程或正式业务事实。
- 本轮为 Windows CPython 3.12 + SQLite 验证，不包含 PostgreSQL、生产配置或员工正式权限验收；未启用正式 RBAC。
- 本任务仅新增本验收报告；未修改业务代码、共享 Issue 台账或任何现存采购单/数据库记录。未触发 GitHub Actions、未合并 master、未部署。

## 2026-10-31 原始日志补充复验

本次所有 Python 命令使用真实 **CPython 3.12.16 x64**；解释器、平台和可执行文件路径见 logs/01-python-runtime.log。与 ISS-002 共用同一个已安装的临时 CPython 3.12.16 venv，B 分支的 requirements.lock 安装核对显示所需发行包均已满足，pip check 通过。另行新建 venv 的尝试因离线缓存缺少 asgiref==3.13.0、在线下载未完成而未作为通过证据；原始失败/中断日志保留。

本轮隔离数据库及 MEDIA_ROOT 位于 C:\Users\Johnson\AppData\Local\Temp\sunjack-py312-evidence-20261031-iss045 下，并在写入前校验 Django 实际解析路径。Django check、迁移检查、隔离运行时测试（13/13）、旧脚本与 seed_demo 安全测试（12/12）及完整后端套件均通过。完整套件发现并运行 1028 项：**1009 通过、19 跳过、0 失败**；原始 verbosity 2 输出保留在日志中。

19 项跳过原因及数量：

- 10 项：需要 PostgreSQL 行锁语义（PostgreSQL row-lock tests require PostgreSQL）。
- 3 项：需要真实 PostgreSQL 锁（Real PostgreSQL locks required）。
- 1 项：审计触发器需 PostgreSQL；SQLite 无法验证生产数据库保护。
- 1 项：ISS-006 并发幂等验证需 PostgreSQL 锁语义。
- 1 项：POSIX 文件权限模式检查，仅适用于 POSIX。
- 1 项：当前环境不支持创建符号链接。
- 2 项：Windows 创建符号链接被系统拒绝（WinError 5）。

seed_demo 允许路径在带本轮隔离标记的临时 SQLite 上迁移并成功写入合成演示数据（2 个产品、2 张订单、3 条交易流水）；拒绝路径指向另一个临时目录中的不存在数据库，因缺少隔离身份被拒绝（exit 1），核对确认数据库文件未创建。没有连接或修改工作树默认库、共享业务库或现存采购单。

### 日志索引

- [Python 版本与解释器路径](logs/01-python-runtime.log)
- [requirements.lock 安装/版本满足情况](logs/02-requirements-lock-install.log)及[pip check](logs/04-pip-check.log)
- [全新 venv 离线缓存失败](logs/03-fresh-venv-offline-cache-failure.log)
- [全新 venv 在线下载未完成记录](logs/03-fresh-venv-pypi-fetch-interrupted.log)
- [Django check](logs/05-django-check.log)、[makemigrations 检查](logs/06-makemigrations-check.log)
- [隔离运行时测试](logs/07-isolation-runtime-tests.log)
- [旧流程退役与 seed_demo 单元安全测试](logs/08-legacy-seed-demo-safety-tests.log)
- [完整 Django 后端测试及逐项 skip 原因](logs/09-full-django-backend-suite.log)
- [seed_demo 允许路径的目标校验](logs/10-seed-demo-allow-target-verification.log)、[迁移](logs/11-seed-demo-allow-migrate.log)、[执行](logs/12-seed-demo-allow.log)和[合成记录核对](logs/13-seed-demo-allow-record-check.log)
- [seed_demo 拒绝路径的目标校验](logs/14-seed-demo-deny-target-verification.log)、[原始拒绝输出](logs/15-seed-demo-deny.log)及[无副作用核对](logs/16-seed-demo-deny-side-effect-check.log)
