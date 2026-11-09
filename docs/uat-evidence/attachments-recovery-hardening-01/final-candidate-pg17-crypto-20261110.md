# 最终候选 PostgreSQL 加密恢复与保留演练

2026-11-10（北京时间），在独立 detached 工作树对候选 `4c01d3be84663d9709b437a4b8fe825f993473d7` 运行。环境为 PostgreSQL 17.11、Django 6.0.9、psycopg 3.3.6、GnuPG 2.4.9 和 OpenSSL 3.5.6。脚本自行创建一次性集群、随机临时凭据、签名密钥、数据库和媒体目录，不连接正式数据库。

命令（路径为本机显式指定的可执行文件）：

```text
<python> backend/operations_pg_acceptance.py --postgres-bin <PG17-bin> --gpg <gpg.exe> --openssl <openssl.exe> --msys-paths
```

退出码 0，实际标准输出：

```json
{"status":"PASS","source_sha":"4c01d3be84663d9709b437a4b8fe825f993473d7","scope":"real-PG17-with-simulated-media-fence","active_session_rejected":true,"other_login_rejected":true,"restored_verified":true,"nonempty_media_restored":true,"bank_voucher_file_restored_and_sha_verified":true,"empty_media_root_restored":true,"missing_media_member_rejected":true,"corrupt_media_member_rejected":true,"manifest_digest_mismatch_rejected":true,"source_media_unchanged":true,"audit_truncate_rejected":true,"source_unchanged":true,"audit_row_mutations_rejected":8,"real_lock_competition_rejected":true,"bad_digest_rejected":true,"failed_restore_rejected_and_owned_database_removed":true,"encrypted_retention_removed":2,"replicas_are_local_only":true,"tables":120,"rows":1146,"seconds":106.287,"cleanup":"complete"}
```

脚本对三份临时归档执行加密、解密、实际恢复、签名恢复回执及本地副本校验，再按保留规则删除两份旧归档并确认保留一份及全部三个本地副本。媒体写入栅栏为模拟，副本均在本地；这不能证明目标 ACL、独立故障域副本、正式备份调度或生产环境已验证。
