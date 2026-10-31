# R1-ISS052 PostgreSQL UAT

## 结论：BLOCKED

本轮没有可确认的一次性隔离 PostgreSQL 实例，因此没有执行迁移、数据库测试或任何数据库写入。SQLite 结果不作为 PostgreSQL 验收替代。当前不能判定 ISS-052 的 PostgreSQL 验收通过，也没有足够证据确认或修复产品缺陷。

## 固定来源

- 基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`
- 参考分支：`codex/r1-iss052-audit-hardening-20261031`
- 本次核验时 GitHub 参考分支 HEAD：`70fe8ee1d4ffbd7786f1908804ea7142461d5286`
- 指定实现提交：`ab9ce886094a065766a24b35d9b82c7a7c0fd067`，该提交是上述参考分支 HEAD 的祖先，且固定基线是实现提交的祖先。
- 本次独立分支从指定实现提交创建：`codex/r1-iss052-postgresql-uat-20261101`

## 隔离环境检查

本机检查未发现 `psql`、`pg_isready`、`postgres`、`initdb` 或 `docker` 命令；未发现 PostgreSQL Windows 服务；本机 TCP 5432 无监听进程。没有提供可验证为一次性隔离数据库的连接目标。为避免误连业务数据库，本轮未尝试连接任何数据库，也没有启动或创建数据库服务。

## 验收矩阵

| 项目 | 本轮结果 | 说明 |
|---|---|---|
| 0091、0092、0093、0094 全部迁移 | BLOCKED | 未执行；需要隔离 PostgreSQL |
| 三张审计表的 UPDATE 拒绝 | BLOCKED | 未执行 |
| 三张审计表的 DELETE 拒绝 | BLOCKED | 未执行 |
| 三张审计表的 TRUNCATE 拒绝 | BLOCKED | 未执行 |
| 存在历史记录时危险回退被拒绝 | BLOCKED | 未执行 |
| 空审计表正常回退并重新迁移 | BLOCKED | 未执行 |
| CSV 预览、失败、重试、成功的审计关联 | BLOCKED | 未在 PostgreSQL 上执行相关用例 |
| 真实认证操作人保存 | BLOCKED | 未在 PostgreSQL 上执行相关用例 |
| 业务数据与成功审计的事务一致性 | BLOCKED | 未在 PostgreSQL 上执行相关用例 |

本轮实际执行的 PostgreSQL 测试数：0；通过数、失败数和跳过数均不适用（测试未运行），不得据此宣称通过。

## 已有测试覆盖（仅静态核对，未运行）

- `backend/crm/tests/test_csv_import_audit_postgres.py` 包含针对三张审计表的 UPDATE、DELETE、TRUNCATE 原生 SQL 拒绝用例；类要求 PostgreSQL。
- `backend/crm/tests/test_csv_import_audit_migration_rollback.py` 包含有历史记录时拒绝回退、空表时回退并重新迁移两项用例。
- `backend/crm/tests/test_safe_csv_import.py` 包含预览/失败/重试链路、操作人、审计写入失败回滚、成功审计关联及业务事务相关用例。
- 0091–0094 迁移文件已在指定实现提交中核对；静态阅读不能证明 PostgreSQL 实际执行、触发器行为或回退事务结果。

上述覆盖说明不属于本轮测试结果。既有 SQLite、其他分支或历史报告结果均未计入本次验收。

## 解除阻塞所需条件

提供或在受控本机环境创建一次性 PostgreSQL 实例及专用数据库/账号；确认目标数据库身份、版本和隔离属性，并确认不指向共享或生产业务系统。随后从本分支在该数据库运行指定迁移、`test_csv_import_audit_postgres`、`test_csv_import_audit_migration_rollback` 及 `test_safe_csv_import` 中与审计链路、身份和原子性相关的完整用例，保留原始日志并记录逐项通过/失败/跳过数量。测试结束后销毁该一次性数据库。

## 范围与限制

- 本次仅新增验收记录，没有修改业务代码、迁移、认证或数据库配置。
- 未连接真实业务数据库；未用 SQLite 代替 PostgreSQL 验收。
- 未触发 CI、未合并 master、未部署、未创建 PR。
- PostgreSQL 迁移兼容性、触发器拒绝行为、历史数据回退保护及运行时审计原子性仍需验证。
