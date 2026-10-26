# ISS-043 PostgreSQL 审计防篡改部署 Runbook

本文件是部署前的 DBA/安全操作清单，不在开发环境自动执行，也不连接或修改真实生产数据库。应用迁移 `0088_operationlog_append_only` 只在 PostgreSQL 安装 `crm_operationlog` 的 `BEFORE UPDATE OR DELETE` 触发器；SQLite 开发库明确不作为生产权限证明。

## 运行账号最小权限

在与生产同版本的 PostgreSQL 上，由独立 DBA 先核对表所有者、继承角色和连接账号，再把以下示例中的 `sunjack_runtime` 替换为实际 Django 运行账号。不得把运行账号设为表所有者、超级用户或可绕过权限的维护角色；不得把 `audit_maintenance` 授予应用连接池。

```sql
BEGIN;
REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
    ON TABLE public.crm_operationlog FROM PUBLIC;
REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
    ON TABLE public.crm_operationlog FROM sunjack_runtime;
GRANT SELECT, INSERT ON TABLE public.crm_operationlog TO sunjack_runtime;
GRANT USAGE, SELECT ON SEQUENCE public.crm_operationlog_id_seq TO sunjack_runtime;
COMMIT;
```

部署后用运行账号实际连接验证 `SELECT`/`INSERT` 成功，`UPDATE`/`DELETE`/`TRUNCATE` 失败，并检查 `pg_auth_members`，确保运行账号没有经继承角色重新获得写权限。以下查询只读，不替代实际拒绝测试：

```sql
SELECT grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public' AND table_name = 'crm_operationlog'
ORDER BY grantee, privilege_type;

SELECT member.rolname AS member_role, parent.rolname AS inherited_role
FROM pg_auth_members m
JOIN pg_roles member ON member.oid = m.member
JOIN pg_roles parent ON parent.oid = m.roleid
WHERE member.rolname = 'sunjack_runtime';
```

## 特殊维护

普通 ERP 用户、应用超级管理员和运行账号没有改删历史审计的流程。确需维护时，必须由独立授权的 DBA 使用不在应用连接池中的 `audit_maintenance` 身份，先完成 `pg_dump --table=public.crm_operationlog --format=custom` 备份并保存校验值，登记工单号，使用带工单号的 `application_name`，在受控短事务内暂时禁用触发器、完成最小更正、重新启用触发器，并追加一条带工单号、原因、对象和备份位置的维护审计记录。维护账号不得授予普通用户或应用账号；维护结束后撤销临时授权并复核触发器存在。

当前仓库没有实现绕过触发器的应用 API，也没有执行上述生产维护。真实生产角色、备份恢复演练和 `UPDATE`/`DELETE` 拒绝响应在部署前必须实测，状态为 `PENDING`。
