from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def reject_loss(apps, schema_editor):
    alias = schema_editor.connection.alias
    for name in ('PartyDocumentVersion', 'PartyVersionTerminalEvent', 'PartyQuoteApplication', 'PartyVersionApproval', 'PartyVersionRequest'):
        if apps.get_model('crm', name).objects.using(alias).exists():
            raise RuntimeError('主体版本或申请审批记录已存在，拒绝回退以避免丢失历史。')
    Quote = apps.get_model('crm', 'Quote')
    if Quote.objects.using(alias).filter(models.Q(buyer_tax_id__isnull=False) | models.Q(buyer_country_snapshot__isnull=False)).exists():
        raise RuntimeError('报价买方国家或税号快照已存在，拒绝回退以避免丢失历史。')


def install_guard(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql': return
    schema_editor.execute("""CREATE FUNCTION crm_party_document_version_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'party document versions are append-only'
        USING ERRCODE = '42501'; END; $$""")
    schema_editor.execute("""CREATE TRIGGER crm_party_document_version_immutable_guard
        BEFORE UPDATE OR DELETE ON crm_partydocumentversion
        FOR EACH STATEMENT EXECUTE FUNCTION crm_party_document_version_immutable()""")
    schema_editor.execute("""CREATE TRIGGER crm_party_document_version_truncate_guard
        BEFORE TRUNCATE ON crm_partydocumentversion
        FOR EACH STATEMENT EXECUTE FUNCTION crm_party_document_version_immutable()""")


def remove_guard(apps, schema_editor):
    reject_loss(apps, schema_editor)
    if schema_editor.connection.vendor != 'postgresql': return
    schema_editor.execute('DROP TRIGGER crm_party_document_version_truncate_guard ON crm_partydocumentversion')
    schema_editor.execute('DROP TRIGGER crm_party_document_version_immutable_guard ON crm_partydocumentversion')
    schema_editor.execute('DROP FUNCTION crm_party_document_version_immutable()')


class Migration(migrations.Migration):
    dependencies = [('crm', '0113_party_request_lifecycle'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='PartyDocumentVersion', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('version_no', models.PositiveIntegerField()), ('base_snapshot', models.JSONField()), ('snapshot', models.JSONField()),
            ('identity_fingerprint', models.CharField(max_length=64)), ('base_fingerprint', models.CharField(max_length=64)), ('snapshot_fingerprint', models.CharField(max_length=64)),
            ('approved_fingerprint', models.CharField(max_length=64)), ('approval_attestation_fingerprint', models.CharField(max_length=64)),
            ('source_trust', models.CharField(choices=[('unknown', '未知'), ('unverified', '未核验')], max_length=24)),
            ('version_fingerprint', models.CharField(max_length=64)), ('created_at', models.DateTimeField(auto_now_add=True)),
            ('applied_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='applied_document_party_versions', to=settings.AUTH_USER_MODEL)),
            ('approval', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='document_version', to='crm.partyversionapproval')),
            ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='party_versions', to='crm.order')),
            ('purchase_order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='party_versions', to='crm.purchaseorder')),
            ('previous', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='next_versions', to='crm.partydocumentversion')),
        ], options={'constraints':[
            models.CheckConstraint(condition=(models.Q(order__isnull=False,purchase_order__isnull=True)|models.Q(order__isnull=True,purchase_order__isnull=False)),name='party_doc_one_target'),
            models.CheckConstraint(condition=models.Q(version_no__gte=1),name='party_doc_version_positive'),
            models.UniqueConstraint(fields=('order','version_no'),condition=models.Q(order__isnull=False),name='party_doc_order_version_unique'),
            models.UniqueConstraint(fields=('purchase_order','version_no'),condition=models.Q(purchase_order__isnull=False),name='party_doc_purchase_version_unique'),
        ]}),
        migrations.RunPython(migrations.RunPython.noop, reject_loss),
        migrations.RunPython(install_guard, remove_guard),
    ]
