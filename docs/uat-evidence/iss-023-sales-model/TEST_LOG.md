# ISS-023 测试日志

日期：2026-10-26  
基线：`f12b591cb90d6a5d8ebfedf1c559703377c92d84`  
分支：`codex/iss-023-sales-model`

## 自动化结果

| 检查 | 结果 |
|---|---|
| SKU / Sales Model 后端专项 | `crm.tests.test_sku_commercial_identity`：最终修补后 31/31 OK；覆盖自动生成、自动刷新、人工型号、历史版本、重复身份、报价/订单快照和权限边界 |
| ISS-020 导出专项 | `crm.tests.test_iss020_quote_export`：与 SKU 专项合并运行通过；保存版本 PI/XLSX DTO 与缺失型号识别保持通过 |
| Django 全量回归 | 933 tests，13 skipped，OK（最终条件修补前的全量基线回归）；最终修补后的 SKU 专项 31/31 OK |
| 前端 Node 全量 | `npm run test:unit`：154/154 pass |
| 有效 Vitest | SKU、产品、报价、PI 相关 5 个文件：44/44 pass；`tests/trade-units.spec.js`：4/4 pass |
| 前端生产构建 | `npm run build`：pass；仅有既有大 chunk warning |
| 迁移检查 | 独立 SQLite 全新迁移完成；`python manage.py makemigrations --check --dry-run`：No changes detected |
| Chrome 控制台 | 桌面与 `390×844` 窄屏回归无 error/warning |

## 独立浏览器环境

后端使用隔离 SQLite `sunjack-iss023-browser.sqlite3` 和临时媒体目录，前端代理到 `8102`，Vite 监听 `5192`。种子数据只用于本轮开发验收，不代表生产数据。

真实 Chrome 操作包括：打开历史空型号 SKU、输入并确认人工 `CUSTOM-CHROME`、普通描述字段编辑、列表刷新后的型号核对，以及窄屏布局观察。页面写入仅发生在隔离测试数据库。

## 交付边界

本地自动化和 Chrome 结果不替代生产数据库、真实正式账号、PostgreSQL、反向代理或生产数据抽查。未执行生产部署；不生成或记录任何真实密钥。Issue 保持未关闭，等待独立代码、业务、权限和视觉审查。

