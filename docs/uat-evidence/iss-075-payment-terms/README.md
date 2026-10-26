# ISS-075 供应商固定付款规则退出常规前端

本目录保存本分支的真实浏览器、隔离数据库和最终测试证据。所有场景运行在独立 SQLite 数据库及开发超级管理员身份下；未连接生产环境，未修改真实业务数据。

## 已确认与已修复

- 已确认缺陷：供应商常规编辑、列表/筛选曾暴露固定付款规则；采购单创建/更换供应商时还会从供应商配置或系统默认值隐式生成 30%/70% 付款快照。
- 已修复：常规供应商前端仅保留付款备注；采购单付款阶段改为本单独立保存，空白时可保存草稿，也可确认下单但不生成虚假应付计划；已填写的本单快照仍按原规则生成计划。
- 兼容修复：无付款阶段的正式采购单仍可登记真实付款流水，但不会伪造付款计划；有显式快照的正式单据和已有付款计划继续按原流程核销。
- 历史误报：ISS-074 的异步继承/取消提醒疑点在本次真实浏览器路径中未重现；本分支移除了该付款条件异步来源，但 ISS-074 不在本轮单独关闭。

## 真实 Chrome 证据

Playwright 使用 Chrome 通道、1440px 桌面及 700px 窄屏，并通过本地 Vite + Django 隔离服务执行：

1. `01-supplier-list-no-fixed-rule.png`：供应商列表无固定付款规则列/筛选，只显示付款备注。
2. `02-new-po-empty-payment-terms.png`：新采购单付款计划为空，显示“未协商时可暂不设置”，没有“使用系统默认”。
3. `03-history-po-payment-plan.png`：历史正式 PO 保留 50%/50%，首付款和尾款均为 CNY 500.00。
4. `04-narrow-supplier-list.png`：700px 窄屏列表无横向溢出，列表可见。

`browser-log.json` 记录 API 状态均成功，`noHorizontalOverflow` 为 `true`。`fixture.json` 记录隔离场景：历史 PO 总额 CNY 1,000.00，计划 CNY 500.00 + CNY 500.00；新空条件 PO 确认后计划数为 0。

## 测试原始日志

- `backend-full-test.log`：Django 全量 932 项，`OK (skipped=13)`。
- `frontend-node-test-full.log`：仓库 `npm run test:unit`，153 项通过。
- `frontend-vitest-valid.log`：有效 Vitest 集合 67 个文件 / 657 项通过；`detail-drawer-typography.spec.js` 属于同一仓库 Node 原生测试，已包含在上面的 Node 全量结果中。
- `frontend-build.log`：Vite 生产构建成功。
- `sqlite-fresh-migrate.log`：全新 SQLite 从初始迁移执行至 `crm.0087_amount_calculation_compatibility` 成功。
- `makemigrations-check.log`：`No changes detected`。
- `django-check.log`：Django system check 无问题。
- `playwright-report.json`：真实 Chrome 回归报告。

## 后续恢复固定规则的边界

数据库字段 `Supplier.payment_terms_config`、后端 `default_payment_terms()` / `validate_payment_terms()`、供应商规则摘要和 `PaymentTermsEditor` 的系统默认能力均保留，未删除迁移或历史记录。未来若业务重新启用，应新增明确的产品/权限开关并只在用户显式选择时复制到采购单快照；不能恢复供应商配置或 30%/70% 的隐式回填，也不能改写已有正式 PO 的快照、付款、应付或银行流水。
