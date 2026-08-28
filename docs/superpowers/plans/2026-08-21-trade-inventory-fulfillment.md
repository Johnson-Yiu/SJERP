# 贸易型库存、采购与订单履约 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 将报价、订单、采购、收货、发货、库存和收付款串成适用于订单驱动采购贸易公司的可审计业务闭环。

**Architecture:** Django REST Framework 在现有 crm 应用中新增供应商、采购、到货和发货聚合；领域服务在数据库事务内生成不可变库存流水并回算订单履约与 SKU 库存。Vue 前端在现有单据抽屉基础上增加报价库存提示、订单履约操作和采购页面，库存页只消费后端汇总字段。

**Tech Stack:** Python 3 / Django 5.2 / Django REST Framework / SQLite 开发数据库 / Vue 3 / Vite / Vitest。

**Spec:** docs/superpowers/specs/2026-08-21-trade-inventory-fulfillment-design.md

## Global Constraints

- 首版固定使用 默认仓，不提供多仓配置或跨仓调拨。
- 报价仅显示可用库存和交期参考，绝不锁定库存。
- 订单确认时锁定可用现货并形成待采购需求；采购不依赖客户定金到账。
- 自动生成的采购入库和销售出库流水不可编辑、不可删除；手工流水仅限盘盈、盘亏、样品出库、客户退回。
- 数量和金额必须大于零；普通收货与普通发货不得超过剩余数量。
- 超到和超发必须选择原因；客户追加超发必须生成可计价订单增补明细。
- 收货、发货、供应商付款的业务单据、库存流水和财务流水必须在一个数据库事务中写入。
- 保留历史库存和财务流水；既有库存流水视为历史手工账。

---

## File Structure

| File | Responsibility |
| --- | --- |
| backend/crm/models.py | 供应商、采购、到货、发货、预留和库存流水来源字段。 |
| backend/crm/services/fulfillment.py | 分配、收货、发货、超额、取消和供应商付款的原子服务。 |
| backend/crm/serializers.py | API 输入校验与汇总资源序列化。 |
| backend/crm/views.py | ViewSet、专用动作、报价库存提示、订单履约和 SKU 库存汇总。 |
| backend/crm/urls.py | 新资源路由。 |
| backend/crm/migrations/0016_trade_fulfillment.py | 前向迁移；不改写历史流水。 |
| backend/crm/tests/test_fulfillment.py | 完整业务闭环 API 回归测试。 |
| frontend/src/views/SupplierPage.vue | 供应商维护与采购汇总。 |
| frontend/src/views/PurchaseOrderPage.vue | 采购单、分批到货和付款操作。 |
| frontend/src/components/ReceiptModal.vue | 到货登记及超到原因校验。 |
| frontend/src/components/ShipmentModal.vue | 发货登记、物流和超发校验。 |
| frontend/src/components/SupplierPaymentModal.vue | 供应商付款。 |
| frontend/src/components/OrderDetailModal.vue | 履约数据、创建采购和发货入口。 |
| frontend/src/components/QuoteEditorModal.vue | 报价行库存和参考交期提示。 |
| frontend/src/components/QuoteDetailModal.vue | 已保存报价库存提示。 |
| frontend/src/views/InventoryPage.vue | 实际、预留、可用、在途、待采购和异常。 |
| frontend/src/views/ResourcePage.vue | 自动流水只读与受限手工库存调整。 |
| frontend/src/resourceConfigs.js | 供应商和库存流水配置。 |
| frontend/src/router.js / frontend/src/App.vue | 新页面路由与导航。 |

### Task 1: 建立领域数据模型、迁移与模型约束

**Files:**
- Modify: backend/crm/models.py
- Create: backend/crm/migrations/0016_trade_fulfillment.py
- Create: backend/crm/tests/test_fulfillment.py

**Interfaces:**
- Consumes: Order、OrderItem、SKU、InventoryMovement、Transaction。
- Produces: Supplier、PurchaseOrder、PurchaseOrderItem、GoodsReceipt、Shipment、ShipmentItem、InventoryReservation；Transaction.purchase_order 与 InventoryMovement 来源审计字段。

- [ ] **Step 1: 写出失败的模型约束测试**

~~~python
def test_purchase_item_and_shipment_item_reject_non_positive_quantity(self):
    purchase = PurchaseOrder.objects.create(
        purchase_no="PO-001", supplier=self.supplier, order=self.order,
        order_date=date(2026, 8, 21), status="draft", currency="USD",
    )
    with self.assertRaises(IntegrityError):
        PurchaseOrderItem.objects.create(
            purchase_order=purchase, sku=self.sku,
            quantity=Decimal("0"), unit_price=Decimal("2"),
        )
    shipment = Shipment.objects.create(
        order=self.order, shipment_date=date(2026, 8, 21), status="draft",
    )
    with self.assertRaises(IntegrityError):
        ShipmentItem.objects.create(
            shipment=shipment, order_item=self.order_item,
            sku=self.sku, quantity=Decimal("0"),
        )
~~~

- [ ] **Step 2: 运行模型测试，确认当前失败**

Run: python manage.py test crm.tests.test_fulfillment.FulfillmentModelTests -v 2（工作目录：backend）  
Expected: FAIL，导入 Supplier、PurchaseOrder 等模型失败。

- [ ] **Step 3: 实现模型与数据库检查约束**

~~~python
class Supplier(TimestampedModel):
    name = models.CharField(max_length=200, unique=True)
    contact_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    currency = models.CharField(max_length=10, default="USD")
    payment_terms = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

class PurchaseOrder(TimestampedModel):
    STATUS_CHOICES = [
        ("draft", "草稿"), ("ordered", "已下单"), ("partial", "部分到货"),
        ("completed", "已完成"), ("cancelled", "已取消"),
    ]
    purchase_no = models.CharField(max_length=40, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="purchase_orders")
    order_date = models.DateField()
    expected_arrival_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    currency = models.CharField(max_length=10, default="USD")
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, default=1)
    notes = models.TextField(blank=True)

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="purchase_order_items")
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    unit_price = models.DecimalField(max_digits=14, decimal_places=4)
    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="purchase_item_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="purchase_item_price_non_negative"),
        ]
~~~

Add GoodsReceipt(purchase_item, receipt_date, quantity, unit_cost, is_overage, overage_reason, notes, inventory_movement OneToOneField); Shipment(order, shipment_date, logistics_provider, waybill_no, status, notes); ShipmentItem(shipment, order_item, sku, quantity, is_overage, overage_reason, creates_supplement, inventory_movement OneToOneField); InventoryReservation(order_item, sku, quantity). The two inventory_movement fields are nullable during object construction and set before their outer atomic transaction commits. Add quantity-greater-than-zero checks to each. Overage reasons are overprocurement, gift, carton_variance, customer_addon, gift_or_sample, packing_variance.

Extend InventoryMovement with source_type choices manual/receipt/shipment/return, source_no, is_automatic=False, is_overage=False, overage_reason. Extend Transaction with nullable purchase_order ForeignKey(PurchaseOrder, SET_NULL, related_name="transactions").

- [ ] **Step 4: 生成并检查前向迁移**

Run: python manage.py makemigrations crm --name trade_fulfillment && python manage.py migrate（工作目录：backend）  
Expected: 创建 0016_trade_fulfillment.py 并成功迁移，不删除或改写既有记录。

- [ ] **Step 5: 运行模型测试，确认通过**

Run: python manage.py test crm.tests.test_fulfillment.FulfillmentModelTests -v 2（工作目录：backend）  
Expected: PASS。

- [ ] **Step 6: 提交模型变更**

~~~bash
git add backend/crm/models.py backend/crm/migrations/0016_trade_fulfillment.py backend/crm/tests/test_fulfillment.py
git commit -m "feat: add procurement and fulfillment domain models"
~~~

### Task 2: 实现库存分配、采购、到货、发货、付款原子服务

**Files:**
- Create: backend/crm/services/__init__.py
- Create: backend/crm/services/fulfillment.py
- Modify: backend/crm/tests/test_fulfillment.py

**Interfaces:**
- Consumes: Task 1 模型。
- Produces: allocate_order(order)、create_purchase_order(order, supplier, items)、record_receipt(purchase_item, payload)、confirm_shipment(order, payload)、record_supplier_payment(purchase_order, payload)、cancel_or_reduce_order(order, replacement_items)。

- [ ] **Step 1: 写出失败的业务服务测试**

~~~python
def test_order_allocation_uses_stock_then_marks_remaining_for_procurement(self):
    InventoryMovement.objects.create(
        movement_no="HIST-IN", movement_date=date.today(), type="purchase_in",
        sku=self.sku, quantity=Decimal("6"), warehouse="默认仓",
    )
    reservations = allocate_order(self.order)  # order item quantity is 10
    self.assertEqual(reservations[0].quantity, Decimal("6"))
    self.assertEqual(order_item_metrics(self.order_item)["to_procure_quantity"], Decimal("4"))

def test_receipt_and_shipment_create_automatic_movements(self):
    receipt = record_receipt(self.purchase_item, {
        "receipt_date": "2026-08-21", "quantity": "10", "unit_cost": "3",
    })
    self.assertTrue(receipt.inventory_movement.is_automatic)
    shipment = confirm_shipment(self.order, {
        "shipment_date": "2026-08-21",
        "items": [{"order_item": self.order_item.id, "quantity": "10"}],
    })
    self.assertEqual(shipment.items.count(), 1)
    self.assertEqual(InventoryMovement.objects.filter(source_type="shipment", is_automatic=True).count(), 1)
~~~

- [ ] **Step 2: 运行服务测试，确认当前失败**

Run: python manage.py test crm.tests.test_fulfillment.FulfillmentServiceTests -v 2（工作目录：backend）  
Expected: FAIL，crm.services.fulfillment 不存在。

- [ ] **Step 3: 实现库存口径与业务服务**

~~~python
@transaction.atomic
def allocate_order(order: Order) -> list[InventoryReservation]:
    InventoryReservation.objects.filter(order_item__order=order).delete()
    created = []
    for item in order.items.select_related("sku").order_by("id"):
        available = sku_metrics(item.sku)["available_quantity"]
        quantity = min(item.quantity, max(Decimal("0"), available))
        if quantity:
            created.append(InventoryReservation.objects.create(
                order_item=item, sku=item.sku, quantity=quantity,
            ))
    return created

def sku_metrics(sku: SKU) -> dict[str, Decimal]:
    actual = signed_inventory_quantity(sku)
    reserved = active_reservation_quantity(sku)
    in_transit = open_purchase_quantity(sku) - received_quantity_for_sku(sku)
    return {
        "actual_quantity": actual, "reserved_quantity": reserved,
        "available_quantity": actual - reserved,
        "in_transit_quantity": in_transit,
    }
~~~

Use select_for_update() for the order, purchase item, order item and SKU rows changed. record_receipt rejects a normal quantity above purchase_item.quantity minus received quantity; only an is_overage receipt with a permitted receipt reason may exceed it. It creates GoodsReceipt, one purchase_in automatic InventoryMovement, and recalculates PO status in one transaction. confirm_shipment rejects ordinary quantity above unshipped quantity or available stock; overage needs a permitted reason. customer_addon creates OrderItem using the source price and notes="超发客户追加"; other reasons create a zero-price supplement. Each shipment item creates one automatic sale_out movement.

record_supplier_payment creates confirmed expense Transaction with purchase_order, category="供应商付款", generated transaction number; reject amount above PO unpaid amount. cancel_or_reduce_order rejects reducing below shipped quantity, retains received stock, frees only unneeded reservations and leaves ordered POs unchanged.

- [ ] **Step 4: 运行服务测试，确认通过**

Run: python manage.py test crm.tests.test_fulfillment.FulfillmentServiceTests -v 2（工作目录：backend）  
Expected: PASS，收货/发货均有来源单号和自动库存流水。

- [ ] **Step 5: 提交服务变更**

~~~bash
git add backend/crm/services backend/crm/tests/test_fulfillment.py
git commit -m "feat: automate inventory fulfillment transactions"
~~~

### Task 3: 暴露受控 REST API、汇总字段和只读自动流水

**Files:**
- Modify: backend/crm/serializers.py
- Modify: backend/crm/views.py
- Modify: backend/crm/urls.py
- Modify: backend/crm/tests/test_fulfillment.py

**Interfaces:**
- Consumes: Task 2 服务与模型。
- Produces: /suppliers/、/purchase-orders/、/purchase-orders/{id}/receive/、/purchase-orders/{id}/pay/、/orders/{id}/fulfillment/、/orders/{id}/ship/、/quotes/{id}/availability/。

- [ ] **Step 1: 写出失败的 API 测试**

~~~python
def test_automatic_inventory_movement_is_read_only(self):
    movement = self.create_automatic_receipt_movement()
    response = self.client.patch(
        "/api/inventory-movements/{}/".format(movement.id),
        {"notes": "changed"}, format="json",
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("自动", response.data["detail"])

def test_quote_availability_does_not_create_reservation(self):
    response = self.client.get("/api/quotes/{}/availability/".format(self.quote.id))
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(response.data["items"][0]["available_quantity"], "6.00")
    self.assertFalse(InventoryReservation.objects.exists())
~~~

- [ ] **Step 2: 运行 API 测试，确认当前失败**

Run: python manage.py test crm.tests.test_fulfillment.FulfillmentApiTests -v 2（工作目录：backend）  
Expected: FAIL，专用动作与只读保护尚未实现。

- [ ] **Step 3: 实现序列化器、ViewSet 和动作**

~~~python
class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related("supplier", "order").prefetch_related("items__sku", "items__receipts", "transactions")
    serializer_class = PurchaseOrderSerializer

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        input_serializer = ReceiptInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        receipt = record_receipt(
            self.get_object().items.get(pk=input_serializer.validated_data["purchase_item"].id),
            input_serializer.validated_data,
        )
        return Response(GoodsReceiptSerializer(receipt).data, status=201)
~~~

Add PurchaseOrder.pay and Order.ship actions using their Task 2 services. Add Order.fulfillment returning order, items, purchase_orders, shipments and fulfillment_summary; each item includes allocated_quantity, to_procure_quantity, in_transit_quantity, arrived_quantity, shipped_quantity, unshipped_quantity. Add Order.create_purchase_draft returning only unprocured lines. Add Quote.availability returning each quote item available_quantity and reference_lead_time_days without calling allocate_order.

InventoryMovementViewSet must reject update and destroy when instance.is_automatic; create may only accept adjust_in, adjust_out, sample_out, return_in and defaults to source_type="manual". SKU responses expose actual_quantity, reserved_quantity, available_quantity, in_transit_quantity, to_procure_quantity, has_anomaly; old stock_quantity equals actual_quantity. Register suppliers and purchase-orders.

- [ ] **Step 4: 运行 API 测试，确认通过**

Run: python manage.py test crm.tests.test_fulfillment.FulfillmentApiTests -v 2（工作目录：backend）  
Expected: PASS，普通越界返回 400，带原因的超额创建完整关联记录。

- [ ] **Step 5: 提交 API 变更**

~~~bash
git add backend/crm/serializers.py backend/crm/views.py backend/crm/urls.py backend/crm/tests/test_fulfillment.py
git commit -m "feat: expose procurement and fulfillment APIs"
~~~

### Task 4: 将订单创建、编辑和取消接入库存预留

**Files:**
- Modify: backend/crm/serializers.py
- Modify: backend/crm/views.py
- Modify: backend/crm/tests/test_fulfillment.py

**Interfaces:**
- Consumes: allocate_order、cancel_or_reduce_order、Order.fulfillment。
- Produces: 订单 POST/PATCH 的预留生命周期；取消订单释放预留但不删除业务记录。

- [ ] **Step 1: 写出失败的订单生命周期测试**

~~~python
def test_creating_an_order_reserves_only_available_stock_and_cancellation_releases_it(self):
    self.make_stock(quantity="6")
    response = self.client.post("/api/orders/", self.order_payload(quantity="10"), format="json")
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    self.assertEqual(InventoryReservation.objects.get().quantity, Decimal("6"))
    response = self.client.patch(
        "/api/orders/{}/".format(response.data["id"]),
        {"status": "cancelled"}, format="json",
    )
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertFalse(InventoryReservation.objects.exists())
~~~

- [ ] **Step 2: 运行订单生命周期测试，确认当前失败**

Run: python manage.py test crm.tests.test_fulfillment.OrderReservationTests -v 2（工作目录：backend）  
Expected: FAIL，创建和更新订单尚未调用分配服务。

- [ ] **Step 3: 在订单序列化器与删除语义中调用服务**

~~~python
@transaction.atomic
def create(self, validated_data):
    order = self._create_order_and_items(validated_data)
    if order.status in {"confirmed", "production", "shipped"}:
        allocate_order(order)
    return order

@transaction.atomic
def update(self, instance, validated_data):
    replacement_items = validated_data.pop("items", None)
    if validated_data.get("status") == "cancelled" or replacement_items is not None:
        return cancel_or_reduce_order(instance, replacement_items, validated_data)
    return instance
~~~

For any item edit, lock and validate before replacing; reject a SKU/quantity replacement below shipped quantity. OrderViewSet.destroy returns HTTP 405 for confirmed orders and only deletes drafts without shipment, receipt or transaction links. Update existing workbench to use the fulfillment service, not manual inventory movement inference.

- [ ] **Step 4: 运行订单生命周期测试，确认通过**

Run: python manage.py test crm.tests.test_fulfillment.OrderReservationTests -v 2（工作目录：backend）  
Expected: PASS，取消释放未发货预留，已收货不改变实际库存。

- [ ] **Step 5: 提交订单预留变更**

~~~bash
git add backend/crm/serializers.py backend/crm/views.py backend/crm/tests/test_fulfillment.py
git commit -m "feat: reserve inventory through order lifecycle"
~~~

### Task 5: 实现供应商和采购单前端及收货/付款交互

**Files:**
- Create: frontend/src/views/SupplierPage.vue
- Create: frontend/src/views/PurchaseOrderPage.vue
- Create: frontend/src/components/ReceiptModal.vue
- Create: frontend/src/components/SupplierPaymentModal.vue
- Modify: frontend/src/resourceConfigs.js
- Modify: frontend/src/router.js
- Modify: frontend/src/App.vue
- Create: frontend/src/components/ReceiptModal.test.js

**Interfaces:**
- Consumes: /suppliers/、/purchase-orders/、/purchase-orders/{id}/receive/、/purchase-orders/{id}/pay/。
- Produces: 供应商维护、采购状态、分批到货和供应商付款。

- [ ] **Step 1: 写出失败的收货表单测试**

~~~javascript
it('requires an overage reason when receipt exceeds remaining quantity', async () => {
  const wrapper = mount(ReceiptModal, {
    props: { purchaseItem: { id: 3, remaining_quantity: '4.00' } },
  })
  await wrapper.get('[aria-label="到货数量"]').setValue('5')
  await wrapper.get('form').trigger('submit')
  expect(wrapper.text()).toContain('超到必须选择原因')
})
~~~

- [ ] **Step 2: 运行前端测试，确认当前失败**

Run: npm run test -- ReceiptModal.test.js（工作目录：frontend）  
Expected: FAIL，组件尚不存在。

- [ ] **Step 3: 实现供应商、采购和收货/付款界面**

~~~javascript
const payload = computed(() => ({
  purchase_item: props.purchaseItem.id,
  receipt_date: draft.receipt_date,
  quantity: Number(draft.quantity),
  unit_cost: Number(draft.unit_cost),
  is_overage: Number(draft.quantity) > Number(props.purchaseItem.remaining_quantity),
  overage_reason: Number(draft.quantity) > Number(props.purchaseItem.remaining_quantity) ? draft.overage_reason : '',
  notes: draft.notes,
}))
async function save() {
  if (payload.value.is_overage && !payload.value.overage_reason) return setError('超到必须选择原因。')
  emit('saved', await api.post('/purchase-orders/' + props.purchaseOrderId + '/receive/', payload.value))
}
~~~

SupplierPage fields are name, contact_name, phone, email, currency, payment_terms, notes; detail shows purchase count, purchase amount, paid and unpaid. PurchaseOrderPage uses status filters draft, ordered, partial, completed, cancelled; list fields purchase number, supplier, sales order, ETA, payable, paid, unpaid, status; detail lines ordered/received/remaining, a receipt button per unreceived line, and a payment button when unpaid positive. Its new-purchase form calls /orders/{id}/create-purchase-draft/ when createFromOrder exists, requires a supplier, accepts order date and ETA, and submits purchase_no, supplier, order, currency, exchange_rate, expected_arrival_date, notes plus lines containing sku, quantity, unit_price to /purchase-orders/. The default status is ordered once saved.

SupplierPaymentModal posts transaction_date, amount, currency, exchange_rate, payment_method, reference, notes to purchase-orders/{id}/pay/; reject amount not positive and amount above unpaid_amount. Add /suppliers and /purchase-orders routes and put “供应商管理”“采购管理” before “库存” in navigation.

- [ ] **Step 4: 运行收货测试并构建**

Run: npm run test -- ReceiptModal.test.js && npm run build（工作目录：frontend）  
Expected: PASS，且 Vite 构建成功。

- [ ] **Step 5: 提交采购前端变更**

~~~bash
git add frontend/src/views/SupplierPage.vue frontend/src/views/PurchaseOrderPage.vue frontend/src/components/ReceiptModal.vue frontend/src/components/SupplierPaymentModal.vue frontend/src/components/ReceiptModal.test.js frontend/src/resourceConfigs.js frontend/src/router.js frontend/src/App.vue
git commit -m "feat: add supplier procurement and receipt screens"
~~~

### Task 6: 实现订单履约、发货和报价库存参考界面

**Files:**
- Create: frontend/src/components/ShipmentModal.vue
- Modify: frontend/src/components/OrderDetailModal.vue
- Modify: frontend/src/components/QuoteEditorModal.vue
- Modify: frontend/src/components/QuoteDetailModal.vue
- Modify: frontend/src/views/DocumentPage.vue
- Create: frontend/src/components/ShipmentModal.test.js

**Interfaces:**
- Consumes: /orders/{id}/fulfillment/、/orders/{id}/create-purchase-draft/、/orders/{id}/ship/、/quotes/{id}/availability/。
- Produces: 订单履约抽屉、采购草稿跳转、发货登记、报价库存和交期提示。

- [ ] **Step 1: 写出失败的发货超额测试**

~~~javascript
it('requires overage reason before sending customer addon', async () => {
  const wrapper = mount(ShipmentModal, {
    props: { orderId: 7, items: [{ id: 9, quantity: '10.00', unshipped_quantity: '8.00' }] },
  })
  await wrapper.get('[aria-label="发货数量-9"]').setValue('10')
  await wrapper.get('form').trigger('submit')
  expect(wrapper.text()).toContain('超发必须选择原因')
  await wrapper.get('[aria-label="超发原因-9"]').setValue('customer_addon')
  await wrapper.get('form').trigger('submit')
  expect(api.post).toHaveBeenCalledWith(
    '/orders/7/ship/', expect.objectContaining({
      items: [expect.objectContaining({ overage_reason: 'customer_addon' })],
    }),
  )
})
~~~

- [ ] **Step 2: 运行发货测试，确认当前失败**

Run: npm run test -- ShipmentModal.test.js（工作目录：frontend）  
Expected: FAIL，组件尚不存在。

- [ ] **Step 3: 实现履约抽屉、发货表单和报价提示**

~~~javascript
function validate() {
  for (const item of draft.items.filter(item => Number(item.quantity) > 0)) {
    if (Number(item.quantity) > Number(item.unshipped_quantity) && !item.overage_reason) {
      return '超发必须选择原因。'
    }
  }
  return ''
}
async function save() {
  const error = validate()
  if (error) return setError(error)
  emit('saved', await api.post('/orders/' + props.orderId + '/ship/', {
    shipment_date: draft.shipment_date, logistics_provider: draft.logistics_provider,
    waybill_no: draft.waybill_no, notes: draft.notes,
    items: draft.items.filter(item => Number(item.quantity) > 0).map(item => ({
      order_item: item.id, quantity: Number(item.quantity),
      overage_reason: Number(item.quantity) > Number(item.unshipped_quantity) ? item.overage_reason : '',
    })),
  }))
}
~~~

Replace OrderDetailModal’s existing “履约流水” tab with per-SKU ordered, allocated, to procure, in transit, arrived available, shipped, unshipped. “创建采购单” calls create-purchase-draft then routes to purchase-orders?createFromOrder={id}, prefilled only with unprocured lines. “创建发货单” opens ShipmentModal. Show POs and shipments with number/status; reload fulfillment after save.

QuoteEditorModal fetches /skus/ and renders “可用现货 N / 参考交期 X 天” below each item; QuoteDetailModal fetches quote availability and shows the same data. Neither path creates a reservation. DocumentPage refreshes quote stock after save and opens order workbench after order creation.

- [ ] **Step 4: 运行发货测试并构建**

Run: npm run test -- ShipmentModal.test.js && npm run build（工作目录：frontend）  
Expected: PASS，未选原因的超发不能提交，构建成功。

- [ ] **Step 5: 提交订单与报价前端变更**

~~~bash
git add frontend/src/components/ShipmentModal.vue frontend/src/components/ShipmentModal.test.js frontend/src/components/OrderDetailModal.vue frontend/src/components/QuoteEditorModal.vue frontend/src/components/QuoteDetailModal.vue frontend/src/views/DocumentPage.vue
git commit -m "feat: connect order fulfillment and quote availability"
~~~

### Task 7: 升级库存页和库存流水的可审计展示

**Files:**
- Modify: frontend/src/views/InventoryPage.vue
- Modify: frontend/src/views/ResourcePage.vue
- Modify: frontend/src/resourceConfigs.js
- Create: frontend/src/views/InventoryPage.test.js

**Interfaces:**
- Consumes: SKU 汇总字段、库存流水来源字段和只读 API 错误。
- Produces: 库存可用性仪表盘、库存异常、自动流水只读和受限手工调整。

- [ ] **Step 1: 写出失败的库存口径展示测试**

~~~javascript
it('renders actual, reserved, available, in-transit and to-procure values', async () => {
  mockApi.get.mockResolvedValue({
    data: [{
      sku: 'LED-01', actual_quantity: '10.00', reserved_quantity: '6.00',
      available_quantity: '4.00', in_transit_quantity: '8.00',
      to_procure_quantity: '2.00', has_anomaly: false,
    }],
  })
  const wrapper = mount(InventoryPage)
  await flushPromises()
  expect(wrapper.text()).toContain('可用库存')
  expect(wrapper.text()).toContain('4')
  expect(wrapper.text()).toContain('在途采购')
})
~~~

- [ ] **Step 2: 运行库存页测试，确认当前失败**

Run: npm run test -- InventoryPage.test.js（工作目录：frontend）  
Expected: FAIL，页面尚未展示完整库存口径。

- [ ] **Step 3: 实现库存与库存流水受控 UI**

~~~javascript
function stockState(row) {
  if (row.has_anomaly) return { label: '需处理', className: 'danger' }
  if (Number(row.available_quantity) < 0) return { label: '缺货', className: 'danger' }
  if (Number(row.to_procure_quantity) > 0) return { label: '待采购', className: 'warning' }
  if (Number(row.in_transit_quantity) > 0) return { label: '在途', className: 'info' }
  return { label: '可发', className: 'success' }
}
~~~

Show summary cards actual, reserved, available, in-transit, to-procure. Each SKU row links to orders?sku={id}, purchase-orders?sku={id}, inventory-movements?sku={id}. Extend movement list with source_type_display, source_no, is_automatic, is_overage, overage_reason_display. ResourcePage hides edit/delete for automatic inventory movements and states “系统自动生成，不能修改或删除”. Manual movement select renders only adjust_in, adjust_out, sample_out, return_in.

- [ ] **Step 4: 运行库存测试并构建**

Run: npm run test -- InventoryPage.test.js && npm run build（工作目录：frontend）  
Expected: PASS，且 Vite 构建成功。

- [ ] **Step 5: 提交库存界面变更**

~~~bash
git add frontend/src/views/InventoryPage.vue frontend/src/views/InventoryPage.test.js frontend/src/views/ResourcePage.vue frontend/src/resourceConfigs.js
git commit -m "feat: show auditable inventory availability"
~~~

### Task 8: 执行端到端回归、迁移验证和权限验收

**Files:**
- Modify: backend/crm/models.py
- Modify: backend/crm/tests/test_fulfillment.py
- Modify: frontend/src/components/OrderDetailModal.vue
- Modify: frontend/src/views/PurchaseOrderPage.vue

**Interfaces:**
- Consumes: Tasks 1–7 的 API、领域服务和界面。
- Produces: 可重复的端到端回归与人工验收清单。

- [ ] **Step 1: 写出失败的完整闭环测试**

~~~python
def test_quote_to_order_procurement_partial_receipt_shipment_and_payments(self):
    quote = self.make_quote(quantity="10")
    self.client.get("/api/quotes/{}/availability/".format(quote.id))
    self.assertFalse(InventoryReservation.objects.exists())
    order = self.create_order_from_quote(quote)
    purchase = self.create_purchase_for_order(order, quantity="10")
    self.receive(purchase.items.get(), quantity="4")
    self.receive(purchase.items.get(), quantity="6")
    self.ship(order, quantity="10")
    self.pay_supplier(purchase, amount="30")
    self.receive_customer_payment(order, amount="50")
    self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("0"))
    self.assertEqual(PurchaseOrder.objects.get(pk=purchase.pk).unpaid_amount, Decimal("0"))
    self.assertEqual(Order.objects.get(pk=order.pk).balance_amount, Decimal("0"))
~~~

- [ ] **Step 2: 运行全套后端测试**

Run: python manage.py test crm.tests -v 2（工作目录：backend）  
Expected: PASS；若失败，补充对应实现或测试夹具直到通过。

- [ ] **Step 3: 补齐权限枚举和端到端断言**

~~~python
MODULE_CHOICES = [
    ("suppliers", "供应商管理"), ("purchases", "采购管理"),
    ("receipts", "到货登记"), ("shipments", "发货管理"),
    ("inventory_adjustments", "库存调整"), ("supplier_payments", "供应商付款"),
]
~~~

Merge these six tuples into existing RolePermission.MODULE_CHOICES. When RBAC_ENFORCEMENT=true, map list/retrieve to can_view, POST to can_create, PATCH/PUT to can_update, DELETE to can_delete for each new ViewSet/action. Extend end-to-end tests: no reservation on quote view; partial receipt/shipment; normal over-limit rejection; valid over-receipt; customer_addon priced line; gift/sample zero-price line; automatic movement immutability; cancellation retains stock; supplier expense and customer income totals.

- [ ] **Step 4: 运行全部自动验证**

Run: python manage.py migrate && python manage.py test crm.tests -v 2（工作目录：backend）；npm run test -- --run && npm run build（工作目录：frontend）  
Expected: 迁移、Django 测试、Vitest 测试和前端构建全部通过。

- [ ] **Step 5: 人工验收并提交**

Use a fresh local database to: create a quote for 10 units; confirm it becomes an order and reserves only stock; create a PO before customer deposit; receive 4 then 6; pay supplier; ship 10 with logistics and waybill; record customer deposit/balance; inspect inventory, movements, PO payable and order receivable. Then verify over-receipt and customer-addon over-shipment require reasons and preserve document links.

~~~bash
git add backend/crm/models.py backend/crm/tests/test_fulfillment.py frontend/src/components/OrderDetailModal.vue frontend/src/views/PurchaseOrderPage.vue
git commit -m "test: cover trade inventory fulfillment workflow"
~~~
