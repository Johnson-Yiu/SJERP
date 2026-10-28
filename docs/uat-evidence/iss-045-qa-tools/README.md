# R1-ISS-045-QA-TOOLS 验收报告

日期：2026-10-28
分支：`codex/audit-iss045-legacy-test-scripts`
固定基线：`bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`
远端状态：`origin/codex/audit-iss045-legacy-test-scripts` 在本轮开始核实时没有返回引用，目标分支此前未推送。

## 结论

本轮没有修改产品业务规则、serializer、状态机或数据库迁移。

- `run_business_flow_checks.py`：退役。保留源码和 `docs/添加数据测试.md` 中的历史 50/50 证据，不再允许执行，不再作为 QA/UAT 门禁。
- `run_edge_business_flow_checks.py`：退役。原因同上；它的异常意图仍可作为历史参考，但不代表当前 API/UI 覆盖。
- `seed_demo.py`：保留为本地开发演示初始化工具，不是测试工具。增加 fail-closed 运行环境检查，只允许开发环境 SQLite；显式 `DATABASE_URL` 必须带有当前隔离运行器的完整身份标记。

这次审计不把旧脚本的单次成功、历史 50/50 或 `seed_demo` 成功初始化当作系统完整验收。

## 使用与调用位置

| 脚本 | 当前调用证据 | 结论 |
|---|---|---|
| `backend/crm/management/commands/run_business_flow_checks.py` | 无 CI、启动器或现行测试调用；仅历史文档引用 | 退役，源码保留 |
| `backend/crm/management/commands/run_edge_business_flow_checks.py` | 无 CI、启动器或现行测试调用；仅历史文档引用 | 退役，源码保留 |
| `backend/crm/management/commands/seed_demo.py` | `README.md` 本地启动说明；`start-main-worktree.ps1` 仅在新 `backend/db.sqlite3` 时调用 | 保留为本地演示工具 |

CI 只调用 `check`、迁移完整性检查和 Django 测试，没有调用上述三个命令。历史文档 `docs/添加数据测试.md` 的原始结果不删除，已追加本轮退役说明。

## API、ORM、状态和成功判定审计

### `run_business_flow_checks.py`

- 大部分写入通过 DRF `APIClient` 逐个请求完成，但命令直接导入 ORM 模型读取内部状态，并直接调用 `record_supplier_payment` 检查超额付款；因此它不是 UI/serializer/完整业务入口测试。
- 会持久化创建一整批 `E2E-*` 数据，命令本身没有事务回滚或隔离数据库保护。
- 当前固定基线复测（只放宽 `testserver` 到隔离环境的 `ALLOWED_HOSTS`）在第 7 项因跟进 serializer 要求非空内容而失败；修正该项后，第 24 项仍因当前订单工作流要求先保存草稿、再确认而失败，随后读取失败响应的 `id` 触发 `KeyError`。因此最后的“恰好 50 项”和汇总 `Result` 断言没有可靠执行机会。
- 虽然多数成功判定包含状态码和少量字段，但部分只判断 HTTP 201/200；错误路径依赖英文/中文错误文本，且把失败响应直接当作带 `.data` 的 DRF response，不能稳定区分业务拒绝与服务器/Host 错误。
- 没有覆盖当前收货/发货冲销、root/child 拆分预收款作废、正式快照、导出链等后续契约。

### `run_edge_business_flow_checks.py`

- 写入主要通过 `APIClient`，ORM 仅用于读取订单计划、库存预留等内部状态；没有直接 ORM 写入，但仍会持久化整批 `EDGE-*` 数据。
- 隔离复测在第 6 项因跟进请求缺少当前 serializer 要求的非空内容而失败；继续运行时依赖前一步响应的 `id`，因此第 7 项和第 18 项出现级联失败/`KeyError`。
- 它仍假定可直接 PATCH 状态、直接创建某些库存/财务记录，并未覆盖当前回滚原子性和正式 UI 入口；50 项汇总同样可能在前置错误后不可达。

### `seed_demo.py`

- 直接 ORM `get_or_create`/`update_or_create` 写入产品、客户、联系人、跟进、报价、订单、订单明细、库存流水和财务流水，绕过 serializer、业务服务、付款计划、供应商/客户快照和收发货/冲销状态机。
- 使用的字段在当前模型中大多仍存在，且 `lead`、`customer`、`company`、`sent`、`production`、`completed`、`purchase_in`、`sale_out` 等字符串仍在当前 choices 中；这只能证明字段未删除，不能证明直接写入符合当前业务流程。
- 关键语义风险仍存在：直接写入 `purchase_in`/`sale_out` 没有正式 receipt/shipment 来源信息；订单直接进入 `production`/`completed`，没有通过确认流程生成完整计划与快照；交易不指定 `kind`、计划或付款关联而落入默认 `other`；这些记录不可作为真实业务事实。
- `payment_terms_config`、`payment_terms_snapshot` 由迁移 `0072` 引入并仍是当前字段；脚本没有正确构造供应商执行付款规则或采购付款快照。`FollowUp.next_action` 仍是当前字段，`next_follow_up_mode` 则由迁移 `0073` 增加，脚本没有设置该新语义。

## 实际数据库风险

在修改前，开发配置允许 `DATABASE_URL` 覆盖默认 SQLite，三个命令都没有自己的数据库目标检查；因此旧命令或 `seed_demo` 可能连接开发配置指向的共享/真实数据库。`seed_demo` 还会更新固定 demo 编号，存在覆盖已有演示记录的风险。

本轮采取的最小保护是：

1. 两个持久化旧业务流命令在进入 ORM/API 操作前直接抛出 `CommandError`，阻止误用；历史源码保留。
2. `seed_demo` 拒绝非 development、非 SQLite 及未带隔离身份的显式 `DATABASE_URL`。
3. 带显式 SQLite 的运行必须通过 `backend/test_support/isolated_runtime.py` 的 marker、临时目录、数据库路径、媒体路径和单数据库校验。

这不会把默认本地开发 SQLite 宣称为生产安全边界；本地开发人员仍应把它视为演示数据而非业务库。

## 隔离验证

验证使用当前隔离运行器的相同 fail-closed 校验：临时目录下新建 marker、`db.sqlite3` 和 `media/`，迁移完成后调用 `verify_isolated_runtime(settings=settings, database_must_exist=True)`，未连接主工作树的 `backend/db.sqlite3`、PostgreSQL 或任何共享业务库。

| 命令 | 结果 |
|---|---|
| `python manage.py check` | PASS |
| `python manage.py makemigrations --check --dry-run` | PASS，`No changes detected` |
| `python -m unittest discover -s test_support -p "test_*.py" -v` | PASS，10/10 隔离运行时测试 |
| `python manage.py test crm.tests.test_environment_isolation crm.tests.test_legacy_qa_tools` | PASS，7 项定向测试 |
| `python manage.py test --verbosity 1` | PASS，1005 项，18 skipped，OK |
| 隔离迁移 + `verify_isolated_runtime` + `manage.py seed_demo` | PASS；seed 仅写入本轮临时 SQLite |
| 退役命令调用 | PASS（按预期拒绝执行）；未产生业务写入 |

旧命令的“放宽 `testserver` 后”复测仅用于审计其当前漂移，数据库为一次性临时 SQLite；两条命令均以非零退出并在前置断言失败后中止，不作为通过结果。

## 待后续事项

- 如未来需要新的后端业务流回归，应另立任务，使用当前 API/serializer 和隔离运行器重写为可回滚、可重复的测试，不恢复这两条持久化旧命令。
- 当前报告没有复测真实 PostgreSQL、生产部署配置或正式员工权限；这些仍属于部署/权限验收范围。
- `seed_demo` 仍不应创建付款计划、快照或冲销事实；如演示页面需要这些状态，应使用专门的隔离 fixture，并明确标注为合成数据，不把演示脚本改造成业务造数入口。

本轮未修改 `docs/PROJECT_ISSUES.md` 或 `docs/PROJECT_PHASES.md`，未触发 GitHub Actions，未合并 master，未部署。
