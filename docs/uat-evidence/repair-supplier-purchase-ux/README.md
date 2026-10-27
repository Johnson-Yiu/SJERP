# 供应商与采购浏览器回归修复验收

## 基本信息

- 项目：SUNJACK-ERP
- 任务：供应商和采购浏览器回归 8 项失败排查
- 基线：`054bd82518039a5bc0e0c14234964a14d7fbbfd8`
- 分支：`codex/repair-supplier-purchase-ux`
- Worktree：独立 worktree
- 结论：代码未发现需要修改的产品缺陷；修正了与 ISS-075 现行契约不一致的过时浏览器断言。
- 共享 `docs/PROJECT_ISSUES.md`、`docs/PROJECT_PHASES.md` 未修改。

## 失败归因

本轮对照了当前源码、ISS-075 验收记录和实际 API 请求，没有重新引入供应商固定付款规则。

| 失败 | 结论 | 依据与处理 |
| --- | --- | --- |
| supplier-ux 三个视口找不到 `.terms-description` | 过时测试 | 当前供应商表单使用付款条款备注；`ResourcePage.vue`、`EntityDetailModal.vue` 和 `_supplier_context` 均不再提供固定付款规则描述。断言改为验证付款备注及“不生成付款计划”提示。 |
| `payment_terms_config.map` 为 undefined | 过时测试 | ISS-075 已将供应商固定规则退出常规前端。测试不再构造或检查供应商固定规则 payload；后端历史字段仍保留兼容性。 |
| 找不到“比例 % 1”输入框 | 过时测试 | 供应商编辑器不再有比例输入框。采购单内的 `PaymentTermsEditor` 仍只处理本次采购单付款计划，未被删除或重新暴露到供应商页面。 |
| `termsMode=custom&page=2` 预期 1 行、实际 25 行 | 过时测试 | 当前供应商列表支持搜索、供应类别等现行筛选，不再声明固定付款规则筛选。测试改用现行 `supplyCategory` 筛选，并验证分页返回和回到采购页后的现行付款计划提示。 |
| ISS-022 真实场景 120 秒超时 | 环境/运行隔离问题，非产品缺陷 | 首次复现时同一证据端口存在多个遗留 Django 监听器，且请求落入混合数据库，观察到 `/api/purchase-orders/` 返回 `count:4` 而不是新库预期的空集。停止专用端口进程树、换用新 SQLite 并以单一服务重跑后通过。 |
| ISS-075 真实场景 120 秒超时 | 环境/运行隔离问题，非产品缺陷 | 同样清理专用端口的旧进程并关闭 Vite 复用；使用单一 Django 服务、独立 SQLite 和 Chrome 重跑后通过。没有增加测试超时。 |

## 自动化结果

以下命令均在本分支执行，浏览器使用真实 Chrome channel，未触发 GitHub Actions：

| 验证 | 结果 |
| --- | --- |
| `supplier-ux.spec.js` | 8 passed，51.0 s |
| `iss022-moq-real.spec.js` | 1 passed，15.3 s；独立 SQLite |
| `iss075-payment-terms-real.spec.js` | 1 passed，18.6 s；独立 SQLite |
| `node --test src/views/PurchaseOrderPage.test.js` | 13 passed |
| `npm run test:unit` | 156 passed，0 failed |
| 相关 Django 测试：`test_purchase_moq test_purchase_payment_terms test_supplier_terms_display test_procurement` | 35 passed，0 failed |
| `python manage.py check` | 通过，无 system check 问题 |
| `python manage.py makemigrations --check --dry-run` | 通过，No changes detected |
| `npm run build` | 通过；仅有既存的大 chunk 警告，无构建失败 |

ISS-022 的真实流程仍覆盖 MOQ 草稿、低 MOQ 例外理由、正式下单二次核验、例外持久化和状态筛选。ISS-075 的真实流程仍覆盖供应商付款备注、空付款计划正式采购单、历史付款计划和窄屏供应商列表。没有改变 MOQ 例外审批、正式下单二次核验、历史付款计划或供应商备注规则。

## 真实 Chrome 视觉验收

已使用独立本地服务和真实 Chrome 检查桌面页面：

- 供应商列表：保留搜索、供应类别筛选、重置和刷新；不显示固定付款规则编辑器。
- 供应商详情：显示“付款条款说明（备注）”及“仅供沟通参考，不生成付款计划”；不显示“系统执行付款规则”。
- 采购管理：列表、状态筛选、待处理筛选和新建采购单入口可用。

窄屏截图通过 Chrome Playwright 回归生成，并检查 `noHorizontalOverflow: true`。截图和请求日志如下：

### ISS-022

- [普通纸箱/等于 MOQ](iss022/01-equal-moq-draft.png)
- [MOQ 详情](iss022/02-equal-moq-detail.png)
- [正式下单](iss022/03-equal-moq-ordered.png)
- [低 MOQ 转换提示](iss022/04-low-moq-conversion-warning.png)
- [MOQ 例外对话框](iss022/05-low-moq-exception-dialog.png)
- [取消后保留草稿](iss022/06-cancel-keeps-draft.png)
- [例外已持久化](iss022/07-moq-exception-persisted.png)
- [已下单筛选](iss022/08-ordered-filter.png)
- [窄屏采购列表](iss022/09-narrow-purchase-list.png)
- [浏览器请求与布局日志](iss022/browser-log.json)
- [测试 fixture](iss022/fixture.json)
- [Playwright 结果](iss022/playwright-report.json)

### ISS-075

- [桌面供应商列表（无固定规则）](iss075/01-supplier-list-no-fixed-rule.png)
- [新采购单为空付款计划](iss075/02-new-po-empty-payment-terms.png)
- [历史采购单付款计划](iss075/03-history-po-payment-plan.png)
- [窄屏供应商列表](iss075/04-narrow-supplier-list.png)
- [浏览器请求与布局日志](iss075/browser-log.json)
- [测试 fixture](iss075/fixture.json)
- [Playwright 结果](iss075/playwright-report.json)

## 改动与后续事项

- 改动文件：`frontend/browser-tests/supplier-ux.spec.js`。
- 未修改产品业务代码、数据库迁移、权限逻辑或共享开发台账。
- 未发现当前代码可证实的产品缺陷，因此没有新增延期缺陷记录。
- 本地测试需要确保证据端口只有一个 Django 服务，且 Playwright 不复用旧 Vite 进程；后续若继续扩展回归，可将端口清理和 fresh SQLite 初始化固化到测试入口。该项属于测试环境可靠性改进，不影响本轮业务验收。
- 生产服务器、Nginx、真实 PostgreSQL 和部署容量告警不在本任务范围内，未宣称已验证。

## 交付限制

所有本轮 commit message 均包含 `[skip ci]`。本分支不合并 master、不关闭 Issue、不部署。
