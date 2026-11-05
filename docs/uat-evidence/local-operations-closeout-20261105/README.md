# LOCAL-OPERATIONS-CLOSEOUT-03

基线 `bcdcb57545f121b8a4102f352c74008b47372035`；独立分支 `codex/local-operations-closeout-20261105`。本报告只覆盖隔离合成环境，不是部署批准。

## 环境与已有证据

本机 Windows 10、CPython 3.12.16；[只读检查及 WSL 原始输出 base64](logs/environment.json)显示 WSL 列表退出 1、返回安装帮助，PATH 无 Docker/Podman。未安装、启动或配置系统组件。`backend/operations_local_environment.py` 可重跑只读检查；发现命令不等于已经证明隔离能力。

来源 `4a4f338b09e9a464f1e66c24a905c35c970729bf` 的 Linux 专项和其[原始报告](../linux-operations-acceptance-20261104/README.md)曾通过，但不含后续 `0037b8c5899554819943944a9cf9e4ea952d2bae` 正式 CLI 回执属组补修；[集成复审](../integration-closeout-02/REVIEW-LINUX-STABLE-SOURCE.md)明确该区别。不能拿历史成功代替基线后的跨 UID 验收。本轮不运行 GitHub Actions。

## 可重复入口与交接

在一次性 Linux 环境先运行 `python backend/operations_local_environment.py`。准备独立 Python 依赖、OpenSSL、setpriv 和三个专供测试的非零 UID/GID；只在确认整台环境可丢弃时，以 root 执行：

```sh
SUNJACK_DISPOSABLE_LINUX=yes python backend/operations_local_handoff.py --signer-uid 10001 --reader-uid 10002 --other-uid 10003 --group-gid 10004
```

该脚本只创建自己的临时目录，不创建账号或启动服务；用不同 UID 调用现有 `publish_receipt_file`，验证 0600、0640、非授权读取、写入及签名私钥访问拒绝，使用合成签名验证原始文件，并检查已有目标拒绝和暂存文件清理。**脚本尚未在 Linux 执行**；它验证的是合成签名的交接，不执行数据库恢复，不能冒充真实恢复回执链。Windows 安全拒绝记录见 [日志](logs/handoff-windows-denied.log)。脚本不改变真实用户、组或服务器；应在可丢弃 Linux 的 UID 命名空间内使用，不应在生产主机运行。

真实链仍须在获准一次性 Linux/PG17 环境执行：以合成新财务和历史数据进行备份、加密、解密、正式恢复 CLI、审计及附件校验；恢复账号生成 `receipt_output`，设置专用 `receipt_read_group` 后，以保留账号读取同一文件运行 monitor 和 prune，另以无权账号尝试读写。复验错包、篡改、过期、无权、已有目标、工具与清理失败，并核对源库和至少一个有效副本。现有 `backend/crm/tests/linux_operations_pg_acceptance.py` 包含正式 CLI 和真实 PG17 演练，但其入口专为 GitHub job-owned service 设计，本轮没有伪造 CI 环境运行它。

配置、密钥分离、静默前提及命令详见[现有运维手册](../operations-readiness-batch-20261104/RUNBOOK.md)。保留/监控使用受 root 保护的信任根并以非 root 执行；恢复签名私钥只由恢复身份持有。监控退出 0 表示健康，异常或过期退出非零；外部告警需另验。

## 结果与门槛

- 运维专项：[日志](logs/operations-tests.log)，55 项、2 项 POSIX 条件跳过；跳过不算通过。`pip check`、Django check 和迁移差异检查通过。
- [依赖比对](logs/lock-check-vendored.log)：CPython 3.12.16 环境的 16 个适用锁定版本均匹配。第一次比对命令因独立 `packaging` 未安装报 `ModuleNotFoundError`；改用 pip 自带的同名解析器完成检查，没有安装或升级依赖。
- Windows 上复用现有一次性 PostgreSQL 17 脚本，在干净后端源码 `4633452546c647a72bd8698dd4eb191293049b9d` 使用合成资料：[真实数据库恢复日志](logs/postgres-drill-clean.log)通过；102 表、1025 行、恢复后审计拒绝及源数据不变，180.094 秒，临时集群清理完成。包含真实加解密、三次恢复签名和两份旧归档保留处理；媒体栅栏在此演练中模拟，副本同机；该夹具未证明本轮完整新财务/历史样本及跨 UID 正式 CLI 链。[沙箱令牌失败](logs/postgres-drill.log)和[源码不干净时的保护性拒绝](logs/postgres-drill-unsandboxed.log)均保留，未关闭检查。
- [本地 CRM 全量](logs/backend-crm.log)：1397 项，1317 通过、80 跳过、0 失败，1152.345 秒，隔离 SQLite。一次无标签命令发现 0 项，另留 [无效运行日志](logs/backend-full.log)，不算成功验收。
- 目标服务器必须另验正式证书、代理、私有媒体 ACL、维护与应用数据库角色、密钥交接、所有写入者静默、真实调度告警、容量与独立故障域备份。历史的本机副本和自签证书不构成生产验收。
- 最终 GitHub 专项必须在明确允许恢复 CI 后对最终集成 SHA 单独执行，覆盖真实 Linux 只读栅栏、0037 跨 UID 正式回执与 PG17 合成财务/历史链。当前为 **NOT RUN**。
