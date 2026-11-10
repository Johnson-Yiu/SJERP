"""Seed only the disposable ISS-007 browser database with synthetic records."""

from base64 import b64decode
from datetime import date, timedelta

import django

django.setup()

from django.core.files.base import ContentFile
from django.utils import timezone

from crm.models import Contact, Customer, FollowUp, Product, Quote, SKU
from crm.quote_snapshots import create_quote_items


if Customer.objects.exists() or Product.objects.exists() or Quote.objects.exists():
    raise SystemExit("Refusing to seed a non-empty ISS-007 database")

png = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
customer = Customer.objects.create(
    name="ISS007 隔离验收客户",
    code="ISS007-C001",
    country="Germany",
    status="customer",
    owner="ISS007 UAT",
)
contact = Contact.objects.create(
    customer=customer,
    name="ISS007 验收联系人",
    email="iss007-contact@example.test",
    phone="+49 30 555000",
    is_primary=True,
)
follow_up = FollowUp.objects.create(
    customer=customer,
    contact=contact,
    followed_at=timezone.now() - timedelta(days=1),
    type="email",
    subject="ISS007 附件上传与重开",
    content="隔离环境正式业务流程验收记录。",
    result="等待附件复核",
    next_action="确认附件可读",
    next_follow_up_mode="keep",
    owner="ISS007 UAT",
)
product = Product.objects.create(
    code="ISS007-P001",
    name="ISS007 验收灯具",
    name_en="ISS007 Verification Lamp",
    sales_model_prefix="ISS7",
)
sku = SKU.objects.create(
    product=product,
    sku="ISS007-SKU001",
    display_name_cn="ISS007 可上传图片 SKU",
    sales_model="ISS7-001",
    description_en="Synthetic SKU used only for attachment UAT.",
)
sku.image.save("iss007-initial.png", ContentFile(png), save=True)
quote = Quote.objects.create(
    quote_no="ISS007-Q001",
    customer=customer,
    quote_date=date(2026, 10, 28),
    valid_until=date(2026, 11, 28),
    currency="USD",
    buyer_company_name=customer.name,
    recipient_name=contact.name,
    buyer_email=contact.email,
)
items = create_quote_items(
    quote,
    [{"sku": sku, "quantity": "2.00", "unit_price": "12.50", "description": "ISS007 historical image snapshot"}],
)
print({
    "customer": customer.pk,
    "contact": contact.pk,
    "follow_up": follow_up.pk,
    "product": product.pk,
    "sku": sku.pk,
    "quote": quote.pk,
    "quote_item": items[0].pk,
    "sku_image": sku.image.name,
    "quote_image_snapshot": items[0].image_snapshot.name,
})

from crm.models import QuoteImportantNote
QuoteImportantNote.objects.create(root_quote=quote, source_quote=quote, content='<p>隔离测试备注</p>')
