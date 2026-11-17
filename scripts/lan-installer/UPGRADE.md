# 局域网内测升级执行

升级入口为 `upgrade-pilot-release.py`。实例目录内的 `current` 是指向同目录 `versions/<SHA>` 的符号链接。部署时将已有 systemd unit 的应用及 Python 路径都指向 `current/release` 和 `current/venv`，Nginx 静态根使用 `current/release/frontend/dist`。unit 保留数据库预检和 HTTP 就绪检查。

1. 使用离线载荷暂存目标版本。核对正在运行的版本、目标版本、专用集群和媒体卷。停对应服务并按既有维护流程实施数据库和媒体写入隔离。
2. 运行升级入口的 `backup` 子命令，提供当前版本的干净维护检出和备份配置。现有工具完成联合备份和加密回读验证。升级入口重新核对归档摘要，再写入与此次升级对应的备份记录。
3. 按既有维护流程将媒体卷恢复可写，恢复本实例的运行账号与独立迁移账号所需权限。应用服务继续保持停止，其他写入入口继续保持静默。
4. 一小时内运行 `activate`，提供独立迁移 JSON。字段与运行配置同名，包含 `APP_STAGE`、`DJANGO_ALLOWED_HOSTS`、`DJANGO_SECRET_KEY`、`DATABASE_URL`、`PGPASSFILE`、`MEDIA_ROOT`。文件和 passfile 由运维账号保护。迁移角色须能调用 `pg_control_system()` 核验集群标识。脚本会复查备份和身份、输出迁移计划、执行迁移，再原子切换链接并启动服务。

发生迁移或启动失败时保留升级状态、备份记录和旧版本。检查 systemd 日志、当前链接与数据库迁移记录。若需要回退，按现有流程恢复到新隔离数据库及媒体目录并核对，再决定是否切换。失败标记处理前禁止重新执行升级。
