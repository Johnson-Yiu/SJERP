"""Create only synthetic records for the integrated browser review database."""

from datetime import datetime
from pathlib import Path
import json

from django.utils import timezone

from crm.models import Contact, Customer, FollowUp, Product, SKU

root = Path(__file__).resolve().parent
customer, _ = Customer.objects.get_or_create(
    code="ISS-INTEGRATION-C",
    defaults={
        "name": "ISS 集成浏览器客户",
        "country": "Germany",
        "status": "customer",
        "address": "集成验收原地址",
        "next_follow_up": "2026-11-12",
    },
)
customer.name = "ISS 集成浏览器客户"
customer.country = "Germany"
customer.status = "customer"
customer.address = "集成验收原地址"
customer.next_follow_up = "2026-11-12"
customer.save()
contact, _ = Contact.objects.get_or_create(
    customer=customer,
    name="集成主联系人",
    defaults={"email": "integration-primary@example.com", "phone": "+49 111 222", "is_primary": True},
)
contact.email = "integration-primary@example.com"
contact.phone = "+49 111 222"
contact.is_primary = True
contact.save()
product, _ = Product.objects.get_or_create(code="ISS-INTEGRATION-P", defaults={"name": "集成验收灯具"})
sku, _ = SKU.objects.get_or_create(
    sku="ISS-INTEGRATION-SKU",
    defaults={"product": product, "sales_model": "ISS-INTEGRATION-MODEL", "unit": "pcs", "default_price": "10.00"},
)
FollowUp.objects.get_or_create(
    customer=customer,
    subject="已有计划：客户回访",
    defaults={
        "contact": contact,
        "followed_at": timezone.make_aware(datetime(2026, 10, 25, 9, 0)),
        "type": "call",
        "content": "集成验收既有跟进记录。",
        "next_follow_up_mode": "set",
        "next_follow_up": "2026-11-12",
        "owner": "集成验收",
    },
)
(root / "browser-fixture.json").write_text(
    json.dumps({"customer": customer.pk, "contact": contact.pk, "product": product.pk, "sku": sku.pk}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(json.dumps({"customer": customer.pk, "contact": contact.pk, "product": product.pk, "sku": sku.pk}, ensure_ascii=False))
