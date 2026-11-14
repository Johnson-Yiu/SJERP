# LAN-PILOT-READINESS-01

审阅基线 `96276dffa07c11fb60720a439269df8c36031f7a`。用 [Linux 运行入口](../../deployment/LOCAL-RUNTIME.md)及原有模板交接单实例。以下为非敏感样例，实际配置由获准的运维人员填写。

| 项目 | 样例或待填写项 |
| --- | --- |
| 版本 | 示例使用本页基线，交付时换成最终集成 SHA，并核对包清单和摘要 |
| Linux 系统、磁盘/卷空间、安装权限、服务及端口占用 | UNKNOWN，目标主机待指定 |
| Nginx HTTPS | `https://erp-a.example.invalid/`，实际内网 DNS、监听地址、证书与信任待确认 |
| Gunicorn | `127.0.0.1:18131`，`sjerp-local@a.service` |
| PostgreSQL 17 | `127.0.0.1:5432/sjerp_a`，专用运行角色 `sjerp_a_runtime`，迁移角色另配 |
| 发布/构建 | `/srv/sjerp/a/release`，`frontend/dist`、`backend/staticfiles` 位于发布目录内 |
| 媒体 | `/var/lib/sjerp/a/private-media`，持久卷，与发布和公共静态目录分离 |
| 机器配置 | `/etc/sjerp/a/runtime.env` 等，密码、密钥、证书私钥在受保护的仓库外位置 |
| 联合备份 | `/etc/sjerp/a/backup.json`，实际归档与独立备份位置由恢复交接填写 |

## 验收记录

- 开发宿主实查为 Windows，WSL 列表命令退出 1，当前 PATH 无 Docker 或 psql。该宿主仅用于准备交付；指定 Linux 主机及第二台授权终端的可访问性均为 UNKNOWN。
- Windows 定向复验 `python manage.py test crm.tests.test_local_runtime_check crm.tests.test_local_runtime_http` 通过 3 项，覆盖模拟数据库身份、迁移、审计权限和媒体边界，以及回环 HTTP 会话启动检查。测试未使用真实业务库。
- 已有[隔离运行证据](../local-runtime-delivery-01/README.md)可复用，包括临时 Linux 实例生命周期与 PostgreSQL 角色检查。其运行配置和版本为历史证据。
- 待在指定 Linux 主机用合成资料完成：启动、重复启动核对同一 unit/主进程、停止再启动、独立监听端口冲突且原监听者继续服务；登录/退出，上传后重启，下载并比对摘要，执行一次既有导出，重开记录确认数据库保留。
- 待在第二台获准的局域网终端检查证书信任、登录、附件上传/下载及退出。实际 HTTPS 地址及验收路径由运维私下交接。
- 本轮未运行目标服务、未注册常驻服务或调度、未更改网络或真实业务库。
