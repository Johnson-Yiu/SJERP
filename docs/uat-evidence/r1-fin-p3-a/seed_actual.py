import os, sys
sys.path.insert(0, "backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DATABASE_URL"] = "sqlite:///D:/Codex项目/森爵照明管理系统/.r1-fin-p3-a-isolated.sqlite3"
os.environ["RMB_CASH_ACCOUNT_IDS"] = "SYNTH_FX,SYNTH_CNY"
import django
django.setup()
from django.contrib.auth.models import AnonymousUser
from crm.models import Transaction, RmbCashEvent
from crm.services import cash_events as cash
from crm.tests.test_cash_events import payload
user = AnonymousUser()
receipt = Transaction.objects.get(transaction_no="P2C-USD-A-60")
p = payload([receipt], key="P3A-FX-705", bank_date="2026-10-19", bank_net_amount="705.00", fee_mode="included", fee_amount="5.00")
event, created = cash.register_event(p, user)
if created:
    cash.confirm_event(event.pk, user, voucher_checked=True)
print({"event_no": "P3A-FX-705", "created": created, "status": RmbCashEvent.objects.get(pk=event.pk).status})
