import json
from crm.models import NewProductReminder, OperationLog
rows=[]
for pk in (2,3,56,57):
 o=NewProductReminder.objects.get(pk=pk)
 assert o.version==3 and o.voided_at and o.void_reason in ("合成验收：客户调整用途","内置浏览器验收：需求用途调整","真实HTTP合成验收")
 assert o.specification in ("IP67 4000K","IP67 / 3000K / 庭院入口","IP68") and o.contact_id is None and o.product_id is None
 logs=OperationLog.objects.filter(entity="crm.newproductreminder",object_id=str(pk)).order_by("id")
 assert logs.count()==3 and all(x.operator_id is None for x in logs)
 assert [x.after_data["version"] for x in logs]==[1,2,3]
 rows.append({"id":pk,"version":o.version,"void_reason":o.void_reason,"created_by":o.created_by,"audit_count":logs.count(),"audit_versions":[x.after_data["version"] for x in logs]})
q=NewProductReminder.objects.filter(requirement="合成分页壁灯")
assert q.count()==52 and q.values("customer").distinct().count()==2 and q.values("specification").distinct().count()==52
print(json.dumps({"status":"PASS","synthetic_database":".tmp-reminder-uat.sqlite3","record_checks":rows,"pagination_requirements":q.count(),"customers":2},ensure_ascii=False,indent=2))
