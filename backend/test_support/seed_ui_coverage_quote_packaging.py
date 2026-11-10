"""Reuse the ISS-007 quote fixture and add a synthetic packaging template in the isolated database."""
import runpy
from pathlib import Path
import django
django.setup()
from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime
from crm.models import PackagingTemplate

verify_isolated_runtime(settings=settings, database_must_exist=True)
runpy.run_path(str(Path(settings.BASE_DIR).parent / 'docs/uat-evidence/r1-pre-uat-iss007-attachment-flow/seed_isolated.py'))
PackagingTemplate.objects.create(name='合成包装模板', carton_length=50, carton_width=40, carton_height=30, carton_tare_weight='1.5', partial_carton_policy='SAME_CARTON', active=True)
print('Added synthetic packaging template in isolated database')
