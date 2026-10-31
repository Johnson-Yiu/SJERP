# R1-ISS-028/035 分类与 SKU 模板复验

## 结论

在最新基线 `bd324a8c3fb64af245c3afcabbd4301c84f7711c` 上完成真实 Chrome 复验。根分类可在产品编辑器中直接选择并保存；分类树、根/子分类筛选、属性继承、已发布 SKU 参数方案、已接受报价及已确认订单快照、普通 SKU 编辑保存与重新打开均通过。

本轮没有修改产品业务代码、数据库迁移或全局 Issue 台账。仅扩充了浏览器验收断言和只读 SQLite 证据采集器。

## 基线及历史修复核对

- 历史成果：`901b762fba20ed558f554cfba37175b303f83db9`（根分类可直接选择）。该提交不是最新基线的祖先提交，因此没有把历史测试结论当成本轮证据，也没有移植产品代码。
- 最新基线的 `frontend/src/views/ProductPage.vue` 已包含父级分类旁的“选择”操作及 `选择分类 <分类名>` 可访问名称。本轮从基线启动 Chrome，分别在 1440px 和 390px 点击该操作、保存产品，并通过 GET API 核对主分类 ID，结果均通过。

## 真实 Chrome 环境

- Windows，Playwright 配置 `channel=chrome`，使用本机 Google Chrome 二进制；浏览器以无头模式运行。
- Chrome：`156.0.8078.48`；User-Agent 中为 `HeadlessChrome/156.0.0.0`。
- 视口：1440×960 和 390×844。
- 浏览器环境原始记录：[`browser-environment.json`](browser/iss028-035-category-schema.spec/browser-environment.json)。

## 隔离与测试数据

使用仓库的 `run-isolated-browser-tests.mjs`。本轮运行 ID 为 `17954a6c-8796-4132-ac95-9545a62c2bd5`；Django 使用独立临时 SQLite：`C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-repair-06-0TqnCE\db.sqlite3`，媒体目录位于同一临时根目录。隔离身份、数据库路径、媒体路径及 Vite `/api` 代理身份均通过校验。运行器执行了全新数据库迁移和迁移完整性检查。

测试只创建带随机验收标识的合成分类、产品、SKU、客户、报价和订单。报价通过业务 API 标记为已发送；销售订单通过业务 API 确认。数据库快照脚本以 SQLite 只读模式访问运行器的临时数据库，并拒绝读取临时根目录之外的文件。测试结束后，运行器确认本轮 API/Vite 进程树停止、端口释放，并删除本轮临时 DB 和媒体目录。

## 验收矩阵

| 项目 | 结果 | 本轮证据 |
|---|---|---|
| 根分类直接选择及保存 | PASS | 1440px、390px 分别在产品编辑器选择根分类；产品 GET 返回目标根分类 ID。 |
| 根/子分类筛选 | PASS | 两种视口下根分类和子分类筛选返回预期合成产品行；页面 URL 的 `category` 参数与筛选一致。 |
| 子分类继承父级属性 | PASS | API `effective_attributes` 和页面继承标记一致；继承属性的四个开关保持只读；1440px、390px 均验证。 |
| 修改分类模板不覆盖已发布 SKU | PASS | 模板 `uppercase` 规则在 UI 修改并刷新后保持；已发布方案定义、SKU Code、Sales Model、显示名、规格、参数、版本及身份签名不变。 |
| 修改模板不覆盖报价/订单快照 | PASS | 修改前后直接比较 SQLite 中已接受报价及已确认订单的主记录和明细快照，结果完全相同。 |
| 普通 SKU 保存及重新打开 | PASS | 1440px 保存并重新打开；390px 再次编辑、保存并重新打开。描述持久化，身份字段保持不变。 |
| 新产品采用最新分类模板 | PASS | 模板变更后新建产品及 SKU；新发布参数方案采用最新模板且 `uppercase=true`。 |
| 390px 页面宽度及面板布局 | PASS / NOTE | `documentElement.scrollWidth` 与 `body.scrollWidth` 均为 390px；树面板与配置面板 DOM 几何框没有交叠。历史报告提及的窄屏侧栏遮挡仍作为既有后续事项记录，本轮未改造。窄屏树面板纵向位于属性内容之前，属性表仍在内部横向滚动容器中。 |

数据库前后快照：[`iss035-api-and-db-snapshots.json`](browser/iss028-035-category-schema.spec/iss035-api-and-db-snapshots.json)。布局与 DOM 宽度：[`iss028-browser-layout.json`](browser/iss028-035-category-schema.spec/iss028-browser-layout.json)、[`iss035-browser-layout.json`](browser/iss028-035-category-schema.spec/iss035-browser-layout.json)。

## 测试结果

- 隔离真实 Chrome Playwright：2/2 场景通过，失败 0，跳过 0，退出码 0。
- Django system check：通过。
- 全新 SQLite 全迁移及 `migrate --check`：通过。
- 前端定向单元测试（`CategoryPage.test.js`、`SKUPage.test.js`）：11/11 通过。
- `npm run build`：通过；输出仍有既有的大型 JavaScript chunk（约 1.13 MB）警告，本任务未做分包修改。
- 页面测试日志出现 Django `UnorderedObjectListWarning`（产品列表 QuerySet 未显式排序）；本轮隔离合成数据断言通过，未扩大为查询排序修复。
- `git diff --check`：通过。
- 未触发 CI。

运行日志存档：[`chrome-isolated-run.log`](chrome-isolated-run.log)、[`focused-unit-tests.log`](focused-unit-tests.log)、[`frontend-build.log`](frontend-build.log)。为避免暴露隔离运行器临时 API 凭据，Chrome 日志中的 token 字段及 tokenized URL 值已替换为 `<REDACTED>`；其余证据文本已扫描，未发现凭据字段值。SQLite 快照只读采集器：[`inspect_fixture_sqlite.py`](inspect_fixture_sqlite.py)。

## 浏览器截图

截图均来自本轮集成基线的 Google Chrome：

- 根分类选择及筛选：[`01 desktop`](browser/iss028-035-category-schema.spec/01-iss028-root-category-assignment-desktop.png)、[`02 desktop`](browser/iss028-035-category-schema.spec/02-iss028-root-category-filter-desktop.png)、[`03 desktop`](browser/iss028-035-category-schema.spec/03-iss028-child-category-filter-desktop.png)、[`04 mobile`](browser/iss028-035-category-schema.spec/04-iss028-root-category-assignment-390.png)、[`05 mobile`](browser/iss028-035-category-schema.spec/05-iss028-root-category-filter-390.png)、[`06 mobile`](browser/iss028-035-category-schema.spec/06-iss028-child-category-filter-390.png)。
- 属性继承与模板修改：[`07 desktop`](browser/iss028-035-category-schema.spec/07-iss028-inherited-attributes-1440.webp)、[`08 mobile`](browser/iss028-035-category-schema.spec/08-iss028-inherited-attributes-390.png)、[`09 desktop`](browser/iss028-035-category-schema.spec/09-iss035-category-template-changed-1440.webp)、[`10 mobile`](browser/iss028-035-category-schema.spec/10-iss035-category-template-changed-390.png)。07、09 为无损 WebP 转码版本；像素级对比与原始 Chrome PNG 一致，供本报告远端存档。
- SKU 编辑保存及重开：[`11 desktop`](browser/iss028-035-category-schema.spec/11-iss035-ordinary-sku-save-1440.png)、[`12 desktop`](browser/iss028-035-category-schema.spec/12-iss035-reopened-sku-1440.png)、[`13 mobile`](browser/iss028-035-category-schema.spec/13-iss035-ordinary-sku-save-390.png)、[`14 mobile`](browser/iss028-035-category-schema.spec/14-iss035-reopened-sku-390.png)。
