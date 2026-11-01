# R1-POSTGRES-TEST-ISOLATION-01

- 日期：2026-11-02。
- 固定基线：`2e25b743884123d7ae5599c89586988a12791bf4`，来源 `codex/r1-iss006-postgres-concurrency-gaps-20261101`。
- 新分支：`codex/r1-postgres-test-isolation-20261102`。
- 独立工作树：`C:\Users\Johnson\.codex\worktrees\r1-postgres-test-isolation-20261102\森爵照明管理系统`。
- **验收结论：BLOCKED。已实现测试专用候选方案及回归测试，但本机没有 PostgreSQL，不能认定真实清理冲突已彻底解决。**

## 根因及方案选择

在专用虚拟环境从 `backend/requirements.lock` 安装并逐项核对全部 16 个版本，实际 Django 为 **6.0.9**。读取该安装的真实源代码，确认 `TransactionTestCase._fixture_teardown()` 调用 flush；PostgreSQL `sql_flush()` 生成一个 TRUNCATE，`execute_sql_flush()` 在 atomic 内执行。迁移 0094 的三张 CSV 审计表 BEFORE TRUNCATE 触发器因此会阻止原生清理。完整源码输出见 [Django flush](logs/django609-flush-source.json) 和 [建库/销毁实现](logs/django609-creation-source.json)。

比较了永久修改触发器、测试角色/会话绕过、保留审计表不清理、逐例重新建库，以及仅清理阶段的事务化方案。选择最后一种，保留现有 TransactionTestCase 的测试语义及 Django 原生 flush SQL；清理权限不暴露给应用 API、普通 manage.py flush 或测试正文。生产审计保护和迁移不变。

## 边界及实现

| 控制 | 实现与拒绝策略 |
|---|---|
| 明确识别临时库 | runner 在建库前生成 `test_sunjack_<随机32位hex>`，记录 CREATE 确认成功的目标；只在 Django 完成建库后登记清理身份。来源库名与目标必须不同 |
| 防止连接覆盖 | PostgreSQL 仅支持显式数字回环 HOST、显式 USER、简单来源库名、空 OPTIONS、无 libpq PG* 环境变量；拒绝 dbname/hostaddr/service 等覆盖；维护连接固定使用 Django 基类的 postgres 维护库通道，禁止回退到来源库 |
| 防止误删 | CREATE 只尝试一次，不使用 autoclobber 的 DROP 已存在库重试；销毁只使用本次成功 CREATE 时记录的库名及连接配置副本，通过单独维护连接操作，不使用测试结束后的 NAME/HOST/OPTIONS |
| 运行范围 | 仅当前 runner 管理的 TransactionTestCase fixture teardown 临时接管当前连接的 execute_sql_flush；正文、独立工作线程和普通 flush 没有此 hook。测试环境结束后撤销 patch |
| 事务清理 | 验证连接对象、配置快照、数据库实际名称及 public schema；取三表 ACCESS EXCLUSIVE 锁，确认原三触发器存在、函数/类型正确且启用；只停用这三条指定 TRUNCATE 触发器；执行原生 SQL；重新启用并再次核对，再提交 |
| 失败恢复 | SQL/检查/恢复阶段异常由外层 atomic 回滚数据和 DDL；不在已中止事务的 finally 内尝试恢复 SQL。锁超时 5 秒、statement timeout 20 秒。hook 生命周期通过 ExitStack 复原 |
| 建库/销毁失败 | 只尝试销毁已确认创建的随机库；分别尝试已登记目标，保留失败库名和人工隔离清理提示；恢复 connection.settings_dict 与 settings.DATABASES 的 NAME/TEST.NAME，并关闭连接 |
| 不支持的组合 | PostgreSQL 多别名、共享别名、显式镜像、并行、keepdb、自定义 TEST.NAME、远端/空/DNS HOST、非 public schema 均明确拒绝；没有静默改变共享库或路由语义 |

安全设计依据：PostgreSQL 的 [TRUNCATE 文档](https://www.postgresql.org/docs/17/sql-truncate.html) 说明截断数据可随事务回滚，[显式锁文档](https://www.postgresql.org/docs/17/explicit-locking.html) 说明 ACCESS EXCLUSIVE 与所有表锁冲突且锁持有至事务结束；[ALTER TABLE 文档](https://www.postgresql.org/docs/17/sql-altertable.html) 支持按触发器名启停。由此设计为“锁覆盖整个停用/恢复区间、停用状态不提交”。**这一设计论证不替代真实 PostgreSQL 运行证明。**

没有使用 session_replication_role、DISABLE TRIGGER ALL 或删除触发器。UPDATE/DELETE 审计触发器和约束不参与启停。正常 SQL TRUNCATE 拒绝和其他连接在清理期间被锁阻止，均有 PostgreSQL 专项用例，尚待实测。

## 修改文件

- `backend/crm/postgres_test_cleanup.py`：测试库绑定、身份/触发器核验、事务清理及 teardown 限定 hook。
- `backend/crm/test_runner.py`：随机临时库生命周期、连接预检、严格维护连接、创建/销毁归属记录、失败恢复；既有开发测试权限约定保持。
- `backend/crm/tests/test_postgres_test_isolation.py`：21 项控制流程测试和 6 项真实 PostgreSQL 测试。
- `docs/PROJECT_ISSUES.md`、`docs/PROJECT_PHASES.md`：本轮记录，既有 Issue 状态与历史不删除、不关闭。
- 本报告及 `logs/`：完整命令、输出、失败探针和各轮验证记录。

未改模型、业务服务、API、配置、依赖锁、任何迁移或工作流；尤其 `0094_csv_import_audit_truncate_guard.py` 与基线完全相同。

## 实际验证结果

| 验证 | 实际结果 / 证据边界 | 日志 |
|---|---|---|
| 锁定依赖 | 16 项精确版本一致、pip check 通过；Python 3.14.5 / Django 6.0.9 | [安装](logs/locked-install.json)、[逐项核对](logs/discovery-and-lock.json) |
| 最终相关回归 | **137 项发现，113 通过，24 项 PostgreSQL 跳过，0 失败**；独立内存 SQLite、临时媒体目录 | [最终完整日志](logs/regression-final.json) |
| 流程隔离验证 | 最终回归包含 21 项 Mock 控制流程测试；覆盖身份拒绝、hook 范围、连接覆盖、来源库回退禁用、碰撞不删库、部分建库失败、双配置恢复、销毁漂移和失败继续回收；不是 PostgreSQL 模拟验收 | 同上 |
| 静态检查 | 语法编译、Django check、迁移一致性及 diff 检查通过；生产代码/迁移/工作流无差异 | [最终静态检查](logs/static-final.json)、[暂存差异核对](logs/final-git-review.json) |
| 模块静态导入与发现 | 52 项发现，0 执行；禁止数据库连接下完成 | [导入发现](logs/discovery-and-lock.json) |
| 真实 PostgreSQL | **BLOCKED：0 项实际执行**；工具/服务/Docker 缺失，127.0.0.1:5432 不可连接 | [环境探测](logs/postgres-environment.json) |

最终回归模块：隔离机制、原 PostgreSQL 并发、ISS-006 幂等、CSV PostgreSQL 追加保护、CSV 审计迁移回退、安全 CSV 导入、履约、履约审计原子性、库存冲销审计原子性。137 中的 24 个跳过项包含本轮 6 个真实 PostgreSQL 用例；SQLite 结果不能证明任何锁或 DDL 回滚行为。

六个 PostgreSQL 专项分别覆盖：三触发器存在及直接 TRUNCATE 拒绝、完整 TransactionTestCase 生命周期清理后再次拒绝、正文直接调用后端 flush 仍拒绝、截断后故障回滚数据与触发器、SQL 错误恢复后重试、独立连接在停用窗口被锁阻止（不同 PID、期望 SQLSTATE 55P03）。全部保持 BLOCKED。

## 静态复核与日志说明

辅助只读复核发现并在本轮修正了连接 OPTIONS/libpq 覆盖、建库失败遗漏回收、配置双表示恢复，以及最终销毁依赖活动 NAME 的风险。多别名/镜像采用明确拒绝，而非未经实测实现共享分组。均补充控制流程断言；辅助静态复核不等于用户/ChatGPT 正式独立验收。

日志按实际阶段保留：初始 17 项隔离回归、26 项中间回归、127/133 项综合回归，以及最后的 137 项回归。前几轮之后因静态复核补充安全边界而重跑，以 `regression-final.json` 为最终代码依据。一次建库源码探针错误地把 ConnectionProxy 当作实际 wrapper，产生 AttributeError，见 [首次探针](logs/creation-source-first-attempt.json)；已更正为 connections['default'] 并成功读取，不作为产品缺陷。故障注入测试的预期 DatabaseError traceback 随完整测试输出保留。

所有 JSON 的 output 保留实际合并输出，转义换行/空白解码后即原始日志。未运行 GitHub Actions、全量后端、前端或浏览器；本轮无可见 UI 改动。

## 剩余风险和下一步

1. **没有彻底验收解决真实 PostgreSQL 清理冲突。** 六个本轮 SQL/锁测试、原并发测试、CSV 原始 UPDATE/DELETE/TRUNCATE、迁移往返及其他 TransactionTestCase 的 PostgreSQL 执行均待补验。
2. 在获准的专用本地 PostgreSQL 17 实例中，使用可创建/销毁临时库的测试账号、数字回环 HOST、空 OPTIONS、无 PG* 环境变量和 public schema；需要 postgres 维护库可连接。不得将真实业务服务器/数据库作为该环境。
3. 使用锁定依赖执行日志中的同一组测试，DATABASE_URL 改为上述专用测试实例配置；runner 自动生成随机库名。确认 PostgreSQL vendor，全部用例实际执行、无 teardown 错误，记录触发器状态及故障恢复证据后，再运行完整 PostgreSQL 后端回归。
4. 确认本轮随机测试库均被销毁；如回收失败按错误附注中的精确随机名人工核对，不能扩大为来源库/历史库清理。网络故障或无法 DROP 时保留 BLOCKED，不宣称回收成功。
5. 此方案针对已检查的 Django 6.0.9 私有测试接口；框架升级、远端/多库/镜像/并行/keepdb 和自定义 schema 需另行设计与实测，目前明确拒绝。

ISS-006 仍为 NEEDS_VERIFICATION，ISS-052 既有状态不变；PostgreSQL 验收继续 BLOCKED。提交使用 `[skip ci]`，推送独立分支，等待独立审查。不创建 PR、不合并 master、不部署、不连接实际业务数据库。
