import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from crm.models import Contact, Customer, FollowUp, InventoryMovement, Order, OrderItem, Product, ProductCategory, ProductCertificate, ProductParameter, Quote, QuoteItem, SKU, Transaction


class Command(BaseCommand):
    help = "创建本地开发环境演示数据（不是 QA/UAT 测试夹具）"

    def _assert_safe_runtime(self):
        if settings.APP_STAGE != "development":
            raise CommandError("seed_demo 仅允许在 APP_STAGE=development 的本地环境运行。")

        databases = settings.DATABASES
        if set(databases) != {"default"}:
            raise CommandError("seed_demo 拒绝配置了额外数据库连接的环境。")

        database = databases.get("default", {})
        if database.get("ENGINE") != "django.db.backends.sqlite3":
            raise CommandError("seed_demo 拒绝非 SQLite 数据库；请使用本地开发库或隔离运行器。")

        # An explicit DATABASE_URL may point at a developer's shared or real
        # business database.  Only the existing fail-closed isolation marker
        # may authorize such an explicit database selection.
        if os.getenv("DATABASE_URL", "").strip():
            required = (
                "ISOLATED_TEST_ROOT",
                "ISOLATED_TEST_RUN_ID",
                "ISOLATED_TEST_TOKEN",
                "ISOLATED_TEST_DATABASE",
                "ISOLATED_TEST_MEDIA_ROOT",
            )
            if any(not os.getenv(key, "").strip() for key in required):
                raise CommandError(
                    "seed_demo 拒绝未标记的 DATABASE_URL；请使用默认本地 SQLite，"
                    "或通过当前隔离运行器提供完整隔离身份。"
                )
            try:
                from test_support.isolated_runtime import verify_isolated_runtime

                verify_isolated_runtime(settings=settings, database_must_exist=True)
            except Exception as exc:
                raise CommandError(f"seed_demo 隔离校验失败：{exc}") from exc
            return

        # Without an explicit, verified isolation identity, only the regular
        # SQLite file belonging to this checkout's development settings is
        # allowed.  APP_STAGE=development and SQLite alone are not sufficient:
        # custom settings could otherwise point at a shared business database.
        expected_database = Path(settings.BASE_DIR) / "db.sqlite3"
        configured_database = Path(str(database.get("NAME", "")))
        if not configured_database.is_absolute():
            configured_database = Path(settings.BASE_DIR) / configured_database
        try:
            if configured_database.is_symlink():
                raise CommandError("seed_demo 拒绝符号链接数据库。")
            if configured_database.resolve(strict=False) != expected_database.resolve(strict=False):
                raise CommandError("seed_demo 仅允许当前工作树 backend/db.sqlite3 或已验证的隔离数据库。")
            if not configured_database.is_file():
                raise CommandError("seed_demo 要求本地开发数据库已由迁移创建。")
        except (OSError, RuntimeError, ValueError) as exc:
            raise CommandError("seed_demo 无法安全验证本地开发数据库路径。") from exc

    def handle(self, *args, **options):
        self._assert_safe_runtime()
        lighting, _ = ProductCategory.objects.get_or_create(name="商业照明")
        outdoor, _ = ProductCategory.objects.get_or_create(name="户外照明")
        p1, _ = Product.objects.update_or_create(code="SL-DOWN", defaults={"name": "LED Downlight", "category": lighting})
        p2, _ = Product.objects.update_or_create(code="SL-FLOOD", defaults={"name": "LED Flood Light", "category": outdoor})
        s1, _ = SKU.objects.update_or_create(sku="SL-DOWN-12W-4K", defaults={"product": p1, "specification": "12W / 4000K / White", "cost_price": 3.2, "default_price": 6.8})
        s2, _ = SKU.objects.update_or_create(sku="SL-FLOOD-100W", defaults={"product": p2, "specification": "100W / IP66", "cost_price": 18, "default_price": 35})
        ProductParameter.objects.update_or_create(product=p1, group="电气参数", name="功率", defaults={"value": "12", "unit": "W", "sort_order": 1})
        ProductParameter.objects.update_or_create(product=p1, group="光学参数", name="色温", defaults={"value": "4000", "unit": "K", "sort_order": 2})
        ProductParameter.objects.update_or_create(product=p2, group="防护参数", name="防护等级", defaults={"value": "IP66", "sort_order": 1})
        ProductCertificate.objects.update_or_create(product=p1, name="CE-LVD", defaults={"certificate_no": "CE-SL-2026-001", "issuer": "TÜV Rheinland", "issued_date": date.today() - timedelta(days=90), "expires_on": date.today() + timedelta(days=1000)})
        ProductCertificate.objects.update_or_create(product=p2, name="RoHS", defaults={"certificate_no": "ROHS-SL-2026-008", "issuer": "SGS", "issued_date": date.today() - timedelta(days=60), "expires_on": date.today() + timedelta(days=1030)})

        c1, _ = Customer.objects.update_or_create(code="C-0001", defaults={"name": "Lumière Distribution SAS", "country": "法国", "source": "展会", "status": "company", "owner": "Johnson", "next_follow_up": date.today()})
        c2, _ = Customer.objects.update_or_create(code="C-0002", defaults={"name": "Northstar Lighting LLC", "country": "美国", "source": "Google", "status": "customer", "owner": "Mia"})
        c3, _ = Customer.objects.update_or_create(code="C-0003", defaults={"name": "Bright Home Trading", "country": "阿联酋", "source": "Alibaba", "status": "lead", "owner": "Leo", "next_follow_up": date.today() + timedelta(days=2)})
        contact, _ = Contact.objects.update_or_create(customer=c1, email="marie@example.com", defaults={"name": "Marie Dubois", "title": "Purchasing Manager", "phone": "+33 1 88 00 00 00", "is_primary": True})
        FollowUp.objects.get_or_create(customer=c1, subject="确认下季度采购计划", defaults={"contact": contact, "followed_at": timezone.make_aware(datetime.combine(date.today() - timedelta(days=3), datetime.min.time().replace(hour=10))), "type": "email", "content": "客户预计追加筒灯订单，等待最终数量。", "next_action": "发送阶梯报价", "next_follow_up": date.today(), "owner": "Johnson"})

        quote, _ = Quote.objects.update_or_create(quote_no="QT-2026-001", defaults={"customer": c3, "quote_date": date.today() - timedelta(days=5), "valid_until": date.today() + timedelta(days=25), "status": "sent", "currency": "USD", "exchange_rate": Decimal("7.20")})
        QuoteItem.objects.get_or_create(quote=quote, sku=s2, defaults={"quantity": 200, "unit_price": 34})

        order1, _ = Order.objects.update_or_create(order_no="SO-2026-001", defaults={"customer": c1, "order_date": date.today() - timedelta(days=35), "status": "completed", "currency": "USD", "exchange_rate": Decimal("7.18")})
        OrderItem.objects.get_or_create(order=order1, sku=s1, defaults={"quantity": 1200, "unit_price": 6.5, "cost_price": 3.2})
        order2, _ = Order.objects.update_or_create(order_no="SO-2026-002", defaults={"customer": c2, "order_date": date.today() - timedelta(days=8), "expected_ship_date": date.today() + timedelta(days=20), "status": "production", "currency": "USD", "exchange_rate": Decimal("7.21")})
        OrderItem.objects.get_or_create(order=order2, sku=s2, defaults={"quantity": 300, "unit_price": 34.5, "cost_price": 18})
        InventoryMovement.objects.update_or_create(movement_no="IM-2026-001", defaults={"movement_date": date.today() - timedelta(days=45), "type": "purchase_in", "sku": s1, "quantity": 1500, "warehouse": "中山成品仓", "unit_cost": 3.2, "reference": "PO-2026-006"})
        InventoryMovement.objects.update_or_create(movement_no="IM-2026-002", defaults={"movement_date": date.today() - timedelta(days=30), "type": "sale_out", "sku": s1, "order": order1, "quantity": 1200, "warehouse": "中山成品仓", "unit_cost": 3.2})
        InventoryMovement.objects.update_or_create(movement_no="IM-2026-003", defaults={"movement_date": date.today() - timedelta(days=15), "type": "purchase_in", "sku": s2, "quantity": 500, "warehouse": "中山成品仓", "unit_cost": 18, "reference": "PO-2026-011"})
        Transaction.objects.update_or_create(transaction_no="TX-2026-001", defaults={"transaction_date": date.today() - timedelta(days=30), "direction": "income", "category": "订单收款", "amount": 7800, "currency": "USD", "exchange_rate": Decimal("7.18"), "customer": c1, "order": order1, "payment_method": "T/T"})
        Transaction.objects.update_or_create(transaction_no="TX-2026-002", defaults={"transaction_date": date.today() - timedelta(days=6), "direction": "income", "category": "订单定金", "amount": 3105, "currency": "USD", "exchange_rate": Decimal("7.21"), "customer": c2, "order": order2, "payment_method": "T/T"})
        Transaction.objects.update_or_create(transaction_no="TX-2026-003", defaults={"transaction_date": date.today() - timedelta(days=2), "direction": "expense", "category": "样品运费", "amount": 1200, "currency": "CNY", "exchange_rate": 1, "notes": "DHL 样品寄送"})
        self.stdout.write(self.style.SUCCESS("演示数据已就绪。"))
