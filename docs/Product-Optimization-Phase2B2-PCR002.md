# SUNJACK-ERP Product Optimization Phase 2B-2 — PCR-002

## 范围与验收结论

本次只实现销售订单列表的状态筛选、待办筛选及筛选上下文保留；没有修改订单生命周期、报价工作流、数据模型或权限策略，也没有新增迁移。

**PCR-002 当前验收状态：未通过（等待补齐两项真实 UI 覆盖）。** UAT-P2B2-002 的本地开发数据没有已发货订单样例；UAT-P2B2-008 的报价排序参数会发送到后端，但报价树在前端仍按报价编号排序，切换排序后可见顺序没有变化。报价树排序超出本 PCR 的允许改动范围。

## 筛选语义

订单状态使用 `status=<status>` 精确匹配以下既有状态：`draft`、`confirmed`、`production`、`shipped`、`completed`、`cancelled`。未传状态时保持原有列表结果。

`todo=unshipped` 只包含 `confirmed` 与 `production`。现有发货生命周期在订单明细全部发完后才进入 `shipped`，因此列表直接使用这两个正式履约状态表示仍有发货工作，不重新计算另一套发货生命周期。

`todo=due` 的条件为：

- `expected_ship_date` 非空；
- `expected_ship_date <= timezone.localdate()`；
- 状态为 `confirmed` 或 `production`。

这会排除草稿、已发货、已完成、已取消订单，也不把未来 3/7/30 天等自定义窗口加进本阶段。状态、待办、客户、报价、产品、SKU 及后端搜索可组合。

## 页面与路由

订单页新增状态和待办下拉框及重置按钮；报价页继续使用原有状态、客户、排序和重置控件。订单状态与待办从路由查询读取，并通过同页 `router.push` 更新：

- `/orders?status=production`
- `/orders?todo=unshipped`
- `/orders?status=confirmed&todo=due`

查询变化不会改变页面路由身份。打开/关闭详情时保留状态、待办及其他查询键；直接链接和刷新能恢复控件；浏览器前进/后退同步 URL、控件和列表。订单搜索继续保存在页面状态，并与路由筛选一并发送给现有后端搜索。订单重置只清搜索、`status` 和 `todo`，保留 `customer`、`quote`、`detail` 等其他查询键。

## 业务理由

- `unshipped` 采用 `confirmed/production`，因为只有全部明细完成出库后订单才进入 `shipped`。
- `due` 同时要求本地日期已到和正式履约状态，防止草稿交期、终态订单或没有交期的订单变成待办。
- 到期边界使用 Django `timezone.localdate()`，符合项目 `Asia/Shanghai` 时区。
- 汇总卡片仍基于当前筛选结果，不新增汇总端点。

## 真实 UI UAT

验收日期：2026-10-05；环境：本地开发数据，通过内置 Browser 插件操作 `http://127.0.0.1:5192`。

| 项目 | 结果 | 证据与说明 |
| --- | --- | --- |
| UAT-P2B2-001 状态筛选 | PASS | 草稿显示 `SO-2026-00005`；生产中显示 `SO-2026-00031`；已完成的 28 行均显示“已完成”。 |
| UAT-P2B2-002 待出库 | PARTIAL | 列表显示 `SO-2026-00031`（生产中）、`SO-2026-00032` 与 `SO-2026-00033`（已确认），没有草稿、已完成或已取消行。`status=shipped&todo=unshipped` 返回空集。当前本地数据没有已发货订单，故无法用真实已发货行完成 UI 排除验收；后端测试用真实 `shipped` 记录验证排除。 |
| UAT-P2B2-003 交期已到 | PASS | 页面显示 `SO-2026-00032`（已确认，2026-10-04）及 `SO-2026-00031`（生产中，2026-10-05）；已确认且预计 2026-10-20 的 `SO-2026-00033` 未显示。详情工作台确认了两条到期日期及状态。 |
| UAT-P2B2-004 搜索 + 待办 | PASS | 搜索 `SO-2026-00032`，同时选 `todo=due` 和 `status=confirmed`，交集只显示 `SO-2026-00032`；请求包含 `search`、`todo`、`status`。 |
| UAT-P2B2-005 详情上下文 | PASS | 在搜索、状态、待办均启用时打开 `SO-2026-00032`；URL 保留查询并追加 `detail=32`。搜索值、控件和一行筛选结果保持；关闭详情后返回同一筛选列表。 |
| UAT-P2B2-006 直接链接 / 刷新 | PASS | 直接打开 `/orders?todo=unshipped` 并刷新；下拉框恢复“待出库”，三条列表记录和状态保持匹配。 |
| UAT-P2B2-007 前进 / 后退 | PASS | 从 `todo=unshipped` 通过页面切换到 `todo=due`；浏览器后退恢复三行待出库列表，前进恢复两行交期已到列表，URL 与控件同步。 |
| UAT-P2B2-008 报价回归 | PARTIAL | 报价搜索、状态、客户、重置均工作；排序控件切换会发送 `ordering=updated_at` / `-updated_at` 等参数。真实 UI 的可见报价树顺序没有随选项变化：现有 `quoteTreeRows` 会按报价编号重新排序。本 PCR 按限定没有改报价树；需在允许的报价范围内另行处理后重验此项。 |

### 通过普通页面创建的 UAT 订单

原开发数据没有确认中或生产中的订单，也没有到期正式订单，所以通过订单新建表单补建最少的筛选样例；没有通过 API 或数据库脚本注入数据。

- `SO-2026-00031`：2026-10-05 交期；经“确认订单”后再经“开始生产”进入生产中。
- `SO-2026-00032`：2026-10-04 交期；经“确认订单”进入已确认。
- `SO-2026-00033`：2026-10-20 交期；经“确认订单”进入已确认，用于验证未来交期不进入 `due`。
- 三张订单使用现有开发客户与 SKU-000001，各一条 10 pcs、USD 10 的明细。通过确认对话框后创建了应收计划；数据保留在本地开发数据库中。没有可用库存，未尝试造库存或创建发货记录。

真实页面证据：`PCR002-UAT-due-list.png` 展示两条交期已到结果；`PCR002-UAT-due-order-detail.png` 展示 `SO-2026-00032` 的状态与预计交期。

## 自动化验证

- `crm.tests.test_order_list_filters`：4 项通过（精确状态、客户组合、`unshipped` 生命周期范围、按本地日期的 `due`、终态排除、搜索组合）。
- `python manage.py test`：482 项通过，10 项跳过。
- `python manage.py check`：通过，无系统问题。
- `python manage.py makemigrations --check --dry-run`：通过，无迁移变更。
- `npm run test:unit`：109 项通过。
- `node --test tests/detail-drawer-typography.spec.js`：1 项通过。
- `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js`：12 个文件、77 项通过。
- `npm run build`：通过；构建工具报告现有单个约 985 kB 的压缩前 JS 包超过 500 kB 提示。

## 限制与待办

1. 当前本地开发数据没有 `shipped` 样例和可用库存。为了不在 PCR-002 中额外写入库存/发货业务记录，真实 UI 的 `shipped` 排除覆盖标为部分通过；后端过滤测试覆盖该状态。
2. 报价根节点在 `DocumentPage.vue` 的现有报价树计算中按报价编号排序，抵消了后端排序顺序。此行为未由 PCR-002 引入；报价范围确认后需单独修正并重新执行 UAT-P2B2-008。
3. 因 UAT-P2B2-002 和 UAT-P2B2-008 尚未完全通过，本文不将 PCR-002 标为 PASS。
