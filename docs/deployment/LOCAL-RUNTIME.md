# 森爵 ERP 本地运行交接

## 日常使用

业务准备环境使用 Linux 上独立的 Gunicorn、Nginx、PostgreSQL 17 和私有媒体卷。Windows 上的 `start-main-worktree.ps1` 只用于开发演示，会迁移本工作树 SQLite 并在新库写入演示数据。Windows 可通过浏览器访问已验收的 Linux 实例。可选目标为已有且获准使用的 Linux 主机或虚拟机，也可评估具备 Linux 文件系统和 systemd 的 WSL2；本次 Windows 检查未发现可运行的 WSL 发行版或容器环境。原生 Windows 的 Gunicorn 和现有 POSIX 私有媒体、只读挂载及跨 UID 回执方案需另行适配和验收。

- **访问地址**以运维交付的 HTTPS 地址为准。样例实例 `a` 使用 `https://erp-a.example.invalid/`。Gunicorn 样例仅监听 `127.0.0.1:18131`，由该实例的 Nginx 虚拟主机转发。
- **数据位置**由运维交付单记录。实例 `a` 使用 `/srv/sjerp/a/release` 的冻结提交、独立 PostgreSQL 数据库 `sjerp_a`、`/var/lib/sjerp/a/private-media` 及独立备份目标。配置、密码文件、密钥在发布目录之外。每个实例使用不同 unit、数据库/运行角色、媒体根、Gunicorn 端口和 HTTPS 主机名。禁止用另一个工作树的配置启动。
- **启动与停止**由有权限的运维人员执行 `systemctl start sjerp-local@a.service` 和 `systemctl stop sjerp-local@a.service`。systemd 管理该 unit 的进程组，重复操作可使用同一命令。端口冲突时查日志并协调端口，保留占用端口的实例。
- **成功判断**查看 `systemctl status sjerp-local@a.service`。启动阶段须通过 PostgreSQL 身份、迁移状态、审计角色、媒体目录及 Gunicorn HTTP 检查。日常判断还须打开实例 HTTPS 首页，确认 `/api/session/csrf/` 返回 HTTP 200 和 CSRF cookie。当前数据库复查由运维以该 unit 的运行身份及环境执行 `python manage.py check_local_runtime`。unit 显示 active 只代表进程状态。
- **报障**请记录实例名、发生时间和浏览器现象。运维用 `journalctl -u sjerp-local@a.service -n 100 --no-pager` 获取应用日志，按实际 Nginx 配置查代理错误日志。共享前脱敏。
- **备份与恢复**由运维按 [ISS-018 手册](ISS-018-数据库与附件一致性备份恢复.md)确认静默窗口并执行。业务使用者不要自行迁移、导入真实数据、清库、恢复、调整账号权限或启用调度。

## 运维准备及维护

1. 对每个实例填写冻结 SHA、HTTPS 地址、回环端口、PostgreSQL 主机/端口/库名/运行角色、媒体卷及备份与演练目标。核对各实例无重叠。用 `python backend/operations_local_environment.py` 检查工具，用 `python backend/operations_preflight.py --config /etc/sjerp/a/preflight.json` 检查已有目录和容量。JSON 可参照 [预检样例](operations-preflight.example.json)。这两项为只读。
2. 准备独立虚拟环境，安装 `backend/requirements.lock`，执行 `pip check`。在同一虚拟环境运行 pip install -r docs/deployment/sjerp-local-service-requirements.txt，执行 pip check 并核对 gunicorn --version 为 27.0.0。实例准备、路径填写和服务配置由环境管理员完成。业务人员使用管理员交付的 HTTPS 地址。前端在构建环节使用 `npm ci` 和 `npm run build`。准备 [Nginx 样例](operations-nginx.conf.example) 对应的独立虚拟主机，修正端口、证书、静态目录，执行 `nginx -t`。私有媒体不得成为 Nginx root/alias。按 [ISS-043](ISS-043-PostgreSQL审计防篡改.md)核验受限运行角色、独立迁移角色和审计表。提供受保护的 [环境文件](sjerp-local-runtime.env.example)、[Gunicorn 配置](sjerp-local-gunicorn.conf.py.example)及 [systemd unit 样例](sjerp-local%40.service.example)，由获准的环境管理员审核及配置。样例未注册，未启用自动重启或开机启动。
3. **空环境初始化**由 DBA 确认专用空库与媒体卷后，在独立维护环境以迁移角色先执行 `python manage.py migrate --plan`，再执行 `python manage.py migrate --noinput`。核查客户、供应商、产品、SKU、订单、报价等业务表为空，保留迁移所需基础字典。运行账号按既有部署手册单独核验。日常 unit 只做只读迁移检查，遇到待迁移时拒绝启动。
4. **已有库升级**先停对应 unit，确认其他写入者静默，使用 `python backend/operations_backup.py backup --config /etc/sjerp/a/backup.json` 完成数据库与媒体联合备份，核对退出 0、归档 SHA256 和可恢复性，再用独立迁移角色核对目标、审查 `migrate --plan` 后执行迁移。配置使用既有身份及只读栅栏校验。升级失败保持停服，保留日志和迁移状态，评估已提交的迁移及非原子步骤。需要回退时，用匹配备份版本恢复数据库与媒体到新隔离目标，核对后再由授权人员决定切换。
5. **恢复演练**使用 `python backend/operations_backup.py restore --config /etc/sjerp/a/restore-drill.json` 指向经核验的隔离集群、归档摘要和新的媒体目标。核对记录数、关键金额和库存、附件引用和 SHA256。加密演练使用 `restore-encrypted-verify` 及既有签名回执保护。按既有手册使用 `operations_copy.py` 验证独立副本，`operations_monitor.py --config ...` 监控归档和回执，任何非零退出均按失败处理。调度与告警模板由运维另行批准。
