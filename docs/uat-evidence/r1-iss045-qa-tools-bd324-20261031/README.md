# R1-ISS-045-QA-TOOLS 验收记录

日期：2026-10-31
分支：`codex/r1-iss045-qa-tools-bd324-20261031`
固定基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`
复用的历史审计成果：`966deaa209cd5b115704a67e58aeb12783b9a60a`
最终提交 SHA：以该分支交付时的 Git `HEAD` 为准（见任务最终回报）。

## 结论

- **PASS**：两条旧业务流程管理命令仍 fail-closed，历史源码及 2026-09-22 的历史 50/50 证据均保留；没有把历史结果当作当前验收。
- **PASS**：`seed_demo` 的未标记数据库目标现被限制为当前 checkout 的默认开发 SQLite 文件；显式数据库 URL 必须通过当前隔离运行器校验。拒绝额外连接、非 SQLite、非默认路径及未迁移创建的默认数据库。
- **PASS**：相关安全测试、隔离运行时测试、Django 全量后端测试、迁移检查和真实隔离 seed 流程均完成。
- **NEEDS VERIFICATION**：本轮运行环境只有 Python 3.14.5，未用 CI 声明的 Python 3.12 执行；SQLite 不能验证 PostgreSQL 行锁和生产数据库保护分支。不得将本地 SQLite 结果外推为 PostgreSQL 或正式环境通过。
- **FIX REQUIRED / BLOCKED**：本轮没有发现需要进一步修改的本地问题，也没有阻塞项。

## 脚本使用与调用关系

| 脚本 | 当前代码/调用关系 | 处置及验收边界 |
|---|---|---|
| `backend/crm/management/commands/run_business_flow_checks.py` | Django 管理命令；`handle()` 在旧流程执行前直接抛出退役错误。当前只由退役安全测试调用，并被历史文档引用。未见 README 启动器或 `.github/workflows/ci.yml` 调用。 | 退役状态维持；保留整个历史源码及历史证据，不执行其旧流程，不作为 QA/UAT gate。 |
| `backend/crm/management/commands/run_edge_business_flow_checks.py` | Django 管理命令；`handle()` 在旧流程执行前直接抛出退役错误。当前只由退役安全测试调用，并被历史文档引用。未见 README 启动器或 `.github/workflows/ci.yml` 调用。 | 退役状态维持；保留源码，不执行其旧流程，不作为 QA/UAT gate。 |
| `backend/crm/management/commands/seed_demo.py` | `README.md` 有迁移后的手动开发指引；`start-main-worktree.ps1` 在启动时记录数据库是否原先不存在，迁移后仅对首次创建的 `backend/db.sqlite3` 调用一次。未见 `.github/workflows/ci.yml` 调用。 | 保留为本地演示数据工具，不是测试夹具、业务闭环或正式业务造数入口。直接 ORM 写入仍有状态语义风险，所以只允许受限开发/隔离数据库。 |

`docs/添加数据测试.md` 保留原始 50/50 历史批次；同文件的后续说明明确记录旧脚本已退役、当前契约漂移及其不代表验收。`docs/uat-evidence/iss-045-qa-tools/README.md` 作为早期审计记录保留。本报告是固定基线上的安全复核，不改写早期报告所对应的历史结果。

CI 工作流审查结果：`.github/workflows/ci.yml` 没有调用上述三个命令；当前仍只运行 Django 检查、迁移检查和测试等工作流步骤。本轮没有修改 CI 配置，也没有触发 GitHub Actions。

## 修改记录

1. `backend/crm/management/commands/seed_demo.py`
   - 保持 `APP_STAGE=development` 和 SQLite 限制。
   - 拒绝任何额外数据库 alias，确保该命令无法通过其他连接访问共享库。
   - 未设置非空 `DATABASE_URL` 时，要求数据库解析到当前 checkout 的 `backend/db.sqlite3`，拒绝符号链接，并要求数据库文件已由迁移创建。
   - 设置非空 `DATABASE_URL` 时，仍要求完整隔离标记，并由 `verify_isolated_runtime(..., database_must_exist=True)` 验证临时根目录、marker、数据库路径、媒体路径和单数据库配置。
   - 未改写 `seed_demo` 的业务数据生成方式；它仍是合成演示数据，不能生成/证明合规的正式订单、库存或财务事实。
2. `backend/crm/tests/test_legacy_qa_tools.py`
   - 新增验证：允许已存在的 checkout 默认 SQLite；拒绝非默认/共享 SQLite、额外数据库 alias 和迁移前的缺失数据库；允许具有匹配 marker 的隔离 SQLite。
   - 保留两条旧命令的退役断言及既有部署环境、非 SQLite、未标记 URL 拒绝断言。
3. `README.md`
   - 明确 `seed_demo` 的允许数据库路径、显式 URL 隔离要求及新增拒绝条件。
4. 新增本验收报告；未删除、覆盖或改写历史验收记录。

## 本地验证

运行环境：CPython 3.14.5；使用 `backend/requirements.lock` 在系统临时目录建立一次性虚拟环境。Django 依赖检查无损坏。测试数据库、媒体目录和 `seed_demo` 实际写入库均位于 `C:\Users\Johnson\AppData\Local\Temp\sunjack-iss045-*`，未连接工作树默认数据库、共享业务数据库或生产数据库。

| 检查 | 实际结果 |
|---|---|
| `python manage.py check` | PASS；无系统检查问题 |
| `python manage.py makemigrations --check --dry-run` | PASS；`No changes detected` |
| `python -m pip check` | PASS；`No broken requirements found` |
| `python manage.py test crm.tests.test_legacy_qa_tools --verbosity 2` | PASS；10 通过、0 失败、0 跳过 |
| `python -m unittest discover -s test_support -p "test_*.py" -v` | PASS；13 通过、0 失败、0 跳过 |
| `python manage.py test --verbosity 1` | PASS；共 1028 项，1009 通过、19 跳过、0 失败，Django 输出 `OK` |
| 隔离数据库 `migrate --noinput` + `seed_demo` + 数据核验 | PASS；当前叶迁移全部成功；demo 命令成功，仅在本轮临时 SQLite 中核实到 2 个产品、2 个订单和 3 条交易流水 |
| `git diff --check` | PASS；无空白错误 |

全量测试中的 19 项跳过由当前 SQLite/Windows 环境决定，包含要求真实 PostgreSQL 行锁或 PostgreSQL 数据库保护验证的测试，以及依赖平台 ACL、文件模式或 symlink 能力的测试。测试过程打印的若干 400/403/409/500 日志来自断言负向响应或显式注入异常的测试；最终全量测试汇总为 `OK`，没有测试失败。新安全测试中 Django 会对临时覆盖 `DATABASES` 打印 `UserWarning`；这不影响测试结果。

## 剩余限制

- 项目 CI 使用 Python 3.12；本机仅发现 Python 3.14.5，本轮使用锁定依赖完成本地回归，但仍需在隔离 CI 环境确认 Python 3.12 兼容性。
- PostgreSQL 专用并发/行锁测试及 PostgreSQL 部署配置未在本轮运行。它们应在独立、一次性 PostgreSQL 测试服务中验证；本报告不声称其通过。
- 本轮没有运行旧业务流命令，也没有运行可能触及当前 checkout 开发库的启动器。退役状态由 fail-closed 定向测试验证；demo 的实际命令只在标记隔离 SQLite 中运行。
- 不应将 `seed_demo` 的成功运行解释为真实业务闭环或正式业务事实验收。
