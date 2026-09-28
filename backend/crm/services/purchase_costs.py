"""Purchase cost attribution; never creates stock movements or payment entries."""
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from crm.models import Order, PurchaseOrder, PurchaseCostAllocation

CENT = Decimal("0.01")


def validate_allocation_integrity(purchase, records=None):
    """Require every purchase line to have a complete persisted quantity attribution."""
    totals = {}
    if records is None:
        records = PurchaseCostAllocation.objects.filter(purchase_item__purchase_order=purchase)
    for record in records:
        totals[record.purchase_item_id] = totals.get(record.purchase_item_id, Decimal(0)) + record.quantity
    for item in purchase.items.all():
        if totals.get(item.pk, Decimal(0)) != item.quantity:
            raise serializers.ValidationError(f"{item.sku_code_snapshot} 的成本归属数量必须等于采购数量。")


@transaction.atomic
def rebuild_default_cost_allocations(purchase):
    """Persist the version-zero default attribution; never replace manual allocations."""
    purchase = PurchaseOrder.objects.select_for_update().get(pk=purchase.pk)
    if purchase.cost_allocation_version != 0:
        raise serializers.ValidationError("已有人工成本分配，不能重建默认归属。")
    items = list(purchase.items.all())
    PurchaseCostAllocation.objects.filter(purchase_item__purchase_order=purchase).delete()
    PurchaseCostAllocation.objects.bulk_create([
        PurchaseCostAllocation(
            purchase_item=item,
            target_type="order" if purchase.order_id else "inventory",
            order=purchase.order if purchase.order_id else None,
            quantity=item.quantity,
        ) for item in items
    ])
    validate_allocation_integrity(purchase)


class AllocationInput(serializers.Serializer):
    target_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    purchase_item = serializers.IntegerField(min_value=1)
    target_type = serializers.ChoiceField(choices=PurchaseCostAllocation._meta.get_field("target_type").choices)
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all(), required=False, allow_null=True)
    quantity = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=CENT)


    def validate(self, attrs):
        if attrs["target_type"] == "other" and not attrs["target_name"]:
            raise serializers.ValidationError({"target_name": "选择其他时，请填写成本归属名称。"})
        if attrs["target_type"] != "other":
            attrs["target_name"] = ""
        return attrs


class ExpenseInput(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=CENT)
    method = serializers.ChoiceField(choices=["amount", "quantity"])


class CostInput(serializers.Serializer):
    version = serializers.IntegerField(min_value=0)
    allocations = AllocationInput(many=True)
    expenses = ExpenseInput(many=True)


def split_amount(amount, weights):
    """Largest remainder in stable row order; all shares sum to the rounded total."""
    total = sum(weights, Decimal(0))
    amount = amount.quantize(CENT, rounding=ROUND_HALF_UP)
    if not total:
        if amount:
            raise serializers.ValidationError("采购金额为零，附加费用请改用按数量分摊。")
        return [Decimal(0)] * len(weights)
    exact = [amount * weight / total for weight in weights]
    shares = [value.quantize(CENT, rounding=ROUND_DOWN) for value in exact]
    remaining = int((amount - sum(shares)) / CENT)
    for index in sorted(range(len(weights)), key=lambda i: exact[i] - shares[i], reverse=True)[:remaining]:
        shares[index] += CENT
    return shares


def cost_summary(purchase, records=None, expenses=None):
    rows = []
    for item in purchase.items.all():
        allocations = ([record for record in records if record.purchase_item_id == item.pk] if records is not None else list(item.cost_allocations.select_related("order")))
        amounts = split_amount(item.amount, [a.quantity for a in allocations])
        for allocation, amount in zip(allocations, amounts):
            rows.append({"purchase_item": item.pk, "sku_code": item.sku_code_snapshot,
                "display_name": item.display_name_snapshot or item.sku.display_name_cn or item.sku.product.name,
                "target_name": allocation.target_name,
                "target_type": allocation.target_type, "order": allocation.order_id,
                "order_no": allocation.order.order_no if allocation.order_id else "",
                "quantity": allocation.quantity, "base_amount": amount, "additional_amount": Decimal(0)})
    expense_breakdown = []
    expenses = purchase.additional_costs if expenses is None else expenses
    for expense in expenses:
        shares = split_amount(Decimal(expense["amount"]), [r["base_amount"] if expense["method"] == "amount" else r["quantity"] for r in rows])
        expense_breakdown.append({**expense, "shares": shares})
        for row, share in zip(rows, shares):
            row["additional_amount"] += share
    for row in rows:
        row["total_amount"] = row["base_amount"] + row["additional_amount"]
    return {"version": purchase.cost_allocation_version, "allocations": rows,
        "expenses": expenses, "expense_breakdown": expense_breakdown,
        "base_amount": sum((r["base_amount"] for r in rows), Decimal(0)),
        "additional_amount": sum((r["additional_amount"] for r in rows), Decimal(0)),
        "total_amount": sum((r["total_amount"] for r in rows), Decimal(0))}


def prepare_costs(purchase, payload):
    if purchase.status == "cancelled":
        raise serializers.ValidationError("已取消的采购单不能分配成本。")
    if payload["version"] != purchase.cost_allocation_version:
        raise serializers.ValidationError("成本分配已被其他人修改，请关闭后重新打开。")
    items = {item.pk: item for item in purchase.items.all()}
    totals = {pk: Decimal(0) for pk in items}
    records = []
    for row in payload["allocations"]:
        pk = row["purchase_item"]
        if pk not in items:
            raise serializers.ValidationError("分配明细不属于当前采购单。")
        order = row.get("order")
        if (row["target_type"] == "order") != bool(order):
            raise serializers.ValidationError("销售订单归属必须选择订单，其他归属不能关联订单。")
        if order and order.status == "cancelled":
            raise serializers.ValidationError("不能分配到已取消的销售订单。")
        totals[pk] += row["quantity"]
        if totals[pk] > items[pk].quantity:
            raise serializers.ValidationError(f"{items[pk].sku_code_snapshot} 分配数量超过采购数量。")
        records.append(PurchaseCostAllocation(purchase_item=items[pk], target_type=row["target_type"], order=order, quantity=row["quantity"], target_name=row.get("target_name", "")))
    for pk, item in items.items():
        if totals[pk] < item.quantity:
            records.append(PurchaseCostAllocation(purchase_item=item, target_type="inventory", quantity=item.quantity - totals[pk]))
    expenses = [{**e, "amount": str(e["amount"])} for e in payload["expenses"]]
    return records, expenses


def preview_costs(purchase, payload):
    records, expenses = prepare_costs(purchase, payload)
    return cost_summary(purchase, records=records, expenses=expenses)


@transaction.atomic
def save_costs(purchase, payload):
    purchase = PurchaseOrder.objects.select_for_update().get(pk=purchase.pk)
    records, expenses = prepare_costs(purchase, payload)
    PurchaseCostAllocation.objects.filter(purchase_item__purchase_order=purchase).delete()
    PurchaseCostAllocation.objects.bulk_create(records)
    validate_allocation_integrity(purchase, records)
    purchase.additional_costs = expenses
    purchase.cost_allocation_version += 1
    purchase.save(update_fields=["additional_costs", "cost_allocation_version", "updated_at"])
    return cost_summary(purchase)  # Calculation failure rolls back the whole replacement.


def order_purchase_cost(order):
    purchases = PurchaseOrder.objects.filter(items__cost_allocations__target_type="order", items__cost_allocations__order=order).exclude(status__in=["draft", "cancelled"]).distinct()
    base = additional = Decimal(0)
    for purchase in purchases:
        for row in cost_summary(purchase)["allocations"]:
            if row["order"] == order.pk:
                base += row["base_amount"] * purchase.exchange_rate
                additional += row["additional_amount"] * purchase.exchange_rate
    return base, additional
