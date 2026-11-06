# SALES-ORDER-IMPORT-01 验收记录

## 基线与范围

- 固定集成基线：`origin/codex/sunjack-first-release-core-uat-01`，提交 `1a2ec0f5c940386e445e59967d498ca1187aa6be`。
- 独立工作树分支：`codex/sales-order-import-01`。
- 本包改动范围：数据导入页、销售订单 XLSX 导入接口与来源幂等记录、迁移、定向测试及新增导入文案。
- 导入按来源订单编号合并多条 SKU 明细；精确匹配客户编号、SKU 和交易单位；核对订单客户、日期、币种与汇率一致；复用 `OrderSerializer` 的订单金额、单位及创建规则。
- 预览只读取并校验，不创建业务记录。确认按整张来源订单创建草稿；任一明细错误时该单不创建。导入不确认订单、不占库存、不生成应收计划、不登记发货。
- 已结清、已收款、已发货或需接续的旧订单引导至“历史资料预检与承接”。既有来源订单号不可重复导入，内容变更也不会覆盖；创建的导入草稿受保护，不能绕过幂等记录删除。

## 定向验证

| 范围 | 结果 |
| --- | --- |
| SQLite 后端 `crm.tests.test_sales_order_import` | 8 项，6 通过、2 项 PostgreSQL 并发测试按条件跳过、0 失败。使用内存 SQLite 测试库。 |
| PostgreSQL 后端 `crm.tests.test_sales_order_import` | PostgreSQL 17.11，8/8 通过，0 跳过。两个独立并发场景分别验证同一预览重复提交和不同预览竞争同来源订单号。临时集群只绑定 `127.0.0.1`；测试库及 0 个遗留 `test_*` 库均已核对，之后停止并清除本次集群目录。 |
| 其他后端检查 | `makemigrations --check --dry-run` 报告 `No changes detected`；定向测试的 Django system check 无问题。 |
| 前端定向测试 | `import-ux.spec.js`、`import-preview-state.spec.js`、`sales-order-import-ux.spec.js` 共 9/9 通过。当前工作树复用已有 `node_modules`，实际 Vitest 4.1.11、Vite 8.2.0，与清单声明版本不同；未安装/升级依赖。 |
| 前端生产构建 | `npm run build` 通过；构建提示主 JS chunk 超过 500 KB。 |
| 真实 Chrome | 系统安装的 Google Chrome 完成可见页面与交互验收：下载 XLSX 模板、上传预览 3 条明细/2 张订单、确认后创建 1 张含 2 个 SKU 行的草稿、整单跳过 1 张有错行订单、查看结果并下载含未知 SKU 错误的 CSV。页面 JS 错误为 0。截图见 [`chrome-sales-order-import.png`](chrome-sales-order-import.png)。 |

后端测试覆盖多订单多明细、交易单位换算与金额、预览无写入、结果回看、重复上传/重复确认、来源编号内容变更拒绝、修正失败单后重试、错行整单回滚、权限与客户数据范围，以及导入草稿通过原订单确认流程。PostgreSQL 并发测试确认每个来源编号最终只有一张草稿，不覆盖既有订单。

## 可复跑入口

- PostgreSQL：`python docs/uat-evidence/sales-order-import-20261106/run-postgres.py --postgres-bin <本机 PostgreSQL 17 bin 目录>`。脚本自行创建唯一临时集群、端口、账号和测试库，检查集群身份与残留测试库，再清理自身临时目录。
- 前端合成资料：`seed-chrome-visual.py` 只接受本包指定命名的全新临时目录及 SQLite 数据库；生成合成客户、SKU、交易单位和 XLSX 文件。
- Chrome：在前端依赖可用、临时 API/Vite 服务运行后，设置 `CRM_SALES_ORDER_IMPORT_XLSX`，从 `frontend` 目录运行 `node ../docs/uat-evidence/sales-order-import-20261106/chrome-acceptance.mjs`。

未运行本地全量测试，未运行 GitHub Actions，符合本工作包要求。没有连接真实业务库或历史导入实例，没有新增 Issue 或改变既有 Issue 状态。
