"""Seed only the browser runner's disposable test database."""
import hashlib
import json
from datetime import date
from decimal import Decimal

import django
from django.conf import settings
from django.core.files.base import ContentFile

django.setup()

from crm.models import Customer, FinanceVoucher, Order, Product, SKU
from crm.services.finance import record_transaction
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)
customer = Customer.objects.create(code="QTY-UAT", name="数量变更验收客户")
product = Product.objects.create(code="QTY-UAT", name="数量变更验收灯具")
sku = SKU.objects.create(product=product, sku="QTY-UAT-SKU", unit="pcs")
fixtures = {}
for case, quantity, price in (("CENTS", 1, "0.335"), ("FEE", 10, "100")):
    order = Order.objects.create(order_no=f"QTY-UAT-{case}", customer=customer,
                                 order_date=date.today(), currency="USD", status="confirmed")
    order.items.create(sku=sku, quantity=quantity, unit_price=Decimal(price))
    plan = order.payment_plans.create(direction="receivable", currency="USD", planned_amount=order.total_amount)
    fixtures[case] = {"id": order.pk, "number": order.order_no}
    if case == "FEE":
        content = b"%PDF-1.4\nSynthetic quantity UAT bank voucher\n%%EOF"
        proof = FinanceVoucher(original_name="quantity-uat.pdf", sha256=hashlib.sha256(content).hexdigest(),
                               size=len(content), scope="transaction", actor={"kind": "synthetic_fixture"})
        proof.file.save("quantity-uat.pdf", ContentFile(content), save=False)
        proof.save()
        record_transaction(dict(
            kind="customer_receipt", direction="income", order=order, plan=plan, customer=customer,
            amount="980", remittance_amount="1000", bank_fee_amount="20", fee_responsibility="company",
            fee_reason="验收用银行手续费由我方承担", fee_evidence=proof, currency="USD",
        ))
print(json.dumps(fixtures))
