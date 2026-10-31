"""Read-only before/after snapshots for the isolated ISS-028/035 Chrome run."""

import json
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        raise SystemExit("usage: inspect_fixture_sqlite.py JSON_IDS")

    ids = json.loads(sys.argv[1])
    root = Path(os.environ["ISOLATED_TEST_ROOT"]).resolve(strict=True)
    database = Path(os.environ["ISOLATED_TEST_DATABASE"]).resolve(strict=True)
    if root == Path(root.anchor) or root not in database.parents:
        raise SystemExit("refusing: SQLite path is not inside the isolated run root")
    if database.is_symlink() or not database.is_file():
        raise SystemExit("refusing: isolated SQLite path is not a regular file")

    uri = f"file:{quote(database.as_posix(), safe='/:')}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        def rows(query, parameters=()):
            return [dict(row) for row in connection.execute(query, parameters)]

        root_id, child_id = ids["root_id"], ids["child_id"]
        product_id, sku_id = ids["product_id"], ids["sku_id"]
        result = {
            "database_path": str(database),
            "categories": rows(
                "SELECT id, name, parent_id FROM crm_productcategory WHERE id IN (?, ?) ORDER BY id",
                (root_id, child_id),
            ),
            "attributes": rows(
                "SELECT id, category_id, name, key, default_value, unit, include_in_sku, include_in_sales_model, uppercase, required "
                "FROM crm_categoryattribute WHERE category_id IN (?, ?) ORDER BY id",
                (root_id, child_id),
            ),
            "product": rows(
                "SELECT id, code, name, category_id, sales_model_prefix FROM crm_product WHERE id = ?",
                (product_id,),
            ),
            "sku": rows(
                "SELECT id, sku, sales_model, display_name_cn, specification, parameter_values, schema_version, identity_signature, description_cn "
                "FROM crm_sku WHERE id = ?",
                (sku_id,),
            ),
            "plans": rows(
                "SELECT id, product_id, version, status, definitions, assignments, baseline "
                "FROM crm_skuparameterplan WHERE product_id = ? ORDER BY version",
                (product_id,),
            ),
            "quote": rows(
                "SELECT id, quote_no, status, revision_no, buyer_company_name, recipient_name, buyer_address, buyer_email, buyer_phone, "
                "currency, exchange_rate, shipping_fee, discount, notes FROM crm_quote WHERE id = ?",
                (ids["quote_id"],),
            ),
            "quote_items": rows(
                "SELECT qi.id, qi.sku_id, qi.sku_code_snapshot, qi.sales_model_snapshot, qi.product_name_snapshot, qi.unit_snapshot, "
                "qi.quantity, qi.unit_price, qi.description, qi.notes FROM crm_quoteitem qi "
                "JOIN crm_quote q ON q.id = qi.quote_id WHERE q.id = ? ORDER BY qi.id",
                (ids["quote_id"],),
            ),
            "order": rows(
                "SELECT id, order_no, status, quote_id, customer_name_snapshot, customer_country_snapshot, customer_address_snapshot, "
                "customer_contact_name_snapshot, customer_phone_snapshot, customer_email_snapshot, currency, exchange_rate, notes "
                "FROM crm_order WHERE id = ?",
                (ids["order_id"],),
            ),
            "order_items": rows(
                "SELECT oi.id, oi.sku_id, oi.sku_code_snapshot, oi.sales_model_snapshot, oi.display_name_snapshot, "
                "oi.description_snapshot, oi.unit_snapshot, oi.quantity, oi.unit_price, oi.notes FROM crm_orderitem oi "
                "JOIN crm_order o ON o.id = oi.order_id WHERE o.id = ? ORDER BY oi.id",
                (ids["order_id"],),
            ),
        }

        if "new_product_id" in ids:
            result["new_product"] = rows(
                "SELECT id, code, name, category_id FROM crm_product WHERE id = ?",
                (ids["new_product_id"],),
            )
            result["new_plans"] = rows(
                "SELECT id, product_id, version, status, definitions, baseline FROM crm_skuparameterplan "
                "WHERE product_id = ? ORDER BY version",
                (ids["new_product_id"],),
            )
        if "new_sku_id" in ids:
            result["new_sku"] = rows(
                "SELECT id, sku, sales_model, display_name_cn, specification, parameter_values, schema_version, identity_signature "
                "FROM crm_sku WHERE id = ?",
                (ids["new_sku_id"],),
            )

        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
