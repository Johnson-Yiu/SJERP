"""Prevent ordinary model saves from overwriting formal party facts."""
from django.core.exceptions import ValidationError


def guard_formal_party_snapshot(instance, fields, update_fields):
    if instance._state.adding or instance.pk is None:
        return
    checked_fields = fields
    if update_fields is not None:
        requested = set(update_fields)
        checked_fields = tuple(field for field in fields
            if field in requested or (field.endswith('_id') and field[:-3] in requested))
        if not checked_fields:
            return
    original = type(instance)._base_manager.select_for_update().filter(pk=instance.pk).values('status', *checked_fields).first()
    if not original or original['status'] == 'draft':
        return
    changes = [field for field in checked_fields if getattr(instance, field) != original[field]]
    if changes:
        raise ValidationError('正式单据主体快照不能直接修改；更正须经独立审核。')
