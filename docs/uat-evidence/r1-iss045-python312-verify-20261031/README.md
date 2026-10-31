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
