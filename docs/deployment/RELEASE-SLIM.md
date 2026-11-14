# 局域网内测发布包

在包含候选提交的可信 Git 检出中运行以下命令。使用 Python 3.12+、与候选 CI 相同的 Node/npm。输出的父目录须已存在，每次使用新的目录。构建机可使用已备齐的 npm 缓存并传入 `--offline`。

```text
python scripts/build_pilot_release.py build <40位候选SHA> <新目录>
python scripts/build_pilot_release.py verify <新目录>
```

构建工具从指定 Git 树提取输入并以锁文件执行 `npm ci`、`npm run build`。`RELEASE.json` 记录提交、工具版本、文件字节和 SHA-256。交接时随附独立可信渠道取得的清单摘要，接收后比对摘要并执行 verify。清单覆盖文件与内容完整性。

运行内容包括 Django 与迁移、生产静态资源、后端依赖锁和前端锁、报价和装箱模板、运行配置样例。字体沿用当前样式中的 Google Fonts 和本地回退字体。离线内网需在目标终端核对回退渲染。业务库、媒体、凭据、环境配置和虚拟环境放在发布目录之外。部署按 [本地运行交接](LOCAL-RUNTIME.md)执行，Nginx 静态根指向包内 `frontend/dist`。备份工具的 PostgreSQL 源码身份校验需要 Git。备份和恢复由管理员从与 `RELEASE.json` 同 SHA 的独立干净维护检出执行。

最终集成 SHA 确定后重新生成并验证，使用同一候选完成启动、静态资源、模板、附件上传下载和导出冒烟。

## 阶段验证

基线 `96276dffa07c11fb60720a439269df8c36031f7a`，Node 24.16.0。离线 npm 安装、Vite 构建及清单校验通过。清单覆盖 327 个文件、5,128,478 字节，阶段 `RELEASE.json` 的 SHA-256 为 `d17d3db875e21334a320fb967231871d98a0f2ce500fbab76246ebb3290074ed`。

Windows、Python 3.14.5、隔离合成 SQLite 和私有媒体完成包内迁移与 Django check。回环 HTTP 获取首页、JS、CSS 成功。Django HTTP 框架测试客户端登录及退出，下载并解读销售订单 XLSX 模板，上传合成凭证，另一个 Django 进程复读持久化凭证并通过 HTTP 接口下载，返回字节完全一致，销售报表 CSV 下载通过。两份报价模板和一份装箱模板可解析。最终候选构建、Linux 目标机、Nginx/Gunicorn/PostgreSQL 以及第二台局域网终端待验。

## 清理准备

本轮未删除任何候选。复用 [03 初查](../uat-evidence/prelaunch-review-closeout-03.md)，以下在 2026-11-14 补录实际逻辑文件字节。目录扫描避开 junction；底层分配、压缩和重复路径会影响实际释放量。

| 分类 | 路径和实测字节 | 清理门槛和恢复 |
| --- | --- | --- |
| 可再生 | 主树 `frontend/dist` 1,477,233，集成树 `frontend/dist` 2,133,454 | 预览与服务确认退出后可清理。按相应 SHA 和锁文件重建。 |
| 可再生但在用 | 主树 `frontend/node_modules` 155,325,519，`ui-prelaunch-polish-01/frontend/node_modules` 148,262,182 | 核对各工作树引用。03 已确认集成树依赖 junction 指向后者。所有任务退出相关路径后从 lock 重装。 |
| 历史结果待归档 | 集成树 `docs/uat-evidence/batch02-final4-full` 90,608,295，`batch02-final4-scoped-retry` 39,603,981 | 含未提交的运行产物及复审索引。候选认证后由协调任务逐文件确认，先写入获准私有归档，记录清单与 SHA-256，再复验解包和索引。归档位置待定。 |
| 保留 | `.git/objects` 1,085,557,861 | 所有 linked worktree 的共同对象。未纳入清理。 |
| 保留 | `local-data` 236,000，`.experience-preview-data` 2,547,569，`.system-temp-recovery-20261027` 63,942,090，`.tmp` 115,337,687 | 仅检查目录字节。含可能仍在用的数据或所有权未知产物；逐项确认前保留，任何业务库、媒体与恢复归档须保留。 |

现行集成工作树扫描为 1,408,421,506 字节。基线 `96276dff` 的 Git 树按路径统计为 1,150,696,544 字节，其中 `docs/uat-evidence` 为 1,137,143,016 字节。最大单项 `review-integration-batch-20261104/ci-1f189c3-ui-screenshots.zip` 为 30,898,981 字节。隔离浏览器工具检查证据目录边界，历史报告和部分工具保留对该目录的引用，因此目录整体排除在删除候选之外。逐文件清理须核对工作流、测试入口、证据索引及归档可读性。已跟踪文件须经正常提交删除。未合入成果、业务模板、迁移、当前审计证据和工作树管理信息保留。
