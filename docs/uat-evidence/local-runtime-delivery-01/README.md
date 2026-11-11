# SJERP LOCAL-RUNTIME-DELIVERY-01

共同基线 `c21a1060cb99bdf6bda33a07c7ba01b990f4878f`。从用户指定 SJERP 获取远端分支，工作树位于 `.task-worktrees/local-runtime-delivery-01`。本机原 origin URL 使用 SUNJACK-ERP 名称，交付推送明确指定 SJERP。

## 能力与来源

- Windows 演示入口迁移 SQLite 并仅对新库调用 `seed_demo`。现标注用途、限定本工作树数据、首次安装使用锁定依赖、占用端口时提前失败。专用 Node 合约测试通过。
- 基线包含 `operations_local_environment.py`、`operations_preflight.py`、`operations_backup.py`、`operations_copy.py`、`operations_monitor.py` 和现有 PG17 验收工具。核对 `sjerp/codex/local-operations-closeout-20261105`（`250c3b7f55585acccb73b2efc1b0993605be0b0b`）对应代码，基线额外包含隔离 PG17 演练。沿用现有备份、独立副本、回执、保留及监控。
- 新增运维入口见[操作说明](../../deployment/LOCAL-RUNTIME.md)。systemd unit 样例提供启动、状态、停止及日志，启动前只读查运行库、迁移、角色和媒体，启动后验证 Gunicorn HTTP 会话入口。
- [历史 Windows 隔离 PG17](../local-operations-closeout-20261105/README.md)曾验证真实数据库恢复 102 表、1025 行、审计拒绝和源库不变，模拟了 Linux 媒体栅栏，副本同机。[历史 Linux 专项](../linux-operations-acceptance-20261104/README.md)对应 `4a4f338b09e9a464f1e66c24a905c35c970729bf`，早于后续正式回执属组补修。

## 目标环境待验

本机 Windows 可用性检查中 WSL 列表退出 1，未发现可用 Docker/Podman。未注册系统服务、调度或告警。需提供获准的 Linux 或具备等价条件的隔离环境、冻结 release、固定 Gunicorn 来源和版本、独立 PG17 目标及运行/迁移/维护角色、媒体卷及 ACL、HTTPS 主机名和证书、独立备份目标、密钥及 RPO/RTO。用合成资料实测两实例生命周期及故障退出、端口冲突、空库初始化、DB/媒体联合恢复、运行角色拒绝、真实跨 UID 回执、监控故障及升级失败处置。目标机另行核验业务访问和恢复验收。

## U4 公共台账及接线建议

- 将本包记录为本地运维入口待独立复审，ISS-018/043/047 保留部署待验，不新增重复 Issue 或关闭历史条目。
- 复用通用 CI；Linux operations 工作流的 push 分支为白名单。将冻结集成分支加入专项触发范围，执行真实 Linux/PG17 专项，并在一次性 systemd 环境验新 unit。若 Gunicorn 纳入应用 venv 依赖，由 U4 同步直接依赖和传递锁并验收；本包未改共享依赖和工作流。


## 本轮执行

- Windows CPython 3.14.5，按后端 lock 安装到本工作树独立 venv，pip check 通过。
- node --test scripts/start-service.test.mjs 通过 1 项。Django 定向运行 test_local_runtime_http、test_iss018_backup_recovery、test_operations_backup、test_operations_preflight、test_operations_copy、test_operations_retention，56 项中通过 53、平台条件跳过 3、失败 0。首次运行未找到 OpenSSL，加入本机 Git 随附 OpenSSL 的命令级 PATH 后复跑。HTTP 检查使用独立回环临时端口；SQLite 恢复、备份拒绝及监控过期/篡改均复用既有专项。
- Windows 临时 SQLite 文件仅运行 migrate，客户、供应商、产品、SKU、订单和报价表均为空，媒体目录为空。独立运行配置检查使用保留但未监听的回环端口，拒绝了不可达 PostgreSQL；另外拒绝开发设置和不匹配的实例库名。
- 远端提交、通用 CI 与专项状态见交付回复。目标环境尚未验收。

## 运行链路复验

本包状态为运行准备已实现，目标环境运行链路待验。一次性 GitHub Linux 演练复用 postgres-role-receipts 作业的所有权校验和合成 PG17 集群。新增脚本从交付的 unit 渲染两份临时实例，只替换 runner 路径和 Unix 运行身份。实例使用各自数据库、数据库角色、媒体目录和回环端口；runner Unix 身份共用。临时 unit 不注册开机启动，退出时清理。既有联合恢复脚本在同一 job 校验合成数据库和附件。

管理员安装独立服务依赖清单中的固定 Gunicorn，配置实际主机、HTTPS、数据库及媒体权限。业务人员使用管理员交付的 HTTPS 地址。需要 U4 在最终集成 SHA 调度既有 Linux 专项，并在公共台账保留真实主机、HTTPS、实际媒体 ACL、独立备份目标和调度待验。
