"""Real HTTP regression for the synthetic sales/procurement core flow.

Reference records are isolated test fixtures. Quotes, sales orders, purchase
orders, receipts, shipments, and finance events are created only through the
application HTTP endpoints so their serializers and lifecycle transitions run.
"""

import http.client
import hashlib
import csv
import io
import json
import os
from email.message import Message
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.test import Client, LiveServerTestCase, override_settings
from openpyxl import load_workbook

from crm.models import (
    Customer,
    FulfillmentIdempotency,
    GoodsReceipt,
    InventoryMovement,
    OperationLog,
    Order,
    PaymentPlan,
    Product,
    PurchaseOrder,
    Shipment,
    SKU,
    Supplier,
    SupplierSKU,
    Transaction,
)
from crm.services.fulfillment import sku_metrics


@override_settings(
    DEVELOPMENT_SUPERADMIN=False,
    RBAC_ENFORCEMENT=True,
    AUDIT_LOG_ENABLED=True,
)
class ReviewCoreHttpTests(LiveServerTestCase):
    """Exercise persisted business transitions over Django's real HTTP server."""

    request_date = date(2026, 11, 4)

    @classmethod
    def setUpClass(cls):
        cls.evidence_dir = os.environ.get("REVIEW_CORE_EVIDENCE_DIR", "").strip()
        if cls.evidence_dir:
            evidence_path = Path(cls.evidence_dir)
            if evidence_path.exists() and any(evidence_path.iterdir()):
                raise RuntimeError(f"REVIEW_CORE_EVIDENCE_DIR must be empty for this run: {evidence_path}")
            evidence_path.mkdir(parents=True, exist_ok=True)
        super().setUpClass()

    def setUp(self):
        self.assertFalse(settings.DEVELOPMENT_SUPERADMIN)
        self.assertTrue(settings.RBAC_ENFORCEMENT)
        self.assertTrue(settings.AUDIT_LOG_ENABLED)
        suffix = self._testMethodName.lower().replace("test_", "")[:18]
        self.customer = Customer.objects.create(
            code=f"RCH-C-{suffix}",
            name=f"Review synthetic buyer {suffix}",
            country="Germany",
            address="Berlin, Germany",
        )
        self.product = Product.objects.create(
            code=f"RCH-P-{suffix}",
            name=f"Review synthetic product {suffix}",
        )
        self.sku = SKU.objects.create(
            product=self.product,
            sku=f"RCH-SKU-{suffix}",
            display_name_cn="合成测试灯具",
        )
        self.supplier = Supplier.objects.create(
            code=f"RCH-V-{suffix}",
            name=f"Review synthetic supplier {suffix}",
        )
        self.supplier_source = SupplierSKU.objects.create(
            supplier=self.supplier,
            sku=self.sku,
            supplier_sku_code=f"RCH-SOURCE-{suffix}",
            supplier_model=f"MODEL-{suffix}",
            currency="USD",
            purchase_price=Decimal("2.00"),
            moq=Decimal("1"),
            lead_time_days=5,
        )

        # This is an explicitly synthetic test superuser because RBAC is active;
        # it grants this isolated flow full application permissions only.
        # force_login establishes its Django session but does not test the ERP
        # business login entry point or prove real employee-role behavior.
        user = get_user_model().objects.create_superuser(
            username=f"review-http-{suffix}",
            email=f"review-http-{suffix}@example.invalid",
            password="isolated-test-only",
        )
        self.session_user = user
        session_client = Client()
        session_client.force_login(user)
        csrf_token = get_token(HttpRequest())
        self.cookie_header = "; ".join((
            f"{settings.SESSION_COOKIE_NAME}={session_client.cookies[settings.SESSION_COOKIE_NAME].value}",
            f"{settings.CSRF_COOKIE_NAME}={csrf_token}",
        ))
        self.csrf_token = csrf_token
        self.http_events = []
        self.saved_artifacts = {}

    def _save_evidence(self, name, content, content_type):
        digest = hashlib.sha256(content).hexdigest()
        self.assertTrue(digest)
        if not self.evidence_dir:
            return digest
        prefix = "sales" if self._testMethodName.startswith("test_quote") else "procurement"
        path = Path(self.evidence_dir) / f"{prefix}-{name}"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            self.fail(f"Refusing to overwrite existing evidence file: {path}")
        path.write_bytes(content)
        saved = path.read_bytes()
        self.assertEqual(saved, content)
        saved_digest = hashlib.sha256(saved).hexdigest()
        self.assertEqual(saved_digest, digest)
        self.saved_artifacts[path.name] = {
            "content_type": content_type,
            "bytes": len(saved),
            "sha256": saved_digest,
        }
        return saved_digest

    def _save_database_snapshot(self, name, snapshot):
        content = (json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n").encode("utf-8")
        return self._save_evidence(name, content, "application/json; charset=utf-8")

    def tearDown(self):
        if self.evidence_dir:
            prefix = "sales" if self._testMethodName.startswith("test_quote") else "procurement"
            manifest = {
                "test": self._testMethodName,
                "http_events": self.http_events,
                "artifacts": self.saved_artifacts,
            }
            content = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
            path = Path(self.evidence_dir) / f"{prefix}-manifest.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                self.fail(f"Refusing to overwrite existing evidence manifest: {path}")
            path.write_bytes(content)
            self.assertEqual(path.read_bytes(), content)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), hashlib.sha256(content).hexdigest())
        super().tearDown()

    def _request(self, method, path, data=None, headers=None):
        server = urlsplit(self.live_server_url)
        connection = http.client.HTTPConnection(server.hostname, server.port, timeout=30)
        body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
        request_headers = {
            "Accept": "application/json",
            "Cookie": self.cookie_header,
            "X-CSRFToken": self.csrf_token,
        }
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        request_headers.update(headers or {})
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            response_body = response.read()
            response_headers = {key.lower(): value for key, value in response.getheaders()}
        except (ConnectionError, OSError) as exc:
            self.fail(f"{method} {path} closed its HTTP connection without a response: {exc}")
        finally:
            connection.close()

        content_type = response_headers.get("content-type", "")
        if "json" in content_type:
            content_type_header = Message()
            content_type_header["content-type"] = content_type
            header_charset = content_type_header.get_content_charset()
            response_charset = header_charset or "utf-8"
            try:
                payload = json.loads(response_body.decode(response_charset))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = {"invalid_json_bytes": len(response_body)}
                response_charset = "invalid"
        else:
            payload = response_body
            response_charset = content_type.split("charset=", 1)[1].split(";", 1)[0].strip() if "charset=" in content_type else None
        event = {
            "method": method,
            "path": path,
            "status": response.status,
            "content_type": content_type,
            "response_charset": response_charset,
            "charset_source": (
                "Content-Type header" if "json" in content_type and header_charset
                else "JSON default UTF-8" if "json" in content_type
                else "Content-Type header" if response_charset
                else "not applicable"
            ),
            "response_bytes": len(response_body),
            "response_sha256": hashlib.sha256(response_body).hexdigest(),
            "detail": payload.get("detail") if isinstance(payload, dict) else None,
        }
        if response.status >= 400:
            event["error_response_raw_hex"] = response_body.hex()
        self.http_events.append(event)
        print("CORE_HTTP " + json.dumps(event, ensure_ascii=False, sort_keys=True))
        return response.status, payload, response_headers

    def _expect(self, method, path, expected_status, data=None, headers=None):
        status_code, payload, response_headers = self._request(method, path, data, headers)
        self.assertEqual(status_code, expected_status, f"{method} {path}: {payload!r}")
        return payload, response_headers

    def _create_accepted_quote_and_order(self, quantity="10", unit_price="25.00"):
        quote, _ = self._expect("POST", "/api/quotes/", 201, {
            "customer": self.customer.pk,
            "quote_date": self.request_date.isoformat(),
            "valid_until": "2026-12-04",
            "currency": "USD",
            "exchange_rate": "7.100000",
            "items": [{
                "sku": self.sku.pk,
                "quantity": quantity,
                "unit_price": unit_price,
                "description": "Synthetic core-flow item",
            }],
        })
        self._expect("POST", f"/api/quotes/{quote['id']}/mark-sent/", 200, {})
        accepted, _ = self._expect("POST", f"/api/quotes/{quote['id']}/accept/", 200, {})
        self.assertEqual(accepted["status"], "accepted")

        order_draft, _ = self._expect("GET", f"/api/quotes/{quote['id']}/order-draft/", 200)
        saved_order, _ = self._expect("POST", "/api/orders/", 201, order_draft)
        self.assertEqual(saved_order["status"], "draft")
        self.assertEqual(saved_order["quote"], quote["id"])
        return quote, saved_order

    def _snapshot(self, order_id=None, purchase_id=None):
        orders = Order.objects.filter(pk=order_id) if order_id else Order.objects.all()
        purchases = PurchaseOrder.objects.filter(pk=purchase_id) if purchase_id else PurchaseOrder.objects.all()
        return {
            "orders": list(orders.order_by("pk").values("id", "status", "cancellation_reason")),
            "purchases": list(purchases.order_by("pk").values("id", "status", "cancellation_reason")),
            "receipts": list(GoodsReceipt.objects.order_by("pk").values(
                "id", "purchase_item_id", "quantity", "reversal_inventory_movement_id",
            )),
            "shipments": list(Shipment.objects.order_by("pk").values("id", "status")),
            "movements": list(InventoryMovement.objects.order_by("pk").values(
                "id", "movement_no", "type", "quantity", "source_type", "source_no",
            )),
            "plans": list(PaymentPlan.objects.order_by("pk").values(
                "id", "status", "settled_amount", "planned_amount",
            )),
            "transactions": list(Transaction.objects.order_by("pk").values(
                "id", "status", "amount", "void_reason",
            )),
            "idempotency": list(FulfillmentIdempotency.objects.order_by("pk").values(
                "id", "key", "operation", "target_id", "status",
            )),
            "operation_logs": list(OperationLog.objects.order_by("pk").values(
                "id", "entity", "object_id", "operator_id", "action", "action_label",
            )),
        }

    def _assert_audit_operator(self, *, label, object_id):
        rows = list(OperationLog.objects.filter(
            action_label=label,
            object_id=str(object_id),
        ).order_by("pk"))
        self.assertTrue(rows, f"Missing audit row for {label} object={object_id}")
        self.assertTrue(all(row.operator_id == self.session_user.pk for row in rows))
        return rows

    def test_quote_export_order_and_receivable_are_saved_and_reconciled_over_http(self):
        quote, saved_order = self._create_accepted_quote_and_order()

        saved_quote, _ = self._expect("GET", f"/api/quotes/{quote['id']}/", 200)
        self.assertEqual(saved_quote["status"], "accepted")
        export_status, workbook_bytes, export_headers = self._request("GET", f"/api/quotes/{quote['id']}/export/")
        self.assertEqual(export_status, 200)
        self.assertIn("spreadsheetml.sheet", export_headers.get("content-type", ""))
        # Re-fetching and opening the endpoint's actual response verifies a saved
        # file, rather than a workbook built directly from test-side model data.
        workbook = load_workbook(BytesIO(workbook_bytes), read_only=True, data_only=False)
        self.assertIn("PI", workbook.sheetnames)
        sheet = workbook["PI"]
        exported_values = [value for row in sheet.iter_rows(values_only=True) for value in row if value is not None]
        exported_text = {str(value) for value in exported_values}
        self.assertIn(quote["quote_no"], exported_text)
        self.assertIn(self.customer.name, exported_text)
        self.assertIn("Synthetic core-flow item", exported_text)
        exported_numbers = set()
        for value in exported_values:
            if isinstance(value, (int, float, Decimal)):
                exported_numbers.add(Decimal(str(value)))
        self.assertIn(Decimal("250.00"), exported_numbers)
        workbook.close()
        self.assertEqual(workbook_bytes[:2], b"PK")
        xlsx_sha256 = self._save_evidence("quote-pi.xlsx", workbook_bytes, export_headers["content-type"])
        self.assertEqual(hashlib.sha256(workbook_bytes).hexdigest(), xlsx_sha256)

        before_quote_reject_logs = list(
            OperationLog.objects.order_by("pk").values_list("id", "operator_id", "action_label")
        )
        rejected, _ = self._expect("POST", f"/api/quotes/{quote['id']}/reject/", 400, {})
        self.assertEqual(rejected.get("detail"), "当前报价状态不能执行此操作，请创建修订版重新报价。")
        self.assertEqual(
            list(OperationLog.objects.order_by("pk").values_list("id", "operator_id", "action_label")),
            before_quote_reject_logs,
        )
        self.assertFalse(OperationLog.objects.filter(
            action_label="客户拒绝报价", object_id=str(quote["id"]),
        ).exists())
        current_quote, _ = self._expect("GET", f"/api/quotes/{quote['id']}/", 200)
        self.assertEqual(current_quote["status"], "accepted")
        self._assert_audit_operator(label="客户接受报价", object_id=quote["id"])

        self.assertEqual(PaymentPlan.objects.filter(order_id=saved_order["id"]).count(), 0)
        confirmed, _ = self._expect("POST", f"/api/orders/{saved_order['id']}/confirm/", 200, {})
        self.assertIn(confirmed["status"], {"confirmed", "production"})
        self._assert_audit_operator(label="确认销售订单", object_id=saved_order["id"])
        report_query = {
            "source": "sales",
            "group_by": "customer",
            "date_from": self.request_date.replace(day=1).isoformat(),
            "date_to": "2026-11-30",
        }
        report_data, _ = self._expect("GET", "/api/reports/data/?" + urlencode(report_query), 200)
        csv_status, csv_bytes, csv_headers = self._request(
            "GET", "/api/reports/data/?" + urlencode({**report_query, "export": "csv"}),
        )
        self.assertEqual(csv_status, 200)
        self.assertIn("text/csv", csv_headers.get("content-type", ""))
        self.assertTrue(csv_bytes.startswith(b"\xef\xbb\xbf"))
        csv_text = csv_bytes.decode("utf-8-sig")
        self.assertIn(self.customer.name, csv_text)
        self.assertEqual(csv_headers.get("content-type", "").lower().find("charset=utf-8") >= 0, True)
        xlsx_report_total = Decimal(str(report_data["totals"]["amount"]))
        csv_rows = [row for row in csv_text.splitlines() if row]
        self.assertTrue(csv_rows)
        parsed_csv = list(csv.reader(io.StringIO(csv_text)))
        self.assertGreaterEqual(len(parsed_csv), 5)
        self.assertIn(self.customer.name, csv_text)
        self.assertEqual(Decimal(parsed_csv[-1][1]), xlsx_report_total)
        csv_sha256 = self._save_evidence("sales-report.csv", csv_bytes, csv_headers["content-type"])
        self.assertEqual(hashlib.sha256(csv_bytes).hexdigest(), csv_sha256)
        plans_response, _ = self._expect(
            "GET",
            "/api/payment-plans/?" + urlencode({
                "direction": "receivable",
                "search": saved_order["order_no"],
            }),
            200,
        )
        listed_plans = plans_response.get("results", plans_response)
        self.assertTrue(listed_plans)
        plans = list(PaymentPlan.objects.filter(order_id=saved_order["id"], status="open").order_by("pk"))
        self.assertTrue(plans)
        self.assertEqual(
            sum((row.planned_amount for row in plans), Decimal("0")),
            Order.objects.get(pk=saved_order["id"]).total_amount,
        )

        plan = plans[0]
        settled, _ = self._expect("POST", f"/api/payment-plans/{plan.pk}/settle/", 201, {
            "amount": "10.00",
            "transaction_date": self.request_date.isoformat(),
        })
        self.assertEqual(settled["direction"], "income")
        plan.refresh_from_db()
        self.assertEqual(plan.settled_amount, Decimal("10.00"))

        before_rejected_settlement = self._snapshot(order_id=saved_order["id"])
        self._save_database_snapshot("before-finance.json", before_rejected_settlement)
        rejected_settlement, _ = self._expect(
            "POST", f"/api/payment-plans/{plan.pk}/settle/", 400, {
                "amount": "0.00",
                "transaction_date": self.request_date.isoformat(),
            },
        )
        self.assertEqual(rejected_settlement.get("amount"), ["必须大于零。"])
        self.assertEqual(self._snapshot(order_id=saved_order["id"]), before_rejected_settlement)

        voided, _ = self._expect(
            "POST", f"/api/transactions/{settled['id']}/void/", 200,
            {"reason": "Synthetic HTTP core-flow correction"},
        )
        self.assertEqual(voided["void_reason"], "Synthetic HTTP core-flow correction")
        plan.refresh_from_db()
        self.assertEqual(plan.settled_amount, Decimal("0"))
        self.assertEqual(plan.remaining_amount, plan.planned_amount)
        self._save_database_snapshot("after-finance.json", self._snapshot(order_id=saved_order["id"]))
        self.assertTrue(OperationLog.objects.exists())
        self.assertFalse(OperationLog.objects.exclude(operator_id=self.session_user.pk).exists())

    def test_purchase_partial_fulfillment_reversal_cancel_and_atomic_failures_over_http(self):
        quote, saved_order = self._create_accepted_quote_and_order(quantity="10", unit_price="25.00")
        order_id = saved_order["id"]
        order_item_id = saved_order["items"][0]["id"]

        allocation_path = f"/api/orders/{order_id}/items/{order_item_id}/supplier-allocation/"
        self._expect("POST", allocation_path, 200, {
            "supplier_sku": self.supplier_source.pk,
            "scope": "recommended",
            "note": "Synthetic review flow",
        })
        confirmed, _ = self._expect("POST", f"/api/orders/{order_id}/confirm/", 200, {})
        self.assertIn(confirmed["status"], {"confirmed", "production"})
        producing, _ = self._expect("POST", f"/api/orders/{order_id}/start-production/", 200, {})
        self.assertEqual(producing["status"], "production")

        plan, _ = self._expect("GET", f"/api/orders/{order_id}/procurement-plan/", 200)
        self.assertTrue(plan["items"])
        group = {
            "supplier": self.supplier.pk,
            "currency": "USD",
            "exchange_rate": "7.100000",
            "items": [{
                "order_item": order_item_id,
                "quantity": "10.00",
                "unit_price": "2.00",
            }],
        }
        generated, _ = self._expect(
            "POST", f"/api/orders/{order_id}/generate-purchase-drafts/", 201,
            {"groups": [group]},
        )
        self.assertEqual(generated["created_count"], 1)
        abandoned_id = generated["purchase_orders"][0]["id"]
        abandoned, _ = self._expect(
            "POST", f"/api/purchase-orders/{abandoned_id}/cancel/", 200,
            {"reason": "Synthetic draft cancellation"},
        )
        self.assertEqual(abandoned["status"], "cancelled")

        restored_plan, _ = self._expect("GET", f"/api/orders/{order_id}/procurement-plan/", 200)
        restored_line = next(row for row in restored_plan["items"] if row["order_item"] == order_item_id)
        self.assertEqual(Decimal(str(restored_line["draft_procurement_quantity"])), Decimal("0"))
        self.assertEqual(Decimal(str(restored_line["draftable_quantity"])), Decimal("10"))

        generated_again, _ = self._expect(
            "POST", f"/api/orders/{order_id}/generate-purchase-drafts/", 201,
            {"groups": [group]},
        )
        purchase_id = generated_again["purchase_orders"][0]["id"]
        payment_terms_snapshot = [
            {"label": "预付款", "ratio": "0.30", "due_basis": "order_date", "offset_days": 0},
            {"label": "尾款", "ratio": "0.70", "due_basis": "no_date", "offset_days": 0},
        ]
        self._expect("PATCH", f"/api/purchase-orders/{purchase_id}/", 200, {
            "payment_terms_snapshot": payment_terms_snapshot,
            "exchange_rate": "7.100000",
        })
        placed, _ = self._expect("POST", f"/api/purchase-orders/{purchase_id}/place/", 200, {})
        self.assertEqual(placed["status"], "ordered")
        self._assert_audit_operator(label="确认采购下单", object_id=purchase_id)

        payable_response, _ = self._expect(
            "GET", "/api/payment-plans/?" + urlencode({
                "direction": "payable",
                "purchase_order": purchase_id,
            }), 200,
        )
        payable_rows = payable_response.get("results", payable_response)
        self.assertTrue(payable_rows)
        payable_plan = PaymentPlan.objects.filter(purchase_order_id=purchase_id, status="open").order_by("pk").first()
        self.assertIsNotNone(payable_plan)
        payable_payment, _ = self._expect(
            "POST", f"/api/payment-plans/{payable_plan.pk}/settle/", 201, {
                "amount": "1.00",
                "transaction_date": self.request_date.isoformat(),
            },
        )
        self.assertEqual(payable_payment["direction"], "expense")
        payable_plan.refresh_from_db()
        self.assertEqual(payable_plan.settled_amount, Decimal("1.00"))
        self._expect(
            "POST", f"/api/transactions/{payable_payment['id']}/void/", 200,
            {"reason": "Synthetic payable reversal"},
        )
        payable_plan.refresh_from_db()
        self.assertEqual(payable_plan.settled_amount, Decimal("0"))

        self._save_database_snapshot(
            "before-fulfillment.json",
            self._snapshot(order_id=order_id, purchase_id=purchase_id),
        )

        purchase_item = PurchaseOrder.objects.get(pk=purchase_id).items.get()
        receipt_headers = {"Idempotency-Key": "review-core-receipt-partial"}
        receipt, _ = self._expect(
            "POST", f"/api/purchase-orders/{purchase_id}/receive/", 201, {
                "purchase_item": purchase_item.pk,
                "receipt_date": self.request_date.isoformat(),
                "quantity": "4.00",
                "unit_cost": "2.00",
            }, receipt_headers,
        )
        purchase = PurchaseOrder.objects.get(pk=purchase_id)
        self.assertEqual(purchase.status, "partial")
        self._assert_audit_operator(label="登记采购到货", object_id=purchase_id)

        before_over_receipt = self._snapshot(order_id=order_id, purchase_id=purchase_id)
        over_receipt, _ = self._expect(
            "POST", f"/api/purchase-orders/{purchase_id}/receive/", 400, {
                "purchase_item": purchase_item.pk,
                "receipt_date": self.request_date.isoformat(),
                "quantity": "7.00",
                "unit_cost": "2.00",
            }, {"Idempotency-Key": "review-core-receipt-overage"},
        )
        self.assertTrue(over_receipt.get("detail"))
        self.assertEqual(self._snapshot(order_id=order_id, purchase_id=purchase_id), before_over_receipt)

        before_po_cancel = self._snapshot(order_id=order_id, purchase_id=purchase_id)
        self._expect(
            "POST", f"/api/purchase-orders/{purchase_id}/cancel/", 400,
            {"reason": "Cannot cancel a purchase with an active receipt"},
        )
        self.assertEqual(self._snapshot(order_id=order_id, purchase_id=purchase_id), before_po_cancel)

        shipment, _ = self._expect(
            "POST", f"/api/orders/{order_id}/ship/", 201, {
                "shipment_date": self.request_date.isoformat(),
                "items": [{"order_item": order_item_id, "quantity": "3.00"}],
            }, {"Idempotency-Key": "review-core-shipment-partial"},
        )
        self._assert_audit_operator(label="确认订单发货", object_id=order_id)
        self.assertTrue(shipment.get("id"))
        self.assertEqual(Shipment.objects.filter(order_id=order_id, status="confirmed").count(), 1)
        self.assertEqual(
            sum((line.quantity for line in Shipment.objects.get(pk=shipment["id"]).items.all()), Decimal("0")),
            Decimal("3.00"),
        )

        before_order_cancel = self._snapshot(order_id=order_id, purchase_id=purchase_id)
        self._expect(
            "POST", f"/api/orders/{order_id}/cancel/", 400,
            {"reason": "Cannot cancel while a shipment is active"},
        )
        self.assertEqual(self._snapshot(order_id=order_id, purchase_id=purchase_id), before_order_cancel)

        before_receipt_reversal = self._snapshot(order_id=order_id, purchase_id=purchase_id)
        self._expect(
            "POST", f"/api/purchase-orders/{purchase_id}/receipts/{receipt['id']}/reverse/", 400,
            {"reason": "Receipt stock has been consumed"},
        )
        self.assertEqual(self._snapshot(order_id=order_id, purchase_id=purchase_id), before_receipt_reversal)

        self._expect(
            "POST", f"/api/shipments/{shipment['id']}/reverse/", 200,
            {"reason": "Synthetic partial shipment reversal"},
        )
        reversed_receipt, _ = self._expect(
            "POST", f"/api/purchase-orders/{purchase_id}/receipts/{receipt['id']}/reverse/", 200,
            {"reason": "Synthetic receipt reversal after shipment reversal"},
        )
        self.assertTrue(reversed_receipt)

        cancelled_purchase, _ = self._expect(
            "POST", f"/api/purchase-orders/{purchase_id}/cancel/", 200,
            {"reason": "Synthetic purchase cancellation after reversal"},
        )
        self.assertEqual(cancelled_purchase["status"], "cancelled")
        cancelled_order, _ = self._expect(
            "POST", f"/api/orders/{order_id}/cancel/", 200,
            {"reason": "Synthetic order cancellation after reversals"},
        )
        self.assertEqual(cancelled_order["status"], "cancelled")

        order = Order.objects.get(pk=order_id)
        self.assertTrue(order.payment_plans.filter(status="cancelled").exists())
        self.assertTrue(PaymentPlan.objects.filter(purchase_order_id=purchase_id, status="cancelled").exists())
        metrics = sku_metrics(self.sku)
        self.assertEqual(metrics["actual_quantity"], Decimal("0"))
        self.assertEqual(metrics["reserved_quantity"], Decimal("0"))
        self.assertFalse(FulfillmentIdempotency.objects.filter(
            key__in=("review-core-receipt-overage",),
        ).exists())
        self.assertTrue(FulfillmentIdempotency.objects.filter(
            key="review-core-receipt-partial", status="succeeded",
        ).exists())
        self.assertTrue(FulfillmentIdempotency.objects.filter(
            key="review-core-shipment-partial", status="succeeded",
        ).exists())
        self._save_database_snapshot("after-cancel.json", self._snapshot(order_id=order_id, purchase_id=purchase_id))
        self.assertTrue(OperationLog.objects.exists())
        self.assertFalse(OperationLog.objects.exclude(operator_id=self.session_user.pk).exists())
