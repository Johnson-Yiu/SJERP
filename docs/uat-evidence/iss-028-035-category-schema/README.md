# ISS-028 / ISS-035 分类与 SKU 模板隔离验收

## 验收结论

| Issue | 结论 | 依据 / 遗留说明 |
|---|---|---|
| ISS-028 | **PASS** | 根分类原先无法直接选中已在真实 Chrome 中复现；产品编辑器增加“选择”操作后，根分类保存、根/子分类筛选及子类属性继承均通过隔离 API、数据库和浏览器核验。 |
| ISS-035 | **PASS** | 分类模板规则变化并刷新后，既有已发布 SKU 方案、SKU 身份及报价/订单快照未被改写；普通 SKU 描述保存可重开读取；模板修改后新建产品采用新模板。 |

两项结果分别记录，不合并 Issue 状态。窄屏（390×844）真实页面截图显示应用全局侧栏覆盖了部分内容，虽然页面没有横向溢出；这是本轮未修改的窄屏布局遗留项，不影响本次 API/数据保持断言，但仍需独立 UX 验收。未据此扩大到全局导航改造。

## 基线、历史失败条件与改动边界

- 固定基线：`bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`
- 分支：`codex/verify-iss028-035-category-schema`
- 历史 ISS-028 失败记录见 [`真实用户E2E-UAT-20260923.md`](../../真实用户E2E-UAT-20260923.md)：第 73–75 行记录选择父分类“商业照明”后产品列表显示“未分类”，而子分类产品显示正常。
- ISS-035 历史问题见 [`Phase4-生产化加固审计与实施计划.md`](../../Phase4-生产化加固审计与实施计划.md) 第 279 行：已发布 SKU schema 与分类模板变更提示不一致。历史材料没有记录完整复现步骤；本轮据现行规则验证模板改动不得静默改写已发布 SKU。
- 真实复现后，仅调整 `frontend/src/views/ProductPage.vue` 分类选择器：分支分类仍可点击展开，并增加独立“选择”按钮以直接归属当前层级。未改 SKU 编码生成规则、后端业务逻辑、权限或历史数据。

## 隔离环境与可复现命令

所有浏览器数据均为合成资料，运行于 R1-REPAIR-06 隔离启动器创建的 SQLite、MEDIA_ROOT 和服务端口。未连接用户业务库；正式 RBAC 未启用。审计日志在该隔离环境中按启动配置关闭，因此本报告不把审计日志作为通过证据。

在仓库根目录的 `frontend` 目录执行：

```powershell
npm run test:browser:isolated:verify
$env:ISS028_035_EVIDENCE_DIR = 'D:\Codex项目\森爵照明管理系统\.worktrees\iss028-035-category-schema\docs\uat-evidence\iss-028-035-category-schema'
$env:PLAYWRIGHT_CHANNEL = 'chrome'
npm run test:browser:isolated -- --business-test iss028-035-category-schema.spec.js
npm run test:unit
npx --no-install vitest run tests/product-master-ux.spec.js tests/sku-ux.spec.js --environment jsdom
npm run build
```

浏览器实跑结果：2 tests passed。隔离运行 ID `46000467-930c-4865-bc61-ac4dda0e1f14`；API/Vite 端口分别为 `9028` / `9029`；SQLite 位于 `C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-repair-06-gUVHUP\db.sqlite3`，媒体目录同一运行临时根下。启动器在运行前核验直接 API、Vite `/api` 代理、runId/token、实际 SQLite 路径、MEDIA_ROOT 与迁移；运行结束只清理该次临时资源。

聚焦 Django 回归命令（独立临时目录、SQLite、MEDIA_ROOT）：

```powershell
python docs/uat-evidence/iss-028-035-category-schema/run_isolated_django_tests.py
```

结果：56 tests passed；迁移从空隔离测试数据库全部应用，Django system check 无问题。此次 `manage.py test` 使用 Django SQLite 测试运行器的共享内存测试库；隔离脚本仍显式设置独立临时数据库身份和媒体目录，并在结束时仅清理自己的临时根。

## 场景与原始证据

| 场景 | 结果 | 证据 |
|---|---|---|
| ISS-028 修复前：点击带子类的根分类仅展开，不能将产品归属到根分类 | 真实 Chrome 复现 | [`00-iss028-root-category-selection-before-fix.png`](00-iss028-root-category-selection-before-fix.png) |
| ISS-028 修复后：在产品编辑器直接选择根分类并保存 | 通过；GET 产品 API 返回根分类 ID 与名称 | [`01-iss028-root-category-assignment-after-fix.png`](01-iss028-root-category-assignment-after-fix.png)、[`iss028-http-results.json`](iss028-http-results.json) |
| ISS-028 根分类筛选 | 通过；根分类结果包含归属根类产品，未显示“未分类” | [`02-iss028-root-category-filter.png`](02-iss028-root-category-filter.png) |
| ISS-028 子分类筛选 | 通过；只返回对应子类产品 | [`03-iss028-child-category-filter.png`](03-iss028-child-category-filter.png) |
| ISS-028 根属性对子分类的继承及只读状态 | 通过；API `effective_attributes` 标记 inherited/source，浏览器继承开关禁用 | [`04-iss028-inherited-attributes-desktop.png`](04-iss028-inherited-attributes-desktop.png)、[`05-iss028-inherited-attributes-narrow.png`](05-iss028-inherited-attributes-narrow.png) |
| ISS-035 分类模板规则变更、重开与刷新 | 通过；规则持久化，新模板对既有已发布方案显示不自动跟随的提示 | [`06-iss035-category-template-changed-desktop.png`](06-iss035-category-template-changed-desktop.png)、[`07-iss035-category-template-changed-narrow.png`](07-iss035-category-template-changed-narrow.png) |
| ISS-035 已发布 SKU 普通保存及重开 | 通过；中文描述保存后可重开读取，SKU 编码、销售型号和参数保持不变 | [`08-iss035-ordinary-sku-save.png`](08-iss035-ordinary-sku-save.png)、[`09-iss035-reopened-sku-after-save.png`](09-iss035-reopened-sku-after-save.png) |

窄屏浏览器尺寸及页面宽度记录见 [`iss028-browser-layout.json`](iss028-browser-layout.json) 和 [`iss035-browser-layout.json`](iss035-browser-layout.json)：均为 viewport/page/body `390px`，无横向页面溢出。截图同时如实保留了全局侧栏覆盖内容的现状。

## 数据与快照核对

浏览器测试通过真实 UI 操作与隔离 `/api` 请求构造根/子分类、属性、产品、已发布 SKU、合成客户、报价及草稿订单。完整 HTTP 结果保存在 `iss028-http-results.json` 和 `iss035-api-and-db-snapshots.json`。测试使用只读 SQLite 检查器在操作前后读取同一隔离文件；路径必须位于该运行标记的临时根目录内。

ISS-035 前后数据库对比结果：

- 原分类属性 `uppercase` 从 `0` 改为 `1`；原产品已发布 `sku_definitions` 未变化。
- 既有 SKU `SKU-000001` 的销售型号 `M924F0A63`、规格、参数、显示身份及 `schema_version=1` 均保持不变。
- 普通 SKU 保存只更新本轮合成中文描述；随后真实重开确认描述已保存、销售型号未变化。
- 既有报价行和订单行快照在数据库前后比较完全相同（包括 SKU 编码、销售型号、定义快照等字段）。
- 模板变更后新建产品的 SKU 方案采用 `uppercase=true`，与既有产品保持的旧方案不同，证明新旧行为边界。

数据库字段完整前后值及记录 ID 见 [`iss035-api-and-db-snapshots.json`](iss035-api-and-db-snapshots.json)。合成资料均以“验收”名称/描述和 `example.com` 邮箱生成。

## 测试结果与遗留项

- 隔离启动器自测：13 passed（含端口占用、错误代理目标和并行工作树场景）。
- 真实 Chrome 浏览器测试：2 passed。
- `npm run test:unit`：169 passed。
- 聚焦 Vitest（产品主数据 / SKU）：28 passed。
- 聚焦 Django 分类/SKU 身份、商业身份与 SKU 方案测试：56 passed。
- `npm run build`：成功；存在既有 Vite chunk 大小警告（主 JS 约 1,126.67 kB，gzip 约 393.68 kB），本任务未进行性能重构。
- `git diff --check`：通过。
- 未运行 GitHub Actions；未修改共享项目台账、未合并 master、未启用正式 RBAC。

遗留：窄屏时全局侧栏覆盖页面部分内容，需独立 UX 任务处理；隔离审计日志关闭，因此没有审计日志验收证据。未发现 ISS-035 模板变化静默重写既有 SKU 身份或历史报价/订单快照的问题。
