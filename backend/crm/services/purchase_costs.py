"""Purchase cost attribution; never creates stock movements or payment entries."""
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from crm.models import Order, PurchaseOrder, PurchaseCostAllocation, SKU

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
    method = serializers.ChoiceField(choices=["amount"], error_messages={
        "invalid_choice": "新增或修改公共费用只支持按采购金额比例分摊。",
    })


class CostInput(serializers.Serializer):
    version = serializers.IntegerField(min_value=0)
    allocations = AllocationInput(many=True)
    expenses = ExpenseInput(many=True)


class IncompletePurchaseCost(serializers.ValidationError):
    """Known cost data inconsistency, safe to expose to authorized readers."""


def split_amount(amount, weights, *, quantum=CENT):
    """Largest remainder in stable row order; all shares sum to the rounded total."""
    if amount < 0:
        return [-share for share in split_amount(-amount, weights, quantum=quantum)]
    total = sum(weights, Decimal(0))
    amount = amount.quantize(quantum, rounding=ROUND_HALF_UP)
    if not total:
        if amount:
            raise IncompletePurchaseCost("采购金额为零，不能分摊正公共费用；请核对采购金额或移除公共费用。")
        return [Decimal(0)] * len(weights)
    exact = [amount * weight / total for weight in weights]
    shares = [value.quantize(quantum, rounding=ROUND_DOWN) for value in exact]
    remaining = int((amount - sum(shares)) / quantum)
    for index in sorted(range(len(weights)), key=lambda i: exact[i] - shares[i], reverse=True)[:remaining]:
        shares[index] += quantum
    return shares


def cost_summary(purchase, records=None, expenses=None):
    rows = []
    adjustment = purchase.approved_change_amount
    for item in purchase.items.order_by("pk"):
        allocations = ([record for record in records if record.purchase_item_id == item.pk] if records is not None else list(item.cost_allocations.select_related("order")))
        if adjustment and sum(allocation.quantity for allocation in allocations) != item.quantity:
            raise IncompletePurchaseCost("采购成本归属不完整，无法分摊合同金额变更。")
        amounts = split_amount(item.amount, [a.quantity for a in allocations])
        for allocation, amount in zip(allocations, amounts):
            rows.append({"purchase_item": item.pk, "sku_code": item.sku_code_snapshot,
                "display_name": item.display_name_snapshot or item.sku.display_name_cn or item.sku.product.name,
                "target_name": allocation.target_name,
                "target_type": allocation.target_type, "order": allocation.order_id,
                "order_no": allocation.order.order_no if allocation.order_id else "",
                "quantity": allocation.quantity, "base_amount": amount, "additional_amount": Decimal(0)})
    weights = [row["base_amount"] for row in rows]
    if adjustment:
        if any(weight < 0 for weight in weights) or not sum(weights):
            raise IncompletePurchaseCost("采购合同金额变更无法分摊，请核对原采购金额和成本归属。")
    # Contract changes can carry four decimal places. Use cents when possible.
    quantum = CENT if adjustment == adjustment.quantize(CENT) else Decimal("0.0001")
    for row, share in zip(rows, split_amount(adjustment, weights, quantum=quantum)):
        row["contract_change_amount"] = share
        if adjustment and row["base_amount"] + share < 0:
            raise IncompletePurchaseCost("合同金额变更导致采购归属成本为负，请核对采购金额。")
    expense_breakdown = []
    expenses = purchase.additional_costs if expenses is None else expenses
    for expense in expenses:
        shares = split_amount(Decimal(expense["amount"]), [r["base_amount"] if expense["method"] == "amount" else r["quantity"] for r in rows])
        expense_breakdown.append({**expense, "shares": shares})
        for row, share in zip(rows, shares):
            row["additional_amount"] += share
    for row in rows:
        row["total_amount"] = row["base_amount"] + row["contract_change_amount"] + row["additional_amount"]
    return {"version": purchase.cost_allocation_version, "allocations": rows,
        "expenses": expenses, "expense_breakdown": expense_breakdown,
        "contract_change_amount": adjustment,
        "base_amount": sum((r["base_amount"] for r in rows), Decimal(0)),
        "additional_amount": sum((r["additional_amount"] for r in rows), Decimal(0)),
        "total_amount": sum((r["total_amount"] for r in rows), Decimal(0))}


def prepare_costs(purchase, payload):
    # Keep legacy quantity interpretation in read-only cost_summary only.
    if any(expense.get("method") != "amount" for expense in payload["expenses"]):
        raise serializers.ValidationError("新增或修改公共费用只支持按采购金额比例分摊。")
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
    from crm.services.fulfillment import rebalance_sku_reservations

    purchase = PurchaseOrder.objects.select_for_update().get(pk=purchase.pk)
    # Match receipt's PO -> Orders -> SKU lock order. Serializer instances may
    # predate a concurrent cancellation, so validate the locked current rows.
    order_ids = {row["order"].pk for row in payload["allocations"] if row.get("order")}
    order_ids.update(PurchaseCostAllocation.objects.filter(
        purchase_item__purchase_order=purchase, order__isnull=False,
    ).values_list("order_id", flat=True))
    orders = {row.pk: row for row in Order.objects.select_for_update().filter(pk__in=order_ids).order_by("pk")}
    if order_ids - orders.keys():
        raise serializers.ValidationError("成本归属订单已不存在，请重新选择。")
    payload = {**payload, "allocations": [
        {**row, "order": orders[row["order"].pk]} if row.get("order") else row
        for row in payload["allocations"]
    ]}
    records, expenses = prepare_costs(purchase, payload)
    PurchaseCostAllocation.objects.filter(purchase_item__purchase_order=purchase).delete()
    PurchaseCostAllocation.objects.bulk_create(records)
    validate_allocation_integrity(purchase, records)
    purchase.additional_costs = expenses
    purchase.cost_allocation_version += 1
    purchase.save(update_fields=["additional_costs", "cost_allocation_version", "updated_at"])
    for sku in SKU.objects.filter(
        pk__in=purchase.items.order_by("sku_id").values_list("sku_id", flat=True).distinct()
    ).order_by("pk"):
        rebalance_sku_reservations(sku)
    return cost_summary(purchase)  # Calculation failure rolls back the whole replacement.


def order_purchase_cost_components(order):
    purchases = PurchaseOrder.objects.filter(items__cost_allocations__target_type="order", items__cost_allocations__order=order).exclude(status__in=["draft", "cancelled"]).distinct()
    base = adjustment = additional = Decimal(0)
    for purchase in purchases:
        for row in cost_summary(purchase)["allocations"]:
            if row["order"] == order.pk:
                base += row["base_amount"] * purchase.exchange_rate
                adjustment += row["contract_change_amount"] * purchase.exchange_rate
                additional += row["additional_amount"] * purchase.exchange_rate
    return base, adjustment, additional


def order_purchase_cost(order):
    base, adjustment, additional = order_purchase_cost_components(order)
    return base + adjustment, additional
