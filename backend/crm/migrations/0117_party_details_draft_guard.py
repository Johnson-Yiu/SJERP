from django.db import migrations


def install(apps, editor):
    if editor.connection.vendor == 'postgresql':
        editor.execute("""CREATE FUNCTION crm_party_details_draft_only() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE s text; h boolean := false; q bigint; o bigint; p bigint;
        BEGIN
          IF TG_OP = 'UPDATE' AND (OLD.quote_id IS DISTINCT FROM NEW.quote_id OR OLD.order_id IS DISTINCT FROM NEW.order_id OR OLD.purchase_order_id IS DISTINCT FROM NEW.purchase_order_id) THEN
            RAISE EXCEPTION 'party details target cannot change' USING ERRCODE = '23514';
          END IF;
          IF TG_OP = 'DELETE' THEN q := OLD.quote_id; o := OLD.order_id; p := OLD.purchase_order_id;
          ELSE q := NEW.quote_id; o := NEW.order_id; p := NEW.purchase_order_id; END IF;
          IF q IS NOT NULL THEN SELECT status INTO s FROM crm_quote WHERE id=q FOR UPDATE;
          ELSIF o IS NOT NULL THEN SELECT status, historical_only INTO s, h FROM crm_order WHERE id=o FOR UPDATE;
          ELSIF p IS NOT NULL THEN SELECT status, historical_only INTO s, h FROM crm_purchaseorder WHERE id=p FOR UPDATE; END IF;
          IF s IS DISTINCT FROM 'draft' OR h THEN RAISE EXCEPTION 'party details require draft document' USING ERRCODE = '23514'; END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END $$""")
        editor.execute('CREATE TRIGGER crm_party_details_draft_guard BEFORE INSERT OR UPDATE OR DELETE ON crm_partydocumentdetailsstorage FOR EACH ROW EXECUTE FUNCTION crm_party_details_draft_only()')
    elif editor.connection.vendor == 'sqlite':
        for op, row in [('INSERT', 'NEW'), ('UPDATE', 'NEW'), ('DELETE', 'OLD')]:
            moved = "(OLD.quote_id IS NOT NEW.quote_id OR OLD.order_id IS NOT NEW.order_id OR OLD.purchase_order_id IS NOT NEW.purchase_order_id) OR " if op == 'UPDATE' else ''
            condition = (f"{moved}COALESCE(CASE WHEN {row}.quote_id IS NOT NULL THEN (SELECT status FROM crm_quote WHERE id={row}.quote_id) "
                f"WHEN {row}.order_id IS NOT NULL THEN (SELECT CASE WHEN historical_only THEN '' ELSE status END FROM crm_order WHERE id={row}.order_id) "
                f"WHEN {row}.purchase_order_id IS NOT NULL THEN (SELECT CASE WHEN historical_only THEN '' ELSE status END FROM crm_purchaseorder WHERE id={row}.purchase_order_id) END, '') != 'draft'")
            editor.execute(f"CREATE TRIGGER crm_party_details_draft_{op.lower()} BEFORE {op} ON crm_partydocumentdetailsstorage WHEN {condition} BEGIN SELECT RAISE(ABORT, 'party details require draft document'); END")
    else:
        raise RuntimeError('Unsupported database for party details protection.')


def uninstall(apps, editor):
    Storage = apps.get_model('crm', 'PartyDocumentDetailsStorage')
    if Storage.objects.using(editor.connection.alias).filter(details__isnull=False).exists():
        raise RuntimeError('主体资料已存在，拒绝回退以避免丢失历史。')
    if editor.connection.vendor == 'postgresql':
        editor.execute('DROP TRIGGER crm_party_details_draft_guard ON crm_partydocumentdetailsstorage')
        editor.execute('DROP FUNCTION crm_party_details_draft_only()')
    elif editor.connection.vendor == 'sqlite':
        for op in ('insert', 'update', 'delete'):
            editor.execute(f'DROP TRIGGER crm_party_details_draft_{op}')


class Migration(migrations.Migration):
    dependencies = [('crm', '0116_party_document_details_storage')]
    operations = [migrations.RemoveConstraint(model_name='partydocumentdetailsstorage', name='party_details_not_enabled'),
                  migrations.RunPython(install, uninstall)]
