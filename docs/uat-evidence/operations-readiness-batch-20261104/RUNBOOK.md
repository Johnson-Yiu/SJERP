# 运维工具执行说明（仍在实施）

所有命令先在任务自建的一次性目录运行。凭据只由受保护的凭据文件、操作系统密钥存储或受控运行环境注入；禁止放进命令参数、配置 JSON、归档、日志或版本控制。

## 只读部署检查

复制 `docs/deployment/operations-preflight.example.json`，填写已存在且互不嵌套的媒体、静态、备份目录和公开 HTTPS origin：

```sh
python backend/operations_preflight.py --config /absolute/path/nonsecret-config.json
```

任何结果的 `backup_authorized` 都是 false。该命令只检查配置与本机容量，不证明 HTTPS 服务可用、全写入者静默或备份一致。

## 验证副本

```sh
python backend/operations_copy.py --source /absolute/path/verified-backup --destination /absolute/path/new-copy --sha256 <可信来源的完整SHA256>
```

源摘要、复制后摘要、源复查全部一致才返回 `VERIFIED_COPY`。已有目标一律拒绝；失败只尝试清理本次创建的目标，清理失败保留原错误及清理错误。没有自动保留删除功能。副本验证不能证明原备份可恢复；同机复制始终返回 `independent_failure_domain_verified=false`。目标目录须由运维独占，不能允许不可信进程替换路径。使用独立故障域、独立密钥保管和实际恢复演练后才能另行验收容灾。

## HTTPS 代理模板

`docs/deployment/operations-nginx.conf.example` 是待填写的 Nginx http 上下文模板。填写证书、域名和目录，保持私有媒体无 root/alias；仅允许代理连接本机应用端口，防火墙拒绝外部直连应用。必须执行 `nginx -t -c <完整配置>`，再验证未登录/越权附件拒绝、`/media/` 直链拒绝、API 私有响应不缓存、Cookie Secure/SameSite，以及重启后媒体摘要不变。

当前未发现可用 nginx/docker/podman；未运行真实代理或容器。后续已从 Git 安装目录找到 GnuPG 2.4.9/OpenSSL 3.5.6，并完成独立临时目录的实际加密演练。模板仍不代表目标环境通过。

## 联合备份与恢复入口

入口配置为 `docs/deployment/operations-backup.example.json`。示例有意包含无效身份和 SHA，必须由管理员填写一次性环境的实测值。配置只保存连接目标和 pgpass 路径；密码不得放入 JSON。Linux 上凭据和密钥文件采用仅所属维护账号可读权限，目录由独立管理员管理；Windows 部署的 NTFS ACL 未验收。

```sh
python backend/operations_backup.py backup --config /absolute/path/backup.json
python backend/operations_backup.py restore --config /absolute/path/restore.json
```

备份采用数据库导出快照和逐表 SHARE 锁，核对迁移完成状态、逐表全部行的排序摘要、数量、序列及四类附件引用。`destination_directory` 每次生成新的随机文件名；`destination` 则必须指向不存在的文件，两者只选其一。加密配置存在时，明文 ZIP 只在任务临时目录存留，使用 GnuPG AES256 加密后实际解密复核，再返回成功。任意文件单独存在不等于备份成功，必须保留命令零退出及完整返回凭据；失败中断的孤立文件不能进入保留清单。

维护条件非常严格：必须只有专用维护账号可登录，其他登录角色全部禁用，源库不存在其他连接或 prepared transaction；媒体位于无子挂载的专用本地 ext4/xfs/btrfs 文件系统，文件系统及挂载均只读。工具仅验证、不擅自更改账号或挂载。运行前管理员须列明并停止 Web、worker、计划任务、管理命令及外部写入者，再实施并验证这些边界。维护账号的凭据不得交给 Web/worker。具备 DB/OS 管理权限者属于可信维护边界，不能让其同时执行其他写入。不能提供上述证明时命令拒绝执行。

恢复配置使用**目标集群**的明确身份和维护连接，另填 `archive`、可信 `expected_sha256`、现有私有 `media_parent`、同版 `app_sha`。目标数据库总是新建，不接受指定已有目标或覆盖开关。加密归档先用下方解密命令在受控临时目录解密，确认明文摘要，再交给恢复入口。恢复先验证归档路径、摘要、版本和容量，然后恢复进新库；核对所有行和序列、附件引用、媒体摘要及审计拒绝。失败只删除本次创建的新库及媒体；失败和清理错误均保留。源库及原媒体不作为回滚删除目标。

恢复使用 `--no-owner --no-acl`，不会复制源维护角色或密码；新库由维护账号拥有，**不能直接切换为应用运行库**。DBA 必须重新实施并实际验证运行账号非 owner、非 superuser、无触发器维护权限、审计表仅追加权限。应用开发超级管理员不等于该维护账号。最小权限依环境授权 `SELECT`、数据库建库/删本次库能力和 `pg_control_system()` 执行权限；服务运行账号不应继承这些权限。现有 ISS-043 的角色及触发器边界继续有效。

## 加密、保留与调度

```sh
python backend/operations_archive.py encrypt --config /absolute/path/encrypt.json
python backend/operations_archive.py decrypt --config /absolute/path/decrypt.json
python backend/operations_archive.py prune --config /absolute/path/retention.json
python backend/operations_archive.py prune --config /absolute/path/retention.json --execute-prune
```

加解密 JSON 字段：`source`、`destination`、绝对 `executable`、独立 `key_file`、可信 `expected_sha256`，Git/MSYS GnuPG 额外设置 `msys_paths:true`；解密的摘要是明文摘要。密钥至少 32 字节，由密钥管理方生成高熵随机值并独立保管，不能与归档放在同一备份目录。GnuPG 配置及 agent 使用临时独立目录，仅终止该临时 home 的 agent。不能把摘要当作签名或把本地双副本当作异地容灾。

保留 JSON 字段：绝对 `root`、32位十六进制 `owner_id`、`keep>=1`、`minimum_age_seconds>=0`、`receipts`。预先明确登记根目录 `.sunjack-backup-owner`；工具不接管未知目录。每条凭据包含 `name`（`backup-<32位hex>.gpg`）、`sha256`、同值 `restore_verified_sha256`、带时区 `created_at` 和根目录外的绝对 `replica` 路径。凭据由受控成功恢复流程保管，不能人工猜填“已验证”。默认仅计划；执行前全量校验清单及副本，删除前再次核对，仅删明确列出的旧归档，至少保留一份最新备份且不删副本。副本不可达/损坏、归属或恢复凭据不符时拒绝；未知文件从不列入删除。

部署目录的 `.service.example`、`.timer.example` 和告警模板是未启用的交接配置。定时器只调用工具，不代替维护编排；没有全写入者条件就会失败。`OnFailure` 进入 syslog 告警入口；目标监控通道实际投递、失败告警和漏调度告警仍待目标环境实测。当前未安装、启用或向外发送告警。

## 一致性与验收边界

写入面包括 HTTP 上传及业务写入、管理命令（导入/seed/migrate/shell）、数据库直接客户端、部署迁移及媒体文件系统直接写入。源码搜索未发现不能因此证明部署没有 worker/计划任务；部署资产清单必须列出实际系统服务、任务、容器、账户、数据库角色与卷写入者。

维护机制必须在操作系统/存储和数据库边界阻断这些写入者，并在备份窗口内保持；配置标志、活动连接瞬时为空、两次文件摘要一致、单进程锁都不充分。现有 isolated_postgres_drill 继续只作其原始隔离演练，不作为本入口的替代品。新专项 `operations_pg_acceptance.py` 的数据库、竞争和恢复是真实 PG17；Linux 媒体栅栏明确模拟，不作为全写入者验收。
