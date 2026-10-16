"""Add synthetic roles only to an empty dedicated R0-F8C database; never change presets."""
from pathlib import Path
from django.conf import settings
from django.db import transaction
from crm.models import AccessRole,RolePermission,EmployeeProfile,OrganizationUnit,Position
assert settings.DATABASES['default']['ENGINE']=='django.db.backends.sqlite3'
assert Path(settings.DATABASES['default']['NAME']).resolve()==(settings.BASE_DIR/'r0f8c-ux.sqlite3').resolve(), 'Run only against the dedicated backend database'
assert (settings.BASE_DIR/'r0f8c-ux.sqlite3').exists()
assert not EmployeeProfile.objects.exists()
assert not AccessRole.objects.filter(code__startswith='r0f8c_').exists()
import json
from crm.permissions import development_superadmin_enabled
root=settings.BASE_DIR.parent/'docs/uat-evidence/r0-f8c'
(root/'preset-baseline.json').write_text(json.dumps({'roles':list(AccessRole.objects.order_by('id').values()),'permissions':list(RolePermission.objects.order_by('id').values()),'employees':EmployeeProfile.objects.count(),'rbac_enforcement':settings.RBAC_ENFORCEMENT,'development_superadmin_enabled':development_superadmin_enabled()},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
with transaction.atomic():
    for code,name in [('r0f8c_editor','R0F8C 合成编辑角色'),('r0f8c_other','R0F8C 另一合成角色')]:
        role=AccessRole.objects.create(code=code,name=name,description='仅供本轮隔离UI测试的合成角色，不对应真实员工。长说明：'+'部门、岗位、功能操作与数据范围各自保持现有定义。'*5,default_data_scope='self',priority=90)
        for module,_ in RolePermission.MODULE_CHOICES:RolePermission.objects.create(role=role,module=module)
    unit=OrganizationUnit.objects.create(code='R0F8C-TEST',name='R0F8C 合成长名称部门 · 多岗位及组织结构布局检查',type='department')
    Position.objects.create(unit=unit,code='R0F8C-TEST-POS',name='R0F8C 合成长岗位名称（未绑定角色，只读）',level='staff')
print('Added 2 synthetic roles, 1 synthetic department/position; no employees or preset changes')
