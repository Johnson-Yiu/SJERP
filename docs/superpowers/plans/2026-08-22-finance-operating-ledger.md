# 财务经营台账 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为订单驱动的贸易业务建立与订单、采购和库存联动的应收应付、实际收付款及经营财务概览。

**Architecture:** 使用 `PaymentPlan` 管理销售订单和采购单的合同原币收付款节点；`Transaction` 作为实际收付款、费用、预收预付、退款与冲销的唯一流水。领域服务负责生成计划、核销、作废及汇总，Vue 页面使用 REST API 展示概览、计划和统一登记。

**Tech Stack:** Django 5、Django REST Framework、Vue 3、Vite、Vitest。

**Spec:** `docs/superpowers/specs/2026-08-22-finance-operating-ledger-design.md`

## Global Constraints

- 本期不实现银行账户余额、自动对账、会计凭证、总账、税务申报或事务所导出。
- 合同计划及核销以原币金额判断；经营报表统一按人民币金额汇总。
- 已确认流水只能作废后重记，不能原地修改金额、关联订单或关联计划。
- 不修改现有未提交的 `backend/crm/migrations/0017_product_suppliers.py`；新增迁移依赖它并使用下一编号。
- 新接口遵循现有 `/api/`、DRF `ModelViewSet` 和前端 `api.js` 模式。

---

## File structure

- `backend/crm/models.py`：`PaymentPlan`、合同变更、扩展 `Transaction` 及订单/采购汇总属性。
- `backend/crm/migrations/0018_finance_operating_ledger.py`：独立、可回滚的财务结构迁移。
- `backend/crm/services/finance.py`：计划生成、核销、预收预付、作废替代、概览指标。
- `backend/crm/serializers.py`、`views.py`、`urls.py`、`context.py`：验证、API、路由与详情联动。
- `backend/crm/tests/test_finance.py`：财务领域与 API 回归测试。
- `frontend/src/views/FinanceDashboardPage.vue`：五项指标与到期/逾期清单。
- `frontend/src/views/PaymentPlanPage.vue`：应收/应付计划维护与核销。
- `frontend/src/components/OrderSearchModal.vue`：订单模糊搜索弹窗。
- `frontend/src/components/TransactionFormModal.vue`、`frontend/src/views/TransactionPage.vue`：统一实际收付款与费用登记。
- `frontend/src/components/OrderDetailModal.vue`、`frontend/src/views/PurchaseOrderPage.vue`：订单与采购单内财务汇总。
- `frontend/src/router.js`、`frontend/src/App.vue`：财务导航与路由。

## Task 1: 建立财务领域模型与迁移

**Files:**
- Modify: `backend/crm/models.py`
- Create: `backend/crm/migrations/0018_finance_operating_ledger.py`
- Create: `backend/crm/tests/test_finance.py`

**Interfaces:**
- Produces: `PaymentPlan`, `OrderChangeRequest`, `PurchaseOrderChangeRequest`; `Transaction.plan`, `Transaction.kind`, `Transaction.rmb_amount`, `Transaction.replaces`。
- Consumes: 现有 `Order`、`PurchaseOrder`、`Customer`、`Supplier`、`Transaction`。

- [ ] **Step 1: 写失败的模型约束测试**

```python
def test_plan_belongs_to_exactly_one_contract(self):
    plan = PaymentPlan(direction="receivable", currency="USD", planned_amount="100")
    with self.assertRaises(ValidationError):
        plan.full_clean()

def test_confirmed_transaction_cannot_change_amount(self):
    row = TransactionFactory(status="confirmed", amount="100")
    row.amount = Decimal("120")
    with self.assertRaises(ValidationError):
        row.full_clean()
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python manage.py test crm.tests.test_finance.PaymentPlanModelTests -v 2`

Expected: FAIL，因为模型尚不存在。

- [ ] **Step 3: 实现最小模型与迁移**

```python
class PaymentPlan(TimestampedModel):
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.PROTECT, related_name="payment_plans")
    purchase_order = models.ForeignKey(PurchaseOrder, null=True, blank=True, on_delete=models.PROTECT, related_name="payment_plans")
    direction = models.CharField(max_length=12, choices=[("receivable", "应收"), ("payable", "应付")])
    due_date = models.DateField(null=True, blank=True)
    planned_amount = models.DecimalField(max_digits=14, decimal_places=2)
    settled_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=10)
    status = models.CharField(max_length=12, default="open")
```

Implement a model `clean()` requiring exactly one contract, plus immutability validation for confirmed transactions. Add ledger kinds: customer receipt, supplier payment, order expense, period expense, unallocated advance, refund and exchange difference. Generate a migration dependent on `0017_product_suppliers`.

- [ ] **Step 4: 验证模型与迁移**

Run: `python manage.py makemigrations --check`

Run: `python manage.py test crm.tests.test_finance.PaymentPlanModelTests -v 2`

Expected: no new migrations; PASS.

- [ ] **Step 5: 提交**

```bash
git add backend/crm/models.py backend/crm/migrations/0018_finance_operating_ledger.py backend/crm/tests/test_finance.py
git commit -m "feat: add finance ledger domain models"
```

## Task 2: 实现计划生成、核销与冲销服务

**Files:**
- Create: `backend/crm/services/finance.py`
- Modify: `backend/crm/serializers.py`
- Modify: `backend/crm/tests/test_finance.py`

**Interfaces:**
- Produces: `ensure_default_payment_plans(contract, deposit_ratio=Decimal("0.30"))`, `record_transaction(payload)`, `void_transaction(transaction, replacement_payload=None)`。
- Consumes: Task 1 模型及现有订单、采购单。

- [ ] **Step 1: 写失败的服务测试**

```python
def test_excess_receipt_becomes_unallocated_advance(self):
    plan = PaymentPlanFactory(planned_amount="100", settled_amount="0", currency="USD")
    applied = record_transaction({"kind": "customer_receipt", "plan": plan, "amount": "120", "currency": "USD", "rmb_amount": "864"})
    plan.refresh_from_db()
    self.assertEqual(applied.amount, Decimal("100"))
    self.assertEqual(plan.status, "settled")
    self.assertTrue(Transaction.objects.filter(kind="unallocated_advance", amount="20").exists())
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python manage.py test crm.tests.test_finance.FinanceServiceTests -v 2`

Expected: FAIL，因为服务尚不存在。

- [ ] **Step 3: 实现事务性服务**

```python
@transaction.atomic
def record_transaction(payload):
    plan = payload.get("plan")
    original_amount = Decimal(str(payload["amount"]))
    remaining = plan.planned_amount - plan.settled_amount if plan else original_amount
    applied_amount = min(original_amount, remaining)
    row = Transaction.objects.create(**{**payload, "amount": applied_amount, "status": "confirmed"})
    if plan:
        plan.settled_amount += applied_amount
        plan.status = "settled" if plan.settled_amount == plan.planned_amount else "open"
        plan.save(update_fields=["settled_amount", "status"])
    return row
```

Extend the service to create default 30%/70% plans for confirmed sales and non-cancelled purchase orders, split overpayment into same-party unallocated advance, refuse cross-party allocation, calculate RMB exchange differences, reverse settlement on void, and create a replacement linked by `replaces`.

- [ ] **Step 4: 运行服务测试**

Run: `python manage.py test crm.tests.test_finance.FinanceServiceTests -v 2`

Expected: PASS for instalments, advances, exchange difference, void/replacement and cross-party rejection.

- [ ] **Step 5: 提交**

```bash
git add backend/crm/services/finance.py backend/crm/serializers.py backend/crm/tests/test_finance.py
git commit -m "feat: add payment plan settlement services"
```

## Task 3: 接入订单、采购单、变更单与财务 API

**Files:**
- Modify: `backend/crm/serializers.py`
- Modify: `backend/crm/views.py`
- Modify: `backend/crm/urls.py`
- Modify: `backend/crm/context.py`
- Modify: `backend/crm/tests/test_finance.py`

**Interfaces:**
- Produces: `/api/payment-plans/`, `/api/order-changes/`, `/api/purchase-order-changes/`, `/api/finance-dashboard/`, `/api/orders/search/`。
- Consumes: Task 2 service functions.

- [ ] **Step 1: 写失败的 API 测试**

```python
def test_finance_dashboard_has_requested_metrics(self):
    response = self.client.get("/api/finance-dashboard/")
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(set(response.data["metrics"]), {
        "receivable_count", "receivable_rmb", "payable_count",
        "payable_rmb", "monthly_sales_rmb",
    })

def test_order_search_returns_expected_columns(self):
    response = self.client.get("/api/orders/search/?q=ACME")
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(set(response.data[0]), {
        "id", "customer_name", "country", "order_no", "total_amount", "currency",
    })
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python manage.py test crm.tests.test_finance.FinanceApiTests -v 2`

Expected: FAIL，路由不存在。

- [ ] **Step 3: 实现 API 和现有单据联动**

Implement `PaymentPlanSerializer` fields `remaining_amount`, `is_overdue`, `contract_no`, `counterparty_name` and RMB conversion. Make order and purchase serializers call plan generation after line items exist. Add plan filters for direction, order, purchase order, status and overdue; add settle and cancel actions. Extend transactions with party, contract, direction, kind, status, dates and currency filters; reject direct patch of confirmed rows. Add approved contract-change actions that only append plan capacity after approval. Add dashboard metrics and fuzzy order search results. Extend contexts and workbenches with plans, expense and profit summary.

- [ ] **Step 4: 运行 API 与履约回归**

Run: `python manage.py test crm.tests.test_finance crm.tests.test_fulfillment -v 1`

Expected: PASS; existing receipt, supplier payment and shipment workflows continue to pass.

- [ ] **Step 5: 提交**

```bash
git add backend/crm/serializers.py backend/crm/views.py backend/crm/urls.py backend/crm/context.py backend/crm/tests/test_finance.py
git commit -m "feat: expose finance ledger APIs"
```

## Task 4: 构建财务概览与应收应付页面

**Files:**
- Create: `frontend/src/views/FinanceDashboardPage.vue`
- Create: `frontend/src/views/PaymentPlanPage.vue`
- Create: `frontend/src/views/FinanceDashboardPage.test.js`
- Create: `frontend/src/views/PaymentPlanPage.test.js`
- Modify: `frontend/src/router.js`
- Modify: `frontend/src/App.vue`

**Interfaces:**
- Consumes: `GET /api/finance-dashboard/`, `GET /api/payment-plans/`, `POST /api/payment-plans/:id/settle/`。
- Produces: `/finance`, `/receivables`, `/payables`。

- [ ] **Step 1: 写失败的页面测试**

```javascript
it('renders the five agreed finance metrics', async () => {
  api.get.mockResolvedValue({ data: { metrics: {
    receivable_count: 3, receivable_rmb: '100', payable_count: 2,
    payable_rmb: '80', monthly_sales_rmb: '300',
  }, due_items: [] } })
  render(FinanceDashboardPage)
  expect(await screen.findByText('待收笔数')).toBeInTheDocument()
  expect(screen.getByText('月度销售额')).toBeInTheDocument()
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `npm run test:unit -- FinanceDashboardPage.test.js PaymentPlanPage.test.js`

Expected: FAIL，组件不存在。

- [ ] **Step 3: 实现页面、筛选和导航**

Build the five dashboard cards and due/overdue links. Create one reusable plan page keyed by receivable/payable direction with contract, counterparty, date and status filters, original-currency amount, RMB amount and settlement entry. Add 财务概览、应收计划、应付计划、财务流水 to the finance navigation.

- [ ] **Step 4: 运行前端测试与构建**

Run: `npm run test:unit -- FinanceDashboardPage.test.js PaymentPlanPage.test.js`

Run: `npm run build`

Expected: PASS.

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/FinanceDashboardPage.vue frontend/src/views/PaymentPlanPage.vue frontend/src/views/FinanceDashboardPage.test.js frontend/src/views/PaymentPlanPage.test.js frontend/src/router.js frontend/src/App.vue
git commit -m "feat: add finance dashboard and plan pages"
```

## Task 5: 重构统一财务流水与订单搜索

**Files:**
- Create: `frontend/src/components/OrderSearchModal.vue`
- Create: `frontend/src/components/TransactionFormModal.vue`
- Create: `frontend/src/components/OrderSearchModal.test.js`
- Create: `frontend/src/components/TransactionFormModal.test.js`
- Create: `frontend/src/views/TransactionPage.vue`
- Modify: `frontend/src/router.js`

**Interfaces:**
- Consumes: `GET /api/orders/search/?q=`, `GET/POST /api/transactions/`。
- Produces: `OrderSearchModal` emits `select(order)`; `TransactionFormModal` emits `saved(transaction)`。

- [ ] **Step 1: 写失败的订单搜索测试**

```javascript
it('selects an order for an order expense', async () => {
  api.get.mockResolvedValue({ data: [{
    id: 9, customer_name: 'ACME', country: '英国',
    order_no: 'SO-9', total_amount: '1000', currency: 'USD',
  }] })
  render(OrderSearchModal, { props: { open: true } })
  await userEvent.type(screen.getByLabelText('搜索订单'), 'ACME')
  expect(await screen.findByText('ACME｜英国｜SO-9｜USD 1000')).toBeInTheDocument()
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `npm run test:unit -- OrderSearchModal.test.js TransactionFormModal.test.js`

Expected: FAIL，组件不存在。

- [ ] **Step 3: 实现统一登记与搜索弹窗**

Replace generic `transactions` resource routing with `TransactionPage`. The form chooses kind, original amount, exchange rate and RMB amount; customer receipts and supplier payments require their correct counterparty. For an order expense, an order search button opens the modal and renders exactly `客户名称｜国家｜订单号｜订单金额`; no order submits a period expense. Add filters for counterparty, contract, direction, kind, status, dates and currency. Confirmed rows expose “作废并重记”, never inline amount editing.

- [ ] **Step 4: 运行组件测试与构建**

Run: `npm run test:unit -- OrderSearchModal.test.js TransactionFormModal.test.js`

Run: `npm run build`

Expected: PASS.

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/OrderSearchModal.vue frontend/src/components/TransactionFormModal.vue frontend/src/components/OrderSearchModal.test.js frontend/src/components/TransactionFormModal.test.js frontend/src/views/TransactionPage.vue frontend/src/router.js
git commit -m "feat: add unified finance transaction entry"
```

## Task 6: 在订单、采购单和详情页展示财务结果

**Files:**
- Modify: `frontend/src/components/OrderDetailModal.vue`
- Modify: `frontend/src/views/PurchaseOrderPage.vue`
- Modify: `frontend/src/components/EntityDetailModal.vue`
- Modify: `frontend/src/views/PurchaseOrderPage.test.js`
- Modify: `backend/crm/tests/test_finance.py`

**Interfaces:**
- Consumes: order/purchase workbench fields `payment_summary`, `plans`, `expense_summary`, `profit_summary`。
- Produces: 从订单或采购单预填关联单据和可用计划的收付款登记入口。

- [ ] **Step 1: 写失败的展示测试**

```javascript
it('shows purchase payable, paid and outstanding amounts', async () => {
  api.get.mockResolvedValue({ data: {
    purchase: { purchase_no: 'PO-1' },
    payment_summary: { payable_amount: '1000', paid_amount: '300', balance_amount: '700' },
  } })
  render(PurchaseOrderPage)
  expect(await screen.findByText('待付 700')).toBeInTheDocument()
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `npm run test:unit -- PurchaseOrderPage.test.js`

Expected: FAIL，尚未渲染财务汇总。

- [ ] **Step 3: 实现单据内联动**

Order detail displays receivable, received, outstanding, linked purchases, linked expenses and estimated gross profit in RMB. Purchase detail displays payable, paid and outstanding. Both open unified transaction entry with the contract and candidate plans prefilled. Entity detail pages expose finance plans and transactions without changing existing inventory sections.

- [ ] **Step 4: 运行集成回归**

Run: `npm run test:unit -- PurchaseOrderPage.test.js`

Run: `python manage.py test crm.tests.test_finance crm.tests.test_fulfillment crm.tests.test_quotes -v 1`

Expected: PASS.

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/OrderDetailModal.vue frontend/src/views/PurchaseOrderPage.vue frontend/src/components/EntityDetailModal.vue frontend/src/views/PurchaseOrderPage.test.js backend/crm/tests/test_finance.py
git commit -m "feat: connect finance summaries to orders and purchases"
```

## Task 7: 完整业务场景验证

**Files:**
- Modify: `backend/crm/tests/test_finance.py`
- Modify: `frontend/src/views/FinanceDashboardPage.test.js`
- Modify: `frontend/src/views/PaymentPlanPage.test.js`

**Interfaces:**
- Consumes: Tasks 1–6 的 API、服务和页面。
- Produces: 可重复运行的贸易订单资金周期回归覆盖。

- [ ] **Step 1: 写端到端场景测试**

```python
def test_order_driven_trade_cash_cycle(self):
    order = create_confirmed_order(currency="USD", total="1000")
    purchase = create_purchase_order(order, currency="CNY", total="5000")
    pay_purchase_deposit(purchase, amount="1500", rmb_amount="1500")
    receive_customer_deposit(order, amount="300", rmb_amount="2160")
    add_order_expense(order, amount="200", currency="CNY", rmb_amount="200")
    dashboard = finance_dashboard()
    self.assertEqual(dashboard["metrics"]["receivable_rmb"], Decimal("5040"))
    self.assertEqual(dashboard["metrics"]["payable_rmb"], Decimal("3500"))
```

- [ ] **Step 2: 运行完整验证**

Run: `python manage.py test crm.tests.test_finance crm.tests.test_fulfillment crm.tests.test_quotes -v 1`

Run: `npm run test:unit`

Run: `npm run build`

Expected: all PASS.

- [ ] **Step 3: 手动验证页面**

Run development services and verify `/finance`, `/receivables`, `/payables`, `/transactions`, an order detail and a purchase detail. Verify order expense fuzzy search displays `客户名称｜国家｜订单号｜订单金额`, and no account-balance UI is present.

- [ ] **Step 4: 提交**

```bash
git add backend/crm/tests/test_finance.py frontend/src/views/FinanceDashboardPage.test.js frontend/src/views/PaymentPlanPage.test.js
git commit -m "test: cover finance operating ledger workflow"
```

