<script setup>
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api } = useWorkspaceApi()
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Building2, Check, ChevronRight, Crown, KeyRound, UsersRound } from 'lucide-vue-next'

import { accessState, loadAccessControl } from '../accessControl'
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'
import PageLoadState from '../components/PageLoadState.vue'

const data = ref({ units: [], roles: [], modules: [], summary: {} })
const loading = ref(false), hasLoaded = ref(false), saving = ref(false), switching = ref(false)
const error = ref(''), saveError = ref(''), success = ref(''), needsReadback = ref(false)
const selectedRoleId = ref(null), draft = ref([]), savedDraft = ref([]), moduleSearch = ref(''), roleSearch = ref('')
let alive = true, loadVersion = 0
const company = computed(() => data.value.units.find(unit => unit.type === 'company'))
const departments = computed(() => data.value.units.filter(unit => unit.type === 'department'))
const selectedRole = computed(() => data.value.roles.find(role => role.id === selectedRoleId.value))
const globalRoles = computed(() => data.value.roles.filter(role => ['superadmin', 'admin'].includes(role.code)).sort((a, b) => a.priority - b.priority))
const canEditSelected = computed(() => accessState.loaded && !accessState.error && accessState.operator?.can_manage_permissions === true && selectedRole.value && selectedRole.value.code !== 'superadmin')
const busy = computed(() => loading.value || saving.value)
const actions = [['can_view', '查看'], ['can_create', '新建'], ['can_update', '修改'], ['can_delete', '删除'], ['can_export', '导出'], ['can_import', '导入']]
const roleByPosition = { SALES_MANAGER: 'sales_manager', SALESPERSON: 'salesperson', MERCHANDISER: 'merchandiser', OPS_MANAGER: 'ops_manager', WEBSITE_OPS: 'website_ops', PLATFORM_OPS: 'platform_ops', WAREHOUSE_MANAGER: 'warehouse_manager', WAREHOUSE_STAFF: 'warehouse_staff', FINANCE_MANAGER: 'finance_manager', FINANCE_STAFF: 'finance_staff', HR_ADMIN_MANAGER: 'hr_admin_manager', HR_STAFF: 'hr_staff', ADMIN_STAFF: 'admin_staff' }
const guard = useUnsavedChangesGuard({ data: () => draft.value, enabled: () => hasLoaded.value && Boolean(selectedRole.value), busy: () => busy.value })
const dirty = guard.dirty
const visibleRoles = computed(() => data.value.roles.filter(role => `${role.name} ${role.code}`.toLowerCase().includes(roleSearch.value.trim().toLowerCase())))
const visibleModules = computed(() => data.value.modules.filter(module => `${module.name} ${module.code}`.toLowerCase().includes(moduleSearch.value.trim().toLowerCase())))
function permissionFor(module) { return draft.value.find(item => item.module === module) || {} }
function changed(module) { const before = savedDraft.value.find(row => row.module === module) || {}; return actions.some(([key]) => Boolean(before[key]) !== Boolean(permissionFor(module)[key])) }
const changedCount = computed(() => data.value.modules.filter(module => changed(module.code)).length)
function resetDraft() {
  const effective = selectedRole.value?.has_all_permissions === true
    ? null
    : (selectedRole.value?.permissions || selectedRole.value?.effective_permissions || [])
  draft.value = data.value.modules.map(module => {
    const source = effective === null
      ? Object.fromEntries(actions.map(([key]) => [key, true]))
      : effective.find(row => row.module === module.code) || {}
    return { module: module.code, ...Object.fromEntries(actions.map(([key]) => [key, Boolean(source[key])])) }
  })
  savedDraft.value = JSON.parse(JSON.stringify(draft.value)); guard.markClean()
}
async function selectRole(id) {
  if (busy.value || switching.value || needsReadback.value || id === selectedRoleId.value) return
  switching.value = true
  try { await guard.requestClose(() => { if (!alive) return; selectedRoleId.value = id; saveError.value = ''; success.value = ''; moduleSearch.value = ''; resetDraft() }) }
  finally { switching.value = false }
}
function selectRoleByCode(code) { const role = data.value.roles.find(item => item.code === code); if (role) selectRole(role.id) }
function updatePermission(module, action, checked) {
  if (!canEditSelected.value || busy.value || switching.value || needsReadback.value) return
  const permission = permissionFor(module)
  permission[action] = checked
  if (action !== 'can_view' && checked) permission.can_view = true
  if (action === 'can_view' && !checked) actions.slice(1).forEach(([key]) => { permission[key] = false })
  saveError.value = ''; success.value = ''
}
async function discard() {
  if (busy.value || switching.value || needsReadback.value) return
  await guard.requestClose(() => { resetDraft(); saveError.value = ''; success.value = '' })
}
async function readback(roleId) {
  // Both reads are needed: the stored matrix and the current operator may differ after a save.
  const results = await Promise.allSettled([api.get(`/access-roles/${roleId}/`), loadAccessControl({ force: true })])
  if (!alive) return
  const [roleResult, operatorResult] = results
  if (roleResult.status === 'fulfilled') {
    const role = roleResult.value.data
    if (role?.id === roleId && Array.isArray(role.permissions)) {
      const index = data.value.roles.findIndex(item => item.id === roleId)
      if (index >= 0) data.value.roles[index] = role
      resetDraft()
    } else throw new Error('服务器返回的角色配置不完整，请重新读取。')
  }
  if (roleResult.status === 'rejected') throw roleResult.reason
  if (operatorResult.status === 'rejected') throw operatorResult.reason
  needsReadback.value = false
  success.value = '权限已保存，并已重新读取服务器配置。'
}
async function savePermissions() {
  if (busy.value || switching.value || needsReadback.value || !canEditSelected.value || !dirty.value) return
  const roleId = selectedRole.value.id, permissions = JSON.parse(JSON.stringify(draft.value))
  saving.value = true; saveError.value = ''; success.value = ''
  let submitted = false
  try {
    await api.post(`/access-roles/${roleId}/permission-matrix/`, { permissions })
    if (!alive) return
    submitted = true; needsReadback.value = true; savedDraft.value = JSON.parse(JSON.stringify(draft.value)); guard.markClean()
    await readback(roleId)
  } catch (e) { if (alive) saveError.value = submitted ? `权限已提交，但重新核对失败：${e.message}。请重新读取，不要重复保存。` : e.message }
  finally { if (alive) saving.value = false }
}
async function retryReadback() {
  if (busy.value || !needsReadback.value) return
  saving.value = true; saveError.value = ''; success.value = ''
  try { await readback(selectedRoleId.value) }
  catch (e) { if (alive) saveError.value = `权限已提交，仍未完成核对：${e.message}。可重试，或离开后重新打开此页。` }
  finally { if (alive) saving.value = false }
}
async function fetchOverview() {
  const request = ++loadVersion
  loading.value = true; error.value = ''
  try {
    const response = (await api.get('/organization/overview/')).data
    if (!alive || request !== loadVersion) return
    if (!Array.isArray(response.roles) || !Array.isArray(response.modules) || !Array.isArray(response.units)) throw new Error('组织数据不完整，请重新加载。')
    data.value = response
    selectedRoleId.value = response.roles.some(role => role.id === selectedRoleId.value) ? selectedRoleId.value : response.roles.find(role => role.code === 'superadmin')?.id || response.roles[0]?.id || null
    hasLoaded.value = true; needsReadback.value = false; saveError.value = ''; success.value = ''; resetDraft()
  } catch (e) { if (alive && request === loadVersion) error.value = e.message }
  finally { if (alive && request === loadVersion) loading.value = false }
}
async function refresh() { if (!busy.value && !switching.value && !needsReadback.value) await guard.requestClose(() => { resetDraft(); return fetchOverview() }) }
onMounted(fetchOverview)
onBeforeUnmount(() => { alive = false; loadVersion++ })
</script>

<template>
  <div class="organization-page">
    <div class="page-head"><div><h2>组织与权限</h2><p>查看组织架构，按角色维护功能权限。</p></div><button class="btn btn-secondary" :disabled="busy || switching || needsReadback" @click="refresh">{{ loading ? '正在刷新…' : '刷新' }}</button></div>
    <PageLoadState :loading="loading" :has-loaded="hasLoaded" :error="error" @retry="refresh" />
    <template v-if="hasLoaded">
      <div class="permission-note"><KeyRound :size="18" /><div><strong>{{ accessState.operator?.development_superadmin ? '开发身份：全部功能与数据权限' : data.enforcement ? '当前服务端已启用权限执行' : '当前服务端未启用权限执行' }}</strong><p>此页只维护已有角色模板，不改变当前访问模式。正式人员权限与数据范围仍需单独配置和验收。</p></div></div>
      <div class="org-summary"><div v-for="(label,key) in {departments:'部门',positions:'岗位',roles:'角色模板',members:'成员账号'}" :key="key" class="panel"><span>{{ label }}</span><strong>{{ data.summary?.[key] ?? 0 }}</strong></div></div>
      <details class="panel organization-panel"><summary>组织架构 <small>部门与岗位</small></summary><div class="section-title"><div><p>选择岗位，查看对应角色；部门与岗位资料在此只读。</p></div><Building2 :size="20" /></div>
        <div class="org-root"><button v-for="role in globalRoles" :key="role.id" class="global-role" :class="{selected:selectedRole?.id===role.id}" :disabled="busy || switching || needsReadback" @click="selectRole(role.id)"><Crown v-if="role.code==='superadmin'" :size="15" />{{ role.name }}</button><div class="root-line" /><div class="company-node">{{ company?.name || '未配置公司' }}</div></div>
        <div class="department-grid"><div v-for="department in departments" :key="department.id" class="department-column"><div class="department-node">{{ department.name }}</div><div class="position-stack"><button v-for="position in department.positions" :key="position.id" :class="['position-node',position.level,{selected:selectedRole?.code===roleByPosition[position.code]}]" :disabled="busy || switching || needsReadback || !data.roles.some(role=>role.code===roleByPosition[position.code])" @click="selectRoleByCode(roleByPosition[position.code])"><span>{{ position.name }}</span><small>{{ position.level_display }}</small><ChevronRight :size="13" /></button></div></div></div>
        <p v-if="!departments.length" class="empty-note">暂无部门与岗位资料。</p>
      </details>
      <div class="permission-layout"><aside class="panel role-list"><div class="section-title compact"><div><h3>角色模板</h3><p>共 {{ data.roles.length }} 个角色</p></div><UsersRound :size="18" /></div><input v-model="roleSearch" class="role-search" aria-label="搜索角色" placeholder="搜索角色名称或代码" />
        <button v-for="role in visibleRoles" :key="role.id" :class="{active:selectedRole?.id===role.id}" :disabled="busy || switching || needsReadback" :aria-pressed="selectedRole?.id===role.id" @click="selectRole(role.id)"><span><strong>{{ role.name }}</strong><small>{{ role.default_data_scope_display }}</small></span><ChevronRight :size="14" /></button><p v-if="!visibleRoles.length" class="empty-note">没有匹配的角色。</p>
      </aside>
      <section v-if="selectedRole" class="panel matrix-panel" :aria-busy="busy"><div class="role-header"><div><span class="role-code">{{ selectedRole.code }}</span><h3>{{ selectedRole.name }}</h3><p>{{ selectedRole.description || '暂无角色说明。' }}</p></div><div class="scope-card"><small>默认数据范围（只读）</small><strong>{{ selectedRole.default_data_scope_display || '未提供' }}</strong><p>数据范围当前首先用于客户/CRM/销售记录。产品、SKU、库存等共享主数据不按客户负责人切分。</p></div></div>
        <div class="matrix-tools"><label>查找功能模块<input v-model="moduleSearch" placeholder="输入模块名称或代码" /></label><span>{{ visibleModules.length }} / {{ data.modules.length }} 个模块</span><span v-if="dirty" class="dirty-status" role="status">{{ changedCount }} 个模块有未保存修改</span><span v-else-if="!needsReadback">当前没有未保存修改</span></div>
        <p class="matrix-help">勾选任一操作会同时勾选“查看”；取消“查看”会清除该模块的其他操作权限。筛选只影响显示，保存仍包含全部模块。</p>
        <p v-if="selectedRole.has_all_permissions === true" class="read-only-note">包含全部ERP业务权限，不受普通勾选项限制。此最高角色不可修改；下方勾选反映实际生效权限。</p><p v-else-if="!canEditSelected" class="read-only-note">当前身份只能查看，不能修改角色权限。</p>
        <div class="table-wrap matrix-scroll" tabindex="0" role="region" aria-label="角色权限矩阵，可横向及纵向滚动"><table class="permission-table"><caption class="matrix-caption">{{ selectedRole.name }} · 功能权限</caption><thead><tr><th scope="col">功能模块</th><th v-for="action in actions" :key="action[0]" scope="col">{{ action[1] }}</th></tr></thead><tbody><tr v-for="module in visibleModules" :key="module.code" :class="{changed:changed(module.code)}"><th scope="row">{{ module.name }}</th><td v-for="action in actions" :key="action[0]"><label class="permission-check"><input type="checkbox" :checked="permissionFor(module.code)[action[0]]" :disabled="!canEditSelected || busy || switching || needsReadback" :aria-label="`${selectedRole.name} ${module.name} ${action[1]}`" @change="updatePermission(module.code,action[0],$event.target.checked)" /><span><Check :size="12" /></span></label></td></tr></tbody></table></div>
        <p v-if="!visibleModules.length" class="empty-note">没有匹配的功能模块，请调整搜索条件。</p>
        <div class="matrix-feedback"><p v-if="saveError" role="alert" class="save-error">{{ saveError }}</p><p v-if="success" role="status" class="save-success">{{ success }}</p><p v-if="saving" role="status">{{ needsReadback ? '正在重新读取角色和当前身份权限…' : '正在保存，请勿离开页面…' }}</p><p v-if="needsReadback && !saving">权限已提交，尚未完成核对。可重新读取，或离开后重新打开页面。</p><RouterLink v-if="accessState.error" to="/access-status-error" class="btn btn-secondary">检查权限状态</RouterLink></div>
        <div class="role-header-actions matrix-actions"><button v-if="needsReadback" class="btn btn-primary" :disabled="busy" @click="retryReadback">重新读取已保存配置</button><template v-else-if="canEditSelected"><button class="btn btn-secondary" :disabled="busy || switching || !dirty" @click="discard">撤销未保存修改</button><button class="btn btn-primary" :disabled="busy || switching || !dirty" @click="savePermissions">{{ saving ? '保存中...' : '保存权限' }}</button></template><span v-else>只读配置</span></div>
      </section><section v-else class="panel empty-note">暂无角色模板。</section></div>
    </template>
  </div>
</template>
<style scoped>
.foundation-badge{display:flex;align-items:center;gap:6px;padding:8px 11px;border-radius:20px;background:#e1f1e9;color:#286a55;font-size:var(--text-secondary);font-weight:600}
.permission-note{display:flex;gap:12px;align-items:flex-start;background:#173f37;color:white;border-radius:13px;padding:16px 18px;margin-bottom:14px}.permission-note svg{color:#9fd1bf;flex:none;margin-top:2px}.permission-note strong{font-size:var(--text-body)}.permission-note p{margin:4px 0 0;color:#a9c8be;font-size:var(--text-caption)}
.org-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin-bottom:14px}.org-summary .panel{padding:15px 17px}.org-summary span,.org-summary small{display:block;color:#84928d;font-size:var(--text-caption)}.org-summary strong{display:block;font-size:var(--text-page);color:#1d4439;margin:7px 0 4px}.organization-panel{padding:20px;margin-bottom:14px}.section-title{display:flex;align-items:flex-start;justify-content:space-between}.section-title h3{margin:0;font-size:var(--text-section)}.section-title p{margin:4px 0 0;color:#8a9792;font-size:var(--text-caption)}.section-title>svg{color:#77968b}.org-root{display:flex;flex-direction:column;align-items:center;margin-top:22px}.global-role{border:1px solid #b9c9c3;background:white;color:#38534a;padding:7px 13px;font-size:var(--text-body);display:flex;align-items:center;gap:6px;margin-bottom:7px;border-radius:7px}.global-role:first-child{background:#125b48;color:white;border-color:#125b48}.global-role.selected,.position-node.selected{box-shadow:0 0 0 3px #b9d9cf;border-color:#3f8572}.root-line{width:1px;height:12px;background:#b9c7c2}.company-node,.department-node{border:1px solid #b9c7c2;background:#f9fbfa;border-radius:7px;padding:8px 14px;font-size:var(--text-body);font-weight:600;color:#354a43}.department-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:25px;position:relative}.department-grid:before{content:'';position:absolute;left:10%;right:10%;top:-13px;border-top:1px solid #bdc9c5}.department-column{position:relative}.department-column:before{content:'';position:absolute;left:50%;top:-13px;height:13px;border-left:1px solid #bdc9c5}.department-node{text-align:center}.position-stack{display:flex;flex-direction:column;gap:7px;margin-top:10px}.position-node{width:100%;border:1px solid #dce4e0;background:white;border-radius:8px;padding:8px 9px;display:grid;grid-template-columns:1fr auto;grid-template-areas:'name icon' 'level icon';text-align:left;color:#3f514b}.position-node span{grid-area:name;font-size:var(--text-caption);font-weight:600}.position-node small{grid-area:level;font-size:var(--text-caption);color:#8b9792;margin-top:2px}.position-node svg{grid-area:icon;align-self:center;color:#96a39e}.position-node.supervisor{background:#edf5f1;border-color:#cfe0da}.permission-layout{display:grid;grid-template-columns:250px 1fr;gap:14px}.role-list{padding:15px}.section-title.compact{padding:2px 3px 12px;border-bottom:1px solid var(--line)}.role-list>button{width:100%;border:0;background:transparent;padding:9px 8px;border-radius:8px;display:flex;align-items:center;justify-content:space-between;text-align:left;color:#495b55}.role-list>button:hover,.role-list>button.active{background:#eaf3ef;color:#174f42}.role-list>button span strong,.role-list>button span small{display:block}.role-list>button strong{font-size:var(--text-body)}.role-list>button small{font-size:var(--text-caption);color:#89958f;margin-top:2px}.matrix-panel{min-width:0;overflow:hidden}.role-header{padding:18px 20px;display:flex;justify-content:space-between;gap:18px;align-items:center;border-bottom:1px solid var(--line)}.role-code{text-transform:uppercase;letter-spacing:.1em;color:#83908c;font-size:var(--text-caption)}.role-header h3{font-size:var(--text-section);margin:4px 0}.role-header p{font-size:var(--text-caption);color:#7c8984;margin:0}.role-header-actions{display:flex;align-items:center;gap:9px}.role-header-actions .btn{white-space:nowrap}.role-header-actions .btn:disabled{opacity:.55;cursor:not-allowed}.scope-card{background:#edf5f1;border-radius:9px;padding:10px 12px;min-width:130px}.scope-card small,.scope-card strong{display:block}.scope-card small{font-size:var(--text-caption);color:#789087}.scope-card strong{font-size:var(--text-body);color:#245c4b;margin-top:4px}.permission-table{width:100%;border-collapse:collapse;min-width:760px}.permission-table th{background:#f8faf8;color:#81908b;font-size:var(--text-body);padding:10px;text-align:center;border-bottom:1px solid var(--line)}.permission-table th:first-child,.permission-table td:first-child{text-align:left}.permission-table td{padding:9px 10px;border-bottom:1px solid #edf0ee;text-align:center;font-size:var(--text-body);color:#43534e}.permission-check{display:inline-grid;place-items:center;margin:0}.permission-check input{position:absolute;opacity:0}.permission-check span{width:21px;height:21px;border:1px solid #d5ded9;border-radius:6px;display:grid;place-items:center;color:transparent;background:white;transition:.15s}.permission-check input:checked+span{background:#26705c;border-color:#26705c;color:white}.permission-check input:focus-visible+span{box-shadow:0 0 0 3px #c6dfd7}.permission-check input:disabled+span{opacity:.65;background:#f1f4f2;cursor:not-allowed}
@media(max-width:1150px){.department-grid{grid-template-columns:repeat(3,1fr)}.department-grid:before,.department-column:before{display:none}.permission-layout{grid-template-columns:220px 1fr}}
@media(max-width:800px){.org-summary{grid-template-columns:1fr 1fr}.department-grid{grid-template-columns:1fr 1fr}.permission-layout{grid-template-columns:1fr}.role-list{display:grid;grid-template-columns:1fr 1fr;gap:4px}.role-list .section-title{grid-column:1/-1}}
@media(max-width:520px){.org-summary,.department-grid,.role-list{grid-template-columns:1fr}.role-header{align-items:flex-start;flex-direction:column}.role-header-actions{width:100%;align-items:stretch;flex-direction:column}.scope-card{width:100%}.foundation-badge{align-self:flex-start}}

.organization-page{min-width:0}.organization-panel summary{cursor:pointer;font-size:var(--text-section);font-weight:600;color:#345848}.organization-panel summary small{font-size:var(--text-caption);font-weight:400;color:#7d9184;margin-left:8px}.organization-panel[open] summary{margin-bottom:16px}.permission-layout{grid-template-columns:240px minmax(0,1fr)}.org-summary,.department-grid{min-width:0}.department-column,.role-list,.role-header>div{min-width:0}.department-node,.position-node span,.company-node,.global-role,.role-header,.role-list button{overflow-wrap:anywhere}.role-header{align-items:start;display:grid;grid-template-columns:minmax(0,1fr) minmax(180px,260px)}.scope-card{min-width:0}.role-search,.matrix-tools input{width:100%;min-width:0;box-sizing:border-box;border:1px solid #ccd9d2;border-radius:7px;padding:9px;font:inherit;background:white;color:#36594a}.role-search{margin:12px 0}.matrix-tools{display:flex;align-items:center;flex-wrap:wrap;gap:12px;padding:16px 18px 8px;font-size:var(--text-caption)}.matrix-tools label{display:grid;gap:5px;max-width:100%;width:250px}.matrix-help,.read-only-note{padding:0 18px;font-size:var(--text-caption);color:#687b70;line-height:1.7}.read-only-note{color:#72531d}.dirty-status{color:#936019;font-weight:700}.matrix-scroll{overflow:auto;max-height:540px;position:relative;isolation:isolate;border-top:1px solid #e0e7e2}.matrix-caption{text-align:left;padding:8px 12px;color:#61786c;font-size:var(--text-caption)}.permission-table thead th{position:sticky;top:0;z-index:3;white-space:nowrap}.permission-table tbody th{position:sticky;left:0;z-index:1;background:#fff;text-align:left;padding:10px;min-width:140px;max-width:230px;overflow-wrap:anywhere;font-size:var(--text-body);border-bottom:1px solid #edf0ee}.permission-table thead th:first-child{left:0;z-index:4}.permission-table tr.changed th,.permission-table tr.changed td{background:#fff8e9}.permission-check{min-width:30px;min-height:30px;position:relative}.permission-check input{inset:0;width:100%;height:100%;margin:0;cursor:pointer}.permission-check input:disabled{cursor:not-allowed}.permission-check input:disabled:checked+span{background:#d9e8df;color:#315a43;border-color:#9fb8a9}.matrix-actions{padding:14px 18px;border-top:1px solid #e0e7e2;justify-content:flex-end;flex-wrap:wrap}.matrix-feedback{padding:0 18px;overflow-wrap:anywhere;font-size:var(--text-body)}.save-error{color:#973d36;background:#fff2ef;padding:12px;border-radius:8px}.save-success{color:#286449;background:#eef8f0;padding:12px;border-radius:8px}.empty-note{padding:18px;color:#758579}.page-head{gap:12px}.role-list button:disabled,button:disabled{cursor:not-allowed;opacity:.65}.role-list{align-self:start}.permission-note>div{min-width:0}.permission-note p{line-height:1.7}.permission-table th{font-weight:600}.permission-table tbody th{background-clip:padding-box}
@media(max-width:1200px){.permission-layout{grid-template-columns:minmax(0,1fr)}.role-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.role-list .section-title,.role-list .role-search{grid-column:1/-1}.role-list>button{width:100%;max-width:100%}.role-header{grid-template-columns:minmax(0,1fr) minmax(180px,260px)}}
@media(max-width:650px){.role-list{grid-template-columns:repeat(2,minmax(0,1fr))}.role-header{grid-template-columns:minmax(0,1fr)}.org-summary{grid-template-columns:1fr 1fr}.department-grid{grid-template-columns:1fr 1fr}.matrix-actions{flex-direction:column;align-items:stretch}.role-header-actions{width:auto}}
</style>

