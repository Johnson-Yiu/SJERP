# 最终候选 PostgreSQL 隔离恢复演练

日期：2026-11-09 至 2026-11-10（北京时间）。候选源码：`4c01d3be84663d9709b437a4b8fe825f993473d7`，在独立 detached 工作树运行。使用 PostgreSQL 17.11、Django 6.0.9 和 psycopg 3.3.6。脚本创建随机临时集群、凭据、数据库和媒体目标；不连接正式库。

执行命令（`<python>` 为本机包含以上依赖的隔离解释器，`<pg-bin>` 为本机 PostgreSQL 17.11 可执行目录）：

```text
<python> backend/operations_pg_acceptance.py --postgres-bin <pg-bin>
```

退出码 0，实际标准输出：

```json
{"status":"PASS","source_sha":"4c01d3be84663d9709b437a4b8fe825f993473d7","scope":"real-PG17-with-simulated-media-fence","active_session_rejected":true,"other_login_rejected":true,"restored_verified":true,"nonempty_media_restored":true,"bank_voucher_file_restored_and_sha_verified":true,"empty_media_root_restored":true,"missing_media_member_rejected":true,"corrupt_media_member_rejected":true,"manifest_digest_mismatch_rejected":true,"source_media_unchanged":true,"audit_truncate_rejected":true,"source_unchanged":true,"audit_row_mutations_rejected":8,"real_lock_competition_rejected":true,"bad_digest_rejected":true,"failed_restore_rejected_and_owned_database_removed":true,"encrypted_retention_removed":null,"replicas_are_local_only":true,"tables":120,"rows":1146,"seconds":104.737,"cleanup":"complete"}
```

数据库和媒体均进行了实际备份及恢复；媒体写入栅栏为模拟，不能作为目标系统 ACL 验证。此次未传 GPG/OpenSSL 参数，加密、签名和保留策略未在本次演练执行；`encrypted_retention_removed` 为 null，不能记为通过。独立副本、正式服务配置、目标媒体 ACL、调度及正式用户终端均未核验。本记录不代表正式环境验收。
