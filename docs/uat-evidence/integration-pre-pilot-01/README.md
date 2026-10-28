# R1-INTEGRATION-PRE-PILOT-01 集成报告

日期：2026-10-29  
集成分支：`codex/integration-pre-pilot-01`  
固定基线：`bcb2f4a0c27e200be3fc2c05e0791e7cec499dbb`

## 结论

五个指定成果已按要求从固定基线依次集成。集成过程中没有发现需要追加产品业务修复的明确缺陷，也没有重复修改已封版的 ISS-042、ISS-048 功能。当前工作树仅包含本报告和证据索引更新；没有修改 GitHub Actions、没有触发 CI、没有合并 master、没有部署。

本轮可确认的结果：

- Django 全量测试：1007 项通过，18 项按既有标记跳过。
- Django 系统检查、迁移检查和隔离 SQLite 迁移通过，迁移链完整应用到 `crm.0089_operationlog_operator_protect`。
- ISS-008 国家目录/别名与现有客户接口定向测试：26 项通过。
- ISS-028 / ISS-035 隔离 API、Vite 代理身份、SQLite、迁移和 Playwright：2 项通过。
- ISS-020 报价/PI/交易单位交叉回归：89 项通过。
- `requirements.lock` 的只读安装解析通过，当前 Python 环境 `pip check` 通过。

Vitest 全量和生产构建没有标记为通过：当前本机前端依赖目录不完整，缺少 `mdn-data` 与 Windows `lightningcss` 原生模块，且测试过程中 C 盘空间耗尽。Node 基础脚本另有 2 项测试因其临时 worktree 未安装 Playwright 而失败。这些属于测试环境阻断，不能作为产品缺陷或封版依据。

## 来源与集成提交

| 成果 | 来源 SHA | 集成后提交 | 范围 |
|---|---|---|---|
| Issue 台账校准 | `2bb9d1746d13ce7b1c70e13dee1b8d3b48aaed2e` | `2303c573465701e40db922654e2ae4d25fa5a626` | 台账、阶段记录、124 Issue / 46 规则对账报告 |
| ISS-008-FUP-01 | `80dc73ae4ae47f9e04969f39b441af206d34306b` | `7de261e4e50758b7ba7809170be0a20cb5d384e7` | 249 条 ISO 国家目录、中文别名、API/前端测试及证据 |
| ISS-002 Python 安全 | `85adec7d99d725c7c920c728385172d6517730ce` | `3961ef6c4b0499adb0689f14be73372692ddac3f` | `requirements.txt` 调整和完整 `requirements.lock` |
| ISS-028 / ISS-035 | `901b762fba20ed558f554cfba37175b303f83db9` | `47fcab0f6f37f52475074e65ab7ab188352ae8ce` | 根分类归类、分类模板/SKU 历史边界、窄屏/桌面证据 |
| ISS-045 QA 工具 | `966deaa209cd5b115704a67e58aeb12783b9a60a` | `72a6b27f3f855424f16cd9657996055c68b5ca95` | 旧 QA 命令退役保护、seed 安全边界及测试 |

五个集成提交均保留 `[skip ci]`。没有发现提交间代码冲突；台账提交先落地后，国家目录、依赖、ProductPage 和 QA 工具提交均可直接应用。

## 交叉核验

### 国家目录与现有国家接口

`country_registry` 继续通过现有 `CustomerSerializer` 和 `CustomerViewSet` 入口工作：

- `COUNTRY_CATALOG` 与 `COUNTRY_CHINESE_NAMES` 均覆盖 249 条记录。
- `/api/customers/country-catalog/` 仍返回现有前端选择器使用的列表结构，而不是改变为分页对象。
- 已知中文名、英文名、alpha-2、alpha-3 和既有别名解析为 alpha-2；模糊的 `America` 和未知值不会被猜测。
- 旧客户未知国家文本继续保留供人工复核；报价编号历史不因客户国家重新选择而改写。
- `crm.tests.test_issue_008_country_select` 的 26 项测试通过，覆盖目录、解析、客户 API、国家筛选和报价编号兼容性。

ISS-008 的桌面与 390px 证据仍保留在 [`iss008-fup-01`](../iss008-fup-01/README.md)，没有覆盖历史截图。

### Python 锁定依赖

安装方式为：

```text
python -m pip install --requirement backend/requirements.lock
```

只读核验命令：

```text
python -m pip install --dry-run --ignore-installed --no-deps --requirement requirements.lock
python -m pip check
```

两项均通过；dry-run 显示完整锁定包集合可解析且不会修改当前环境。实际安装没有执行，因此不能把当前全局 Python 3.14 / Django 6.0.6 环境称为锁定环境验收。锁定文件声明的 Django 6.0.9 等版本需在干净虚拟环境中执行真实安装后再做部署验收。

### ProductPage 分类与窄屏

ISS-028 / ISS-035 的 `ProductPage.vue` 仅保留根分类直接归类所需的最小修复，没有改变 SKU 编码、已发布 SKU、报价或订单快照语义。原提交的桌面与窄屏截图继续保留：

- [`iss028-browser-layout.json`](../iss-028-035-category-schema/iss028-browser-layout.json)
- [`05-iss028-inherited-attributes-narrow.png`](../iss-028-035-category-schema/05-iss028-inherited-attributes-narrow.png)
- [`06-iss035-category-template-changed-desktop.png`](../iss-028-035-category-schema/06-iss035-category-template-changed-desktop.png)
- [`07-iss035-category-template-changed-narrow.png`](../iss-028-035-category-schema/07-iss035-category-template-changed-narrow.png)

隔离 Playwright 命令：

```text
node scripts/run-isolated-browser-tests.mjs --business-test iss028-035-category-schema.spec.js
```

第二次执行使用临时证据目录，完成了真实 Django API、Vite `/api` 代理身份、全量 SQLite 迁移和浏览器回归：2 passed。临时数据库、MEDIA_ROOT、截图和日志已清理；已提交的原始证据未被覆盖。

### ISS-045 退役命令

`run_business_flow_checks` 和 `run_edge_business_flow_checks` 现在明确抛出 `CommandError`，提示命令已退役且不能作为 QA/UAT gate；`seed_demo` 仍保留 deployed stage、非 SQLite 和未声明隔离身份的拒绝保护。`crm.tests.test_legacy_qa_tools` 通过，Django `check` 通过，说明普通服务启动路径未因退役保护被改写。退役命令不应被重新接入正常启动或 CI gate。

### 迁移与既有功能边界

- `python manage.py makemigrations --check --dry-run`：`No changes detected`。
- `python manage.py migrate --plan`：可生成完整计划，包含 `crm.0085` 至 `crm.0089`。
- 隔离浏览器运行实际应用全部迁移并通过 `migrate --check`。
- 全量 Django 测试中的 ISS-042 共享报表、ISS-048 财务钻取及其他历史模块均由基线现有代码回归覆盖；本轮没有新增或重写这些功能。
- 报价/PI/交易单位定向回归 89 项通过；首次全量失败是稀疏工作区未物化报价模板，补齐仓库原有两个模板后重跑通过，不是集成提交改坏导出。

## 测试日志与失败分类

| 分类 | 命令/范围 | 结果 |
|---|---|---|
| 后端系统检查 | `python manage.py check` | PASS |
| 后端定向 | 国家目录、旧 QA 工具、ProductPage 相关后端安全测试 | 26/26 PASS |
| 后端报价交叉回归 | `test_iss020_quote_export`, `test_quotes`, `test_trade_units` | 89/89 PASS |
| 后端全量 | `python manage.py test --verbosity 1` | 1007 PASS，18 SKIPPED |
| 迁移 | `makemigrations --check --dry-run`、`migrate --plan`、隔离 `migrate --check` | PASS |
| Python 依赖 | lock dry-run、`pip check` | PASS；未实际安装锁定环境 |
| Node 基础测试 | `npm run test:unit` | 167 PASS；2 项因临时 worktree 缺 Playwright 依赖失败 |
| Vitest | `node node_modules/vitest/vitest.mjs run --configLoader runner` | BLOCKED：依赖目录缺 `mdn-data`，并出现 `document` 环境/磁盘空间错误；不作为产品失败 |
| 前端生产构建 | `node node_modules/vite/bin/vite.js build --configLoader runner` | BLOCKED：依赖目录缺 `lightningcss.win32-x64-msvc.node`；默认配置加载另有 Rolldown sourcemap 环境错误 |
| 隔离浏览器 | ISS-028 / ISS-035 Playwright | 2/2 PASS；使用隔离 SQLite、MEDIA_ROOT、API/Vite 端口 |

Vitest、生产构建和 Node 基础测试的阻断需在干净依赖环境中重新执行。未将这些项目标为通过，也没有因为阻断删断言、降低验收标准或修改业务代码。

## 后续修复清单

1. 在有足够磁盘空间的干净前端环境执行 `npm ci`，确认 `@playwright/test`、`mdn-data` 和 Windows `lightningcss` 可选原生包完整。
2. 重新运行完整 Vitest、前端生产构建及需要的 Playwright 套件；本轮只确认了 ISS-028 / ISS-035 隔离回归。
3. Node 基础测试的并行临时 worktree 需要继承隔离依赖安装策略后再复核 2 项基础设施测试。
4. Python lock 文件需要在干净虚拟环境真实安装并执行 `pip check`；本轮只完成 dry-run 和当前环境检查。
5. ISS-042、ISS-048 及状态对账报告中已有的正式权限、生产数据和部署验收缺口继续按原台账处理，不在本集成任务中关闭。

## 约束记录

本轮未修改 `.github/workflows/`，未触发 GitHub Actions，未连接生产环境，未合并 master，未关闭 Issue。所有新提交均包含 `[skip ci]`。
