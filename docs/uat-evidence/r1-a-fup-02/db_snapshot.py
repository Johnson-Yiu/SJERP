"""DATABASE_VERIFICATION: read-only ORM snapshot of the disposable UAT database."""
import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from crm.models import Order,PaymentPlan,Transaction,Shipment,InventoryMovement,InventoryReservation
assert Path(settings.DATABASES['default']['NAME']).name=='r1a-fup02-isolated.sqlite3'
name=sys.argv[1]
assert name.isidentifier()
data={model.__name__:list(model.objects.order_by('pk').values()) for model in [Order,PaymentPlan,Transaction,Shipment,InventoryMovement,InventoryReservation]}
Path(__file__).with_name(name+'.json').write_text(json.dumps(data,cls=DjangoJSONEncoder,ensure_ascii=False,indent=2),encoding='utf8')
