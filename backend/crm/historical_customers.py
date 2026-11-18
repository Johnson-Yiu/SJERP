from django.db import IntegrityError, transaction
from django.db.models import F, Q, Value
from django.db.models.functions import StrIndex
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError

from .audit import record_operation
from .models import Customer
from .permissions import user_can
from .sales_scope import scope_customer_queryset
from .serializers import CustomerSerializer


@transaction.atomic
def historical_customer_rows(request):
    if not user_can(request.user, "customers", "view") or not user_can(request.user, "customers", "create"):
        raise PermissionDenied()
    names = request.data.get("names")
    if not isinstance(names, list) or not 1 <= len(names) <= 100 or any(
        not isinstance(name, str) or not 1 <= len(name.strip()) <= 200 for name in names
    ):
        raise DRFValidationError("请输入 1 至 100 个客户名称，每个名称最多 200 字。")
    scoped = scope_customer_queryset(Customer.objects.all(), request.user)
    names = list(dict.fromkeys(name.strip() for name in names))
    results = []
    for name in names:
        # Match shorter existing names as well, without inferring identity.
        candidates = scoped.annotate(position=StrIndex(Value(name), F("name"))).filter(Q(name__icontains=name) | Q(position__gt=0))
        exact = scoped.filter(name=name).first()
        customer = exact
        if customer and customer.merged_into_id:
            customer = scoped.filter(pk=customer.merged_into_id).first()
            if not customer:
                raise PermissionDenied()
        row = {"name": name, "existing": bool(exact), "candidates": list(candidates.order_by("name").values("name", "code")[:12])}
        row["similar_inputs"] = [other for other in names if other != name and
                                 (name.casefold() in other.casefold() or other.casefold() in name.casefold())]
        if request.data.get("confirm") is True and not exact:
            serializer = CustomerSerializer(data={"name": name}, context={"request": request, "allow_import_without_contacts": True})
            serializer.is_valid(raise_exception=True)
            try:
                customer = serializer.save(history_pending=True)
            except IntegrityError as exc:
                raise DRFValidationError("客户资料已变化，请重新预览。") from exc
            record_operation(request=request, instance=customer, action="create")
        row["code"] = customer.code if customer else ""
        results.append(row)
    return results
