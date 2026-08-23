from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING

from django.db import transaction

from crm.models import PackingPlan, PackingPlanCarton, PackingPlanCartonItem, ShipmentPackage, ShipmentPackageItem, SKUPackagingProfile


ZERO = Decimal("0")


@dataclass
class EffectivePackaging:
    sku: object
    profile: object | None
    template: object | None
    unit_net_weight: Decimal | None
    qty_per_carton: Decimal | None
    length: Decimal | None
    width: Decimal | None
    height: Decimal | None
    carton_tare_weight: Decimal | None
    gross_weight_override: Decimal | None
    partial_carton_policy: str | None

    @property
    def status(self):
        if not self.profile:
            return "NOT_CONFIGURED"
        required = [self.template, self.unit_net_weight, self.qty_per_carton, self.length, self.width, self.height, self.carton_tare_weight]
        if any(value is None for value in required):
            return "PARTIAL"
        return "VERIFIED" if self.profile.verified_at else "COMPLETE"

    @property
    def cbm(self):
        if not all([self.length, self.width, self.height]): return None
        return (self.length * self.width * self.height / Decimal("1000000")).quantize(Decimal("0.000001"))


def resolve_packaging(sku, overrides=None):
    """The one resolver used by APIs and planners; clients never need fallback rules."""
    overrides = overrides or {}
    try:
        profile = sku.packaging_profile
    except SKUPackagingProfile.DoesNotExist:
        profile = None
    template = overrides.get("packaging_template") or (profile.packaging_template if profile else None)
    def value(name, template_name):
        if name in overrides and overrides[name] is not None: return Decimal(str(overrides[name]))
        profile_value = getattr(profile, f"{name}_override", None) if profile else None
        raw_value = profile_value if profile_value is not None else (getattr(template, template_name, None) if template else None)
        return Decimal(str(raw_value)) if raw_value is not None else None
    return EffectivePackaging(
        sku=sku, profile=profile, template=template,
        unit_net_weight=Decimal(str(overrides["unit_net_weight"])) if overrides.get("unit_net_weight") is not None else (Decimal(str(profile.unit_net_weight)) if profile and profile.unit_net_weight is not None else None),
        qty_per_carton=value("qty_per_carton", "qty_per_carton"), length=value("carton_length", "carton_length"),
        width=value("carton_width", "carton_width"), height=value("carton_height", "carton_height"),
        carton_tare_weight=value("carton_tare_weight", "carton_tare_weight"),
        gross_weight_override=Decimal(str(overrides["gross_weight_override"])) if overrides.get("gross_weight_override") is not None else (Decimal(str(profile.gross_weight_override)) if profile and profile.gross_weight_override is not None else None),
        partial_carton_policy=(overrides.get("partial_carton_policy") or getattr(template, "partial_carton_policy", None)),
    )


def packaging_summary(sku):
    p = resolve_packaging(sku)
    return {"status": p.status, "template": p.template_id if hasattr(p.template, "id") else None, "effective_qty_per_carton": p.qty_per_carton,
            "effective_length": p.length, "effective_width": p.width, "effective_height": p.height,
            "effective_carton_tare_weight": p.carton_tare_weight, "unit_net_weight": p.unit_net_weight,
            "effective_cbm": p.cbm, "partial_carton_policy": p.partial_carton_policy}


def _source_items(source):
    return source.items.select_related("sku__product").all()


@transaction.atomic
def generate_packing_plan(source):
    """Replace only when an operator explicitly requests regeneration, preserving snapshots otherwise."""
    source_key = {"quote": source} if source.__class__.__name__ == "Quote" else {"order": source}
    PackingPlan.objects.filter(**source_key).delete()
    plan = PackingPlan.objects.create(**source_key)
    warnings, carton_no = [], 0
    total_net = total_gross = total_cbm = ZERO
    for line in _source_items(source):
        if line.quantity <= 0:
            warnings.append(f"{line.sku.sku}: 数量必须大于零")
            continue
        pack = resolve_packaging(line.sku)
        if pack.status not in {"COMPLETE", "VERIFIED"}:
            warnings.append(f"{line.sku.sku}: 包装资料{ '未配置' if pack.status == 'NOT_CONFIGURED' else '不完整'}")
            continue
        full_count = int(line.quantity // pack.qty_per_carton)
        remainder = line.quantity % pack.qty_per_carton
        quantities = [pack.qty_per_carton] * full_count
        if remainder:
            if pack.partial_carton_policy == "MANUAL":
                warnings.append(f"{line.sku.sku}: 剩余 {remainder} 需要人工装箱")
            else: quantities.append(remainder)
        for quantity in quantities:
            carton_no += 1
            partial = quantity != pack.qty_per_carton
            needs_confirmation = partial and pack.partial_carton_policy == "REPACK"
            dims_pending = needs_confirmation
            net = (pack.unit_net_weight * quantity).quantize(Decimal("0.001"))
            gross = pack.gross_weight_override if pack.gross_weight_override is not None and not partial else net + pack.carton_tare_weight
            cbm = ZERO if dims_pending else pack.cbm
            snapshot = {"id": pack.template.id, "code": pack.template.code, "name": pack.template.name} if pack.template else {}
            carton = PackingPlanCarton.objects.create(
                packing_plan=plan, carton_no=carton_no, packaging_template_snapshot=snapshot,
                qty_per_carton_snapshot=pack.qty_per_carton, partial_carton_policy_snapshot=pack.partial_carton_policy,
                length=None if dims_pending else pack.length, width=None if dims_pending else pack.width, height=None if dims_pending else pack.height,
                carton_tare_weight=pack.carton_tare_weight, estimated_net_weight=net, estimated_gross_weight=gross,
                estimated_cbm=cbm, is_partial=partial, requires_confirmation=needs_confirmation,
            )
            PackingPlanCartonItem.objects.create(carton=carton, sku=line.sku, sku_code_snapshot=line.sku.sku,
                sku_name_snapshot=line.sku.product.name, unit_net_weight_snapshot=pack.unit_net_weight, quantity=quantity)
            total_net += net; total_gross += gross; total_cbm += cbm
    plan.total_cartons = carton_no; plan.total_net_weight = total_net; plan.total_gross_weight = total_gross; plan.total_cbm = total_cbm
    plan.warnings = warnings; plan.status = "needs_attention" if warnings else "generated"
    plan.save(update_fields=["total_cartons", "total_net_weight", "total_gross_weight", "total_cbm", "warnings", "status", "updated_at"])
    return plan


@transaction.atomic
def copy_estimated_to_actual(shipment, plan):
    shipment.packages.all().delete()
    for carton in plan.cartons.prefetch_related("items").all():
        package = ShipmentPackage.objects.create(shipment=shipment, carton_no=carton.carton_no, length=carton.length, width=carton.width,
            height=carton.height, actual_net_weight=carton.estimated_net_weight, actual_gross_weight=carton.estimated_gross_weight)
        ShipmentPackageItem.objects.bulk_create([ShipmentPackageItem(shipment_package=package, sku=item.sku, quantity=item.quantity) for item in carton.items.all()])
    return shipment
