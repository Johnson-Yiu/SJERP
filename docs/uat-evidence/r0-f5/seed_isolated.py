"""Seed only the empty disposable SQLite database selected by DATABASE_URL."""
from datetime import timedelta

from django.utils import timezone

from crm.models import Contact, Customer, FollowUp


if Customer.objects.exists() or Contact.objects.exists() or FollowUp.objects.exists():
    raise SystemExit("Refusing to seed a non-empty isolated UAT database")

today = timezone.localdate()
first = Customer.objects.create(
    name="R0F5 测试客户·灯具采购有限公司",
    code="R0F5-001", status="customer", country="中国", owner="R0F5 UAT",
)
second = Customer.objects.create(
    name="R0F5 第二客户", code="R0F5-002", status="opportunity",
    country="德国", owner="R0F5 UAT",
)
primary = Contact.objects.create(
    customer=first,
    name="王明（采购负责人）超长姓名窄桌面验收",
    title="国际采购与供应链高级负责人 / 亚太区",
    email="buyer@example.test", phone="+86 138 0000 0000",
    whatsapp="+86 138 0000 0001", is_primary=True, notes="Isolated UAT contact",
)
secondary = Contact.objects.create(
    customer=first, name="李女士", title="采购", phone="020-12345678",
    whatsapp="13800000002",
)
other = Contact.objects.create(
    customer=second, name="Morgan Lee", title="Operations Manager",
    email="morgan@example.test", is_primary=True,
)
FollowUp.objects.create(
    customer=first, contact=primary, followed_at=timezone.now() - timedelta(days=2),
    type="meeting", subject="年度采购计划沟通",
    content="<p>隔离测试跟进内容，检查富文本与长记录展示。</p>",
    result="客户回复：下周确认 SKU 数量。",
    next_action="发送报价并确认交期", next_follow_up=today,
    next_follow_up_mode="set", owner="R0F5 UAT",
)
FollowUp.objects.create(
    customer=first, contact=secondary, followed_at=timezone.now() - timedelta(days=10),
    type="call", subject="历史电话沟通", content="已确认产品规格。",
    result="待内部评估", next_action="等待客户回复",
    next_follow_up=today + timedelta(days=7), next_follow_up_mode="set", owner="R0F5 UAT",
)
FollowUp.objects.create(
    customer=second, contact=other, followed_at=timezone.now() - timedelta(days=1),
    type="email", subject="跨客户跟进", content="已发送产品资料。",
    next_action="安排产品演示", next_follow_up=today - timedelta(days=1),
    next_follow_up_mode="set", owner="R0F5 UAT",
)
print({
    "customers": Customer.objects.count(),
    "contacts": Contact.objects.count(),
    "followups": FollowUp.objects.count(),
})
