"""Seed a fresh H1 acceptance database with synthetic records."""
import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model

from crm.tests.test_history_products import HistoricalProductLinkingTests

assert str(settings.DATABASES["default"]["NAME"]).endswith("h1-browser-fixture.sqlite3")
assert not get_user_model().objects.exists()
settings.ALLOWED_HOSTS += ["testserver"]
fixture = HistoricalProductLinkingTests()
fixture.long_product_name = True
fixture.setUp()
fixture.target()
fixture.target("C")
config = dict(
    line.strip().split("=", 1)
    for line in Path(os.environ["H1_CREDENTIALS"]).read_text(encoding="utf-8-sig").splitlines()
    if line.strip() and not line.startswith("#")
)
get_user_model().objects.create_superuser(
    username=config["ERP_TEST_USERNAME"], first_name=config["ERP_TEST_DISPLAY_NAME"],
    password=config["ERP_TEST_PASSWORD"],
)
print("H1 browser fixture: four archived lines, two formal SKUs, isolated test login.")
