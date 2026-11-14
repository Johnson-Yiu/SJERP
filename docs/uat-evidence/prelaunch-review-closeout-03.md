# PRELAUNCH-REVIEW-CLOSEOUT-03

本机定向测试；GitHub Actions 全量认证。

以分支 codex/prelaunch-repair-integration-02 的最终提交核对 Backend、Backend PostgreSQL、Frontend 和浏览器制品。基线运行 43556958576 及历史本机记录保留原结果。SKU 表格分别显示成本与售价的币种，未知成本币种显示“币种待核实”。

| 清理候选 | 实测大小 | 引用及未提交状态 | 清理准备 |
| --- | ---: | --- | --- |
| 当前集成树 frontend/dist | 2.0 MiB | 本轮构建生成，未作为源码提交。运行预览时可能引用 | 确认预览退出后可重建 |
| 当前集成树 docs/uat-evidence/batch02-final4-full | 83.5 MiB | 上一轮停止的本机全量记录，含未提交运行产物 | 最终认证、归档完成后再审 |
| 当前集成树 docs/uat-evidence/batch02-final4-scoped-retry | 30.8 MiB | 含未提交原图、31/32 索引，供复审参考 | 保留至复审归档 |
| ui-prelaunch-polish-01/frontend/node_modules | 141.4 MiB | 未提交依赖。当前集成树 junction 正引用 | 解除引用前保留 |
| 仓库 .git | 1253.2 MiB | 注册工作树共用；包含提交历史和管理信息 | 排除 |

根工作树及集成树有既存未提交内容。所有注册工作树、测试数据库、媒体、备份、迁移及本轮证据保留。本轮仅盘点，未删除文件。

本机定向结果：ProductSkuManagement Node 1 项通过，真实 Chrome 1 项覆盖四种币种场景，前端构建通过。见 [1366 表格原图](sku-price-currencies-1366.png)。
