"""Historical edge-flow evidence retained for audit purposes.

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

from crm.models import InventoryMovement, InventoryReservation, Order, Transaction


class Command(BaseCommand):
    help = "Retired historical edge-case checks; execution is blocked."

    def handle(self, *args, **options):
        raise CommandError(
            "run_edge_business_flow_checks is retired and cannot be used as a QA/UAT gate. "
            "Use the current isolated API, unit, and browser suites instead."
        )
        client = APIClient()
        client.raise_request_exception = False
        tag = f"EDGE-{date.today():%Y%m%d}-{uuid4().hex[:6].upper()}"
        checks, failures = [], []

        def check(name, condition, detail=""):
            checks.append(name)
            if condition:
                self.stdout.write(self.style.SUCCESS(f"PASS {len(checks):02d} | {name}"))
            else:
                failures.append(f"{name}: {detail or 'assertion failed'}")
                self.stdout.write(self.style.ERROR(f"FAIL {len(checks):02d} | {name} | {detail}"))

        def error(name, response, text=""):
            body = str(getattr(response, "data", getattr(response, "content", b"")))[:300]
            check(name, response.status_code == status.HTTP_400_BAD_REQUEST and text in body, f"status={response.status_code}, body={body}")

        def post(path, payload):
            return client.post(path, payload, format="json")

        today = date.today().isoformat()
        future = (date.today() + timedelta(days=21)).isoformat()

        session = client.get("/api/session/current-operator/")
        check("会话：当前操作人接口可用", session.status_code == 200 and "name" in session.data, str(session.data))
        next_customer_code = client.get("/api/customers/next-code/")
        check("客户：预览下一个客户编码", next_customer_code.status_code == 200 and next_customer_code.data["code"], str(next_customer_code.data))
        customer = post("/api/customers/", {"name": f"{tag} 客户", "country": "United States", "source": "Edge test", "status": "opportunity", "contacts": [{"name": "Edge Buyer", "email": "edge@example.com"}]})
        check("客户：创建商机客户", customer.status_code == 201, str(customer.data))
        customer_id = customer.data["id"]
        sources = client.get("/api/customers/sources/")
        check("客户：来源下拉包含新来源", sources.status_code == 200 and any(x["value"] == "Edge test" for x in sources.data), str(sources.data))
        contacts = client.get(f"/api/contacts/?customer={customer_id}")
        check("客户：联系人筛选正确", contacts.status_code == 200 and contacts.data["count"] == 1, str(contacts.data))
        followup = post("/api/follow-ups/", {"customer": customer_id, "contact": contacts.data["results"][0]["id"], "followed_at": f"{today}T08:00:00Z", "type": "call", "subject": "到期跟进", "next_follow_up": today})
        check("跟进：创建到期跟进", followup.status_code == 201, str(followup.data))
        due_followups = client.get(f"/api/follow-ups/?customer={customer_id}&due=true")
        check("跟进：到期筛选正确", due_followups.status_code == 200 and due_followups.data["count"] == 1, str(due_followups.data))
        followup_methods = client.get("/api/follow-ups/methods/")
        check("跟进：跟进方式字典可用", followup_methods.status_code == 200 and any(x["value"] == "call" for x in followup_methods.data), str(followup_methods.data))

        root = post("/api/categories/", {"name": f"{tag} 根分类"})
        check("分类：创建根分类", root.status_code == 201, str(root.data))
        child = post("/api/categories/", {"name": f"{tag} 子分类", "parent": root.data["id"]})
        check("分类：创建子分类", child.status_code == 201, str(child.data))
        tree = client.get("/api/categories/tree/")
        check("分类：分类树读取", tree.status_code == 200 and any(x["id"] == child.data["id"] for x in tree.data), str(tree.data))
        cycle = post("/api/categories/reorder/", {"id": root.data["id"], "parent": child.data["id"], "index": 0})
        error("分类：禁止移动到子分类形成环", cycle, "不能把分类")
        reorder = post("/api/categories/reorder/", {"id": child.data["id"], "parent": root.data["id"], "index": 0})
        check("分类：同级排序成功", reorder.status_code == 200, str(reorder.data))
        attr_one = post("/api/category-attributes/", {"category": child.data["id"], "name": "电压", "key": "voltage", "default_value": "220V"})
        attr_two = post("/api/category-attributes/", {"category": child.data["id"], "name": "光通量", "key": "lm", "default_value": "1000"})
        check("分类：创建两个可排序属性", attr_one.status_code == 201 and attr_two.status_code == 201, f"{attr_one.data}; {attr_two.data}")
        malformed_attr_sort = post("/api/category-attributes/reorder/", {"category": child.data["id"], "ids": [attr_one.data["id"]]})
        error("分类：不完整属性排序被拦截", malformed_attr_sort, "不一致")
        valid_attr_sort = post("/api/category-attributes/reorder/", {"category": child.data["id"], "ids": [attr_two.data["id"], attr_one.data["id"]]})
        check("分类：完整属性排序成功", valid_attr_sort.status_code == 200, str(valid_attr_sort.data))

        next_product_code = client.get("/api/products/next-code/")
        check("产品：预览下一个产品编码", next_product_code.status_code == 200 and next_product_code.data["code"].startswith("SPU"), str(next_product_code.data))
        product = post("/api/products/", {"name": f"{tag} 产品", "category": child.data["id"], "status": "active"})
        check("产品：创建产品", product.status_code == 201, str(product.data))
        product_id = product.data["id"]
        sku = post("/api/skus/", {"product": product_id, "sku": f"{tag}-A", "cost_price": "2", "default_price": "6"})
        check("SKU：创建 SKU", sku.status_code == 201, str(sku.data))
        sku_id = sku.data["id"]
        duplicate_sku = post("/api/skus/", {"product": product_id, "sku": f"{tag}-A"})
        error("SKU：重复编码被拦截", duplicate_sku, "unique")
        inactive = client.patch(f"/api/skus/{sku_id}/", {"active": False}, format="json")
        check("SKU：可停用 SKU", inactive.status_code == 200 and not inactive.data["active"], str(inactive.data))
        hidden_skus = client.get(f"/api/skus/?product={product_id}")
        check("SKU：默认列表隐藏停用 SKU", hidden_skus.status_code == 200 and hidden_skus.data["count"] == 0, str(hidden_skus.data))
        inactive_skus = client.get(f"/api/skus/?product={product_id}&include_inactive=1")
        check("SKU：显式参数可查看停用 SKU", inactive_skus.status_code == 200 and inactive_skus.data["count"] == 1, str(inactive_skus.data))
        image_missing = client.post(f"/api/skus/{sku_id}/image/", {}, format="multipart")
        error("SKU：缺失图片上传被提示", image_missing, "请上传图片")
        client.patch(f"/api/skus/{sku_id}/", {"active": True}, format="json")

        manual_forbidden = post("/api/inventory-movements/", {"movement_no": f"{tag}-FORBID", "movement_date": today, "type": "purchase_in", "sku": sku_id, "quantity": "2"})
        error("库存：手工采购入库被拦截", manual_forbidden, "仅允许")
        manual = post("/api/inventory-movements/", {"movement_no": f"{tag}-ADJ", "movement_date": today, "type": "adjust_in", "sku": sku_id, "quantity": "5", "notes": "盘点"})
        check("库存：手工盘盈入库成功", manual.status_code == 201 and manual.data["source_type"] == "manual", str(manual.data))
        sku_after_adjust = client.get(f"/api/skus/{sku_id}/")
        check("库存：SKU 实际数量更新", sku_after_adjust.status_code == 200 and sku_after_adjust.data["actual_quantity"] == Decimal("5"), str(sku_after_adjust.data))

        client.patch(f"/api/customers/{customer_id}/", {"country": "Mars"}, format="json")
        invalid_country_quote = post("/api/quotes/", {"customer": customer_id, "quote_date": today, "items": [{"sku": sku_id, "quantity": "1", "unit_price": "6"}]})
        error("报价：不支持国家名称被提示", invalid_country_quote, "无法识别客户国家/地区")
        client.patch(f"/api/customers/{customer_id}/", {"country": "United States of America"}, format="json")
        quote = post("/api/quotes/", {"customer": customer_id, "quote_date": today, "valid_until": future, "currency": "USD", "items": [{"sku": sku_id, "quantity": "2", "unit_price": "6"}]})
        check("报价：支持国家可生成报价号", quote.status_code == 201 and "US" in quote.data["quote_no"], str(quote.data))
        quote_id = quote.data["id"]
        blank_note = post(f"/api/quotes/{quote_id}/important-notes/", {"content": "<br>"})
        error("报价：空重要备注被拦截", blank_note, "不能为空")
        second_customer = post("/api/customers/", {"name": f"{tag} 第二客户", "country": "United States", "contacts": [{"name": "Second"}]})
        wrong_revision_customer = post(f"/api/quotes/{quote_id}/revise/", {"revision_summary": "非法换客户", "customer": second_customer.data["id"]})
        error("报价：修订版更换客户被拦截", wrong_revision_customer, "不能更换客户")
        quote_workbench = client.get(f"/api/quotes/{quote_id}/workbench/")
        check("报价：工作台读取版本与订单汇总", quote_workbench.status_code == 200 and quote_workbench.data["quote"]["id"] == quote_id, str(quote_workbench.data))
        draft = client.get(f"/api/quotes/{quote_id}/order-draft/")
        check("报价：订单草稿继承报价商品", draft.status_code == 200 and draft.data["items"][0]["sku"] == sku_id, str(draft.data))

        empty_order = post("/api/orders/", {"order_no": f"{tag}-EMPTY", "customer": customer_id, "order_date": today, "items": []})
        error("订单：空商品明细被拦截", empty_order, "至少需要")
        order = post("/api/orders/", {"order_no": f"{tag}-SO", "customer": customer_id, "quote": quote_id, "order_date": today, "expected_ship_date": future, "status": "confirmed", "currency": "USD", "items": [{"sku": sku_id, "quantity": "3", "unit_price": "6"}]})
        check("订单：确认订单创建成功", order.status_code == 201, str(order.data))
        order_id = order.data["id"]
        order_item_id = order.data["items"][0]["id"]
        reservation = InventoryReservation.objects.filter(order_item_id=order_item_id).first()
        check("订单：确认订单自动预留现货", reservation is not None and reservation.quantity == Decimal("3"), str(reservation))
        other_sku = post("/api/skus/", {"product": product_id, "sku": f"{tag}-B"})
        mismatch_inventory = post("/api/inventory-movements/", {"movement_no": f"{tag}-MISMATCH", "movement_date": today, "type": "adjust_in", "sku": other_sku.data["id"], "order": order_id, "quantity": "1"})
        error("库存：订单无此 SKU 的流水被拦截", mismatch_inventory, "不在该订单")
        cancelled = client.patch(f"/api/orders/{order_id}/", {"status": "cancelled"}, format="json")
        check("订单：订单可取消", cancelled.status_code == 200 and cancelled.data["status"] == "cancelled", str(cancelled.data))
        check("订单：取消后释放库存预留", not InventoryReservation.objects.filter(order_item_id=order_item_id).exists())
        order_draft_update = client.patch(f"/api/orders/{order_id}/", {"status": "draft"}, format="json")
        check("订单：重新草稿后无预留", order_draft_update.status_code == 200 and not InventoryReservation.objects.filter(order_item__order_id=order_id).exists(), str(order_draft_update.data))

        plan = Order.objects.get(pk=order_id).payment_plans.first()
        currency_mismatch = post(f"/api/payment-plans/{plan.id}/settle/", {"transaction_date": today, "amount": "1", "currency": "EUR", "exchange_rate": "7.2", "category": "测试收款"})
        error("财务：计划收款币种不一致被拦截", currency_mismatch, "币种")
        direct_transaction = post("/api/transactions/", {"transaction_date": today, "direction": "expense", "kind": "period_expense", "category": "测试费用", "amount": "3", "currency": "USD", "exchange_rate": "7.2"})
        check("财务：非合同费用流水可登记", direct_transaction.status_code == 201 and direct_transaction.data["kind"] == "period_expense", str(direct_transaction.data))
        transaction_id = direct_transaction.data["id"]
        locked_transaction = client.patch(f"/api/transactions/{transaction_id}/", {"notes": "改写"}, format="json")
        error("财务：确认流水禁止直接修改", locked_transaction, "不能直接修改")
        voided_transaction = post(f"/api/transactions/{transaction_id}/void/", {})
        check("财务：确认流水可作废", voided_transaction.status_code == 200 and voided_transaction.data["status"] == "cancelled", str(voided_transaction.data))
        repeated_void = post(f"/api/transactions/{transaction_id}/void/", {})
        error("财务：已作废流水不可重复作废", repeated_void, "只有已确认")
        deleted_manual = client.delete(f"/api/inventory-movements/{manual.data['id']}/")
        check("库存：手工流水可删除", deleted_manual.status_code == 204, str(getattr(deleted_manual, "data", "")))
        inventory_detail = client.get(f"/api/skus/{sku_id}/inventory-detail/")
        check("库存：SKU 库存详情可读取", inventory_detail.status_code == 200 and inventory_detail.data["sku"]["id"] == sku_id, str(inventory_detail.data))
        finance_dashboard = client.get("/api/finance-dashboard/")
        check("仪表盘：财务仪表盘保持可用", finance_dashboard.status_code == 200 and "metrics" in finance_dashboard.data, str(finance_dashboard.data))
        customer_insights = client.get(f"/api/customers/{customer_id}/insights/")
        check("客户：客户洞察可读取", customer_insights.status_code == 200 and customer_insights.data["customer"]["id"] == customer_id, str(customer_insights.data))
        product_customers = client.get(f"/api/products/{product_id}/customers/")
        check("产品：产品客户分析可读取", product_customers.status_code == 200, str(product_customers.data))

        self.stdout.write(f"\nBatch: {tag} (all test data retained)")
        self.stdout.write(f"Result: {len(checks) - len(failures)}/{len(checks)} passed")
        if len(checks) != 50:
            raise RuntimeError(f"Expected exactly 50 checks, got {len(checks)}")
        if failures:
            raise RuntimeError("Edge business-flow failures:\n" + "\n".join(failures))
