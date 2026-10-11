<script setup>
import { computed, onMounted, ref } from 'vue'
import { Building2, Check, ChevronRight, Crown, Database, KeyRound, ShieldCheck, UsersRound } from 'lucide-vue-next'
import { api } from '../api'
import { accessState, loadAccessControl } from '../accessControl'

const data = ref({ units: [], roles: [], summary: {} })
const loading = ref(true), saving = ref(false), error = ref(''), selectedRoleId = ref(null)
const toast = ref('')
const company = computed(() => data.value.units.find(unit => unit.type === 'company'))
const departments = computed(() => data.value.units.filter(unit => unit.type === 'department'))
const selectedRole = computed(() => data.value.roles.find(role => role.id === selectedRoleId.value) || data.value.roles[0])
const globalRoles = computed(() => data.value.roles.filter(role => ['superadmin', 'admin'].includes(role.code)).sort((a, b) => a.priority - b.priority))
const canEditSelected = computed(() => accessState.operator?.can_manage_permissions === true && selectedRole.value && selectedRole.value.code !== 'superadmin')
const roleByPosition = {
  SALES_MANAGER: 'sales_manager', SALESPERSON: 'salesperson', MERCHANDISER: 'merchandiser',
  OPS_MANAGER: 'ops_manager', WEBSITE_OPS: 'website_ops', PLATFORM_OPS: 'platform_ops',
  WAREHOUSE_MANAGER: 'warehouse_manager', WAREHOUSE_STAFF: 'warehouse_staff',
  FINANCE_MANAGER: 'finance_manager', FINANCE_STAFF: 'finance_staff',
  HR_ADMIN_MANAGER: 'hr_admin_manager', HR_STAFF: 'hr_staff', ADMIN_STAFF: 'admin_staff',
}
const actions = [['can_view', '查看'], ['can_create', '新建'], ['can_update', '修改'], ['can_delete', '删除'], ['can_export', '导出'], ['can_import', '导入']]

function selectRoleByCode(code) {
  const role = data.value.roles.find(item => item.code === code)
  if (role) selectedRoleId.value = role.id
}
function permissionFor(module) {
  if (!selectedRole.value) return {}
  let permission = selectedRole.value.permissions.find(item => item.module === module)
  if (!permission) {
    permission = { module, can_view: false, can_create: false, can_update: false, can_delete: false, can_export: false, can_import: false }
    selectedRole.value.permissions.push(permission)
  }
  return permission
}
function updatePermission(module, action, checked) {
  const permission = permissionFor(module)
  permission[action] = checked
  if (action !== 'can_view' && checked) permission.can_view = true
  if (action === 'can_view' && !checked) actions.slice(1).forEach(([key]) => { permission[key] = false })
}
async function savePermissions() {
  if (!canEditSelected.value) return
  saving.value = true
  try {
    const permissions = data.value.modules.map(module => ({ module: module.code, ...permissionFor(module.code) }))
    const response = await api.post(`/access-roles/${selectedRole.value.id}/permission-matrix/`, { permissions })
    const index = data.value.roles.findIndex(role => role.id === response.data.id)
    data.value.roles[index] = response.data
    await loadAccessControl({ force: true })
    toast.value = `${response.data.name}权限已保存`
    setTimeout(() => { toast.value = '' }, 2500)
  } catch (e) { toast.value = e.message; setTimeout(() => { toast.value = '' }, 3000) } finally { saving.value = false }
}
async function load() {
  try {
    const response = await api.get('/organization/overview/')
    data.value = response.data
    selectedRoleId.value = response.data.roles.find(role => role.code === 'superadmin')?.id || response.data.roles[0]?.id
  } catch (e) { error.value = e.message } finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <div>
    <div class="page-head"><div><h2>组织与权限</h2><p>以部门、岗位、角色、数据范围四层结构支撑后续团队扩张。</p></div><span class="foundation-badge"><ShieldCheck :size="15" /> 权限底座已建立</span></div>
    <div v-if="loading" class="panel loading"><div class="spinner" /></div>
    <div v-else-if="error" class="panel empty"><Database :size="32" /><h3>权限数据加载失败</h3><p>{{ error }}</p></div>
    <template v-else>
      <div class="permission-note"><KeyRound :size="18" /><div><strong>{{ data.enforcement ? '权限已强制执行' : '权限配置模式' }}</strong><p v-if="data.enforcement">系统正在按成员角色限制功能与数据访问。</p><p v-else>三位合伙人继续使用全局最高权限。成员账号建立前暂不强制拦截；当前可配置角色模板，启用登录后仅超级管理员和管理员能够修改。</p></div></div>

      <div class="org-summary">
        <div class="panel"><span>部门</span><strong>{{ data.summary.departments }}</strong><small>销售、运营、仓管、财务、人事行政</small></div>
        <div class="panel"><span>岗位</span><strong>{{ data.summary.positions }}</strong><small>主管与执行岗位分层</small></div>
        <div class="panel"><span>角色模板</span><strong>{{ data.summary.roles }}</strong><small>按岗位预置功能权限</small></div>
        <div class="panel"><span>成员账号</span><strong>{{ data.summary.members }}</strong><small>建立账号后分配部门与角色</small></div>
      </div>

      <section class="panel organization-panel">
        <div class="section-title"><div><h3>组织架构</h3><p>点击管理员或岗位，可在下方查看对应角色权限。</p></div><Building2 :size="20" /></div>
        <div class="org-root">
          <button v-for="role in globalRoles" :key="role.id" class="global-role" :class="{ selected: selectedRole?.id === role.id }" @click="selectedRoleId = role.id"><Crown v-if="role.code === 'superadmin'" :size="15" />{{ role.name }}</button>
          <div class="root-line" />
          <div class="company-node">{{ company?.name || '森爵照明' }}</div>
        </div>
        <div class="department-grid">
          <div v-for="department in departments" :key="department.id" class="department-column">
            <div class="department-node">{{ department.name }}</div>
            <div class="position-stack">
              <button v-for="position in department.positions" :key="position.id" :class="['position-node', position.level, { selected: selectedRole?.code === roleByPosition[position.code] }]" @click="selectRoleByCode(roleByPosition[position.code])">
                <span>{{ position.name }}</span><small>{{ position.level_display }}</small><ChevronRight :size="13" />
              </button>
            </div>
          </div>
        </div>
      </section>

      <div class="permission-layout">
        <aside class="panel role-list">
          <div class="section-title compact"><div><h3>角色模板</h3><p>{{ data.roles.length }} 个预置角色</p></div><UsersRound :size="18" /></div>
          <button v-for="role in data.roles" :key="role.id" :class="{ active: selectedRole?.id === role.id }" @click="selectedRoleId = role.id">
            <span><strong>{{ role.name }}</strong><small>{{ role.default_data_scope_display }}</small></span><ChevronRight :size="14" />
          </button>
        </aside>
        <section v-if="selectedRole" class="panel matrix-panel">
          <div class="role-header">
            <div><span class="role-code">{{ selectedRole.code }}</span><h3>{{ selectedRole.name }}</h3><p>{{ selectedRole.description }}</p></div>
            <div class="role-header-actions"><div class="scope-card"><small>默认数据范围</small><strong>{{ selectedRole.default_data_scope_display }}</strong></div><button v-if="accessState.operator?.can_manage_permissions" class="btn btn-primary" :disabled="!canEditSelected || saving" @click="savePermissions">{{ selectedRole.code === 'superadmin' ? '最高权限已锁定' : saving ? '保存中...' : '保存权限' }}</button></div>
          </div>
          <div class="table-wrap"><table class="permission-table"><thead><tr><th>功能模块</th><th v-for="action in actions" :key="action[0]">{{ action[1] }}</th></tr></thead><tbody>
            <tr v-for="module in data.modules" :key="module.code"><td>{{ module.name }}</td><td v-for="action in actions" :key="action[0]"><label class="permission-check"><input type="checkbox" :checked="permissionFor(module.code)[action[0]]" :disabled="!canEditSelected" :aria-label="`${selectedRole.name} ${module.name} ${action[1]}`" @change="updatePermission(module.code, action[0], $event.target.checked)" /><span><Check :size="12" /></span></label></td></tr>
          </tbody></table></div>
        </section>
      </div>
    </template>
    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>

<style scoped>
.foundation-badge{display:flex;align-items:center;gap:6px;padding:8px 11px;border-radius:20px;background:#e1f1e9;color:#286a55;font-size:var(--text-secondary);font-weight:600}
.permission-note{display:flex;gap:12px;align-items:flex-start;background:#173f37;color:white;border-radius:13px;padding:16px 18px;margin-bottom:14px}.permission-note svg{color:#9fd1bf;flex:none;margin-top:2px}.permission-note strong{font-size:var(--text-body)}.permission-note p{margin:4px 0 0;color:#a9c8be;font-size:var(--text-caption)}
.org-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin-bottom:14px}.org-summary .panel{padding:15px 17px}.org-summary span,.org-summary small{display:block;color:#84928d;font-size:var(--text-caption)}.org-summary strong{display:block;font-size:var(--text-page);color:#1d4439;margin:7px 0 4px}.organization-panel{padding:20px;margin-bottom:14px}.section-title{display:flex;align-items:flex-start;justify-content:space-between}.section-title h3{margin:0;font-size:var(--text-section)}.section-title p{margin:4px 0 0;color:#8a9792;font-size:var(--text-caption)}.section-title>svg{color:#77968b}.org-root{display:flex;flex-direction:column;align-items:center;margin-top:22px}.global-role{border:1px solid #b9c9c3;background:white;color:#38534a;padding:7px 13px;font-size:var(--text-body);display:flex;align-items:center;gap:6px;margin-bottom:7px;border-radius:7px}.global-role:first-child{background:#125b48;color:white;border-color:#125b48}.global-role.selected,.position-node.selected{box-shadow:0 0 0 3px #b9d9cf;border-color:#3f8572}.root-line{width:1px;height:12px;background:#b9c7c2}.company-node,.department-node{border:1px solid #b9c7c2;background:#f9fbfa;border-radius:7px;padding:8px 14px;font-size:var(--text-body);font-weight:600;color:#354a43}.department-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:25px;position:relative}.department-grid:before{content:'';position:absolute;left:10%;right:10%;top:-13px;border-top:1px solid #bdc9c5}.department-column{position:relative}.department-column:before{content:'';position:absolute;left:50%;top:-13px;height:13px;border-left:1px solid #bdc9c5}.department-node{text-align:center}.position-stack{display:flex;flex-direction:column;gap:7px;margin-top:10px}.position-node{width:100%;border:1px solid #dce4e0;background:white;border-radius:8px;padding:8px 9px;display:grid;grid-template-columns:1fr auto;grid-template-areas:'name icon' 'level icon';text-align:left;color:#3f514b}.position-node span{grid-area:name;font-size:var(--text-caption);font-weight:600}.position-node small{grid-area:level;font-size:var(--text-caption);color:#8b9792;margin-top:2px}.position-node svg{grid-area:icon;align-self:center;color:#96a39e}.position-node.supervisor{background:#edf5f1;border-color:#cfe0da}.permission-layout{display:grid;grid-template-columns:250px 1fr;gap:14px}.role-list{padding:15px}.section-title.compact{padding:2px 3px 12px;border-bottom:1px solid var(--line)}.role-list>button{width:100%;border:0;background:transparent;padding:9px 8px;border-radius:8px;display:flex;align-items:center;justify-content:space-between;text-align:left;color:#495b55}.role-list>button:hover,.role-list>button.active{background:#eaf3ef;color:#174f42}.role-list>button span strong,.role-list>button span small{display:block}.role-list>button strong{font-size:var(--text-body)}.role-list>button small{font-size:var(--text-caption);color:#89958f;margin-top:2px}.matrix-panel{min-width:0;overflow:hidden}.role-header{padding:18px 20px;display:flex;justify-content:space-between;gap:18px;align-items:center;border-bottom:1px solid var(--line)}.role-code{text-transform:uppercase;letter-spacing:.1em;color:#83908c;font-size:var(--text-caption)}.role-header h3{font-size:var(--text-section);margin:4px 0}.role-header p{font-size:var(--text-caption);color:#7c8984;margin:0}.role-header-actions{display:flex;align-items:center;gap:9px}.role-header-actions .btn{white-space:nowrap}.role-header-actions .btn:disabled{opacity:.55;cursor:not-allowed}.scope-card{background:#edf5f1;border-radius:9px;padding:10px 12px;min-width:130px}.scope-card small,.scope-card strong{display:block}.scope-card small{font-size:var(--text-caption);color:#789087}.scope-card strong{font-size:var(--text-body);color:#245c4b;margin-top:4px}.permission-table{width:100%;border-collapse:collapse;min-width:650px}.permission-table th{background:#f8faf8;color:#81908b;font-size:var(--text-body);padding:10px;text-align:center;border-bottom:1px solid var(--line)}.permission-table th:first-child,.permission-table td:first-child{text-align:left}.permission-table td{padding:9px 10px;border-bottom:1px solid #edf0ee;text-align:center;font-size:var(--text-body);color:#43534e}.permission-check{display:inline-grid;place-items:center;margin:0}.permission-check input{position:absolute;opacity:0}.permission-check span{width:21px;height:21px;border:1px solid #d5ded9;border-radius:6px;display:grid;place-items:center;color:transparent;background:white;transition:.15s}.permission-check input:checked+span{background:#26705c;border-color:#26705c;color:white}.permission-check input:focus-visible+span{box-shadow:0 0 0 3px #c6dfd7}.permission-check input:disabled+span{opacity:.65;background:#f1f4f2;cursor:not-allowed}
@media(max-width:1150px){.department-grid{grid-template-columns:repeat(3,1fr)}.department-grid:before,.department-column:before{display:none}.permission-layout{grid-template-columns:220px 1fr}}
@media(max-width:800px){.org-summary{grid-template-columns:1fr 1fr}.department-grid{grid-template-columns:1fr 1fr}.permission-layout{grid-template-columns:1fr}.role-list{display:grid;grid-template-columns:1fr 1fr;gap:4px}.role-list .section-title{grid-column:1/-1}}
@media(max-width:520px){.org-summary,.department-grid,.role-list{grid-template-columns:1fr}.role-header{align-items:flex-start;flex-direction:column}.role-header-actions{width:100%;align-items:stretch;flex-direction:column}.scope-card{width:100%}.foundation-badge{align-self:flex-start}}
</style>
