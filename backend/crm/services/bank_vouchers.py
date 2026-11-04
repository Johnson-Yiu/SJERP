"""File-backed evidence for existing bank events; source scope is never widened."""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from crm.models import FinanceBankVoucherBinding
from crm.services import cash_events as cash
from crm.services import finance_closeout as ledger


def checked_voucher(value, sources, user):
    obj = ledger.voucher(value, scope="bank")
    if sorted(obj.bank_sources) != sorted(sources):
        raise ValidationError("凭证文件绑定的来源与此银行批次不同，请重新上传对应文件。")
    return obj


@transaction.atomic
def bind(event, value, user, operation="update"):
    cash.access(user, operation)
    event = cash.get_event(user, pk=event.pk)
    event = type(event).objects.select_for_update().get(pk=event.pk)
    if event.status != "pending":
        raise ValidationError("仅可为待确认银行事件补充文件凭证，历史确认事实不可覆盖。")
    obj = checked_voucher(value, list(event.sources.values_list("source_id", flat=True)), user)
    previous = FinanceBankVoucherBinding.objects.filter(event=event).first()
    if previous:
        if previous.voucher_id != obj.pk:
            raise ValidationError("文件凭证已绑定，不可覆盖；请取消草稿并重建。")
        return previous
    result = FinanceBankVoucherBinding.objects.create(event=event, voucher=obj, actor=cash.actor(user, "bind_private_voucher"))
    ledger.audit(result, user, "绑定银行私有凭证")
    return result


def require_verified_file(event, user):
    binding = FinanceBankVoucherBinding.objects.filter(event=event).first()
    if binding is None:
        raise ValidationError("须上传并绑定实际私有凭证文件；手填SHA不能代替文件核验。")
    return checked_voucher(binding.voucher_id, list(event.sources.values_list("source_id", flat=True)), user)
