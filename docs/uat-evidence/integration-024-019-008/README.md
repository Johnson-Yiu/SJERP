# ISS-024 / ISS-019 / ISS-008 统一集成验收

## 范围

- 项目：SUNJACK-ERP
- 统一基线：`af018ac63cf71143d223b9f6db4a087707495693`
- 集成分支：`codex/integration-024-019-008`
- 最终提交：`a18d369`
- 独立 worktree：`C:\Users\Johnson\.codex\worktrees\integration-024-019-008\森爵照明管理系统`
- 状态：三项功能均已按 ISS-024 → ISS-019 → ISS-008 顺序集成，等待统一独立审查；未合并 master，未关闭 Issue。

## 成果核验与集成记录

### ISS-008 分支核验

ISS-008 原预期分支首次核验时不在 GitHub 远端。已检查本地独立 worktree，确认其实现提交和验收文档均存在；随后将该分支推送到 `origin`，并用 `git ls-remote --heads origin codex/iss-008-country-select` 确认远端可见：

```text
a14d3d929e0c64dbb06d375d9a0ffa832526af92 refs/heads/codex/iss-008-country-select
```

本次将 `90f30d5` 实现提交和 `a14d3d9` 验收文档提交纳入集成。旧分支 `fix/quote-country-iso-resolution` 未作为本轮 ISS-008 验收结果或集成来源。

### 集成顺序

从统一基线创建独立 worktree 后，按要求完成以下集成：

1. ISS-024：`1d576e961dc021d194e0ec2f9fd7dd6fc629535d`，结果提交 `22342ad`。
2. ISS-019：纳入实现 `6e88084`，以及其验收台账提交 `cb2a90d`、`2776fec`，结果提交分别为 `d924d8d`、`074bb55`、`9e174c0`。
3. ISS-008：`90f30d5`、`a14d3d9`，结果提交分别为 `dc4a67e`、`205c22f`。

冲突仅出现在 `backend/crm/views.py` 和 `docs/PROJECT_PHASES.md`：

- `views.py` 保留 ISS-024 的客户级供应商偏好读取、停用供应商过滤和数据范围逻辑，同时补入 ISS-008 的本地国家目录/API 逻辑。
- `PROJECT_PHASES.md` 同时保留 ISS-019 和 ISS-008 的阶段记录，没有覆盖任一任务证据。
- 数据库迁移没有发生冲突，也没有重写迁移历史。

## 兼容性检查

### ISS-024

- 客户级供应商偏好仍按客户隔离；跨客户请求不会复用其他客户的偏好。
- 停用供应商不进入新采购候选；已有采购、报价和历史展示保持原供应商引用。
- SKU 参考成本和采购单成本继续使用独立字段/口径。
- 采购成本分配相关测试仍通过，未改变 ISS-039 的归属、公共费用、金额守恒、权限脱敏和事务回滚规则。

### ISS-019

- 报表查看权限和 CSV 导出权限分别校验；仅有导出权限而无查看权限的 API 请求会被拒绝。
- [API 原始结果](../iss-019-report-csv/report-api.json)、[真实 CSV](../iss-019-report-csv/report-sales-customer.csv) 和 [HTTP 下载 CSV](../iss-019-report-csv/http-report-sales-customer.csv) 已保存；字节、SHA-256、金额、单据数和数量对账记录在 [csv-byte-check.json](../iss-019-report-csv/csv-byte-check.json)。
- CSV 使用 UTF-8 BOM，公式前缀经过转义；多币种金额按既有汇率和标签口径，数量按单位分别累计。
- 共享报表模板在服务端按当前账号重新校验，不继承模板发布者权限。

### ISS-008

- 使用仓库内版本化 ISO 3166-1 目录和别名表，不依赖页面打开时的外部 API，也没有新增迁移。
- 客户国家输入支持中文、英文、alpha-2 代码和常用简称模糊搜索；保存前必须明确选定，歧义/未知输入不会静默猜测。
- 新报价编号使用保存后的 alpha-2 国家代码；历史报价编号、修订链和 ISS-037 正式单据主体快照不变。
- 客户旧国家文本保留，不进行大规模自动改写。

### 迁移

集成后保留并检查了已有迁移链：`0080_formal_party_snapshots`、`0081_transaction_rmb_reference_label`、多个既有 `0081` 分支、`0082_merge_iss026_iss107_iss017`、ISS-024 的 `0083_customer_supplier_preference` 和 `0084_alter_orderitem_supplier_allocation_scope_and_source`。ISS-008 没有迁移文件，不存在额外并行迁移。

- 全新 SQLite 数据库从零迁移至最新迁移：通过。
- 已有数据库先迁移到 `0082_merge_iss026_iss107_iss017`，再升级至 `0084`：通过。
- 银行资金和历史数据回归验证中的 `bank_net`、旧数据行一致性均保持不变。

## 自动化测试与构建

以下均在集成分支、隔离 SQLite 数据库上执行：

```text
python -B manage.py check
python -B manage.py test crm.tests.test_iss024_reproduction crm.tests.test_supplier_allocation crm.tests.test_supplier_context_scope crm.tests.test_procurement_data_scope crm.tests.test_functional_rbac crm.tests.test_reporting crm.tests.test_issue_008_country_select crm.tests.test_quotes crm.tests.test_quote_revision_tree crm.tests.test_formal_party_snapshots crm.tests.test_integration_039_037_040 crm.tests.test_packing_list_export --verbosity 1
Ran 207 tests
OK

python -B manage.py test --verbosity 1
Ran 877 tests
OK (skipped=13)

npm run test:unit
151 tests passed

npx vitest run tests/country-select.spec.js tests/purchase-costs.spec.js tests/purchase-editor-receipt.spec.js tests/purchase-workbench.spec.js tests/r0f2-overview-reports.spec.js tests/reports.spec.js tests/entity-detail-quote-create.spec.js tests/quote-list-ux.spec.js tests/phase2c-editors.spec.js --environment jsdom --reporter=dot
9 files passed, 74 tests passed

npm run build
2009 modules transformed; production build succeeded
```

Vitest 使用仓库中可识别的有效入口和 `jsdom` 环境；未把仓库中非 Vitest 的 `node:test` 源码误计为失败。构建只有既有大 chunk 提示，没有构建错误。

## 真实 Chrome 回归

真实 Chrome 使用正确的集成服务：前端 `http://127.0.0.1:5196`，后端代理 `8130`，隔离数据库为空数据集以确认页面和权限边界，不使用旧的 `5195/8120` 页面结果。

- 桌面：客户管理显示负责人、国家、状态筛选和重置；报表中心显示已提交查询、数据源/维度/日期范围、CSV 导出和共享模板入口；采购管理显示状态、搜索、仅看待到货和重置筛选。
- 窄屏 `390×844`：客户管理和报价页面完成真实 Chrome 回归，侧边栏收起后表单/筛选区单列排列，按钮和帮助文案可用，无明显横向溢出。
- 截图已在本任务记录中以真实 Chrome 截图展示；没有把代码渲染图片冒充浏览器证据。

## 遗留事项

- GitHub Actions [CI run 40203282554](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/40203282554) 已完成但失败；`backend-postgres`、`frontend`、`backend` 三个 job 均在可见 steps 前结束，`steps=[]`，因此记录为 CI/环境失败，不能作为本地测试或 PostgreSQL 通过的替代。PostgreSQL 本地也未执行。
- 三项功能均已集成，但仍需统一独立审查；不在本任务中合并 master 或关闭 Issue。
