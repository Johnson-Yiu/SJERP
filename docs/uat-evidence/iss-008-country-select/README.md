# ISS-008 国家编码及模糊搜索选择框验收记录

## 范围与基线

- 项目：SUNJACK-ERP
- 任务：ISS-008
- 基线：`af018ac63cf71143d223b9f6db4a087707495693`
- 分支：`codex/iss-008-country-select`
- 实现 Commit：`90f30d5`
- 交付文档 Commit：见本次分支最终 SHA
- 状态：`FIXED_PENDING_REVIEW`，等待统一独立审查；不合并 master，不关闭 Issue

## 实施结果

本轮采用增量方案，不批量改写既有客户国家资料，也没有新增数据库迁移。

- 新增仓库内 `backend/crm/country_registry.py`，内置 249 条 ISO 3166-1 国家目录，保存标准英文名、alpha-2 和 alpha-3；报价运行时不再依赖外部 API。
- 目录数据由开发环境已安装的 `pycountry 26.2.16` 生成并固定进仓库，别名表在同一文件中版本化维护；常用中文名、英文名、代码和简称均通过本地映射处理。
- 交互式客户新建/编辑必须从模糊候选中明确选择，保存值为 alpha-2；候选显示如 `United States / US`。
- `America` 作为模糊搜索词可以展示候选，但不会自动猜测或自动保存；歧义和未知输入分别拒绝保存。
- 导入/历史兼容路径保持原始国家文本，即使文本可识别也不因导入而批量改写；未知历史文本继续保留并标注待人工确认。
- 客户列表和筛选兼容 alpha-2、已知旧名称及历史未知文本；客户展示优先使用标准英文名/代码。
- 新报价编号从保存后的客户 alpha-2 生成；报价根编号分配、修订编号和历史正式单据快照未改动。

## 自动化测试

通过：

```text
python -B manage.py test --verbosity 1
Ran 871 tests in 387.106s
OK (skipped=13)

python -B manage.py test crm.tests.test_dashboard_import crm.tests.BusinessFlowTests.test_customer_csv_import_updates_by_code crm.tests.test_issue_008_country_select --verbosity 1
Ran 24 tests
OK

npm run test:unit
151/151 passed

npx vitest run tests/country-select.spec.js tests/phase2c-editors.spec.js tests/customer-ux.spec.js --environment jsdom --reporter=dot
3 files passed, 16 tests passed

npm run build
Vite production build SUCCESS
```

ISS-008 专项覆盖美国中文/英文/US/America、DE/SE/AT、大小写和空格、模糊候选、键盘上下/Enter 选择、歧义/未知值、旧文本导入、报价历史编号不变、修订编号及编号唯一性。后端测试同时核对国家目录接口、客户 API 标准化和报价编号分配。

直接运行未经筛选的 `npx vitest run` 会把仓库中使用 `node:test` 的源码测试文件和非 jsdom 文件作为 Vitest suite，产生基线级“无 suite / document 未定义 / localStorage 未定义”错误；该入口不作为通过证据，项目有效入口和 ISS-008 定向 Vitest 已通过。

## 真实 Chrome 验收

测试服务使用隔离 SQLite：`iss008-ui.sqlite3`；前端 `http://127.0.0.1:5194/`，后端 `http://127.0.0.1:8120/`。未写入主工作树业务数据库。

- 桌面视口：客户新建/编辑中输入 `us`、`America` 可看到候选，候选显示 `United States / US`；点击候选后保存，API 和列表均显示 `country=US` / `United States / US`。
- 桌面视口：客户列表国家筛选显示标准标签；客户列表、负责人/国家/状态筛选和重置区保持紧凑布局。
- 窄屏视口：`390×844` 下客户编辑表单单列排列，国家帮助文案换行，底部操作区可用，无可见横向溢出。
- 报价页面：桌面 Chrome 已打开报价列表和新建报价表单；报价表单继续使用客户选择、自动生成报价单号、状态/币种/产品明细和保存操作，未改变报价修订链。

本次 Chrome 截图已在任务记录中展示（客户候选下拉、客户编辑桌面/390×844、报价列表及新建报价表单）。截图由真实 Chrome 视口采集；没有将代码渲染图冒充浏览器证据，也没有生成无法追溯的图片文件。

## 数据、权限与遗留事项

- 没有新增或修改 migration；没有自动改写现有客户国家资料。
- 客户查询继续走既有 ViewSet 数据范围，国家筛选只改变查询条件，不扩大可见数据；开发环境仍按项目约定使用开发超级管理员身份。
- 没有修改 ISS-037 历史主体快照或 ISS-039 成本分配。
- 本地 SQLite 全量已通过；本轮未执行 PostgreSQL/CI，需在统一集成环境继续核验。
- 本地实现已提交；最终分支 SHA 以交付消息为准。本轮未执行 GitHub 推送、PostgreSQL/CI，独立审查仍待进行。
