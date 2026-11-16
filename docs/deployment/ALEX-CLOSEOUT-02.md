# ALEX 安装包与功能收尾

从远端 master `7b4e666758ba31a2afd36a7ef81635085a27ff24` 创建集成工作树。审查的历史安装分支为 `611948803e5e7a3f043eda3345570d7a84c15070`。接收四个安装、校验和维护脚本。Windows 预检沿用 master 的 `Check-Alex.cmd` 和 `Check-Alex.ps1`。

ALEX 分支的旧 `ProductSkuManagement.vue` 和草稿回归均未采纳。逐项保存逻辑继续使用 master 的串行保护。业务源码补丁只调整 `PurchaseOrderPage.vue` 草稿 MOQ 比较，以后端认可的两位基础数量单位汇总，正式下单规则与迁移沿用 master。隔离 Chrome 报价用例以合成响应验证确认、取消、检查故障及导出失败后的重新核对，并通过回归保留这些操作。

## 使用同一源码生成和校验

1. 使用 GitHub Actions 认证的完整集成提交 SHA 构建。用 `python scripts/build_pilot_release.py build <源码SHA> <新目录>` 生成运行包。安装包的 `RELEASE.json` 记录同一 SHA。
2. 交付前执行 `python scripts/build_pilot_release.py verify <包目录>`，从可信渠道交接清单 SHA-256。Windows 侧使用同提交的 `scripts/lan-installer/Test-ErpRelease.ps1 -Bundle <包目录> -ManifestSha256 <清单摘要> -ExpectedCommit <源码SHA>` 校验。
3. Windows 预检和虚拟机工具留在维护检出。使用 `New-AlexBuildVm.ps1` 准备隔离构建 VM，使用 `New-AlexVm.ps1` 准备运行 VM。两者都有宿主名、ISO 摘要、既有交换机、磁盘和重名检查。实际运行依据获准的 ALEX 操作安排。
4. 按 [本地运行交接](LOCAL-RUNTIME.md) 启动实例。Linux 的 `erp-control.sh` 调用现有 systemd 服务和 HTTPS 健康检查。备份和恢复演练都由与清单 SHA 相同的干净维护检出调用 `backend/operations_backup.py`，实例配置与私有凭据保存在包外。配置示例见 [备份恢复交接](PILOT-RECOVERY.md)。

交付时同时使用集成源码 SHA、发布清单摘要与 Actions 运行记录。目标主机的 PostgreSQL 和媒体恢复仍按既有交接验收。本轮本机验证使用独立合成数据库和独立媒体目录。
