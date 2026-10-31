# R1-ISS007-SKU-QUOTE-IMAGE-UAT

本轮在固定基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c` 上，以独立分支 `codex/r1-iss007-image-snapshot-uat-20261031` 完成 SKU 图片及报价历史图片快照 UAT。没有修改产品业务逻辑、正式 SKU、报价或订单数据；ISS-007 仍为 `NEEDS_VERIFICATION`，等待独立审查。

## 隔离方式与结果

- 使用项目锁定的 `backend/requirements.lock`，`pip check` 无依赖冲突。
- 使用隔离浏览器运行器、真实安装的 Google Chrome、临时 SQLite 和同一临时根目录下的独立 `MEDIA_ROOT`。运行器在测试前核实数据库/媒体路径和运行身份，迁移全新数据库，结束后停止服务并清理本轮有标记的临时根目录。
- 浏览器运行期间仅创建合成客户、产品、SKU、报价、订单和图片；运行器记录的数据库前后快照均标记 `synthetic_records_only: true`。开发环境继续遵循现有开发超级管理员规则，没有开启正式 RBAC。
- 真实 Chrome 视口：桌面 `1440×1000`，窄屏 `390×844`。
- 最终浏览器回归：1 项通过；前期 9 次运行失败均为测试夹具/选择器/断言迭代，不计为通过；最终通过日志为 [`chrome-uat.log`](chrome-uat.log)。失败尝试日志仅用于本地调试，没有纳入验收材料。
- Django 定向回归：9 项通过；Node 运行器回归：14 项通过；锁定环境 `pip check` 通过。命令及完整输出分别见 [`backend-tests.log`](backend-tests.log)、[`frontend-tests.log`](frontend-tests.log)、[`pip-check.log`](pip-check.log)。

## 验收结果

| 场景 | 实际结果 |
| --- | --- |
| SKU 图片上传及缩略图 | Chrome UI 上传成功；缩略图请求为 WebP 并显示。原图 SHA256：`905113a2c9f67b724fa4789e9b419f02982ca7ba916473f9972f3ffaeb426fb2`。 |
| 替换 SKU 图片 | 替换请求 HTTP 200；替换图 SHA256：`4991af95c7f5acaed2e13ea94ebf0733dd077d7e0f14cac519c3e97e798f3e1a`，SKU 当前媒体引用从原图改为替换图。 |
| 无效图片 | 伪造 PNG 上传 HTTP 400；UI 显示上传失败；SKU 仍保留原图 SHA，随后可成功重试有效图片。 |
| 正式报价历史快照 | SKU 图片替换后，已接受正式报价的 `QuoteItem.image_snapshot` 路径和 SHA 未变化；PI 预览仍显示原始红图。 |
| 确认订单 | 订单状态仍为 `confirmed`，继续关联已接受报价；关联报价图片快照 SHA 仍为原始图。当前 `OrderItem` 没有独立图片快照字段，因此本轮证明的是订单沿用所关联正式报价的历史快照，不声称订单行另存了图片副本。 |
| 报价/PI Excel 导出 | 实际下载 XLSX（11,570 bytes），工作表为 `PI`；检查 ZIP 内嵌图片 SHA 与原始报价快照一致。文件见 [`iss007-formal-quote-pi.xlsx`](browser/iss007-image-snapshot-real.spec/exports/iss007-formal-quote-pi.xlsx)。 |
| 私有图片访问与权限 | 真实 Chrome 通过受保护媒体 API 读取授权图片。定向 RBAC API 测试覆盖有权访问、SKU-only 角色读取历史报价图片拒绝（404）、无客户范围员工拒绝（404）；测试方法见 `test_functional_rbac.FunctionalRBACApiTests.test_sku_and_historical_quote_images_use_protected_media_permissions`。未将开发超级管理员会话误报为匿名拒绝。 |
| 历史图片文件缺失 | 合成历史引用对应文件确实不存在；媒体请求 HTTP 404，PI 页面仍渲染且没有 JavaScript `pageerror`。当前预览显示浏览器默认破图占位，本轮仅验收“不崩溃”，没有扩大为 UI 修补。 |
| 数据库一致性 | 前后记录数一致：Customer 1、Product 1、SKU 1、Quote 2、QuoteItem 2、Order 1、OrderItem 1。只有 SKU 当前图路径/SHA 改变；正式报价快照和确认订单所关联的报价快照均保持原始 SHA。 |

数据库逐字段证据：[`database-before.json`](browser/iss007-image-snapshot-real.spec/database-before.json)、[`database-after.json`](browser/iss007-image-snapshot-real.spec/database-after.json)；汇总：[`browser-results.json`](browser/iss007-image-snapshot-real.spec/browser-results.json)。隔离 SQLite 和媒体目录在成功结束时由运行器清理；快照保存了记录数、引用路径和文件 SHA，不接触真实业务库。

## 截图

- 桌面 SKU 上传完成：[sku-image-upload-desktop-1440.png](browser/iss007-image-snapshot-real.spec/screenshots/sku-image-upload-desktop-1440.png)
- 桌面 PI 原图快照：[quote-pi-original-snapshot-desktop-1440.png](browser/iss007-image-snapshot-real.spec/screenshots/quote-pi-original-snapshot-desktop-1440.png)
- 桌面 SKU 替换后：[sku-image-replaced-desktop-1440.png](browser/iss007-image-snapshot-real.spec/screenshots/sku-image-replaced-desktop-1440.png)
- 桌面替换后仍显示历史报价图：[quote-pi-after-sku-replacement-desktop-1440.png](browser/iss007-image-snapshot-real.spec/screenshots/quote-pi-after-sku-replacement-desktop-1440.png)
- 390px SKU：[sku-image-replaced-mobile-390.png](browser/iss007-image-snapshot-real.spec/screenshots/sku-image-replaced-mobile-390.png)
- 390px 历史 PI：[quote-pi-history-mobile-390.png](browser/iss007-image-snapshot-real.spec/screenshots/quote-pi-history-mobile-390.png)
- 390px 缺失历史图：[missing-history-image-mobile-390.png](browser/iss007-image-snapshot-real.spec/screenshots/missing-history-image-mobile-390.png)

窄屏运行断言 `document.documentElement.scrollWidth <= window.innerWidth` 通过。缺失图片截图中的原生破图图标是实际观察到的占位表现，页面及脚本均未崩溃。

## 测试命令

```powershell
# 独立真实 Chrome + 临时 SQLite / MEDIA_ROOT
$env:PLAYWRIGHT_CHANNEL = 'chrome'
npm run test:browser:isolated -- --business-test iss007-image-snapshot-real.spec.js

# 后端：requirements.lock 安装的隔离虚拟环境；测试数据库由 Django 在测试运行时创建
python manage.py test `
  crm.tests.test_sku_images `
  crm.tests.test_quotes.QuoteApiTests.test_saved_pi_uses_buyer_and_sku_snapshots_after_source_records_change `
  crm.tests.test_quotes.QuoteApiTests.test_pi_data_returns_snapshots_totals_payment_splits_and_product_image_urls `
  crm.tests.test_quotes.QuoteApiTests.test_sku_image_upload_rejects_non_image_mime_type `
  crm.tests.test_quotes.QuoteApiTests.test_sku_image_can_be_cleared_after_upload `
  crm.tests.test_iss020_quote_export.ISS020QuoteExportConsistencyTests.test_formal_export_embeds_the_saved_image_snapshot `
  crm.tests.test_functional_rbac.FunctionalRBACApiTests.test_sku_and_historical_quote_images_use_protected_media_permissions

# 前端隔离运行器自测
node --test frontend/infrastructure-tests/runner-validation.test.mjs
```

没有触发 GitHub Actions，没有创建 PR、合并 master、部署或启用正式 RBAC。真实生产反向代理、对象存储/持久卷 ACL 仍按 ISS-017 部署验收边界待验；本报告只证明本地代码路径与隔离测试。
