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

当前机器未发现 nginx/docker/podman/openssl 命令，未运行代理、容器或加密演练。模板不代表目标环境通过。

## 尚在实施的一致性入口

写入面包括 HTTP 上传及业务写入、管理命令（导入/seed/migrate/shell）、数据库直接客户端、部署迁移及媒体文件系统直接写入。源码搜索未发现不能因此证明部署没有 worker/计划任务；部署资产清单必须列出实际系统服务、任务、容器、账户、数据库角色与卷写入者。

维护机制必须在操作系统/存储和数据库边界阻断这些写入者，并在备份窗口内保持；配置标志、活动连接瞬时为空、两次文件摘要一致、单进程锁都不充分。尚未实现可复用联合备份入口前，不允许用既有 isolated_postgres_drill 命令替代。
