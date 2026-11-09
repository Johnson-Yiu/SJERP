# RELEASE-INTEGRATION-REPAIR-01 验收记录

2026-11-09 · 分支 `codex/release-integration-repair-01` · 共同基线 `c90cacaa99a468d92dd61c41437834c5d8acb094`。业务候选 `019367baa389c2a73ea2d8c58162313e4868fcca`；其后的回归脚本和证据变动不改变业务源码或迁移。状态：集成完成，定向验收通过，仍有发布验收缺项。

| 来源 | 保留和接入的能力 | 本轮核验 |
| --- | --- | --- |
| c90 | 应用主壳、菜单、工作区路由、登录与退出、会话失效、财务 CSV 请求隔离、销售订单导入与历史预检 | Chrome 使用真实 codex 登录；退出、失效、跨账号与迟到响应；销售导入丢响应恢复同批次；旧预检、旧下载响应不覆盖新文件 |
| A `568105bd`、`fed49cd`、`d8264390` | 数字滚轮防误改；失活工作区的 Teleport 移回隐藏且不可交互的面板，恢复激活时保留草稿；库存未保存保护与原提交重放；SKU 成本币种、核实、报价与订单成本快照、风险提示；采购现存、已占用、可用、在途与供应商历史参考 | 数字输入可键盘和方向键修改、滚轮不改值；切换工作区弹层隐藏并保留内容；库存网络中断重放返回同一登记；采购库存、SKU 及报价实际 XLSX |
| B `bfd217ae5c8ca8dccb734af842564bd46111d739` | 结构化收款、现金与手续费拆分、付款、退款与银行退回、同请求幂等、审计；按订单日期统计扣除更正后的有效非现金抵减 | 正式合流后在 Chrome 验证记账、结汇、退款额度、抹零更正；API、下钻和 CSV 数值同口径；PG17 并发定向通过 |
| C `2225173b1bbda1ded0a0ce0a5f1b9e72a014f7fb` | 附件授权下载与内容验证、恢复空媒体目录、清单核对与 PostgreSQL 演练适配 | 保留 [C 独立证据](../attachments-recovery-hardening-01/README.md)；本轮未重做目标环境恢复演练 |
| D `ed1a554e09d8f49c9b0e07b96921b863b2f8e4f7` | 导入结果恢复、历史预检、历史承接入口、国家和分类快照统计，未知历史不回填 | 合流后预检、历史报表与导入恢复；历史财务事实与新增财务规则的全链路仍待核验 |

## 迁移与定向测试

- `crm.0128_merge_release_integration` 连接 A 的 `0123_sku_cost_snapshots`、D 的 `0123_history_reporting_snapshots` 与 B 的 `0127_finance_bank_return_allocation`，保留 c978 与 c90 各自的迁移身份。
- 新空库、原始 c978 至 0120、原始 c90 至 0122，均在 PostgreSQL 17 使用同一业务候选升级到 0128。合成样本核对现金拆分、三项约束、抹零、更正、凭证关联、缺参考汇率及历史快照。复现命令、样本边界和 PG 定向 9/9 见 [PostgreSQL 记录](POSTGRES-019367-EVIDENCE.md)。
- `python backend/test_support/release_integration_sqlite_probe.py`：三入口均通过；额外核对合成旧审计记录、旧成本金额、国家快照及未知成本币种和分类保留为空。
- `python manage.py makemigrations --check --dry-run`：无遗漏；隔离 Chrome 运行器的 Django 检查和空库迁移检查通过。
- `python manage.py test crm.tests.test_inventory_reference crm.tests.test_sku_cost_verification crm.tests.test_inventory_finance_idempotency crm.tests.test_finance_receipt_convergence crm.tests.test_history_import_preflight crm.tests.test_reporting --noinput`：SQLite 88 通过、6 跳过。成本金额输入和非零抵减同口径改动后，重跑 SKU 与非零抵减组合共 10 项通过。
- `node --test frontend/src/views/SKUPage.test.js frontend/src/components/QuoteEditorModal.test.js frontend/src/components/QuoteDetailModal.test.js frontend/src/views/DocumentPage.test.js frontend/src/views/FinanceDashboardPage.test.js`：对应两次定向运行 37+2 项通过。
- 在 frontend 用 Vitest 运行 `src/utils/numericWheelGuard.test.js`、`tests/workspace-manager.spec.js`、`tests/sales-order-import-ux.spec.js`、`tests/history-takeover.spec.js`、`src/components/CashEventEntryForm.spec.js`、`src/components/PurchasePaymentModal.spec.js`：40 项通过。生产构建 `npm run build` 通过。

## 真实 Chrome 与实际下载

使用已配置的本机 `codex` 测试超管，真实会话且开发身份关闭；测试库与媒体目录独立。设置 `ISOLATED_CODEX_TEST_SUPERADMIN=1`、`ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT=docs/uat-evidence/release-integration-repair-01`，通过本机 Git 忽略的凭据配置运行：

```text
node frontend/scripts/run-isolated-browser-tests.mjs --business-test sales-order-import-real.spec.js
node frontend/scripts/run-isolated-browser-tests.mjs --business-test workspace-integration-real.spec.js
node frontend/scripts/run-isolated-browser-tests.mjs --business-test quote-editor-mobile-actions.spec.js
```

结果依次为 7/7、4/4、1/1。较早尝试曾遇到浏览器依赖缺失、登录页等待、旧文案定位和会话共享问题；补齐依赖、更新断言和调整运行顺序后通过，原版本证据未覆盖。

- 财务概览与历史预检：1366×768、1440×900、390px，截图在 [导入和财务浏览器证据](browser/sales-order-import-real.spec/)；历史预检宽表内部可横向滚动，下载按钮可达。财务另保存了结汇、拒绝超额退款和更正结果截图。
- [报价浏览器证据](browser/quote-editor-mobile-actions.spec/)含正式报价 Excel 下载、风险确认与窄屏截图。[下载清单](download-manifest.json)列出正式报价、导入模板、财务 CSV、历史预检 CSV 及导入错误 CSV 的实际文件与校验值。
- [工作区浏览器证据](browser/workspace-integration-real.spec/)包含退出和会话失效截图。[会话身份](browser/codex-identity.json)不包含凭据。

## 仍待验收

- 125% Chrome 原生缩放、财务与历史承接页面的长客户名／长单号及完整多明细组合尚无专项证据。完整打印与分页继续按原范围延期。
- PostgreSQL 迁移使用合成样本，未覆盖真实凭证文件与升级前审计全组合；审计保留已在 SQLite 探针核对。D 的历史财务接续使用既有财务关闭服务，但跨包所有历史资金类型的完整验收仍待补齐。未进行生产环境、正式附件恢复或正式数据导入验证。
- 库存重试验证覆盖同一表单内的未知结果及工作区切换；刷新触发现有未保存保护。强制离开后重新打开表单恢复该笔未知提交不在本轮证据中。
- 本地全量套件、GitHub Actions、正式部署：`NOT_RUN`。
