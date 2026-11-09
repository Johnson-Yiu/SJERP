"""Historical business-flow evidence retained for audit purposes.

This command is no longer a supported QA or UAT entry point.  The original
implementation remains below so its historical assertions stay reviewable,
but execution is deliberately blocked; it creates persistent data and no
longer matches the current UI/API contract.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import (
    ContractChangeRequest,
    InventoryMovement,
    Order,
    PaymentPlan,
    Supplier,
    Transaction,
)
from crm.services.fulfillment import record_supplier_payment


class Command(BaseCommand):
    help = "Retired historical business-flow checks; execution is blocked."

    def handle(self, *args, **options):
        raise CommandError(
            "run_business_flow_checks is retired and cannot be used as a QA/UAT gate. "
            "Use the current isolated API, unit, and browser suites instead."
        )
        client = APIClient()
        # Expected-error checks must record server failures rather than abort the run.
        client.raise_request_exception = False
        tag = f"E2E-{date.today():%Y%m%d}-{uuid4().hex[:6].upper()}"
        sales_model_prefix = f"E{date.today():%m%d}{uuid4().hex[:6].upper()}"
        supplier_code = "".join(chr(65 + (int(ch, 16) % 26)) for ch in uuid4().hex[:2])
        while Supplier.objects.filter(code=supplier_code).exists():
            supplier_code = "".join(chr(65 + (int(ch, 16) % 26)) for ch in uuid4().hex[:2])
        checks, failures = [], []

        def check(name, condition, detail=""):
            checks.append(name)
            if condition:
                self.stdout.write(self.style.SUCCESS(f"PASS {len(checks):02d} | {name}"))
            else:
                failures.append(f"{name}: {detail or 'assertion failed'}")
                self.stdout.write(self.style.ERROR(f"FAIL {len(checks):02d} | {name} | {detail}"))

        def expected_error(name, response, code, text):
            body = str(getattr(response, "data", ""))
            check(name, response.status_code == code and text in body, f"status={response.status_code}, body={body}")

        def post(path, payload):
            return client.post(path, payload, format="json")

        today = date.today().isoformat()
        due = (date.today() + timedelta(days=30)).isoformat()

        company = post("/api/organization-units/", {"name": f"{tag} 公司", "code": f"{tag}-CO", "type": "company"})
        check("组织：创建公司", company.status_code == status.HTTP_201_CREATED, str(company.data))
        department = post("/api/organization-units/", {"name": f"{tag} 销售部", "code": f"{tag}-SA", "type": "department", "parent": company.data.get("id")})
        check("组织：部门关联公司", department.status_code == status.HTTP_201_CREATED and department.data["parent"] == company.data["id"], str(department.data))
        position = post("/api/positions/", {"name": "业务员", "code": f"{tag}-REP", "unit": department.data.get("id"), "level": "staff"})
        check("组织：岗位关联部门", position.status_code == status.HTTP_201_CREATED, str(position.data))

        missing_contact = post("/api/customers/", {"name": f"{tag} 缺联系人客户", "country": "DE"})
        expected_error("客户：缺少联系人被拦截并提示", missing_contact, status.HTTP_400_BAD_REQUEST, "至少填写")
        customer = post("/api/customers/", {"name": f"{tag} 客户", "country": "Germany", "status": "customer", "address": "Berlin", "contacts": [{"name": "Alice", "email": "alice@example.com", "phone": "10086", "is_primary": True}]})
        check("客户：创建客户及首要联系人", customer.status_code == status.HTTP_201_CREATED and customer.data["code"], str(customer.data))
        customer_id = customer.data["id"]
        contact = post("/api/contacts/", {"customer": customer_id, "name": "Bob", "email": "bob@example.com", "is_primary": True})
        check("客户：切换首要联系人", contact.status_code == status.HTTP_201_CREATED and client.get(f"/api/contacts/{contact.data['id']}/").data["is_primary"], str(contact.data))
        followup = post("/api/follow-ups/", {"customer": customer_id, "contact": contact.data["id"], "followed_at": f"{today}T09:00:00Z", "type": "email", "subject": f"{tag} 询价", "next_follow_up": due})
        check("客户：跟进记录关联客户和联系人", followup.status_code == status.HTTP_201_CREATED, str(followup.data))

        category = post("/api/categories/", {"name": f"{tag} 灯具"})
        check("产品：创建分类", category.status_code == status.HTTP_201_CREATED, str(category.data))
        child_category = post("/api/categories/", {"name": f"{tag} 筒灯", "parent": category.data["id"]})
        attribute = post("/api/category-attributes/", {"category": child_category.data["id"], "name": "功率", "key": "watt", "default_value": "12W", "include_in_sku": True, "uppercase": True})
        check("产品：创建分类属性", attribute.status_code == status.HTTP_201_CREATED, str(attribute.data))
        duplicate_attribute = post("/api/category-attributes/", {"category": child_category.data["id"], "name": "重复功率", "key": "watt"})
        expected_error("产品：重复属性键被拦截", duplicate_attribute, status.HTTP_400_BAD_REQUEST, "unique")
        product = post("/api/products/", {"name": f"{tag} 12W 筒灯", "name_en": "E2E Downlight", "sales_model_prefix": sales_model_prefix, "category": child_category.data["id"], "status": "active"})
        check("产品：自动生成产品编号", product.status_code == status.HTTP_201_CREATED and product.data["code"].startswith("SPU"), str(product.data))
        product_id = product.data["id"]
        sku = post("/api/skus/", {"product": product_id, "sku": f"{tag}-DL12", "specification": "12W/4000K", "cost_price": "4", "default_price": "10", "currency": "USD"})
        check("产品：创建 SKU", sku.status_code == status.HTTP_201_CREATED, str(sku.data))
        sku_id = sku.data["id"]
        parameter = post("/api/product-parameters/", {"product": product_id, "group": "光学", "name": "色温", "value": "4000", "unit": "K"})
        certificate = post("/api/product-certificates/", {"product": product_id, "name": "CE", "certificate_no": f"{tag}-CE"})
        product_context = client.get(f"/api/context/products/{product_id}/")
        check("产品：关联详情可追溯 SKU、参数、证书", product_context.status_code == status.HTTP_200_OK, str(product_context.data))

        supplier = post("/api/suppliers/", {"name": f"{tag} 供应商", "code": supplier_code, "supply_categories": [child_category.data["id"]], "payment_terms": "30 days"})
        check("采购：创建供应商", supplier.status_code == status.HTTP_201_CREATED, str(supplier.data))
        quote = post("/api/quotes/", {"customer": customer_id, "quote_date": today, "valid_until": due, "status": "sent", "currency": "USD", "exchange_rate": "7.2", "lead_time_days": 20, "deposit_ratio": "0.30", "items": [{"sku": sku_id, "quantity": "8", "unit_price": "10", "description": "12W downlight"}]})
        check("报价：创建报价及商品快照", quote.status_code == status.HTTP_201_CREATED and len(quote.data["items"]) == 1, str(quote.data))
        quote_id = quote.data["id"]
        availability = client.get(f"/api/quotes/{quote_id}/availability/")
        pi_data = client.get(f"/api/quotes/{quote_id}/pi-data/")
        note = post(f"/api/quotes/{quote_id}/important-notes/", {"content": "<script>alert(1)</script><strong>包装要求</strong>"})
        check("报价：重要备注清洗危险标签", note.status_code == status.HTTP_201_CREATED and "script" not in note.data["content"], str(note.data))
        deactivate = post(f"/api/quotes/{quote_id}/important-notes/{note.data['id']}/deactivate/", {})
        check("报价：重要备注可失效并保留记录", deactivate.status_code == status.HTTP_200_OK and not deactivate.data["is_active"], str(deactivate.data))
        restore = post(f"/api/quotes/{quote_id}/important-notes/{note.data['id']}/restore/", {})
        check("报价：重要备注可恢复", restore.status_code == status.HTTP_200_OK and restore.data["is_active"], str(restore.data))
        missing_revision = post(f"/api/quotes/{quote_id}/revise/", {"items": quote.data["items"]})
        expected_error("报价：缺少修订说明被拦截", missing_revision, status.HTTP_400_BAD_REQUEST, "说明")
        revision = post(f"/api/quotes/{quote_id}/revise/", {"revision_summary": "客户调整数量", "items": [{"sku": sku_id, "quantity": "9", "unit_price": "10"}]})
        check("报价：创建修订版本", revision.status_code == status.HTTP_201_CREATED and revision.data["revision_no"] == 1, str(revision.data))
        saved_update = client.patch(f"/api/quotes/{quote_id}/", {"notes": "should fail"}, format="json")
        expected_error("报价：已保存报价禁止直接修改", saved_update, status.HTTP_400_BAD_REQUEST, "创建迭代版本")
        saved_delete = client.delete(f"/api/quotes/{quote_id}/")
        expected_error("报价：已保存报价禁止删除", saved_delete, status.HTTP_405_METHOD_NOT_ALLOWED, "permanent")

        mismatch_order = post("/api/orders/", {"order_no": f"{tag}-MISMATCH", "customer": customer_id + 999999, "quote": quote_id, "order_date": today, "items": [{"sku": sku_id, "quantity": "8", "unit_price": "10"}]})
        check("订单：非法客户引用被拦截", mismatch_order.status_code == status.HTTP_400_BAD_REQUEST, str(mismatch_order.data))
        order = post("/api/orders/", {"order_no": f"{tag}-SO", "customer": customer_id, "quote": quote_id, "order_date": today, "expected_ship_date": due, "status": "confirmed", "currency": "USD", "exchange_rate": "7.2", "items": [{"sku": sku_id, "quantity": "8", "unit_price": "10", "cost_price": "4"}]})
        check("订单：由报价转订单", order.status_code == status.HTTP_201_CREATED and order.data["quote"] == quote_id, str(order.data))
        order_id = order.data["id"]
        fulfillment = client.get(f"/api/orders/{order_id}/fulfillment/")
        check("订单：库存不足时显示待采购量", fulfillment.status_code == status.HTTP_200_OK and fulfillment.data["items"][0]["to_procure_quantity"] == Decimal("8"), str(fulfillment.data))
        plans = client.get(f"/api/payment-plans/?order={order_id}")
        check("订单：自动生成定金和尾款计划", plans.status_code == status.HTTP_200_OK and plans.data["count"] == 2, str(plans.data))

        purchase = post("/api/purchase-orders/", {"purchase_no": f"{tag}-PO", "supplier": supplier.data["id"], "order": order_id, "order_date": today, "expected_arrival_date": due, "status": "ordered", "currency": "USD", "exchange_rate": "7.2", "items": [{"sku": sku_id, "quantity": "10", "unit_price": "4"}]})
        check("采购：创建采购单并关联销售订单", purchase.status_code == status.HTTP_201_CREATED, str(purchase.data))
        purchase_id = purchase.data["id"]
        purchase_item_id = purchase.data["items"][0]["id"]
        payable_plans = client.get(f"/api/payment-plans/?purchase_order={purchase_id}")
        check("采购：自动生成应付计划", payable_plans.status_code == status.HTTP_200_OK and payable_plans.data["count"] == 2, str(payable_plans.data))
        bad_item_receipt = post(f"/api/purchase-orders/{purchase_id}/receive/", {"purchase_item": 999999, "receipt_date": today, "quantity": "1", "unit_cost": "4"})
        expected_error("收货：非本采购单明细被拦截", bad_item_receipt, status.HTTP_400_BAD_REQUEST, "不属于")
        zero_receipt = post(f"/api/purchase-orders/{purchase_id}/receive/", {"purchase_item": purchase_item_id, "receipt_date": today, "quantity": "0", "unit_cost": "4"})
        expected_error("收货：零数量被拦截", zero_receipt, status.HTTP_400_BAD_REQUEST, "0.01")
        receipt = post(f"/api/purchase-orders/{purchase_id}/receive/", {"purchase_item": purchase_item_id, "receipt_date": today, "quantity": "4", "unit_cost": "4"})
        check("收货：部分到货自动生成入库流水", receipt.status_code == status.HTTP_201_CREATED and receipt.data["inventory_movement"], str(receipt.data))
        over_receipt = post(f"/api/purchase-orders/{purchase_id}/receive/", {"purchase_item": purchase_item_id, "receipt_date": today, "quantity": "7", "unit_cost": "4"})
        expected_error("收货：超到无原因被拦截", over_receipt, status.HTTP_400_BAD_REQUEST, "超到必须")
        approved_over_receipt = post(f"/api/purchase-orders/{purchase_id}/receive/", {"purchase_item": purchase_item_id, "receipt_date": today, "quantity": "7", "unit_cost": "4", "is_overage": True, "overage_reason": "gift"})
        check("收货：超到有原因可登记", approved_over_receipt.status_code == status.HTTP_201_CREATED and approved_over_receipt.data["is_overage"], str(approved_over_receipt.data))
        payment = client.post(f"/api/purchase-orders/{purchase_id}/pay/", {"transaction_date": today, "amount": "12", "currency": "USD", "exchange_rate": "7.2"}, format="json", HTTP_IDEMPOTENCY_KEY=f"{tag}-payment")
        check("采购：供应商付款形成支出流水", payment.status_code == status.HTTP_201_CREATED and payment.data["direction"] == "expense", str(payment.data))
        po = Order.objects.get(pk=order_id).purchase_orders.get(pk=purchase_id)
        try:
            record_supplier_payment(po, {"transaction_date": date.today(), "amount": "999", "currency": "USD", "exchange_rate": "7.2"})
            supplier_overpay_blocked = False
        except Exception as exc:  # Service must give a domain validation error.
            supplier_overpay_blocked = "不能超过采购单未付金额" in str(exc)
        check("采购：超过未付金额的付款被拦截", supplier_overpay_blocked)

        order_item_id = order.data["items"][0]["id"]
        insufficient_shipment = post(f"/api/orders/{order_id}/ship/", {"shipment_no": f"{tag}-SH-BAD", "shipment_date": today, "items": [{"order_item": order_item_id, "quantity": "20", "overage_reason": "customer_addon"}]})
        expected_error("发货：库存不足被拦截", insufficient_shipment, status.HTTP_400_BAD_REQUEST, "库存不足")
        shipment = post(f"/api/orders/{order_id}/ship/", {"shipment_no": f"{tag}-SH-1", "shipment_date": today, "items": [{"order_item": order_item_id, "quantity": "3"}]})
        check("发货：正常发货自动出库", shipment.status_code == status.HTTP_201_CREATED, str(shipment.data))
        no_reason_over_shipment = post(f"/api/orders/{order_id}/ship/", {"shipment_no": f"{tag}-SH-OVER-BAD", "shipment_date": today, "items": [{"order_item": order_item_id, "quantity": "6"}]})
        expected_error("发货：超发无原因被拦截", no_reason_over_shipment, status.HTTP_400_BAD_REQUEST, "超发必须")
        addon_shipment = post(f"/api/orders/{order_id}/ship/", {"shipment_no": f"{tag}-SH-ADD", "shipment_date": today, "items": [{"order_item": order_item_id, "quantity": "6", "overage_reason": "customer_addon"}]})
        check("发货：客户追加超发自动补订单明细", addon_shipment.status_code == status.HTTP_201_CREATED and Order.objects.get(pk=order_id).items.count() == 2, str(addon_shipment.data))
        automatic_movement = InventoryMovement.objects.filter(source_type="shipment", source_no=f"{tag}-SH-1").first()
        protected_movement = client.patch(f"/api/inventory-movements/{automatic_movement.id}/", {"notes": "not allowed"}, format="json")
        expected_error("库存：自动流水禁止修改", protected_movement, status.HTTP_400_BAD_REQUEST, "不能修改")

        receivable = PaymentPlan.objects.filter(order_id=order_id, status="open").order_by("id").first()
        settlement = client.post(f"/api/payment-plans/{receivable.id}/settle/", {"transaction_date": today, "amount": str(receivable.planned_amount + Decimal('5')), "currency": "USD", "exchange_rate": "7.2", "category": "客户收款"}, format="json", HTTP_IDEMPOTENCY_KEY=f"{tag}-plan-settle")
        check("财务：超额收款自动拆分预收款", settlement.status_code == status.HTTP_201_CREATED and Transaction.objects.filter(kind="unallocated_advance", customer_id=customer_id).exists(), str(settlement.data))
        advance = Transaction.objects.filter(kind="unallocated_advance", customer_id=customer_id).latest("id")
        another_order = post("/api/orders/", {"order_no": f"{tag}-SO-ADV", "customer": customer_id, "order_date": today, "expected_ship_date": due, "status": "confirmed", "currency": "USD", "exchange_rate": "7.2", "items": [{"sku": sku_id, "quantity": "1", "unit_price": "10"}]})
        target_plan = PaymentPlan.objects.filter(order_id=another_order.data["id"], status="open").order_by("-planned_amount").first()
        allocation = client.post(f"/api/transactions/{advance.id}/allocate/", {"plan": target_plan.id, "amount": "5"}, format="json", HTTP_IDEMPOTENCY_KEY=f"{tag}-allocation")
        allocation_body = str(getattr(allocation, "data", getattr(allocation, "content", b"")))[:300]
        allocation_settled = getattr(allocation, "data", {}).get("settled_amount", "0")
        check("财务：预收款可核销同客户计划", allocation.status_code == status.HTTP_200_OK and Decimal(str(allocation_settled)) == Decimal("5"), allocation_body)
        inconsistent = post("/api/transactions/", {"transaction_date": today, "direction": "income", "category": "测试", "amount": "1", "currency": "USD", "exchange_rate": "7.2", "customer": customer_id + 999999, "order": order_id})
        check("财务：订单与客户不一致被拦截", inconsistent.status_code == status.HTTP_400_BAD_REQUEST, str(inconsistent.data))
        change = post("/api/contract-changes/", {"order": order_id, "amount_delta": "20", "due_date": due, "notes": "客户追加费用"})
        check("财务：创建订单变更单", change.status_code == status.HTTP_201_CREATED, str(change.data))
        approved_change = post(f"/api/contract-changes/{change.data['id']}/approve/", {})
        check("财务：确认变更单追加应收计划", approved_change.status_code == status.HTTP_201_CREATED and Decimal(str(approved_change.data["planned_amount"])) == Decimal("20"), str(approved_change.data))
        repeated_approval = post(f"/api/contract-changes/{change.data['id']}/approve/", {})
        expected_error("财务：已确认变更单不可重复确认", repeated_approval, status.HTTP_400_BAD_REQUEST, "只有待确认")

        order_workbench = client.get(f"/api/orders/{order_id}/workbench/")
        check("端到端：订单工作台汇总报价、履约、库存和财务", order_workbench.status_code == status.HTTP_200_OK and order_workbench.data["source_quote"]["id"] == quote_id, str(order_workbench.data))
        customer_context = client.get(f"/api/context/customers/{customer_id}/")
        check("端到端：客户详情可追溯报价、订单、采购和流水", customer_context.status_code == status.HTTP_200_OK, str(customer_context.data))
        dashboard = client.get("/api/dashboard/")
        check("端到端：经营仪表盘可汇总测试订单", dashboard.status_code == status.HTTP_200_OK, str(dashboard.data))
        finance_dashboard = client.get("/api/finance-dashboard/")
        check("端到端：财务仪表盘可读取收付款计划", finance_dashboard.status_code == status.HTTP_200_OK, str(finance_dashboard.data))

        self.stdout.write(f"\nBatch: {tag} (all test data retained)")
        self.stdout.write(f"Result: {len(checks) - len(failures)}/{len(checks)} passed")
        if len(checks) != 50:
            raise RuntimeError(f"Expected exactly 50 checks, got {len(checks)}")
        if failures:
            raise RuntimeError("Business-flow failures:\n" + "\n".join(failures))
