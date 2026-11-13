import json
from django.core.management.base import BaseCommand
from crm.services.cost_integrity import inspect_cost_integrity


class Command(BaseCommand):
    help = "只读检查接续订单与派生 SKU 成本来源；不更改或自动修正任何记录。"

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(inspect_cost_integrity(), ensure_ascii=False, indent=2))
