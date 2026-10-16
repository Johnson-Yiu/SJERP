"""Read-only evidence; assert exact isolated DB and unchanged preset/security configuration."""
import json,os
from pathlib import Path
from django.conf import settings
from crm.models import AccessRole,RolePermission,EmployeeProfile
from crm.permissions import development_superadmin_enabled
assert settings.DATABASES['default']['ENGINE']=='django.db.backends.sqlite3'
assert Path(settings.DATABASES['default']['NAME']).resolve()==(settings.BASE_DIR/'r0f8c-ux.sqlite3').resolve(), 'Run only against the dedicated backend database'
assert (settings.BASE_DIR/'r0f8c-ux.sqlite3').exists()
root=settings.BASE_DIR.parent/'docs/uat-evidence/r0-f8c'
baseline=json.loads((root/'preset-baseline.json').read_text(encoding='utf-8'))
normalize=lambda value:json.loads(json.dumps(value,default=str))
ids=[row['id'] for row in baseline['roles']]
assert normalize(list(AccessRole.objects.filter(id__in=ids).order_by('id').values()))==baseline['roles']
assert normalize(list(RolePermission.objects.filter(role_id__in=ids).order_by('id').values()))==baseline['permissions']
assert EmployeeProfile.objects.count()==baseline['employees']==0
assert settings.RBAC_ENFORCEMENT==baseline['rbac_enforcement']==False
assert development_superadmin_enabled()==baseline['development_superadmin_enabled']==True
path=root/'database-verification.json';records=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
record={'step':os.environ.get('F8C_EVIDENCE_STEP','verification'),'preset_roles_unchanged':True,'preset_permissions_unchanged':True,'employees':0,'rbac_enforcement':False,'development_superadmin_enabled':True,'synthetic_roles':list(AccessRole.objects.filter(code__startswith='r0f8c_').order_by('id').values()),'synthetic_permissions':list(RolePermission.objects.filter(role__code__startswith='r0f8c_').order_by('role_id','module').values())}
records.append(normalize(record));path.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: preset roles/permissions unchanged; employees=0; RBAC=false; development superadmin=true')
