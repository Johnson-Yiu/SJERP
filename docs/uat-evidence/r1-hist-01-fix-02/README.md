# R1-HIST-01-FIX-02 验收记录

## 实现范围

本轮仅补齐历史经营分析前端明细展示和窄屏验收，不修改历史资金隔离、后端权限或历史成本逻辑。

历史销售和历史采购分别按接口返回的数据展示：客户/供应商、国家/地区、SKU、产品分类。每个表格显示名称、人民币折算金额及接口提供的订单数或数量。后端已经按权限过滤的空数组不会被前端补造为数据；无可见维度时显示“当前权限下暂无可展示的历史明细”。

窄屏表格保留合理的最小内容宽度，并放在局部 `.analysis-table-wrap` 滚动容器内；页面本身不产生横向滚动。

## 实际测试命令与结果

工作目录：`frontend/`。Vite 测试服务器使用 `VITE_API_PROXY_PORT=8102` 指向本分支后端，地址 `http://127.0.0.1:5196`。

| 命令 | 退出码与结果 |
|---|---|
| `npm run test:unit` | exit 0；142 tests，全部通过 |
| `npm run build` | exit 0；Vite production build 成功；仅有既存 chunk size warning |
| `python manage.py test crm.tests.test_historical_orders --verbosity 1` | exit 0；9 tests，全部通过 |
| `npx playwright test browser-tests/historical-orders-fix-02.spec.js --config=playwright.r1a.config.js --reporter=list` | exit 0；2 tests passed，5.4s |

本轮只修改前端页面、前端测试、Playwright 验收测试和证据文件；上一提交已完成的 SQLite 全量 777 tests（13 skipped）及资金/权限回归未被后端改动影响。

## Playwright 真实浏览器验收

Playwright 使用真实 Chromium，实际调用 `page.setViewportSize()`：

- `width: 700, height: 900`：历史销售与采购明细可见，SKU/客户/供应商表格可操作，页面 `scrollWidth <= 700`；表格在局部容器内滚动。
- `width: 1440, height: 900`：桌面表单、汇总卡片、明细表格和历史订单列表正常，无页面横向溢出。
- 权限受限页面：使用真实浏览器加载受控的销售只读权限响应，隐藏采购页签和无权明细；销售汇总仍可显示，页面不空白，并显示无可展示明细的中性提示。该截图用于前端权限表现验证，正式后端权限仍由既有 RBAC 定向测试覆盖。

截图：

- [700px 窄屏明细](./playwright-700px.png)
- [1440px 桌面明细](./playwright-desktop.png)
- [700px 权限受限页面](./playwright-700px-permission-limited.png)

## 未完成事项

- PostgreSQL 本轮未执行；本机没有 PostgreSQL 连接配置。
- GitHub Actions 继续按项目额度策略保持 `CI PENDING`，未触发无意义运行。
- 未合并 master，未修改 ISS-121 或其他开发分支。
