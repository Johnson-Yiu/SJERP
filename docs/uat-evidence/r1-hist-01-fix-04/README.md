# R1-HIST-01-FIX-04 验收证据

## 根本原因

1440px 桌面端使用双列分析卡片时，卡片内部可视宽度约为 503px，但 `.analysis-table` 固定 `min-width: 520px`。表格实际 DOM 文本仍是 `17` 和 `27`，但右侧约 17px 超出容器可视区域，截图中因此只看到首位数字。

这不是后端统计问题，也不是测试数据问题。当前 API 仍返回销售 SKU 数量 `4 + 17 = 21`、采购 SKU 数量 `6 + 27 = 33`。

## 修改内容

修改 `frontend/src/views/HistoryOrdersPage.vue`：

- 桌面端表格改为卡片宽度自适应，不再强制 `min-width: 520px`。
- 使用固定比例列宽：名称 52%、人民币金额 30%、数量/订单数 18%。
- 名称列允许安全换行，金额和数量列保持不换行。
- 保留局部横向滚动作为防御性样式，但当前 1440px、700px 实际布局均无表格溢出。
- 未修改后端统计、API、历史数据或权限逻辑。

同时增强 `frontend/browser-tests/historical-orders-fix-03.spec.js`：

- 读取实际 `/api/reports/historical/` 响应。
- 校验销售/采购 SKU 明细数量之和等于 API 汇总数量。
- 校验 API 中 `17`、`27` 与页面表格一致。
- 校验 1440px 下表格 `scrollWidth` 不超过容器可视宽度，数字单元格完整位于容器内。
- 继续覆盖 700px、权限受限页面和页面级横向溢出。

## 测试结果

### 后端

命令：`python manage.py test crm.tests.test_historical_orders --verbosity 1`

退出码 `0`，9/9 通过，Django system check 无问题。日志见 `backend-historical-tests.txt`。

### 前端

- `npm run test:unit`：退出码 `0`，142/142 通过。
- `npm run build`：退出码 `0`，Vite 生产构建成功；仅有已有 chunk size warning。

详情见 `frontend-tests-build.txt`。

### Playwright / 真实浏览器

命令：

```text
npx playwright test browser-tests/historical-orders-fix-03.spec.js --config=playwright.r1a.config.js --reporter=list
```

退出码 `0`，2/2 通过。实际 CSS 视口：700×900、1440×900。

断言结果：

- 1440px 销售 SKU 数量完整显示 `17`。
- 1440px 采购 SKU 数量完整显示 `27`。
- 表格容器没有右侧裁切或额外横向滚动。
- 700px 页面没有页面级横向溢出。
- 权限受限页面仍不显示无权明细。

截图：

- `playwright-desktop.png`
- `playwright-700px.png`
- `playwright-700px-permission-limited.png`

实际 API 响应：`api-current-response.json`。

## 未完成事项

- 本轮未修改后端及数据库，不需要迁移。
- 未触发 GitHub Actions，CI 按项目约定保持 PENDING。
- 未运行与本问题无关的全量回归。
