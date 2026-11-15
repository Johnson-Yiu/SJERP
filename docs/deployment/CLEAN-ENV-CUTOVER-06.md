# CLEAN-ENV-CUTOVER-06

开发入口为 E:/ERP/SJERP-Clean。主干 7b4e666758ba31a2afd36a7ef81635085a27ff24，[主干 CI 43677043705](https://github.com/Johnson-Yiu/SJERP/actions/runs/43677043705) 已成功。前端依赖在新仓库独立安装，Python 使用 E:/ERP/SJERP-Dev-Python。锁定依赖 pip check、Django check、独立合成 SQLite 迁移、登录后客户 API 回读、SKU 定向 Node 测试通过。E 盘任务工作树 E:/ERP/SJERP-Cutover-06 直接由新克隆创建。

旧主树 51 项和集成树 147 项已跟踪改动，及旧主树 local-data 的 61 个文件，保存在 E:/ERP/SJERP-Archive-20261115-134619/cutover06-private-160743 的 EFS 加密目录，逐文件实际恢复并比对 SHA-256。保留原目录，归档仅供本机 Windows 用户恢复。未将本地凭据导入新仓库或提交 Git。原文件备份只有部分清单，缺全量完成标记，不能作为整体退役依据。全量状态清单、已完成条目核对、最大占用及异常记录放在同一私有归档。

正常移除 sales-state-closeout-05、quote-state-closeout-06、first-release-consolidation-02、global-numeric-wheel-guard-01 四棵旧工作树。历史独有产物共 33 个，先加密备份并实际恢复校验，已跟踪内容由原 Git 引用保护。各树删除前后的卷可用字节见专属 removal.json。旧主树确定归属的 Django 8100 和 Vite 5191 已停止，其他仍有运行身份待确认的旧服务和素材保留。旧主目录与共享对象库未退役。
