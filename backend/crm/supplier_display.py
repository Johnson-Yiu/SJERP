"""Read-only supplier display values; never infer rules from free-text notes."""
from decimal import Decimal, localcontext

from .payment_terms import default_payment_terms


def payment_terms_summary(config):
    stages = config or default_payment_terms()
    parts = []
    for stage in stages:
        ratio = Decimal(str(stage["ratio"]))
        with localcontext() as context:
            context.prec = max(28, len(ratio.as_tuple().digits) + 2)
            percent = format(ratio * 100, "f")
        if "." in percent:
            percent = percent.rstrip("0").rstrip(".")
        parts.append(f'{stage["label"]} {percent}%')
    return " / ".join(parts) + ("（系统默认）" if not config else "")
