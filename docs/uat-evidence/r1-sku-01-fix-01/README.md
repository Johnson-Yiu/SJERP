# R1-SKU-01-FIX-01 验收证据

基线：`codex/r1-sku-01 @ 57d8c2df573b11621a940a756ef7ed34531e7af6`

本目录由真实 Google Chrome 通道运行 Playwright 生成，截图不是静态 mock 图片。专项测试 fixture 只拦截现有 `/api/` 请求，不替代前端真实页面、路由、组件挂载和下载行为。

## 实际执行结果

- `npm run test:unit`：141 passed，0 failed。
- `npx playwright test browser-tests/r1-sku-01-fix-01.spec.js --reporter=line`：6 passed，0 failed。
- `npx playwright test --reporter=line`：163 passed，0 failed，真实 Chrome 通道，约 6.7 分钟。
- `python backend/manage.py check`：通过。
- `python backend/manage.py makemigrations crm --check --dry-run`：`No changes detected in app 'crm'`。
- 后端回归：216 tests，`OK`。
- `npm run build`：通过；仅保留既有大 chunk warning。

## 专项流程覆盖

- 报价列表有风险：集中展示风险，取消不下载，下一次导出重新执行风险检查。
- 风险检查服务不可用：明确提示无法核实，只有主动确认后才下载。
- Excel 导出失败：显示失败状态，重新导出再次经过风险检查。
- 新建报价和修订报价：保存成功后在风险决策完成前保持编辑器挂载；取消保留已保存报价，确认后下载。
- SKU 成本：未保存成本修改不得核实；零价格或未知币种不得核实；SupplierSKU 同类无效状态不得核实。
- 销售账号：风险提示只显示通用风险，不显示采购金额；SKU 页面采购金额显示为“采购价已隐藏”。

## 截图

- `quote-risk-confirmation.png`：报价风险确认与取消入口。
- `quote-risk-unavailable.png`：风险服务不可用时的主动确认提示。
- `quote-export-failed-retry.png`：Excel 下载失败后的页面重试提示。
- `quote-save-risk-create.png`：新建报价保存成功后风险提示仍覆盖在编辑器之上。
- `sku-unsaved-cost-blocked.png`：未保存 SKU 成本修改时阻止核实。
- `sku-invalid-cost-blocked.png`：零采购参考价/未知币种时阻止核实。
- `quote-risk-sales-no-cost.png`：销售账号可见通用风险但不含采购金额。
- `sku-purchase-price-hidden.png`：无采购查看权限时采购金额脱敏。

详细命令与末尾输出见 [`execution-log.md`](./execution-log.md)。
