# R1-REPAIR-03 独立验收记录

日期：2026-10-28（Asia/Shanghai）  
基线：`054bd82518039a5bc0e0c14234964a14d7fbbfd8`  
分支：`codex/repair-history-recipient-typography`

## 结论

四项既有失败均已完成根因核对和最小修复。历史订单代码本身已经包含 `.analysis-detail-grid`；失败来自浏览器验收连接到共享/过期的前端或后端服务，导致明细为空或响应不是当前 API。ISS-029 邮箱差异来自复用的旧证据数据库联系人已被改成 `uat-alpha@example.test`，而测试固定期待合成夹具的 `primary@example.com`；报价快照后端逻辑没有被证明有缺陷。字体失败是当前源文件真实存在的 `11px`。

本轮新增独立 Playwright 配置，显式使用当前 worktree 的 Vite、临时后端端口和隔离 SQLite；历史分析测试保留原有权限、明细、数量守恒和无横向溢出断言。`fix-03` 的数量可见性断言改为只检查 SKU 明细卡，避免把同一销售/采购数量再次从产品分类卡计入；没有删除验收标准或改变业务预期。

## 最小修改

- `OrderDetailModal.vue` 和 `QuoteDetailModal.vue` 的主体参考文案从硬编码 `11px` 改为现行 `var(--text-caption)`。
- 历史订单两个浏览器测试和 ISS-029 测试支持显式 `R1_REPAIR_EVIDENCE_DIR`，默认路径和原有调用兼容。
- 新增 `playwright.r1-repair-03.config.js`：Chrome channel、独立前端端口、明确 API 代理端口、禁止复用旧服务。
- 新增合成数据准备脚本和 HTTP 证据脚本；数据库文件位于用户目录的隔离临时目录，不属于仓库、不含生产数据。

未修改报价序列化、历史订单权限、历史快照、PI 或 XLSX 生成逻辑；未修改 `docs/PROJECT_ISSUES.md`、`docs/PROJECT_PHASES.md`。

## 复现证据

在修复前从本分支实际运行原始字体测试，稳定失败于：`OrderDetailModal.vue` 出现未预期的 `font-size:11px`。原始 `historical-orders-fix-03` 在合成销售和采购共用同一 SKU 的有效数据上还会把 SKU、产品分类两个表的数量全部抓取，得到 `17,17,27,27`；这确认断言选择器过宽。历史两个“找不到明细/HTML JSON 解析失败”与集成报告记录的共享服务错配一致，而当前页面源模板与当前后端契约核对均正常。

修复后的隔离服务证据：

- `http-evidence.json`：历史报表和当前开发操作人接口均为 HTTP 200、`Content-Type: application/json`，报表销售数量 17、采购数量 27。
- `api-evidence.json`：ISS-029 的非法邮箱 HTTP 400、版本 A HTTP 201、版本 B 空邮箱 HTTP 201，以及主档修改后的版本读取。
- `export-reconciliation.json`：用 openpyxl 将三个实际下载 XLSX 的 PI 单元格与隔离数据库版本字段逐项核对，并记录 SHA-256。
- `fixture.json`：隔离 SQLite、合成客户/联系人/SKU 与历史订单主键。

## 浏览器截图

以下文件由本 worktree 的 Chrome channel Playwright 及 Chrome 视觉核对生成：

- `playwright-700px.png`：历史分析窄屏明细。
- `playwright-desktop.png`：历史分析桌面明细。
- `playwright-700px-permission-limited.png`：受限权限下不显示无权明细。
- `chrome-version-a-saved-pi-1440.png`：版本 A 保存 PI。
- `chrome-version-b-editor-1440.png`：版本 B 编辑器，邮箱显式留空。
- `chrome-version-b-saved-pi-1440.png`、`chrome-version-b-saved-pi-700.png`：版本 B 保存 PI 桌面/窄屏。
- `chrome-order-detail-1440.png`：订单详情抽屉桌面截图，核对修复后的共享字体层级。

Chrome 视觉核对确认历史经营分析标题、销售/采购明细、SKU 数量及窄屏布局可见；报价编辑器保留版本字段和显式空邮箱。

## 实际命令

后端使用本 worktree 的 Python 环境与新 SQLite：

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test crm.tests.test_historical_orders crm.tests.test_quotes
```

前端与浏览器：

```text
node --test tests/detail-drawer-typography.spec.js
npx playwright test browser-tests/historical-orders-fix-02.spec.js browser-tests/historical-orders-fix-03.spec.js --config=playwright.r1-repair-03.config.js --reporter=list
npx playwright test browser-tests/iss029-recipient-snapshot.spec.js --config=playwright.r1-repair-03.config.js --reporter=list
npm run test:unit
npm run build
```

最终结果：字体定向测试通过；最终隔离 Chrome 回归 5 项全部通过（历史订单 4 项、ISS-029 1 项）；后端 75 项、Node 单元 156 项、Vitest 661 项、生产构建、Django check 和迁移检查通过。原始日志：`browser-regression.log`、`backend-targeted.log`、`frontend-unit.log`、`frontend-vitest.log`、`frontend-build.log`、`django-check-migrations.log`。

## 边界与未完成事项

- 仅使用隔离 SQLite，未连接 PostgreSQL 或生产服务。
- 未运行 GitHub Actions、未部署、未合并 master、未关闭 Issue。
- Chrome 视觉证据是开发身份下的本地合成数据验证，不等同于真实员工权限或生产环境验收。
