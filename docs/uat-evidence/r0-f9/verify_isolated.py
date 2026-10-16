from pathlib import Path
from django.conf import settings
from crm.models import Contact, EmployeeProfile, InventoryMovement, PaymentPlan, Transaction, PurchaseOrder, SKU
from crm.permissions import development_superadmin_enabled
from crm.services.fulfillment import sku_metrics
import json
assert Path(settings.DATABASES['default']['NAME']).resolve()==(settings.BASE_DIR/'r0f9-ux.sqlite3').resolve()
sku=SKU.objects.get(sku='R0F9-EXISTING')
plan=PaymentPlan.objects.get(order__order_no='R0F9-O001')
assert plan.settled_amount==10 and plan.remaining_amount==490
assert Contact.objects.get(name='Morgan Lee').notes=='R0F9 保存失败恢复验收'
assert PurchaseOrder.objects.get(purchase_no='R0F9-P001').status=='partial'
assert InventoryMovement.objects.filter(type='purchase_in',quantity=2).count()==1
assert EmployeeProfile.objects.count()==0 and not settings.RBAC_ENFORCEMENT and development_superadmin_enabled()
data={'database':str(settings.DATABASES['default']['NAME']),'development_superadmin':development_superadmin_enabled(),'rbac':settings.RBAC_ENFORCEMENT,'employees':EmployeeProfile.objects.count(),'sku_metrics':sku_metrics(sku),'plan':list(PaymentPlan.objects.values()),'transactions':list(Transaction.objects.values()),'movements':list(InventoryMovement.objects.values()),'contact':list(Contact.objects.filter(name='Morgan Lee').values())}
(settings.BASE_DIR.parent/'docs/uat-evidence/r0-f9/database-verification.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print('Verified synthetic UI writes and unchanged development identity')
