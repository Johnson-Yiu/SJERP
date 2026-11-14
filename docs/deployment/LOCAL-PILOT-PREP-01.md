# SJERP LOCAL-PILOT-PREP-01

## 交付保护与清理

交付文档 HEAD ad207b0e759396fd2eb484727b5bcb8f9fa343d2 与远端一致。[文档 CI 43613937593](https://github.com/Johnson-Yiu/SJERP/actions/runs/43613937593) 核对时仍运行，Backend 已通过。固定运行源码仍是 0b0654de5b079d244b74d752ed4b78710ec4881b，该源码的[主 CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/43577214916)和[Linux 专项](https://github.com/Johnson-Yiu/SJERP/actions/runs/43577218735)已通过。

归档根为 C:/Users/Johnson/AppData/Local/SJERP/DeliveryArchive/0b0654de5b079d244b74d752ed4b78710ec4881b。Windows ACL 只允许 Johnson、SYSTEM 和本机 Administrators。归档包括发布 ZIP、RELEASE.json、原始 build/migrate/smoke/login-http 日志、摘要索引和经验证的解包副本。本机归档不替代异机备份。

- ZIP 1,778,045 字节，SHA-256 ccdbf9b9b01750b6ed697892d97844f4564bb8acff0700b3a32d964651887846。
- RELEASE.json SHA-256 46dc7f82543025530070b655d479b36cda05121700136cbd407eed9e5e64721c。
- 从归档 ZIP 解包，verify 通过 331 文件、5,141,754 字节。
- 仅删除集成工作树 frontend/dist 的 21 个生成文件，逻辑字节 2,133,454。删除前确认无 Git 跟踪、无非忽略文件、无链接及无检测到的预览进程。需要预览时按原锁文件重新构建。逻辑字节与卷可用空间变化口径不同。
- 保留全部活动工作树、Git 对象、源码与迁移。集成树有 147 项已跟踪改动，node_modules junction 仍指向 ui-prelaunch-polish-01 的依赖。保留两处、原始临时证据、历史报告、数据库、私有媒体、备份。历史证据逐文件确认引用并通过恢复验证后再评估冗余副本。

## 本机体验实例

Windows 10 Pro 19045，硬件虚拟化及 SLAT 可用。WSL、VirtualMachinePlatform、Hyper-V 当前禁用，当前用户没有已登记 WSL 发行版，未发现已运行的 Linux 虚拟化进程或已安装的 Docker、VirtualBox、VMware 桌面运行器。当前没有获准可用的 Linux 来宾。状态为 BLOCKED，解除条件是管理员授权启用 WSL2、安装受支持 Linux 发行版及所需服务，或交付一个已经可用且允许本机隔离接入的 Linux 来宾。系统改动前确认重启窗口、宿主磁盘容量及 Linux 持久卷路径。

沿用 [运行交接](LOCAL-RUNTIME.md)、[备份恢复](PILOT-RECOVERY.md) 和 [精简发布](RELEASE-SLIM.md)。为实例 local-pilot 单独准备 Linux 用户、systemd unit、虚拟环境和 PostgreSQL 17 专用集群。配置和凭据放在发布目录外，最小权限访问，应用角色与迁移、备份角色分别配置。媒体保存在 Linux 独立持久文件系统，归档目标与媒体卷分离。维护检出使用同一发布 SHA 的干净 Git 树，与运行包、媒体和数据库分离。依据既有部署配置使用 staging、登录账号和审计；开发超级管理员关闭，数据库由审核后的空库迁移初始化。禁止执行 seed_demo。实例配置只用于体验库。

拟用 Nginx HTTPS 回环端口 18443，Gunicorn 回环端口 18143，PostgreSQL 专用本机 socket 或回环端口 15443。实施前核对占用。宿主仅通过回环访问，核对 Linux 和 Windows 两侧监听，并从第二台设备验证不可访问。禁止使用桥接或面向 LAN 的代理转发。账号凭据通过本机私有渠道保存。

验收先在空库进行：审核迁移计划并执行，确认业务表为空；建立专用验收账户，实际登录退出并核对访问限制；合成客户及附件实写回读，下载比对字节、核对 CSV/XLSX 导出。停止并重启 unit，复读同一主键及媒体摘要。然后进入静默窗口，从同 SHA 维护检出按联合备份手册核对数据库身份与独立只读媒体卷。核验归档和摘要，恢复到不同隔离 PG 集群及新媒体目录；通过应用实际复读客户、附件和导出并核对关键金额、库存与记录数。以上本机服务和恢复步骤尚未执行。现有 CI 与发布包 SQLite 冒烟保留各自范围。

升级先校验新版包和清单，放入新的版本目录。用旧版本维护检出备份数据库和媒体，在恢复副本验新版迁移及业务回读。停应用写入，确认联合备份与迁移计划，切换版本目录并复验。数据卷、凭据与实例配置保持独立。若已迁移且需要回退，从旧版本归档恢复至隔离目标，校验后才切换，避免旧代码直接访问新版库。

迁往 ALEX 前，确认获准的 Linux、PG17、角色、数据和媒体路径。静默源写入，生成联合备份、摘要与签名回执，通过加密渠道传输。ALEX 先以同 SHA 在隔离目标恢复并复核记录、金额、库存、附件字节及读写权限。经授权后安排最终停写、增量差异核对及切换；保留源实例和回退归档至验收结束。当前未导入真实历史数据，ALEX 未部署。
