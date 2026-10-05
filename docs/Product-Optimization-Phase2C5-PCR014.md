# SUNJACK-ERP Product Optimization Phase 2C-5 — PCR-014

## 验收状态

**PCR-014 实现、自动化回归及真实 UI UAT 均通过；UAT-P2C5-001 至 007 为 7/7 PASS。** 本次仅增加 Customer / FollowUp 到预填报价的入口，没有改动后端、数据模型或迁移。

## 实现

- `EntityDetailModal` 新增 `openQuoteForCustomer(customerId)`，只接受正的安全整数 ID；ID 缺失或无效时不打开报价编辑器。
- Customer 根详情在标题操作区显示「新建报价」，使用当前详情上下文中的 Customer ID。
- FollowUp 详情操作区显示「新建报价」，Customer ID 来自 FollowUp 的显式 Customer 关联行（`relationContext().customer`），不从客户名称或显示文字推导。
- 两个入口都复用现有 `quickCreate`、`RelatedCreateModal(entity="quotes", query.customer)` 和 `QuoteEditorModal`。报价编辑器继续把继承的 Customer 设为不可修改。
- Customer「报价记录 → 新增报价」旧入口保留。保存沿用 `RelatedCreateModal @saved → relatedSaved()`，刷新 Customer 上下文并保留选中的报价记录页签。
- 取消只关闭子编辑器，Customer / FollowUp 详情继续打开，URL 状态保持不变。没有新增 FollowUp → Quote 数据库关系；FollowUp 仅通过其 Customer 为该客户创建报价。

## 自动化验证

- 新增 `frontend/tests/entity-detail-quote-create.spec.js`：4 项组件行为测试，覆盖 Customer 快捷入口与无效 ID、客户 ID 传递、旧报价页签保存刷新、FollowUp 使用显式 Customer ID 及取消后保留 `due=true&detail` 路由。
- 更新 `frontend/src/components/RelatedCreateModal.test.js`：新增断言，确认报价 seed 使用 `query.customer`，创建时复用 QuoteEditor 且继承 Customer 保持锁定。
- `npm run test:unit`：111 项通过。
- `node --test tests/detail-drawer-typography.spec.js`：1 项通过。
- 全量 Vitest（CI 同一命令，17 个文件）：103 项通过。
- `npm run build`：通过；Vite 提示主 bundle 超过 500 KB，为现有构建警告。
- `python manage.py check`：通过；`python manage.py makemigrations --check --dry-run`：通过，无待生成迁移。
- `python manage.py test`：512 项通过，10 项按现有条件跳过。
- `git diff --check`：通过。

## UAT-P2C5

真实界面使用内置 Browser 完成，保存的唯一报价属于测试 Customer `UAT-R1 CSV Test Customer`（Customer code `UAT-R1-CSV-CUST-001`）。

| 用例 | 状态 | 记录 |
| --- | --- | --- |
| UAT-P2C5-001 Customer 直达报价 | PASS | Customer 详情标题操作区点击「新建报价」，打开新建报价编辑器；`UAT-R1 CSV Test Customer` 已选中且 Customer 选择框禁用。 |
| UAT-P2C5-002 Customer 取消 | PASS | 点击「取消」后编辑器关闭，原 Customer 详情仍打开，URL 仍为 `/customers`，报价数仍为 3；没有创建报价。 |
| UAT-P2C5-003 Customer 报价页签旧流程 | PASS | 「报价记录 → 新增报价」打开同一编辑器，继承相同 Customer 且选择框禁用；以取消结束，没有多建报价。 |
| UAT-P2C5-004 FollowUp 直达报价 | PASS | FollowUp `id=2` 的详情操作区点击「新建报价」，编辑器选中其关联客户 `UAT-R1 客户 Alpha GmbH`，Customer 选择框禁用。 |
| UAT-P2C5-005 FollowUp 取消 | PASS | 取消后 FollowUp 详情及 `UAT-R1 报价过期回访` 内容仍可见，报价编辑器关闭。 |
| UAT-P2C5-006 待跟进路由保留 | PASS | 在 `/follow-ups?due=true&detail=2` 打开报价编辑器再取消；完整 URL 保持不变，当前待跟进提示、同一 FollowUp 详情及内容均保留。 |
| UAT-P2C5-007 保存实际草稿 | PASS | 从 UAT Customer 快捷入口选择在售 SKU `UAT-R1-CSV-SKU-001`，数量 1、单价 USD 9.90，通过「保存报价」正常创建草稿；Customer 报价记录自动刷新至 4 条，显示该报价及草稿状态。 |

创建报价单号：**SJ20261005CA001**。金额 USD 9.90，状态“草稿”；未推进状态。报价在同一 Customer 的「报价记录」中显示。UAT 截图保存在本机 Codex visualizations 目录，不属于仓库文件。

## CI 与限制

- 开始时基线 `ca41778575bb7e3c735de5d8aabcdcd4d0072e12` 的 CI #134：backend、backend-postgres、frontend 均为 SUCCESS（来自本次交接请求）。
- 本次工作在本地运行了 workflow 的 backend 与 frontend 对应检查；PostgreSQL 服务版测试需要在 push 后的 GitHub Actions `backend-postgres` job 验证。远端本次 run 编号与 job 状态将在 push 后核查。
- 限制：本次没有本地 PostgreSQL 服务；构建保留现有主 bundle 体积警告。两项均不影响本次已通过的应用行为与 UI UAT。

## 变更文件

- `frontend/src/components/EntityDetailModal.vue`
- `frontend/src/components/RelatedCreateModal.test.js`
- `frontend/tests/entity-detail-quote-create.spec.js`
- `docs/Product-Optimization-Phase2C5-PCR014.md`
