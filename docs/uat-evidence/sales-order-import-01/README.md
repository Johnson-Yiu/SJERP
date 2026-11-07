# SALES-ORDER-IMPORT-01 集成验收

## 集成范围

- 基线：`f9dfcd4c5792c4b0f213aeb0940e7e66efecd33a`（FIRST-RELEASE-CONSOLIDATION-02）。
- 来源：`2bff4790f67b81b35a449f143b8cddb6b24e1821`，其父提交为 `aa15c9ba7584599e918c1dd14723d31e31158b3d`。以摘取并逐项合并方式接入；保留当前主体版本、银行资金导航、多标签页、账号会话隔离、新品提醒和历史预检能力。
- 集成分支：`codex/sunjack-sales-order-import-01`。
- 销售导入结果的重复确认与结果查询共用 `_require_batch_result_access`：必须是已认证的原操作人或权限管理员，且结果内每张订单仍处于操作者当前客户范围。重复预览已存在时先执行这两项校验，再考虑返回原结果。
- 迁移保留 `0110_party_version` 与 `0110_sales_order_import_sources`。主体版本支线经 `0118_merge_party_reminders` 汇合，销售导入 `0110` 依赖 `0109_new_product_reminders`；新增无操作 `0119_merge_sales_order_import` 同时依赖 `0118_merge_party_reminders` 和销售导入 `0110`。未改写已存在迁移。

## 定向验收

| 验收项 | 结果 |
| --- | --- |
| 迁移检查 | `makemigrations --check --dry-run` 显示 `No changes detected`；空库已从 `0001` 安装到 `0119_merge_sales_order_import`。 |
| SQLite 定向后端 | `crm.tests.test_sales_order_import`：7 通过，2 项 PostgreSQL 并发测试按后端条件跳过，0 失败。 |
| PostgreSQL 定向后端 | 临时 PostgreSQL 17.11，9/9 通过，0 跳过；完整空库升级通过。相同预览并发确认只建一张订单并返回同一结果；不同预览竞争同来源编号也只建一张订单。测试库为 0 个遗留 `test_*` 数据库；自有临时集群停止并清理。 |
| 受限账号权限回归 | 首次导入创建订单后，将客户负责人改为其他销售；相同预览再次确认及结果查询均返回 403，响应不含 `orders`、订单编号或订单 ID；订单与批次仍各 1 条。 |
| 未收窄范围重复确认 | 原结果保持一致，订单与批次均未重复创建。 |
| 前端定向测试 | `import-ux.spec.js`、`import-preview-state.spec.js`、`sales-order-import-ux.spec.js` 共 9/9 通过。 |
| 真实 Chrome | 使用已认证隔离 `codex` 超级管理员（`development_superadmin=false`、`rbac_enforcement=false`）完成登录和导入页操作。模板实际下载为 10,116 字节 XLSX；上传合成 XLSX 后预览 3 条明细/2 张订单，创建 1 张含 2 行的草稿，未知 SKU 整单未建；实际点击下载错误 CSV 并检查文件内容、UTF-8 BOM 和 SHA-256。结果查询与提交响应一致。桌面和 390px 视口截图已目视检查，页面宽度不溢出。 |

实际文件和截图：[错误 CSV](browser/sales-order-import-real.spec/sales-order-import-errors.csv)、[上传 XLSX](browser/sales-order-import-real.spec/sales-order-import-input.xlsx)、[下载模板](browser/sales-order-import-real.spec/sales-order-import-template.xlsx)、[桌面截图](browser/sales-order-import-real.spec/sales-order-import-1600.png)、[窄屏截图](browser/sales-order-import-real.spec/sales-order-import-390.png)、[浏览器检查结果](browser/sales-order-import-real.spec/browser-results.json)。

此次只运行与销售导入有关的后端、前端、迁移检查和单一真实 Chrome 用例；本地全量测试及 GitHub Actions 均为 `NOT_RUN`。没有连接真实业务库、没有导入真实资料、没有启用正式 RBAC，也没有改变现有 Issue 状态。

### 下一步

内测/上线前仍按权限设计完成全站鉴权与验收；本次按开发约定保留当前开发超级管理员入口，不开启正式 RBAC。销售订单导入保持创建草稿语义；需要承接旧订单时继续使用历史资料预检与承接流程。
