# DISK-RECOVERY-DEEP-AUDIT-07

开发仓库仍为 E:/ERP/SJERP-Clean，master 7b4e666758ba31a2afd36a7ef81635085a27ff24，主干 CI 43677043705 通过。本轮仅执行本机空间和归档操作，没有业务代码变更。

本轮运行记录保存在 E:/ERP/SJERP-Archive-20261115-134619/cutover06-private-160743/deep-audit07-172648。removed.jsonl 保存正常移除的工作树、分支、完整 SHA 和各次卷变化。sparse.jsonl 与 sparse-*.txt 保存只取消检出历史截图及录像的树和具体文件，使用 git sparse-checkout disable 恢复整树。caches.jsonl 保存可从锁文件重建的独立前端依赖清理。分配报告为簇估算，卷实际释放以清理前后可用空间计。历史快照中的数据库、媒体、备份和不明独有内容分别保留。

主树 51 项、集成树 147 项及 local-data 61 个文件的恢复副本 SHA-256 已重新核对。现账户的 EFS 私钥可用，独立私钥备份和跨账户恢复尚未验证，不退役依赖这些备份的敏感原件。原 Git bundle、发布源码和历史分支均保留。
