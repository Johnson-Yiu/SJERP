<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
import { can } from '../accessControl'
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'
const route = useRoute(), router = useRouter()
const { api } = useWorkspaceApi()
const rows = ref([]), count = ref(0), loading = ref(false), busy = ref(false), error = ref(''), feedback = ref('')
const selected = ref(null), editing = ref(false), history = ref([]), voiding = ref(false), reason = ref('')
const customers = ref([]), customerSearch = ref(''), contacts = ref([]), products = ref([]), productSearch = ref('')
const search = ref(route.query.search || ''), state = ref(route.query.state || 'active')
const form = reactive({ customer: '', follow_up: null, contact: null, product: null, requirement: '', specification: '', other_requirements: '' })
const page = computed(() => Number(route.query.page) || 1)
const guard = useUnsavedChangesGuard({ data: () => form, enabled: () => editing.value, busy: () => busy.value })
const displayTime = value => value ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '—'
let requestKey = '', sequence = 0, detailSequence = 0
const writable = computed(() => can('followups', selected.value ? 'update' : 'create'))
async function load() {
  const seq = ++sequence; loading.value = true; error.value = ''
  try {
    const { data } = await api.get('/new-product-reminders/', { params: { tag: '新品提醒', search: route.query.search, state: route.query.state || 'active', page: page.value, customer: route.query.customer } })
    if (seq === sequence) { rows.value = data.results; count.value = data.count }
  } catch (e) { if (seq === sequence) { rows.value = []; error.value = e.message } }
  finally { if (seq === sequence) loading.value = false }
}
async function filter(nextPage = 1) {
  await router.push({ query: { ...route.query, search: search.value || undefined, state: state.value, page: nextPage, detail: undefined } })
}
async function findCustomers() {
  try { customers.value = (await api.get('/customers/', { params: { search: customerSearch.value } })).data.results }
  catch (e) { error.value = e.message }
}
async function findProducts() {
  try { products.value = (await api.get('/products/', { params: { search: productSearch.value } })).data.results }
  catch (e) { error.value = e.message }
}
watch(() => form.customer, async id => {
  contacts.value = []; if (!id || !can('contacts', 'view')) return
  try { contacts.value = (await api.get('/contacts/', { params: { customer: id } })).data.results }
  catch (e) { error.value = e.message }
})
async function open(id) {
  if (!await guard.requestClose(() => { editing.value = false })) return
  const seq = ++detailSequence
  error.value = ''; feedback.value = ''; selected.value = null; history.value = []; voiding.value = false
  try {
    const [record, events] = await Promise.all([api.get(`/new-product-reminders/${id}/`), api.get(`/new-product-reminders/${id}/history/`)])
    if (seq === detailSequence) { selected.value = record.data; history.value = events.data }
  } catch (e) { if (seq === detailSequence) error.value = e.message }
}
async function start() {
  if (!await guard.requestClose(() => { editing.value = false })) return
  ++detailSequence; selected.value = null; history.value = []; error.value = ''; feedback.value = ''; voiding.value = false
  Object.assign(form, { customer: route.query.customer || '', follow_up: route.query.follow_up ? Number(route.query.follow_up) : null, contact: null, product: null, requirement: '', specification: '', other_requirements: '' })
  requestKey = crypto.randomUUID(); editing.value = true; guard.markClean(); await findCustomers()
}
function edit() {
  Object.keys(form).forEach(k => { form[k] = selected.value[k] ?? null }); editing.value = true; guard.markClean()
}
async function save() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    const payload = { ...form, customer: Number(form.customer), contact: form.contact || null, product: form.product || null }
    if (!can('contacts', 'view')) delete payload.contact
    if (!can('products', 'view')) delete payload.product
    const { data } = selected.value
      ? await api.patch(`/new-product-reminders/${selected.value.id}/`, { ...payload, version: selected.value.version })
      : await api.post('/new-product-reminders/', { ...payload, request_key: requestKey })
    guard.markClean(); editing.value = false; selected.value = data; feedback.value = '已保存'
    history.value = (await api.get(`/new-product-reminders/${data.id}/history/`)).data
    await load()
    busy.value = false
    await router.replace({ query: { ...route.query, detail: data.id } })
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
async function confirmVoid() {
  if (busy.value || !reason.value.trim()) return
  busy.value = true; error.value = ''
  try {
    selected.value = (await api.post(`/new-product-reminders/${selected.value.id}/void/`, { reason: reason.value, version: selected.value.version })).data
    voiding.value = false; feedback.value = '已作废'; await load()
    history.value = (await api.get(`/new-product-reminders/${selected.value.id}/history/`)).data
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
watch(() => route.query, async () => {
  search.value = route.query.search || ''; state.value = route.query.state || 'active'; await load()
  if (route.query.detail && String(selected.value?.id) !== String(route.query.detail)) await open(route.query.detail)
  else if (!route.query.detail && !editing.value) { ++detailSequence; selected.value = null; history.value = []; voiding.value = false }
}, { immediate: true })
</script>

<template>
  <section class="reminders">
    <div class="reminder-header"><div><h2>客户产品需求</h2><p>记录客户所找的产品，按关键词查找待联系客户。</p></div><button v-if="can('followups','create')" class="btn btn-primary" :disabled="busy" @click="start">记录新品需求</button></div>
    <form class="filters" @submit.prevent="filter()">
      <label>标签<select aria-label="需求标签"><option>新品提醒</option></select></label>
      <label class="grow">关键词<input v-model="search" placeholder="产品、规格、其他要求或客户" /></label>
      <label>条目状态<select v-model="state"><option value="active">有效条目</option><option value="void">已作废</option><option value="all">全部条目</option></select></label>
      <button class="btn btn-secondary">查询</button>
    </form>
    <p v-if="error" role="alert">{{ error }} <button :disabled="busy" @click="load">重试列表</button></p><p v-if="feedback" role="status">{{ feedback }}</p>
    <p v-if="loading" role="status">正在加载…</p>
    <p v-else-if="!rows.length && !error">没有符合条件的需求。</p>
    <div v-for="row in rows" :key="row.id" class="requirement" :class="{ voided: row.voided_at }">
      <div><strong>{{ row.customer_name }}</strong> <span class="badge">新品提醒</span> <strong v-if="row.voided_at">已作废</strong></div>
      <p>{{ row.requirement }}</p><p v-if="row.specification">规格：{{ row.specification }}</p><p v-if="row.other_requirements">其他要求：{{ row.other_requirements }}</p>
      <button class="btn btn-secondary" :disabled="busy" @click="router.push({query:{...route.query,detail:row.id}})">查看需求 #{{ row.id }}</button>
      <RouterLink :to="{path:'/customers',query:{detail:row.customer}}">查看客户</RouterLink>
    </div>
    <nav class="pager" aria-label="需求分页"><button :disabled="page <= 1 || loading" @click="filter(page-1)">上一页</button><span>共 {{ count }} 条 · 第 {{ page }} 页</span><button :disabled="page * 50 >= count || loading" @click="filter(page+1)">下一页</button></nav>
    <section v-if="editing || selected" class="editor" aria-label="新品需求详情">
      <h3>{{ editing ? (selected ? '修改新品需求' : '记录新品需求') : '新品需求详情' }}</h3>
      <form v-if="editing" @submit.prevent="save">
        <fieldset :disabled="busy"><template v-if="!selected"><label>查找客户<input v-model="customerSearch" /></label><button type="button" @click="findCustomers">查找客户</button><label>客户<select v-model="form.customer" required @change="form.contact=null"><option value="">请选择客户</option><option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option></select></label></template>
        <p v-else>{{ selected.customer_name }}</p>
        <label>所找产品<textarea v-model="form.requirement" required maxlength="12000" /></label><label>规格<textarea v-model="form.specification" maxlength="12000" /></label><label>其他要求<textarea v-model="form.other_requirements" maxlength="12000" /></label>
        <label v-if="can('contacts','view')">联系人（可选）<select v-model="form.contact"><option :value="null">不关联</option><option v-for="c in contacts" :key="c.id" :value="c.id">{{ c.name }}</option></select></label>
        <template v-if="can('products','view')"><label>查找已有产品（可选）<input v-model="productSearch" /></label><button type="button" @click="findProducts">查找产品</button><label>关联产品<select v-model="form.product"><option :value="null">不关联</option><option v-if="form.product && !products.some(p => p.id === form.product)" :value="form.product">已关联产品 #{{ form.product }}</option><option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option></select></label></template>
        <div class="actions"><button class="btn btn-primary" :disabled="!writable">{{ busy ? '正在保存…' : '保存需求' }}</button><button type="button" class="btn btn-secondary" @click="guard.requestClose(() => editing=false)">取消</button></div></fieldset>
      </form>
      <template v-else-if="selected">
        <div :class="{voided:selected.voided_at}"><strong>{{ selected.customer_name }}</strong><p v-if="selected.voided_at"><strong>已作废</strong> · {{ selected.void_reason }}<br>{{ selected.voided_by }} · {{ displayTime(selected.voided_at) }}</p><p>{{ selected.requirement }}</p><p>规格：{{ selected.specification || '—' }}</p><p>其他要求：{{ selected.other_requirements || '—' }}</p><p>记录人：{{ selected.created_by }} · {{ displayTime(selected.created_at) }}</p></div>
        <div class="actions"><RouterLink :to="{path:'/customers',query:{detail:selected.customer}}">查看客户</RouterLink><RouterLink v-if="selected.follow_up" :to="{path:'/follow-ups',query:{detail:selected.follow_up}}">查看来源跟进</RouterLink><RouterLink v-if="selected.product && can('products','view')" :to="{path:'/products',query:{detail:selected.product}}">查看关联产品</RouterLink><button v-if="!selected.voided_at && writable" class="btn btn-secondary" @click="edit">修改需求</button><button v-if="!selected.voided_at && writable" class="btn btn-secondary" @click="voiding=true;reason=''">作废</button></div>
        <form v-if="voiding" @submit.prevent="confirmVoid"><label>作废原因<textarea v-model="reason" required maxlength="4000" :disabled="busy" /></label><p>作废后保留记录和修改历史。</p><button class="btn btn-primary" :disabled="busy || !reason.trim()">确认作废</button><button type="button" :disabled="busy" @click="voiding=false">取消作废</button></form>
        <h4>修改历史</h4><details v-for="h in history" :key="h.id"><summary>{{ h.action_label }} · {{ h.metadata.actor }} · {{ displayTime(h.created_at) }}</summary><p>变更前：{{ h.before_data.requirement || '—' }} / {{ h.before_data.specification || '—' }} / {{ h.before_data.other_requirements || '—' }}</p><p>变更后：{{ h.after_data.requirement }} / {{ h.after_data.specification }} / {{ h.after_data.other_requirements }}</p></details>
      </template>
    </section>
  </section>
</template>
<style scoped>
.reminders{max-width:1100px;margin:auto;color:#243749}.reminder-header,.filters,.actions,.pager{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.reminder-header{justify-content:space-between}h2{margin:0}.reminder-header p{color:#617183}.filters,.editor{padding:20px;background:white;border:1px solid #dce3eb;border-radius:12px;margin:20px 0}.grow{flex:1;min-width:180px}label{display:grid;gap:6px;font-size:14px;margin:8px 0}input,select,textarea{padding:10px;border:1px solid #c4cfd9;border-radius:6px;max-width:100%;min-width:0;background:white;color:#243749}textarea{min-height:80px;resize:vertical}.requirement{padding:18px;margin:12px 0;background:white;border:1px solid #dce3eb;border-radius:10px;overflow-wrap:anywhere}.requirement p,.editor p{white-space:pre-wrap;overflow-wrap:anywhere}.requirement a{margin:12px}.voided{background:#f1f2f4;color:#707780}.badge{font-size:12px;background:#e7f1f4;padding:3px 8px;border-radius:4px}fieldset{border:0;padding:0;min-width:0}.pager{justify-content:center}button,a{touch-action:manipulation}details{margin:14px 0}summary{cursor:pointer;overflow-wrap:anywhere}a{color:#176b85}button{cursor:pointer}button:disabled{cursor:default;opacity:.55}@media(max-width:500px){.filters,.editor{padding:14px}.filters label{width:100%}.grow{min-width:0}.reminder-header{align-items:start}.requirement a{display:inline-block;margin:12px 0}.actions{gap:14px}}
</style>
