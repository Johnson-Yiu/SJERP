from crm.models import Customer, FollowUp, Contact, Product
from django.utils import timezone
c=Customer.objects.create(code="REM-UAT-A",name="合成验收客户甲")
Customer.objects.create(code="REM-UAT-B",name="合成验收客户乙")
FollowUp.objects.create(customer=c,followed_at=timezone.now(),subject="合成新品沟通",content="寻找户外壁灯")
Contact.objects.create(customer=c,name="合成联系人")
Product.objects.create(code="REM-UAT-P",name="合成已建档壁灯")
print("SYNTHETIC_SEED_OK")
