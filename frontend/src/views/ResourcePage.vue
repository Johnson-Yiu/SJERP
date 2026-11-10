<script setup>
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api, listAll } = useWorkspaceApi()
import { useWorkspaceNavigation } from '../composables/useWorkspaceNavigation'
const workspaceNavigation = useWorkspaceNavigation()
function newWorkspaceDraft() {
  if (workspaceNavigation.workspace) return workspaceNavigation.newDraft({ path: route.path, query: { ...route.query, detail: undefined, edit: undefined, create: '1', returnTo: undefined } })
  return openCreate()
}

import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'

import { followUpError } from '../utils/followUpSafety'
import { contactRows, duplicateContactHint, duplicateContactMatches as findDuplicateContactMatches, followUpRows, richTextExcerpt } from '../utils/crmList'
import InventoryPagination from '../components/InventoryPagination.vue'
import { inventoryPage } from '../utils/inventoryPagination'
import { supplierStoreUrl, supplierFilters, supplierRows } from '../utils/supplierPresentation'
import { movementTypes, movementDirection, movementSource, sourceLabels, movementStatus, ledgerFilters, filteredMovements, movementSummary, movementUnit, signedMovement } from '../utils/inventoryLedger'
import CategoryMultiPicker from "../components/CategoryMultiPicker.vue"
import CertificateExpiryBadge from '../components/CertificateExpiryBadge.vue'
import { certificateFileUrl, certificateError } from '../utils/certificateFile'
import { certificateFilters, certificateFilterLabels, certificateFilterQuery } from '../utils/certificateExpiry'
import { computed, onMounted, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronRight, Database, Paperclip, Pencil, Plus, RotateCcw, Search, Trash2, UserRoundPlus, X } from 'lucide-vue-next'

import { apiErrorMessage } from '../utils/apiErrors.js'
import { confirmDialog, inputDialog } from '../dialogs'
import EntityDetailModal from '../components/EntityDetailModal.vue'
import SimpleRichTextEditor from '../components/SimpleRichTextEditor.vue'
import ComboInput from '../components/ComboInput.vue'
import SegmentedDateInput from '../components/SegmentedDateInput.vue'
import SummaryCards from '../components/SummaryCards.vue'
import PageLoadState from '../components/PageLoadState.vue'
import ListEmptyState from '../components/ListEmptyState.vue'
import { customerListStatus } from '../utils/customerListStatus'
import InventoryMovementCreateModal from '../components/InventoryMovementCreateModal.vue'
import SkuContextBanner from '../components/SkuContextBanner.vue'
import { addDays, daysBetween } from '../utils/orderDate'
import { confirmAndDeleteSavedFollowUpAttachment, removeSavedFollowUpAttachmentFromRows } from '../utils/followUpAttachments'
import { clearModalRoute } from '../utils/modalNavigation'
import { routeDataQuery, routeDataQuerySignature } from '../utils/routePageState'
import { skuContextLabel, skuContextId, withoutSkuContext } from '../utils/skuContext'
import { useAccessControl } from '../accessControl'

const props = defineProps({ config: Object })
const { can, accessState } = useAccessControl()
const route = useRoute()
const router = useRouter()
const isParameterPage = computed(() => props.config.endpoint === 'product-parameters')
const parameterProducts = ref([]), parameterOptionError = ref(''), parameterSaveError = ref(''), certificateSaveError = ref(''), currentCertificateFileUrl = ref('')
async function loadParameterProducts() { parameterOptionError.value = ''; try { parameterProducts.value = await listAll('/products/') } catch (error) { parameterOptionError.value = apiErrorMessage(error) } }
const isSupplierPage = computed(() => props.config.endpoint === 'suppliers')
const isContactPage = computed(() => props.config.endpoint === 'contacts')
const isFollowUpPage = computed(() => props.config.endpoint === 'follow-ups')
const isCrmPage = computed(() => isContactPage.value || isFollowUpPage.value)
const crmFilterOptions = reactive({ customers: [], methods: [], owners: [] })
const crmFilterError = ref('')
const crmFilter = computed(() => ({
  search: typeof route.query.search === 'string' ? route.query.search : '',
  customer: typeof route.query.customer === 'string' ? route.query.customer : '',
  owner: typeof route.query.owner === 'string' ? route.query.owner : '',
  primary: typeof route.query.primary === 'string' ? route.query.primary : '',
  type: typeof route.query.type === 'string' ? route.query.type : '',
  from: typeof route.query.from === 'string' ? route.query.from : '',
  to: typeof route.query.to === 'string' ? route.query.to : '',
  sort: route.query.sort === 'oldest' ? 'oldest' : 'newest',
}))
const supplierCategories = ref([]), supplierCategoryError = ref(''), supplierSaveError = ref('')
const supplierLifecycleBusyId = ref(null)
const supplierFilter = computed(() => supplierFilters(route.query))
const supplierGroupTitles = ['基本资料', '联系方式', '可供产品分类', '付款备注', '其他备注']
const listColumns = computed(() => isCertificatePage.value ? [['name','证书与编号'],['product_name','所属产品'],['issuer','签发机构'],['issued_date','签发日期','date'],['expires_on','有效期至','date'],['expiry_status','有效状态'],['file_url','文件']] : isSupplierPage.value
  ? [['name','供应商'],['is_active','状态','status'],['main_products','产品与可供分类'],['contact_name','联系方式'],['payment_terms','付款条款说明（备注）']]
  : isContactPage.value
    ? [['customer_name','所属客户'],['name','联系人'],['contact_methods','联系方式'],['is_primary','主联系人','boolean']]
    : isFollowUpPage.value
      ? [['follow_up_context','客户与联系人'],['followed_at','跟进时间','datetime'],['subject','主题与方式'],['follow_up_content','沟通与回复'],['follow_up_next','下一步安排']]
      : props.config.columns)
const isCustomerPage = computed(() => props.config.endpoint === 'customers')
const customerFilterOptions = reactive({ owners: [], countries: [] })
const customerFilterError = ref('')
const customerStatusOptions = [
  { value: 'lead', label: '线索' },
  { value: 'contact', label: '已联系' },
  { value: 'opportunity', label: '商机' },
  { value: 'customer', label: '正式客户' },
  { value: 'company', label: '返单客户' },
]
const customerFilter = computed(() => ({
  owner: typeof route.query.owner_profile === 'string' ? route.query.owner_profile : '',
  country: typeof route.query.country === 'string' ? route.query.country : '',
  status: typeof route.query.status === 'string' ? route.query.status : '',
}))
const isCoreListPage = computed(() => isCustomerPage.value || isMovementPage.value || isSupplierPage.value)
const primaryAction = computed(() => isCertificatePage.value ? '新建产品证书' : isParameterPage.value ? '新建产品参数' : isCustomerPage.value ? '新建客户' : isMovementPage.value ? '新建库存调整' : isSupplierPage.value ? '新建供应商' : isContactPage.value ? '新建联系人' : isFollowUpPage.value ? '新建跟进记录' : '新建记录')
const listNoun = computed(() => isCertificatePage.value ? '产品证书' : isParameterPage.value ? '产品参数' : isCustomerPage.value ? '客户' : isSupplierPage.value ? '供应商' : isContactPage.value ? '联系人' : isFollowUpPage.value ? '跟进记录' : '库存流水')
const hasListFilters = computed(() => Boolean(query.value || (isCustomerPage.value && [customerFilter.value.owner, customerFilter.value.country, customerFilter.value.status].some(Boolean)) || ((isParameterPage.value || isCertificatePage.value) && route.query.product) || (isCertificatePage.value && route.query.expiry) || (isSupplierPage.value && supplierFilter.value.category) || (isMovementPage.value && [movementFilters.value.type, movementFilters.value.direction, movementFilters.value.source, route.query.sku].some(Boolean)) || (isContactPage.value && [crmFilter.value.customer, crmFilter.value.primary].some(Boolean)) || (isFollowUpPage.value && [crmFilter.value.customer, crmFilter.value.owner, crmFilter.value.type, crmFilter.value.from, crmFilter.value.to, route.query.due].some(Boolean))))
const isMovementPage = computed(() => props.config.endpoint === 'inventory-movements')
const movementSkus = ref([])
const movementFilters = computed(() => ledgerFilters(route.query))
const visibleRows = computed(() => isMovementPage.value ? filteredMovements(rows.value, route.query) : isSupplierPage.value ? supplierRows(rows.value, route.query, supplierCategories.value) : isContactPage.value ? contactRows(rows.value, crmFilter.value) : isFollowUpPage.value ? followUpRows(rows.value, crmFilter.value) : isCertificatePage.value ? [...rows.value].sort((a,b)=>route.query.sort==='name'?String(a.name).localeCompare(String(b.name),'zh-CN'):String(a.expires_on||'9999').localeCompare(String(b.expires_on||'9999')) || Number(a.id)-Number(b.id)) : rows.value)
const ledgerPage = computed(() => inventoryPage(route.query.page, visibleRows.value.length))
const isPaginatedListPage = computed(() => isCustomerPage.value || isCrmPage.value)
const displayRows = computed(() => isMovementPage.value || isSupplierPage.value || isPaginatedListPage.value || isCertificatePage.value ? visibleRows.value.slice((ledgerPage.value - 1) * 25, ledgerPage.value * 25) : visibleRows.value)
const reversing = ref(false)
let ledgerUpdates = Promise.resolve(), ledgerRequest = 0
let crmRequest = 0
function updateLedgerQuery(patch, replace = false) {
  ledgerUpdates = ledgerUpdates.catch(() => {}).then(() => {
    const next = { ...route.query, ...patch }
    if (['search', 'owner_profile', 'country', 'status', 'type', 'direction', 'source', 'supplyCategory'].some(key => key in patch)) delete next.page
    Object.keys(next).forEach(key => { if (next[key] === undefined || next[key] === '') delete next[key] })
    return router[replace ? 'replace' : 'push']({ path: route.path, query: next, hash: route.hash })
  })
  return ledgerUpdates
}
function resetLedgerFilters() { clearTimeout(searchTimer); query.value = ''; return updateLedgerQuery({ search:undefined,type:undefined,direction:undefined,source:undefined }) }
function updateCrmQuery(patch, replace = false) {
  const next = { ...route.query, ...patch }
  if (['search', 'customer', 'owner', 'primary', 'type', 'from', 'to', 'due', 'sort'].some(key => key in patch)) delete next.page
  Object.keys(next).forEach(key => { if (next[key] === undefined || next[key] === '') delete next[key] })
  return router[replace ? 'replace' : 'push']({ path: route.path, query: next, hash: route.hash })
}
function ledgerDataQuery() { const { type, direction, source, page, supplyCategory, termsMode, ...params } = routeDataQuery(route.query); return params }
const isCertificatePage = computed(() => props.config.endpoint === 'product-certificates')
const certificateFilterLabel = computed(() => isCertificatePage.value ? certificateFilterLabels[route.query.expiry] : '')
function setCertificateFilter(expiry) { router.push({ path: route.path, query: certificateFilterQuery(route.query, expiry) }) }
async function loadCrmFilterOptions() {
  if (!isCrmPage.value) return
  crmFilterError.value = ''
  const tasks = []
  if (can('customers', 'view')) tasks.push(listAll('/customers/').then(value => { crmFilterOptions.customers = value }))
  if (isFollowUpPage.value) tasks.push(listAll('/follow-ups/methods/').then(value => { crmFilterOptions.methods = value }))
  if (isFollowUpPage.value) tasks.push(listAll('/follow-ups/owner-options/').then(value => { crmFilterOptions.owners = value }))
  const results = await Promise.allSettled(tasks)
  const failed = results.find(result => result.status === 'rejected')
  if (failed) crmFilterError.value = `筛选选项加载失败：${apiErrorMessage(failed.reason)}`
}
function setCrmFilter(key, value) { void updateCrmQuery({ [key]: value || undefined }) }
function clearDueFollowUpFilter() { void updateCrmQuery({ due: undefined }) }
async function loadCustomerFilterOptions() {
  if (!isCustomerPage.value) return
  customerFilterError.value = ''
  const results = await Promise.allSettled([
    listAll('/customers/owner-options/'),
    listAll('/customers/country-options/'),
  ])
  if (results[0].status === 'fulfilled') customerFilterOptions.owners = results[0].value
  if (results[1].status === 'fulfilled') customerFilterOptions.countries = results[1].value
  const failed = results.find(result => result.status === 'rejected')
  if (failed) customerFilterError.value = `筛选选项加载失败：${apiErrorMessage(failed.reason)}`
}
function setCustomerFilter(key, value) { void updateLedgerQuery({ [key]: value || undefined }) }
const rows = ref([]), loading = ref(true), hasLoaded = ref(false), loadError = ref(''), allRecordsExist = ref(false), saving = ref(false), query = ref('')
const modalOpen = ref(false), detailId = ref(null), editingId = ref(null)
const detailRefresh = ref(0), keepDetailOpen = ref(false)
const form = reactive({}), options = reactive({})
const optionErrors = reactive({}), optionLoaded = reactive({})
const requiredRemoteFields = computed(() => props.config.fields.filter(field => field[3] && ['remote', 'remote_multi', 'combo'].includes(field[2])))
const optionsReady = computed(() => requiredRemoteFields.value.every(field => optionLoaded[field[4]] && !optionErrors[field[4]]))
const filteredListEmpty = computed(() => hasListFilters.value && allRecordsExist.value)
const customerContacts = ref([])
const guard = useUnsavedChangesGuard({ data: () => ({ form, contacts: customerContacts.value, files: pendingFollowUpFiles.value }), enabled: () => modalOpen.value && props.config.endpoint !== 'inventory-movements', busy: () => (isCrmPage.value || isParameterPage.value || isCertificatePage.value) && modalOpen.value && saving.value })
const followUpDays = ref('')
const followUpSaveAttempted = ref(false)
const followUpScheduleError = computed(() => followUpError(form))
const currentFollowUpPlan = computed(() => (options.customers || []).find(customer => String(customer.id) === String(form.customer))?.next_follow_up)
function changeFollowUpMode() {
  if (form.next_follow_up_mode !== 'set') { form.next_follow_up = ''; followUpDays.value = '' }
}
const followUpAttachments = ref([])
const pendingFollowUpFiles = ref([])
const attachmentSaveError = ref('')
const followUpFileInput = ref(null)
const currentOperator = ref('')
const supplierCodeServerError = ref('')
const contactDuplicateRows = ref([])
const contactDuplicateLoading = ref(false)
const contactDuplicateError = ref('')
const contactDuplicateHint = computed(() => isContactPage.value ? duplicateContactHint(contactDuplicateRows.value, form, editingId.value) : '')
const contactDuplicateMatches = computed(() => isContactPage.value ? findDuplicateContactMatches(contactDuplicateRows.value, form, editingId.value) : [])
const toast = reactive({ show: false, message: '', error: false })
let searchTimer, toastTimer
let routeActionVersion = 0
let contactDuplicateRequest = 0
const routeModalOpen = ref(false)

const statusLabels = { lead: '线索', contact: '已联系', opportunity: '商机', customer: '正式客户', company: '返单客户', development: '开发中', discontinued: '停产', draft: '草稿', confirmed: '已确认', production: '生产中', shipped: '已发货', completed: '已完成', cancelled: '已取消' }
const editorFields = computed(() => {
  if (isCertificatePage.value) return [['product','name','certificate_no','issuer'],['issued_date','expires_on'],['file','notes']].map(keys=>keys.map(key=>props.config.fields.find(field=>field[0]===key)))
  if (isParameterPage.value) return [['product','group'],['name','value','unit','sort_order']].map(keys => keys.map(key => props.config.fields.find(field => field[0] === key)))
  if (isSupplierPage.value) return [['name','code','country','main_products'],['contact_name','phone','email','store_url'],['supply_categories'],['payment_terms'],['notes']].map(keys => keys.map(key => props.config.fields.find(field => field[0] === key)))
  if (isContactPage.value) return [['customer','name','title','is_primary'],['phone','whatsapp','email'],['notes']].map(keys => keys.map(key => props.config.fields.find(field => field[0] === key)))
  if (isFollowUpPage.value) return [['customer','contact','followed_at','type'],['subject','content','result'],['next_action','next_follow_up_mode','next_follow_up','owner']].map(keys => keys.map(key => props.config.fields.find(field => field[0] === key)))
  if (props.config.endpoint !== 'customers') return props.config.fields
  const order = ['name', 'code', 'country', 'region', 'owner_profile', 'source', 'website', 'address', 'notes']
  return [...props.config.fields].sort((a, b) => order.indexOf(a[0]) - order.indexOf(b[0]))
})
const editorGroupTitles = computed(() => isCertificatePage.value ? ['证书资料','签发与到期日期','文件与备注'] : isParameterPage.value ? ['所属产品与分组', '参数内容'] : isSupplierPage.value ? supplierGroupTitles : isContactPage.value ? ['所属客户与联系人资料', '联系方式', '备注'] : isFollowUpPage.value ? ['客户与沟通方式', '沟通内容', '下一步安排'] : [])
const editorGroups = computed(() => isSupplierPage.value || isContactPage.value || isFollowUpPage.value || isParameterPage.value || isCertificatePage.value ? editorFields.value : props.config.endpoint === 'customers' ? [editorFields.value.filter(f => !['website', 'address', 'notes'].includes(f[0])), editorFields.value.filter(f => ['website', 'address', 'notes'].includes(f[0]))] : [editorFields.value])
const saveLabel = computed(() => isCertificatePage.value ? '保存证书' : props.config.endpoint === 'customers' ? '保存客户' : isFollowUpPage.value ? '保存跟进' : isContactPage.value ? '保存联系人' : isSupplierPage.value ? '保存供应商' : '保存')
const fieldOptions = computed(() => Object.fromEntries(props.config.fields.filter(field => field[2] === 'select').map(field => [field[0], field[4]])))
const title = computed(() => editingId.value ? `编辑${props.config.title.replace('管理', '')}` : `新建${props.config.title.replace('管理', '')}`)
function editorFieldLabel(field) {
  if (!isFollowUpPage.value) return field[1]
  return ({ subject: '主题', content: '沟通记录', result: '客户回复' })[field[0]] || field[1]
}
const isCustomerCreate = computed(() => props.config.endpoint === 'customers' && !editingId.value)
const ownerProfileReadOnly = computed(() => props.config.endpoint === 'customers' && accessState.operator?.data_scope === 'self')
const isWideForm = computed(() => isCustomerCreate.value || ['follow-ups', 'contacts', 'suppliers'].includes(props.config.endpoint))
const isTransactionPage = computed(() => props.config.endpoint === 'transactions')
const accessModule = computed(() => ({
  customers: 'customers', contacts: 'contacts', 'follow-ups': 'followups', suppliers: 'suppliers',
  'inventory-movements': 'inventory', products: 'products', 'product-parameters': 'parameters',
  'product-certificates': 'certificates', transactions: 'transactions', categories: 'categories',
  'category-attributes': 'categories', 'sku-trade-units': 'trade_units',
}[props.config.endpoint] || props.config.endpoint))
const hasSkuContext = computed(() => props.config.endpoint === 'inventory-movements' && Boolean(skuContextId(route.query.sku)))
const activeSkuContextLabel = computed(() => {
  const sku = movementSkus.value.find(sku => String(sku.id) === skuContextId(route.query.sku))
  return sku ? `${sku.sku} · ${sku.display_name_cn || sku.product_name || ''}` : skuContextLabel(rows.value, route.query.sku)
})
const hasCurrentDueFollowUpContext = computed(() => props.config.endpoint === 'follow-ups' && route.query.due === 'true')
const supplierCodeConflict = computed(() => {
  if (props.config.endpoint !== 'suppliers') return null
  const code = String(form.code || '').trim().toUpperCase()
  if (code.length !== 2) return null
  const match = rows.value.find(row => String(row.code || '').toUpperCase() === code && Number(row.id) !== Number(editingId.value))
  return match ? `代码 ${code} 已由“${match.name}”使用。` : null
})
const supplierCodeError = computed(() => supplierCodeConflict.value || supplierCodeServerError.value)
const resourceMetrics = computed(() => {
  const endpoint = props.config.endpoint
  if (isMovementPage.value) return movementSummary(visibleRows.value)
  if (isSupplierPage.value) return [{label:'供应商',value:visibleRows.value.length,hint:'全部筛选结果'},{label:'可供分类',value:new Set(visibleRows.value.flatMap(row=>row.supply_categories || [])).size,hint:'已选择的分类'},{label:'有店铺链接',value:visibleRows.value.filter(row=>supplierStoreUrl(row.store_url)).length,hint:'可打开的网页链接'}]
  if (isParameterPage.value) return [{label:'参数记录',value:rows.value.length,hint:'当前筛选结果'},{label:'所属产品',value:new Set(rows.value.map(row=>row.product)).size,hint:'当前记录关联产品'},{label:'参数分组',value:new Set(rows.value.map(row=>row.group || '未分组')).size,hint:'当前筛选范围'},{label:'有单位的参数',value:rows.value.filter(row=>row.unit).length,hint:'参数值的展示单位'}]
  if (isCertificatePage.value) return [{label:'证书记录',value:rows.value.length,hint:'当前筛选结果'},{label:'已过期',value:rows.value.filter(r=>r.expiry_status==='expired').length,hint:'按服务端日期判断'},{label:'90天内到期',value:rows.value.filter(r=>['expiring_30','expiring_90'].includes(r.expiry_status)).length,hint:'含今日到期'},{label:'未填有效期',value:rows.value.filter(r=>r.expiry_status==='no_expiry').length,hint:'不代表永久有效'}]
  const total = rows.value.length
  const today = new Date().toISOString().slice(0, 10)
  if (endpoint === 'customers') return [
    { label: '客户总数', value: total, hint: '全部客户档案' },
    { label: '正式客户', value: rows.value.filter(row => ['customer', 'company'].includes(row.status)).length, hint: '已有正式订单' },
    { label: '待开发', value: rows.value.filter(row => ['lead', 'contact', 'opportunity'].includes(row.status)).length, hint: '尚未成交' },
    { label: '累计销售额', value: `¥ ${rows.value.reduce((sum, row) => sum + Number(row.sales_amount || 0), 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, hint: '当前列表累计' },
  ]
  if (endpoint === 'follow-ups') return [
    { label: '跟进记录', value: visibleRows.value.length, hint: '当前筛选结果' },
    { label: '已关联客户', value: new Set(visibleRows.value.map(row => row.customer || row.customer_name).filter(Boolean)).size, hint: '有沟通记录的客户' },
    { label: '计划日期已到记录', value: visibleRows.value.filter(row => row.next_follow_up && String(row.next_follow_up).slice(0, 10) <= today).length, hint: '历史跟进记录统计；当前待跟进以经营概览为准' },
    { label: '本月记录', value: visibleRows.value.filter(row => String(row.followed_at || '').slice(0, 7) === today.slice(0, 7)).length, hint: '按跟进时间统计' },
  ]
  if (endpoint === 'contacts') return [
    { label: '联系人', value: visibleRows.value.length, hint: '当前筛选结果' },
    { label: '主联系人', value: visibleRows.value.filter(row => row.is_primary).length, hint: '客户的主要联系人' },
    { label: '所属客户', value: new Set(visibleRows.value.map(row => row.customer || row.customer_name).filter(Boolean)).size, hint: '当前筛选结果' },
    { label: '有联系方式', value: visibleRows.value.filter(row => row.phone || row.whatsapp || row.email).length, hint: '电话、WhatsApp 或邮箱' },
  ]
  if (endpoint === 'transactions') return [
    { label: '流水笔数', value: total, hint: '当前查询结果' },
    { label: '收入合计', value: `¥ ${rows.value.filter(row => row.direction === 'income').reduce((sum, row) => sum + Number(row.rmb_amount || 0), 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, hint: '账面人民币折算参考（含CNY流水）' },
    { label: '支出合计', value: `¥ ${rows.value.filter(row => row.direction === 'expense').reduce((sum, row) => sum + Number(row.rmb_amount || 0), 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, hint: '账面人民币折算参考（含CNY流水）' },
    { label: '关联订单', value: new Set(rows.value.map(row => row.order || row.order_no).filter(Boolean)).size, hint: '有业务归属的流水' },
  ]
  const primary = endpoint === 'contacts' ? rows.value.filter(row => row.is_primary).length : rows.value.filter(row => ['active', 'development', 'draft'].includes(row.status)).length
  const linked = new Set(rows.value.map(row => row.customer || row.customer_name || row.product || row.product_name || row.supplier || row.supplier_name).filter(Boolean)).size
  return [
    { label: `${props.config.title.replace('管理', '')}总数`, value: total, hint: '当前查询结果' },
    { label: endpoint === 'contacts' ? '主联系人' : '启用 / 进行中', value: primary, hint: endpoint === 'contacts' ? '客户的主要联系人' : '当前有效记录' },
    { label: '关联主体', value: linked, hint: '客户、产品或供应商' },
    { label: '本月新增', value: rows.value.filter(row => String(row.created_at || '').slice(0, 7) === today.slice(0, 7)).length, hint: '按创建时间统计' },
  ]
})

function emptyContact(primary = false) {
  return { name: '', title: '', email: '', phone: '', whatsapp: '', notes: '', is_primary: primary }
}
function addCustomerContact() { customerContacts.value.push(emptyContact(false)) }
function removeCustomerContact(index) {
  if (customerContacts.value.length === 1) return
  const removedPrimary = customerContacts.value[index].is_primary
  customerContacts.value.splice(index, 1)
  if (removedPrimary) customerContacts.value[0].is_primary = true
}
function setPrimaryContact(index) {
  customerContacts.value.forEach((contact, contactIndex) => { contact.is_primary = contactIndex === index })
}

function clearToast() { clearTimeout(toastTimer); toast.show = false }
function notify(message, error = false) { clearTimeout(toastTimer); Object.assign(toast, { show: true, message, error }); toastTimer = setTimeout(() => { toast.show = false }, 2800) }
async function load() {
  loading.value = true
  loadError.value = ''
  if (isCustomerPage.value) {
    const request = ++crmRequest
    const params = { ...routeDataQuery(route.query), search: query.value }
    try {
      const nextRows = await listAll('/customers/', { params })
      if (request !== crmRequest) return
      rows.value = nextRows
      hasLoaded.value = true
      allRecordsExist.value = nextRows.length > 0
      if (!nextRows.length && hasListFilters.value) {
        try {
          const unfiltered = await listAll('/customers/')
          if (request === crmRequest) allRecordsExist.value = unfiltered.length > 0
        } catch { if (request === crmRequest) allRecordsExist.value = false }
      }
    } catch (error) {
      if (request === crmRequest) loadError.value = apiErrorMessage(error)
    } finally {
      if (request === crmRequest) loading.value = false
    }
    return
  }
  if (isSupplierPage.value) {
    const request = ++ledgerRequest
    try {
      const nextRows = await listAll('/suppliers/', { params: { ...ledgerDataQuery(), search: typeof route.query.search === 'string' ? route.query.search : '' } })
      if (request === ledgerRequest) { rows.value = nextRows; hasLoaded.value = true; allRecordsExist.value = nextRows.length > 0 || Boolean(route.query.search) }
    } catch (e) { if (request === ledgerRequest) loadError.value = apiErrorMessage(e) }
    finally { if (request === ledgerRequest) loading.value = false }
    return
  }
  if (isCrmPage.value) {
    const request = ++crmRequest
    const params = isContactPage.value
      ? { ...(route.query.customer ? { customer: route.query.customer } : {}), search: typeof route.query.search === 'string' ? route.query.search : '' }
      : {
        ...(route.query.customer ? { customer: route.query.customer } : {}),
        ...(route.query.owner ? { owner: route.query.owner } : {}),
        ...(route.query.type ? { type: route.query.type } : {}),
        ...(route.query.from ? { from: route.query.from } : {}),
        ...(route.query.to ? { to: route.query.to } : {}),
        ...(route.query.due === 'true' ? { due: 'true' } : {}),
        search: typeof route.query.search === 'string' ? route.query.search : '',
      }
    try {
      const nextRows = await listAll(`/${props.config.endpoint}/`, { params })
      if (request !== crmRequest) return
      rows.value = nextRows
      hasLoaded.value = true
      allRecordsExist.value = nextRows.length > 0
      if (!nextRows.length && hasListFilters.value) {
        const unsearched = { ...params }; delete unsearched.search
        try {
          const unsearchedRows = await listAll(`/${props.config.endpoint}/`, { params: unsearched })
          if (request === crmRequest) allRecordsExist.value = unsearchedRows.length > 0
        } catch { if (request === crmRequest) allRecordsExist.value = false }
      }
    } catch (error) {
      if (request === crmRequest) loadError.value = apiErrorMessage(error)
    } finally {
      if (request === crmRequest) loading.value = false
    }
    return
  }
  if (isCertificatePage.value) {
    const request=++ledgerRequest
    const {search,product,expiry}=route.query
    try{const result=await listAll('/product-certificates/',{params:{search:search||'',...(product?{product}:{}),...(expiry?{expiry}:{})}});if(request!==ledgerRequest)return;rows.value=result;hasLoaded.value=true;allRecordsExist.value=result.length>0||hasListFilters.value}catch(e){if(request===ledgerRequest)loadError.value=apiErrorMessage(e)}finally{if(request===ledgerRequest)loading.value=false}
    return
  }
  if (!isMovementPage.value) {
    try {
      const nextRows = await listAll(`/${props.config.endpoint}/`, { params: { ...routeDataQuery(route.query), search: query.value } })
      rows.value = nextRows
      hasLoaded.value = true
      allRecordsExist.value = nextRows.length > 0
      if (!nextRows.length && hasListFilters.value) {
        try { allRecordsExist.value = (await listAll(`/${props.config.endpoint}/`)).length > 0 } catch { allRecordsExist.value = false }
      }
    } catch (e) { loadError.value = apiErrorMessage(e) } finally { loading.value = false }
    return
  }
  const request = ++ledgerRequest
  try {
    const result = await listAll('/inventory-movements/', { params: { ...ledgerDataQuery(), search: typeof route.query.search === 'string' ? route.query.search : '' } })
    if (request === ledgerRequest) {
      rows.value = result
      hasLoaded.value = true
      allRecordsExist.value = result.length > 0
      if (!result.length && hasListFilters.value) {
        try { allRecordsExist.value = (await listAll('/inventory-movements/', { params: { sku: route.query.sku } })).length > 0 } catch { allRecordsExist.value = false }
      }
    }
  } catch (e) { if (request === ledgerRequest) loadError.value = apiErrorMessage(e) }
  finally { if (request === ledgerRequest) loading.value = false }
}
function delayedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => isParameterPage.value || isCertificatePage.value ? updateLedgerQuery({search:query.value || undefined},true) : isCustomerPage.value ? updateLedgerQuery({ search:query.value || undefined }, true) : isMovementPage.value || isSupplierPage.value ? updateLedgerQuery({ search:query.value || undefined }) : isCrmPage.value ? updateCrmQuery({ search:query.value || undefined }, true) : load(), 300)
}
function clearListFilters() {
  query.value = ''
  if (isParameterPage.value || isCertificatePage.value) return updateLedgerQuery({product:undefined,search:undefined,expiry:undefined,sort:undefined,page:undefined})
  if (isSupplierPage.value) { clearTimeout(searchTimer); return updateLedgerQuery({ search:undefined,supplyCategory:undefined,termsMode:undefined }) }
  if (isMovementPage.value) return resetLedgerFilters()
  if (isCustomerPage.value) return updateLedgerQuery({ search: undefined, owner_profile: undefined, country: undefined, status: undefined, page: undefined }, true)
  if (isCrmPage.value) {
    clearTimeout(searchTimer)
    return updateCrmQuery({ search:undefined, customer:undefined, owner:undefined, primary:undefined, type:undefined, from:undefined, to:undefined, due:undefined, sort:undefined, page:undefined }, true)
  }
  return load()
}
watch(() => route.query.search, value => { if (isMovementPage.value || isCustomerPage.value || isSupplierPage.value || isCrmPage.value || isParameterPage.value || isCertificatePage.value) { clearTimeout(searchTimer); query.value = typeof value === 'string' ? value : '' } }, { immediate:true })
onBeforeUnmount(() => { clearTimeout(searchTimer); clearTimeout(toastTimer); ledgerRequest++; crmRequest++ })
async function loadSupplierCategories() {
  supplierCategoryError.value = ''
  try { supplierCategories.value = await listAll('/categories/tree/') } catch (error) { supplierCategoryError.value = apiErrorMessage(error) }
}
async function loadOptions() {
  const remotes = props.config.fields.filter(f => ['remote', 'combo', 'remote_multi'].includes(f[2]))
  await Promise.all(remotes.map(field => loadRemoteOption(field)))
}
async function loadRemoteOption(field, force = false) {
  const key = field[4]
  if (optionLoaded[key] && !force && !(props.config.endpoint === 'follow-ups' && field[0] === 'customer')) return !optionErrors[key]
  try {
    options[key] = await listAll(`/${key}/`)
    optionLoaded[key] = true
    delete optionErrors[key]
    return true
  } catch (error) {
    optionErrors[key] = `${field[1]}资料加载失败：${apiErrorMessage(error)}`
    return false
  }
}
function retryRemoteOption(field) { return loadRemoteOption(field, true) }
async function loadMovementSkus() {
  try { movementSkus.value = await listAll('/skus/', { params:{ include_inactive:1 } }); delete optionErrors.skus }
  catch (error) { optionErrors.skus = `SKU 资料加载失败：${apiErrorMessage(error)}` }
}
function visibleEditorField(field) {
  return !(props.config.endpoint === 'follow-ups' && field[0] === 'next_follow_up' && form.next_follow_up_mode !== 'set')
}
function visibleOptions(field) {
  const rows = options[field[4]] || []
  if (props.config.endpoint === 'follow-ups' && field[0] === 'contact' && form.customer) return rows.filter(row => Number(row.customer) === Number(form.customer))
  return rows
}
function datetimeLocal() {
  const now = new Date()
  const date = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  return `${date}T${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
}
function syncFollowUpDaysFromDate() {
  if (props.config.endpoint !== 'follow-ups') return
  const startDate = String(form.followed_at || '').slice(0, 10)
  followUpDays.value = startDate && form.next_follow_up ? daysBetween(startDate, form.next_follow_up) : ''
}
function updateFollowUpDate() {
  if (props.config.endpoint !== 'follow-ups') return
  const startDate = String(form.followed_at || '').slice(0, 10)
  if (!startDate || followUpDays.value === '' || followUpDays.value === null) {
    form.next_follow_up = ''
    return
  }
  form.next_follow_up = addDays(startDate, followUpDays.value)
}
function setFollowUpDate(value) {
  form.next_follow_up = value
  syncFollowUpDaysFromDate()
}
function addFollowUpFiles(files) {
  if (props.config.endpoint !== 'follow-ups') return
  const additions = Array.from(files || []).filter(file => file?.name && file.size <= 20 * 1024 * 1024)
  const rejected = Array.from(files || []).filter(file => file?.size > 20 * 1024 * 1024)
  if (rejected.length) notify('单个附件不能超过 20 MB。', true)
  const existingKeys = new Set(pendingFollowUpFiles.value.map(file => `${file.name}:${file.size}:${file.lastModified}`))
  pendingFollowUpFiles.value = [...pendingFollowUpFiles.value, ...additions.filter(file => {
    const key = `${file.name}:${file.size}:${file.lastModified}`
    if (existingKeys.has(key)) return false
    existingKeys.add(key)
    return true
  })]
}
function removePendingFollowUpFile(index) { pendingFollowUpFiles.value.splice(index, 1) }
function onFollowUpFileInput(event) {
  addFollowUpFiles(event.target.files)
  event.target.value = ''
}
function onFollowUpFileDrop(event) { addFollowUpFiles(event.dataTransfer?.files) }
async function uploadFollowUpFiles(id) {
  if (!id || !pendingFollowUpFiles.value.length) return null
  const data = new FormData()
  pendingFollowUpFiles.value.forEach(file => data.append('files', file, file.name))
  const response = await api.post(`/follow-ups/${id}/attachments/`, data, { timeout: 120000 })
  return response.data
}
async function deleteSavedFollowUpAttachment(attachment) {
  clearToast()
  await confirmAndDeleteSavedFollowUpAttachment({
    followUpId: editingId.value,
    attachment,
    api,
    confirmDialog,
    onDeleted: async deleted => {
      followUpAttachments.value = followUpAttachments.value.filter(item => String(item.id) !== String(deleted.id))
      rows.value = removeSavedFollowUpAttachmentFromRows(rows.value, editingId.value, deleted.id)
      if (keepDetailOpen.value) detailRefresh.value += 1
      notify(`已删除附件“${deleted.name}”`)
      await load()
    },
    onError: error => notify(error.message || '删除附件失败', true),
  })
}
function onDateFieldChange(field, value) {
  form[field[0]] = value
  if (props.config.endpoint === 'follow-ups' && field[0] === 'followed_at') syncFollowUpDaysFromDate()
}
async function loadContactDuplicateRows(customerId) {
  const request = ++contactDuplicateRequest
  contactDuplicateRows.value = []
  contactDuplicateError.value = ''
  if (!customerId || !isContactPage.value) {
    contactDuplicateLoading.value = false
    return
  }
  contactDuplicateLoading.value = true
  try {
    const contacts = await listAll('/contacts/', { params: { customer: customerId } })
    if (request === contactDuplicateRequest) contactDuplicateRows.value = contacts
  } catch (error) {
    if (request === contactDuplicateRequest) contactDuplicateError.value = `重复提醒加载失败：${apiErrorMessage(error)}`
  } finally {
    if (request === contactDuplicateRequest) contactDuplicateLoading.value = false
  }
}
function applyDefaultContact() {
  if (props.config.endpoint !== 'follow-ups' || !form.customer) return
  if (form.contact) return
  const contacts = (options.contacts || []).filter(row => Number(row.customer) === Number(form.customer))
  const primary = contacts.find(row => row.is_primary) || contacts[0]
  form.contact = primary?.id || ''
}
function onFieldChange(field) {
  if (props.config.endpoint === 'follow-ups' && field[0] === 'customer') {
    form.contact = ''
    applyDefaultContact()
  }
  if (isContactPage.value && field[0] === 'customer') void loadContactDuplicateRows(form.customer)
}
function normalizeSupplierCode() {
  supplierCodeServerError.value = ''
  form.code = String(form.code || '').replace(/[^a-z]/gi, '').slice(0, 2).toUpperCase()
}
async function loadCurrentOperator() {
  if (currentOperator.value) return currentOperator.value
  try { currentOperator.value = (await api.get('/session/current-operator/')).data.name || '' } catch { currentOperator.value = '' }
  return currentOperator.value
}
function resetForm() {
  followUpSaveAttempted.value = false
  props.config.fields.forEach(([name, , type, , extra]) => {
    const supplierDefault = props.config.endpoint === 'suppliers' && !editingId.value
      ? { country: '中国', payment_terms: '30%预付款，70%尾款发货前结清' }[name]
      : undefined
    form[name] = type === 'remote_multi' ? [] : type === 'checkbox' ? name === 'active' : type === 'select' ? Object.keys(extra)[0] : type === 'file' ? null : (route.query[name] ?? supplierDefault ?? '')
    if (type === 'followup_schedule') form[name] = 'keep'
  })
  supplierCodeServerError.value = ''
}
function normalizeWebsite(value) {
  const website = String(value || '').trim()
  if (!website || /^[a-z][a-z\d+.-]*:\/\//i.test(website)) return website
  return `https://${website}`
}
function isInherited(fieldName) {
  const value = route.query?.[fieldName]
  return !editingId.value && value !== undefined && value !== null && value !== ''
}
function onCertificateFileSelected(event) {
  form.file = event.target.files?.[0] || null
}
async function openCreate({ isCurrent = () => true } = {}) {
  if (!can(accessModule.value, 'create')) return
  clearToast()
  certificateSaveError.value=''
  if (isParameterPage.value) { parameterSaveError.value = ''; toast.show = false }
  if (isMovementPage.value || isSupplierPage.value) toast.show = false
  supplierSaveError.value = ''
  keepDetailOpen.value = false
  editingId.value = null; resetForm()
  currentCertificateFileUrl.value = ''
  if (props.config.endpoint === 'follow-ups' && !form.followed_at) form.followed_at = datetimeLocal()
  customerContacts.value = props.config.endpoint === 'customers' ? [emptyContact(true)] : []
  if (!isMovementPage.value) await loadOptions()
  if ((isCustomerPage.value || isCrmPage.value) && !isCurrent()) return
  if (props.config.endpoint === 'customers') {
    let code
    try { code = (await api.get('/customers/next-code/')).data.code } catch { code = '保存时自动生成' }
    if (!isCurrent()) return
    form.code = code
    form.owner_profile = accessState.operator?.employee_profile_id || ''
  }
  if (['customers', 'follow-ups'].includes(props.config.endpoint) && !form.owner) {
    const owner = await loadCurrentOperator()
    if (!isCurrent()) return
    form.owner = owner
  }
  if (isContactPage.value) void loadContactDuplicateRows(form.customer)
  followUpAttachments.value = []
  pendingFollowUpFiles.value = []
  attachmentSaveError.value = ''
  applyDefaultContact()
  syncFollowUpDaysFromDate()
  if (isCurrent()) { guard.markClean(); modalOpen.value = true }
}
async function openEdit(row, { keepDetail = false, isCurrent = () => true } = {}) {
  if (!can(accessModule.value, 'update')) return
  let editRow = row
  if (props.config.endpoint === 'follow-ups' && (
    !Array.isArray(row.attachments) ||
    props.config.fields.some(([name]) => !Object.prototype.hasOwnProperty.call(row, name))
  )) {
    try { editRow = (await api.get(`/follow-ups/${row.id}/`)).data }
    catch (error) { if (isCurrent()) notify(apiErrorMessage(error), true); return }
    if (!isCurrent()) return
  }
  clearToast()
  certificateSaveError.value=''
  if (isParameterPage.value) { parameterSaveError.value = ''; toast.show = false }
  if (isMovementPage.value || isSupplierPage.value) toast.show = false
  supplierSaveError.value = ''
  if (!keepDetail) detailId.value = null
  keepDetailOpen.value = keepDetail
  editingId.value = editRow.id; resetForm(); await loadOptions()
  if (!isCurrent()) return
  props.config.fields.forEach(([name, , type]) => {
    if (type === 'file') return
    let value = editRow[name]
    if (type === 'datetime-local' && value) value = value.slice(0, 16)
    form[name] = value ?? (type === 'checkbox' ? false : '')
    if (type === 'followup_schedule') form[name] = value || 'keep'
  })
  if (isContactPage.value) void loadContactDuplicateRows(form.customer)
  if (!isCurrent()) return
  currentCertificateFileUrl.value = isCertificatePage.value ? (row.file_url || '') : ''
  followUpAttachments.value = props.config.endpoint === 'follow-ups' ? (editRow.attachments || []) : []
  pendingFollowUpFiles.value = []
  attachmentSaveError.value = ''
  syncFollowUpDaysFromDate()
  guard.markClean()
  modalOpen.value = true
}
const closeModal = () => { if ((isSupplierPage.value || isCrmPage.value || isParameterPage.value || isCertificatePage.value) && saving.value) return; return guard.requestClose(discardModal) }
function discardModal() {
  const refreshDetail = keepDetailOpen.value
  modalOpen.value = false; keepDetailOpen.value = false; followUpDays.value = ''; followUpAttachments.value = []; pendingFollowUpFiles.value = []; attachmentSaveError.value = ''; currentCertificateFileUrl.value = ''
  contactDuplicateRequest += 1; contactDuplicateRows.value = []; contactDuplicateLoading.value = false; contactDuplicateError.value = ''
  if (refreshDetail) detailRefresh.value += 1
  void clearModalRoute(router, route)
}
function openDetail(id) {
  if (workspaceNavigation.workspace) return workspaceNavigation.openTask({ path: route.path, query: { ...route.query, detail: String(id), tab: isCustomerPage.value ? 'followups' : undefined } })
  detailId.value = id
  if (isMovementPage.value) { void updateLedgerQuery({ detail:String(id) }); return }
  if (isSupplierPage.value) { void updateLedgerQuery({ detail:String(id),tab:undefined }); return }
  if (props.config.endpoint === 'customers') void router.push({ path: route.path, query: { ...route.query, detail: String(id), tab: 'followups' } })
  else if (isCrmPage.value) void updateCrmQuery({ detail: String(id) })
}
function openContactCustomer(row) {
  if (!row.customer) return
  void router.push({ path: '/customers', query: { detail: String(row.customer), tab: 'contacts' } })
}
function contactDetailUrl(row) {
  return router.resolve({ path: '/contacts', query: { detail: String(row.id) } }).href
}
function closeDetail() {
  detailId.value = null
  if (!route.query.detail) return
  if (isMovementPage.value) { void updateLedgerQuery({ detail:undefined }, true); return }
  const { detail, tab, ...query } = route.query
  void router.replace({ path: route.path, query, hash: route.hash })
}
function clearSkuFilter() { void router.push(withoutSkuContext(route)) }
function clearFollowUpDueFilter() {
  const { due, ...query } = route.query
  void router.push({ path: route.path, query, hash: route.hash })
}
function detailReturnPath() {
  const query = new URLSearchParams()
  Object.entries(route.query).forEach(([key, value]) => {
    if (!['create', 'edit', 'returnTo', 'detail'].includes(key) && typeof value === 'string') query.set(key, value)
  })
  if (detailId.value) query.set('detail', String(detailId.value))
  return `${route.path}?${query.toString()}`
}
function payload() {
  const data = {}
  props.config.fields.forEach(([name, , type]) => {
    let value = form[name]
    if (type === 'remote_multi') value = (value || []).map(Number)
    if (type === 'remote') value = value ? Number(value) : null
    if (type === 'number') value = value === '' ? 0 : value
    if (type === 'date' && value === '') value = null
    if (type === 'datetime-local' && value && value.length === 16) value += ':00+08:00'
    if (type === 'file') { if (!value) return; data[name] = value; return }
    if (['website', 'store_url'].includes(name)) value = normalizeWebsite(value)
    if (props.config.endpoint === 'follow-ups' && name === 'next_follow_up' && form.next_follow_up_mode !== 'set') value = null
    data[name] = value
  })
  if (isCustomerCreate.value) data.contacts = customerContacts.value
  return data
}
function certificatePayload() {
  const data = new FormData()
  Object.entries(payload()).forEach(([name, value]) => {
    if (value === null || value === undefined || value === '') return
    data.append(name, value instanceof File ? value : String(value))
  })
  return data
}
async function save() {
  if (!can(accessModule.value, editingId.value ? 'update' : 'create')) return
  if (saving.value) return
  clearToast()
  attachmentSaveError.value = ''
  parameterSaveError.value = ''; certificateSaveError.value=''
  if (!optionsReady.value) return notify('关联资料尚未加载完成，请重试后再保存。', true)
  if (isSupplierPage.value) {
    supplierSaveError.value = ''; toast.show = false
    if (!/^[A-Z]{2}$/.test(form.code || '')) { supplierSaveError.value = '二字代码请填写两个英文字母。'; return }
    if (!form.supply_categories?.length) { supplierSaveError.value = '请选择至少一个可供产品分类。'; return }
  }
  if (supplierCodeError.value) return notify(supplierCodeError.value, true)
  if (props.config.endpoint === 'follow-ups') {
    followUpSaveAttempted.value = true
    if (followUpScheduleError.value) return notify(followUpScheduleError.value, true)
  }
  saving.value = true
  try {
    const wasEditing = Boolean(editingId.value)
    const requestPayload = isCertificatePage.value && form.file ? certificatePayload() : payload()
    const response = wasEditing ? await api.put(`/${props.config.endpoint}/${editingId.value}/`, requestPayload) : await api.post(`/${props.config.endpoint}/`, requestPayload)
    const hasPendingAttachments = props.config.endpoint === 'follow-ups' && pendingFollowUpFiles.value.length > 0
    if (!hasPendingAttachments) guard.markClean()
    const savedId = response.data?.id || editingId.value
    if (hasPendingAttachments) {
      try {
        const uploaded = await uploadFollowUpFiles(savedId)
        followUpAttachments.value = [...followUpAttachments.value, ...(uploaded || [])]
        pendingFollowUpFiles.value = []
        guard.markClean()
      } catch {
        if (!editingId.value && savedId) editingId.value = savedId
        attachmentSaveError.value = '跟进记录已保存，附件上传失败。请点击“保存跟进”重试。'
        await load()
        return
      }
    }
    const refreshDetail = keepDetailOpen.value
    modalOpen.value = false
    const successMessage = isCertificatePage.value ? (wasEditing?'证书已更新':'证书已创建') : isContactPage.value ? (wasEditing ? '联系人已更新' : '联系人已创建') : isFollowUpPage.value ? (wasEditing ? '跟进记录已更新' : '跟进记录已保存') : isSupplierPage.value ? (wasEditing ? '供应商修改已保存。' : '供应商创建成功。') : (wasEditing ? '更新成功' : '创建成功')
    notify(successMessage)
    if (workspaceNavigation.workspace && !wasEditing && savedId && !route.query.returnTo) await workspaceNavigation.adoptObject({ path: route.path, query: { ...route.query, detail: String(savedId), create: undefined, edit: undefined, returnTo: undefined } })
    else await clearModalRoute(router, route)
    await load()
    if (refreshDetail) detailRefresh.value += 1
    keepDetailOpen.value = false
  } catch (e) {
    if (isCertificatePage.value) certificateSaveError.value=certificateError(e)
    if (isParameterPage.value) parameterSaveError.value = /product, group, name/.test(apiErrorMessage(e)) ? '该产品的同一分组下已存在这个参数名称，请修改名称或分组。' : apiErrorMessage(e)
    if (isSupplierPage.value) { supplierSaveError.value = apiErrorMessage(e); if (e.response?.data?.code || /重复|二字代码/.test(e.message || '')) supplierCodeServerError.value = Array.isArray(e.response?.data?.code) ? e.response.data.code.join('；') : e.message }
    notify(isCertificatePage.value ? certificateSaveError.value : isParameterPage.value ? parameterSaveError.value : e.message, true)
  } finally { saving.value = false }
}
async function handleInventoryMovementCreated(records) {
  modalOpen.value = false
  notify(`已创建 ${Array.isArray(records) ? records.length : 1} 条库存流水`)
  await clearModalRoute(router, route)
  await load()
  if (detailId.value) detailRefresh.value += 1
}
async function remove(row) {
  if (!can(accessModule.value, 'delete')) return
  clearToast()
  if (!await confirmDialog({ title: '确认删除', message: `确定删除“${row[props.config.key]}”吗？此操作无法撤销。`, confirmText: '确认删除', danger: true })) return
  try { await api.delete(`/${props.config.endpoint}/${row.id}/`); notify(isContactPage.value ? '联系人已删除' : isFollowUpPage.value ? '跟进记录已删除' : '删除成功'); await load() } catch (e) { notify(apiErrorMessage(e), true) }
}
async function toggleSupplierLifecycle(row) {
  if (!isSupplierPage.value || !can('suppliers', 'update') || supplierLifecycleBusyId.value === row.id) return
  const isActive = Boolean(row.is_active)
  const action = isActive ? 'deactivate' : 'activate'
  if (!await confirmDialog({ title: isActive ? '停用供应商' : '启用供应商', message: isActive ? `停用“${row.name}”后，它不会再作为新采购候选；历史采购、付款和来源仍会保留。` : `确认重新启用“${row.name}”吗？`, confirmText: `确认${isActive ? '停用' : '启用'}`, danger: isActive })) return
  supplierLifecycleBusyId.value = row.id
  try {
    const response = await api.post(`/suppliers/${row.id}/${action}/`)
    rows.value = rows.value.map(item => item.id === row.id ? { ...item, ...response.data } : item)
    notify(isActive ? '供应商已停用。' : '供应商已启用。')
    if (detailId.value === row.id) detailRefresh.value += 1
  } catch (error) { notify(apiErrorMessage(error), true) } finally { supplierLifecycleBusyId.value = null }
}
async function reverseInventoryMovement(row) {
  if (reversing.value || !can('inventory', 'update') || !canReverseInventoryMovement(row)) return
  reversing.value = true
  toast.show = false
  try {
    const reason = await inputDialog({
      title: '冲销库存流水',
      message: `冲销后原流水保留，并生成一条反向流水。\n流水号：${row.movement_no}\nSKU：${row.sku_code || row.display_name || row.product_name || '—'}\n类型：${row.type_display}\n原数量：${row.quantity} ${movementUnit(row, movementSkus.value)}\n发生日期：${row.movement_date}\n关联订单：${(row.related_order_nos || []).join('、') || row.order_no || '—'}`,
      label: '冲销原因', placeholder: '请填写冲销原因', required: true, maxLength: 500, confirmText: '确认冲销', danger: true,
    })
    if (!reason) return
    await api.post(`/inventory-movements/${row.id}/reverse/`, { reason })
    notify('库存流水冲销成功。')
    await load()
    if (detailId.value) detailRefresh.value += 1
  } catch (e) { notify(e.message, true) } finally { reversing.value = false }
}
function display(value, type, fieldName = '') {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.length ? value.join('、') : '—'
  if (type === 'money') return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (type === 'rmb') return `¥ ${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  if (type === 'labels') return Array.isArray(value) ? value.join('、') || '未设置' : '未设置'
  if (type === 'number') return Number(value).toLocaleString('zh-CN')
  if (type === 'date') return String(value).slice(0, 10)
  if (type === 'datetime') return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  if (type === 'boolean') return value ? '是' : '否'
  if (type === 'status') return statusLabels[value] || fieldOptions.value[fieldName]?.[value] || value
  if (type === 'signed') return `${Number(value) > 0 ? '+' : ''}${Number(value).toLocaleString('zh-CN')}`
  return value
}
function isReadOnlyAutomaticMovement(row) { return props.config.endpoint === 'inventory-movements' && (row.is_automatic === true || Boolean(row.is_reversed)) }
function canReverseInventoryMovement(row) { return props.config.endpoint === 'inventory-movements' && row.is_automatic !== true && row.source_type === 'manual' && !row.is_reversed }
function formatAttachmentSize(value) {
  const size = Number(value || 0)
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}
function cellClass(type, value) { return { amount: ['money', 'rmb'].includes(type), tag: type === 'tag', status: type === 'status', [value]: type === 'status', direction: type === 'direction', income: value === '收入', expense: value === '支出', positive: type === 'signed' && Number(value) > 0, negative: type === 'signed' && Number(value) < 0 } }
async function editFromDetail(target = {}) {
  const targetEntity = target?.entity || props.config.endpoint
  const targetId = target?.id || detailId.value
  if (!targetId) return
  if (targetEntity !== props.config.endpoint) {
    if (targetEntity === 'follow-ups') router.push({ path: '/follow-ups', query: { edit: String(targetId), returnTo: detailReturnPath() } })
    return
  }
  const row = rows.value.find(item => String(item.id) === String(targetId))
  if (row) await openEdit(row, { keepDetail: true })
  else if (isSupplierPage.value) { try { await openEdit((await api.get(`/suppliers/${targetId}/`)).data, { keepDetail:true }) } catch (error) { notify(apiErrorMessage(error), true) } }
}
async function handleDetailChanged() {
  await load()
  if (detailId.value) detailRefresh.value += 1
}

async function syncModalFromRoute() {
  const version = ++routeActionVersion
  const isCurrent = () => version === routeActionVersion
  if (route.query.create === '1') {
    routeModalOpen.value = true
    await openCreate({ isCurrent })
    return
  }
  if (route.query.edit) {
    routeModalOpen.value = true
    try {
      const row = (await api.get(`/${props.config.endpoint}/${route.query.edit}/`)).data
      if (isCurrent() && String(route.query.edit) === String(row.id)) await openEdit(row, { isCurrent })
    } catch (error) { if (isCurrent()) notify(error.message, true) }
    return
  }
  if (routeModalOpen.value) {
    routeModalOpen.value = false
    modalOpen.value = false
    editingId.value = null
    keepDetailOpen.value = false
    followUpAttachments.value = []
    pendingFollowUpFiles.value = []
  }
}

function routeCreatePrefillSignature() {
  const fields = props.config.fields.map(([name]) => name)
  return JSON.stringify(fields.map(name => [name, route.query[name] ?? null]))
}

watch(() => isCertificatePage.value ? JSON.stringify([route.query.search||'',route.query.product||'',route.query.expiry||'']) : isMovementPage.value || isSupplierPage.value ? JSON.stringify(ledgerDataQuery()) : isCrmPage.value ? JSON.stringify([route.query.customer || '', route.query.owner || '', route.query.type || '', route.query.from || '', route.query.to || '', route.query.due || '', route.query.search || '']) : routeDataQuerySignature(route.query), load)
watch([() => route.query.create, () => route.query.edit, routeCreatePrefillSignature], (current, previous) => {
  const prefillOnlyChanged = previous && current[0] === previous[0] && current[1] === previous[1]
  if (prefillOnlyChanged && route.query.create !== '1') return
  void syncModalFromRoute()
}, { immediate: true })
watch(() => route.query.detail, id => { detailId.value = id ? Number(id) : null }, { immediate: true })
onMounted(() => { void load(); if (isMovementPage.value) void loadMovementSkus(); if (isSupplierPage.value && can('categories','view')) void loadSupplierCategories(); if (isCustomerPage.value) void loadCustomerFilterOptions(); if (isCrmPage.value) void loadCrmFilterOptions(); if ((isParameterPage.value || isCertificatePage.value) && can('products','view')) void loadParameterProducts() })
</script>

<template>
  <div class="resource-page" :class="{ 'finance-resource-page': isTransactionPage, 'inventory-ledger-page': isMovementPage, 'core-list-page': isCoreListPage, 'supplier-page': isSupplierPage }">
    <div class="page-head" :class="{ 'list-intro': isCoreListPage }"><div><h2 v-if="!isCoreListPage">{{ config.title }}</h2><p>{{ config.description }}</p></div><button v-if="can(accessModule, 'create')" class="btn btn-primary" @click="newWorkspaceDraft"><Plus :size="16" /> {{ primaryAction }}</button></div>
    <div v-if="isMovementPage && optionErrors.skus" class="option-load-error" role="alert">{{ optionErrors.skus }} <button type="button" @click="loadMovementSkus">重新加载 SKU 资料</button></div>
    <SummaryCards v-if="hasLoaded" :items="resourceMetrics" />
    <div v-if="isCertificatePage" class="certificate-filters" aria-label="证书有效期筛选"><button v-for="[value, label] in certificateFilters" :key="value" type="button" class="btn" :class="{ 'btn-primary': (route.query.expiry || '') === value }" :aria-pressed="(route.query.expiry || '') === value" @click="setCertificateFilter(value)">{{ label }}</button></div>
    <div v-if="certificateFilterLabel" class="follow-up-due-context" aria-label="当前证书筛选"><span>当前筛选：<strong>{{ certificateFilterLabel }}</strong></span><button type="button" @click="setCertificateFilter('')">清除筛选</button></div>
    <RouterLink v-if="(isCustomerPage || isFollowUpPage) && can('followups','view') && can('customers','view')" class="btn btn-secondary" :to="{path:'/new-product-reminders',query:{tag:'新品提醒',customer:route.query.customer}}">新品提醒</RouterLink>
    <div v-if="hasCurrentDueFollowUpContext" class="follow-up-due-context" aria-label="当前跟进筛选"><span>当前筛选：<strong>今日及逾期待跟进</strong></span><button type="button" @click="clearFollowUpDueFilter">清除待跟进筛选</button></div>
    <div v-if="isCertificatePage" class="certificate-controls"><label v-if="can('products','view')">所属产品<select aria-label="按产品筛选证书" :value="route.query.product || ''" @change="updateLedgerQuery({product:$event.target.value||undefined,page:undefined})"><option value="">全部产品</option><option v-for="p in parameterProducts" :key="p.id" :value="String(p.id)">{{ p.code }} · {{ p.name }}</option></select></label><label>排序<select aria-label="证书排序" :value="route.query.sort || 'expiry'" @change="updateLedgerQuery({sort:$event.target.value,page:undefined})"><option value="expiry">到期日期优先</option><option value="name">证书名称</option></select></label><button class="btn btn-secondary" @click="clearListFilters">重置</button><button class="btn btn-secondary" :disabled="loading" @click="load">刷新</button></div><p v-if="isCertificatePage" class="field-help">到期状态按系统日期和有效期判断；证书文件上传后仅通过 ERP 权限访问，不生成公开链接。</p><p v-if="isCertificatePage && parameterOptionError" role="alert" class="option-load-error">产品选项加载失败：{{ parameterOptionError }} <button @click="loadParameterProducts">重试</button></p><div v-if="isParameterPage" class="parameter-filter-bar"><label v-if="can('products','view')">所属产品<select aria-label="按产品筛选参数" :value="route.query.product || ''" @change="updateLedgerQuery({product:$event.target.value || undefined})"><option value="">全部产品</option><option v-for="product in parameterProducts" :key="product.id" :value="String(product.id)">{{ product.code }} · {{ product.name }}</option></select></label><button class="btn btn-secondary" @click="updateLedgerQuery({product:undefined,search:undefined}); query = ''">重置</button><button class="btn btn-secondary" :disabled="loading" @click="load">刷新</button><button v-if="route.query.product && can('products','view')" class="btn btn-secondary" @click="router.push({path:'/products',query:{detail:route.query.product}})">查看所属产品</button></div><p v-if="isParameterPage" class="field-help">产品参数用于记录通用规格。分类属性用于参数模板，SKU 参数用于具体规格与身份；在此保存不会修改 SKU 参数。</p><p v-if="isParameterPage && parameterOptionError" role="alert" class="option-load-error">{{ parameterOptionError }} <button @click="loadParameterProducts">重试</button></p>
    <div v-if="isCustomerPage" class="customer-filter-bar" aria-label="客户筛选"><label class="customer-search search-box">搜索<input v-model="query" aria-label="搜索客户" placeholder="名称、编号、国家/地区或负责人" @input="delayedSearch" /></label><label>负责人<select aria-label="按负责人筛选客户" :value="customerFilter.owner" @change="setCustomerFilter('owner_profile', $event.target.value)"><option value="">全部负责人</option><option v-for="owner in customerFilterOptions.owners" :key="owner.id" :value="String(owner.id)">{{ owner.label }}</option></select></label><label>国家/地区<select aria-label="按国家/地区筛选客户" :value="customerFilter.country" @change="setCustomerFilter('country', $event.target.value)"><option value="">全部国家/地区</option><option v-for="country in customerFilterOptions.countries" :key="country.value" :value="country.value">{{ country.label }}</option></select></label><label>状态<select aria-label="按客户状态筛选" :value="customerFilter.status" @change="setCustomerFilter('status', $event.target.value)"><option value="">全部状态</option><option v-for="status in customerStatusOptions" :key="status.value" :value="status.value">{{ status.label }}</option></select></label><button type="button" class="btn btn-secondary" @click="clearListFilters">重置</button><button type="button" class="btn btn-secondary" :disabled="loading" @click="load">刷新</button></div>
    <div v-if="isCustomerPage && customerFilterError" class="option-load-error" role="alert">{{ customerFilterError }} <button type="button" @click="loadCustomerFilterOptions">重新加载筛选选项</button></div>
    <div v-if="isCrmPage" class="crm-filter-bar" :class="{ 'follow-up-filter-bar': isFollowUpPage }" :aria-label="isContactPage ? '联系人筛选' : '跟进记录筛选'">
      <label class="crm-search search-box">搜索<input v-model="query" :aria-label="isContactPage ? '搜索联系人' : '搜索跟进记录'" :placeholder="isContactPage ? '姓名、客户、职位或联系方式' : '客户、主题、跟进人或内容'" @input="delayedSearch" /></label>
      <label v-if="crmFilterOptions.customers.length">所属客户<select aria-label="按客户筛选" :value="crmFilter.customer" @change="setCrmFilter('customer', $event.target.value)"><option value="">全部客户</option><option v-for="customer in crmFilterOptions.customers" :key="customer.id" :value="String(customer.id)">{{ customer.name }}</option></select></label>
      <label v-if="isContactPage">联系人类型<select aria-label="按联系人类型筛选" :value="crmFilter.primary" @change="setCrmFilter('primary', $event.target.value)"><option value="">全部联系人</option><option value="primary">主联系人</option><option value="other">其他联系人</option></select></label>
      <template v-if="isFollowUpPage">
        <label v-if="crmFilterOptions.owners.length">跟进人<select aria-label="按跟进人筛选" :value="crmFilter.owner" @change="setCrmFilter('owner', $event.target.value)"><option value="">全部跟进人</option><option v-for="owner in crmFilterOptions.owners" :key="owner.value" :value="owner.value">{{ owner.label }}</option></select></label>
        <label>跟进方式<select aria-label="按跟进方式筛选" :value="crmFilter.type" @change="setCrmFilter('type', $event.target.value)"><option value="">全部方式</option><option v-for="method in crmFilterOptions.methods" :key="method.value" :value="method.value">{{ method.label }}</option></select></label>
        <label>跟进时间从<input aria-label="跟进开始日期" type="date" :value="crmFilter.from" @change="setCrmFilter('from', $event.target.value)" /></label>
        <label>至<input aria-label="跟进结束日期" type="date" :value="crmFilter.to" @change="setCrmFilter('to', $event.target.value)" /></label>
        <label>排序<select aria-label="跟进排序" :value="crmFilter.sort" @change="setCrmFilter('sort', $event.target.value)"><option value="newest">时间从近到远</option><option value="oldest">时间从远到近</option></select></label>
        <button type="button" class="btn" title="按跟进状态筛选" :class="route.query.due === 'true' ? 'btn-primary' : 'btn-secondary'" :aria-pressed="route.query.due === 'true'" @click="setCrmFilter('due', route.query.due === 'true' ? '' : 'true')">{{ route.query.due === 'true' ? '显示全部记录' : '待跟进' }}</button>
      </template>
      <button type="button" class="btn btn-secondary" @click="clearListFilters">重置</button>
      <button type="button" class="btn btn-secondary" :disabled="loading" @click="load">刷新</button>
    </div>
    <div v-if="isCrmPage && crmFilterError" class="option-load-error" role="alert">{{ crmFilterError }} <button type="button" @click="loadCrmFilterOptions">重新加载筛选选项</button></div>
    <SkuContextBanner v-if="hasSkuContext" :label="activeSkuContextLabel" @clear="clearSkuFilter" />
    <div v-if="isMovementPage" class="ledger-filter-bar" aria-label="库存流水筛选">
      <label>搜索<input v-model="query" aria-label="搜索库存流水" placeholder="流水号、SKU、产品、订单、仓库、参考号" @input="delayedSearch" /></label>
      <label>类型<select :value="movementFilters.type" aria-label="按流水类型筛选" @change="updateLedgerQuery({type:$event.target.value || undefined})"><option value="">全部类型</option><option v-for="(label,value) in movementTypes" :key="value" :value="value">{{ label }}</option></select></label>
      <label>方向<select :value="movementFilters.direction" aria-label="按库存方向筛选" @change="updateLedgerQuery({direction:$event.target.value || undefined})"><option value="">全部方向</option><option value="in">入库</option><option value="out">出库</option></select></label>
      <label>来源<select :value="movementFilters.source" aria-label="按流水来源筛选" @change="updateLedgerQuery({source:$event.target.value || undefined})"><option value="">全部来源</option><option value="automatic">系统自动</option><option value="manual">手工登记</option><option value="reversal">冲销</option></select></label>
      <button class="btn btn-secondary" @click="resetLedgerFilters">重置</button>
    </div>
    <p v-if="isMovementPage" class="ledger-help">数量按 SKU 基础单位显示；自动流水不可手工修改。</p>
    <div v-else-if="isSupplierPage" class="supplier-filter-bar" aria-label="供应商筛选"><label>搜索<input v-model="query" aria-label="搜索供应商" placeholder="名称、代码、联系人、产品…" @input="delayedSearch" /></label><label v-if="can('categories','view')">可供分类<select :value="supplierFilter.category" aria-label="按可供分类筛选" @change="updateLedgerQuery({supplyCategory:$event.target.value || undefined})"><option value="">全部分类</option><option v-for="category in supplierCategories" :key="category.id" :value="String(category.id)">{{ category.name }}</option></select></label><button class="btn btn-secondary" @click="clearListFilters">重置</button><button class="btn btn-secondary" :disabled="loading" @click="load">刷新</button></div><div v-if="isSupplierPage && supplierCategoryError" role="alert" class="option-load-error">分类加载失败：{{ supplierCategoryError }} <button @click="loadSupplierCategories">重新加载分类</button></div><p v-if="isSupplierPage" class="supplier-rule-note">付款备注仅供沟通参考；采购单付款条件需逐单协商。</p><div v-if="!isMovementPage && !isSupplierPage && !isCrmPage && !isCustomerPage" class="toolbar"><div class="search-box"><Search :size="17" /><input v-model="query" :aria-label="isCertificatePage ? '搜索产品证书' : isParameterPage ? '搜索产品参数' : undefined" :placeholder="isParameterPage ? '参数名称、值或分组' : '搜索当前列表...'" @input="delayedSearch" /></div></div>
    <div class="panel">
      <PageLoadState :loading="loading" :has-loaded="hasLoaded" :error="loadError" @retry="load" />
      <ListEmptyState v-if="hasLoaded && !visibleRows.length" :entity="listNoun || config.title.replace('管理','')" :filtered="filteredListEmpty" @clear="clearListFilters"><template #action><p v-if="can(accessModule, 'create')">{{ isCustomerPage ? '添加客户资料，记录负责人和跟进计划。' : isContactPage ? '先选择所属客户，再添加联系人。' : isFollowUpPage ? '记录客户沟通和下一步安排。' : `点击“${primaryAction}”开始录入。` }}</p></template></ListEmptyState>
      <div v-else-if="hasLoaded" class="table-wrap"><table class="data-table" :class="{ 'customer-list-table': isCustomerPage, 'supplier-list-table': isSupplierPage, 'contact-list-table': isContactPage, 'follow-up-list-table': isFollowUpPage, 'parameter-list-table': isParameterPage, 'certificate-list-table': isCertificatePage }"><thead><tr><th v-for="col in listColumns" :key="col[0]">{{ col[1] }}</th><th style="text-align:right">操作</th></tr></thead><tbody>
        <tr v-for="row in displayRows" :key="row.id" class="clickable-row" tabindex="0" @click="openDetail(row.id)" @keydown.enter="openDetail(row.id)">
          <td v-for="(col,index) in listColumns" :key="col[0]" :class="{ 'primary-cell': index === 0, 'numeric-cell': ['money', 'rmb'].includes(col[2]) }">
            <template v-if="isCertificatePage && col[0] === 'name'"><strong>{{ row.name }}</strong><small class="supplier-secondary">{{ row.certificate_no || '未填编号' }}</small></template><template v-else-if="isCertificatePage && col[0] === 'file_url'"><a v-if="certificateFileUrl(row.file_url)" :href="certificateFileUrl(row.file_url)" target="_blank" rel="noopener noreferrer" @click.stop>查看文件链接</a><span v-else>{{ row.file_url ? '链接格式不可用' : '未提供文件' }}</span></template><template v-else-if="(isParameterPage || isCertificatePage) && col[0] === 'product_name'"><button v-if="row.product && can('products','view')" class="crm-customer-link" @click.stop="router.push({path:'/products',query:{detail:String(row.product),returnTo:route.fullPath}})">{{ row.product_name || '查看产品' }}</button><span v-else>{{ row.product_name || '—' }}</span></template>
            <template v-else-if="isContactPage && col[0] === 'customer_name'"><button v-if="row.customer" class="crm-customer-link" type="button" @click.stop="openContactCustomer(row)">{{ row.customer_name || '查看客户' }}</button><span v-else>{{ row.customer_name || '—' }}</span></template>
            <template v-else-if="isContactPage && col[0] === 'name'"><strong>{{ row.name }}</strong><small class="crm-secondary">{{ row.title || '未填写职位' }}</small></template>
            <template v-else-if="isContactPage && col[0] === 'contact_methods'"><a v-if="row.phone" :href="`tel:${row.phone}`" @click.stop>{{ row.phone }}</a><small v-if="row.whatsapp" class="crm-secondary">WhatsApp：{{ row.whatsapp }}</small><a v-if="row.email" class="crm-secondary" :href="`mailto:${row.email}`" @click.stop>{{ row.email }}</a><span v-if="!row.phone && !row.whatsapp && !row.email">—</span></template>
            <span v-else-if="isContactPage && col[0] === 'is_primary'" class="crm-primary-badge" :class="{ inactive: !row.is_primary }">{{ row.is_primary ? '主联系人' : '普通联系人' }}</span>
            <template v-else-if="isFollowUpPage && col[0] === 'follow_up_context'"><strong>{{ row.customer_name || '—' }}</strong><small class="crm-secondary">{{ row.contact_name || '未关联联系人' }}</small></template>
            <template v-else-if="isFollowUpPage && col[0] === 'subject'"><strong>{{ row.subject || '跟进记录' }}</strong><small class="crm-secondary">{{ row.type_display || '未标注方式' }}</small></template>
            <template v-else-if="isFollowUpPage && col[0] === 'follow_up_content'"><span>{{ richTextExcerpt(row.content) || '未填写跟进记录' }}</span><small class="crm-secondary">客户回复：{{ richTextExcerpt(row.result, 90) || '—' }}</small></template>
            <template v-else-if="isFollowUpPage && col[0] === 'follow_up_next'"><span>{{ row.next_action || '未填写下一步' }}</span><small class="crm-secondary">{{ row.next_follow_up_mode_display || '保留当前计划' }} · {{ row.next_follow_up || '未安排日期' }}</small></template>
             <template v-else-if="isSupplierPage && col[0] === 'is_active'"><span class="status" :class="row.is_active ? 'active' : 'inactive'">{{ row.is_active ? '启用' : '停用' }}</span></template>
            <template v-else-if="isSupplierPage && col[0] === 'name'"><strong>{{ row.name }}</strong><small class="supplier-secondary">{{ row.code }} · {{ row.country || '未填国家/地区' }}</small></template><template v-else-if="isSupplierPage && col[0] === 'main_products'"><span>{{ row.main_products || '—' }}</span><small class="supplier-secondary">{{ (row.supply_category_names || []).join('、') || '未填可供分类' }}</small></template><template v-else-if="isSupplierPage && col[0] === 'contact_name'"><span>{{ row.contact_name || '—' }}</span><small class="supplier-secondary">{{ row.phone }}</small><small class="supplier-secondary">{{ row.email }}</small><a v-if="supplierStoreUrl(row.store_url)" :href="supplierStoreUrl(row.store_url)" target="_blank" rel="noopener noreferrer" @click.stop>打开店铺</a><small v-else-if="row.store_url" class="supplier-secondary">{{ row.store_url }}</small></template><span v-else-if="isSupplierPage && col[0] === 'payment_terms'" class="supplier-excerpt" :title="row.payment_terms">{{ row.payment_terms || '未填备注' }}</span><template v-else-if="isMovementPage && col[0] === 'sku_code'"><strong>{{ row.sku_code || row.sku_code_snapshot || '—' }}</strong><small class="ledger-secondary">{{ row.product_name || row.display_name }}</small><small v-if="movementUnit(row,movementSkus)" class="ledger-secondary">基础单位：{{ movementUnit(row,movementSkus) }}</small></template><span v-else-if="isMovementPage && col[0] === 'source_type'" class="ledger-source" :class="movementSource(row)">{{ sourceLabels[movementSource(row)] || '未标注' }}</span><span v-else-if="isMovementPage && col[0] === 'signed_quantity'" :class="cellClass('signed',row.signed_quantity)">{{ signedMovement(row,movementUnit(row,movementSkus)) }}</span><template v-else-if="isMovementPage && col[0] === 'reference'"><span>{{ row.reference || row.source_no || '—' }}</span><small class="ledger-secondary">{{ (row.related_order_nos || []).join('、') || row.order_no }}</small><small v-if="row.overage_summary" class="ledger-secondary">{{ row.overage_summary }}</small></template><span v-else-if="isMovementPage && col[0] === 'reversal_status'" :title="row.reversal_status">{{ movementStatus(row) }}</span><CertificateExpiryBadge v-else-if="isCertificatePage && col[0] === 'expiry_status'" :certificate="row" /><span v-else-if="isCustomerPage && col[0] === 'name'" class="customer-name" :title="row.name">{{ row.name }}</span><span v-else-if="isCustomerPage && col[0] === 'country'" :title="row.country_display || row.country">{{ row.country_display || row.country || '—' }}</span><span v-else-if="isCustomerPage && col[0] === 'status'" class="status" :class="row.status" :title="row.status_display || statusLabels[row.status]">{{ customerListStatus(row.status, display(row.status, 'status', 'status')) }}</span><span v-else :class="cellClass(col[2], row[col[0]])">{{ display(row[col[0]], col[2], col[0]) }}</span>
          </td>
           <td><div class="table-actions"><RouterLink v-if="(isCustomerPage || isFollowUpPage) && can('followups','view') && can('customers','view')" :to="{path:'/new-product-reminders',query:{customer:isCustomerPage ? row.id : row.customer,follow_up:isFollowUpPage ? row.id : undefined}}" @click.stop>新品提醒</RouterLink><button class="mini-btn" title="查看详情" :aria-label="isContactPage ? '查看联系人详情' : isFollowUpPage ? '查看跟进详情' : '查看详情'" @click.stop="openDetail(row.id)"><ChevronRight :size="14" /></button><button v-if="can(accessModule, 'update') && !isReadOnlyAutomaticMovement(row)" class="mini-btn" title="编辑" :aria-label="isContactPage ? '编辑联系人' : isFollowUpPage ? '编辑跟进记录' : '编辑'" @click.stop="openEdit(row)"><Pencil :size="14" /></button><button v-if="isSupplierPage && can('suppliers', 'update')" class="mini-btn supplier-lifecycle-btn" :class="{ danger: row.is_active }" :disabled="supplierLifecycleBusyId === row.id" :title="row.is_active ? '停用供应商' : '启用供应商'" :aria-label="row.is_active ? '停用供应商' : '启用供应商'" @click.stop="toggleSupplierLifecycle(row)">{{ row.is_active ? '停用' : '启用' }}</button><button v-if="can('inventory', 'update') && canReverseInventoryMovement(row)" class="mini-btn danger" title="冲销" :disabled="reversing" @click.stop="reverseInventoryMovement(row)"><RotateCcw :size="14" /></button><button v-else-if="can(accessModule, 'delete') && config.endpoint !== 'inventory-movements' && !isReadOnlyAutomaticMovement(row) && !isSupplierPage" class="mini-btn" title="删除" :aria-label="isContactPage ? '删除联系人' : isFollowUpPage ? '删除跟进记录' : '删除'" @click.stop="remove(row)"><Trash2 :size="14" /></button></div></td>
        </tr>
      </tbody></table></div>
    </div>

    <InventoryMovementCreateModal v-if="modalOpen && config.endpoint === 'inventory-movements' && !editingId" @close="closeModal" @saved="handleInventoryMovementCreated" />
    <div v-else-if="modalOpen" class="modal-backdrop"><form :role="isSupplierPage || isCrmPage || isParameterPage || isCertificatePage ? 'dialog' : undefined" :aria-modal="isSupplierPage || isCrmPage || isParameterPage || isCertificatePage ? 'true' : undefined" :aria-label="isSupplierPage || isCrmPage || isParameterPage || isCertificatePage ? title : undefined" class="modal" :class="{ wide: isWideForm, 'customer-editor': isCustomerPage, 'supplier-editor': isSupplierPage, 'crm-editor': isCrmPage, 'parameter-editor': isParameterPage || isCertificatePage }" @submit.prevent="save">
      <div class="modal-head"><h3>{{ title }}</h3><button type="button" class="mini-btn" :aria-label="isCertificatePage ? '关闭证书表单' : isParameterPage ? '关闭参数表单' : isSupplierPage ? '关闭供应商表单' : isContactPage ? '关闭联系人表单' : isFollowUpPage ? '关闭跟进表单' : undefined" :disabled="saving" @click="closeModal"><X :size="17" /></button></div>
      <div class="modal-body" :inert="(isParameterPage || isCertificatePage) && saving"><p v-if="isCertificatePage && certificateSaveError" role="alert" class="supplier-save-error">{{ certificateSaveError }}</p><p v-if="isParameterPage && parameterSaveError" role="alert" class="supplier-save-error">{{ parameterSaveError }}</p><p v-if="isSupplierPage && supplierSaveError" role="alert" class="supplier-save-error">{{ supplierSaveError }}</p><p v-if="isCertificatePage" class="field-help">证书文件必须上传到 ERP 私有存储；查看和下载均需当前证书权限。</p><p v-if="isFollowUpPage" class="field-help">跟进记录或客户回复至少填写一项。</p><template v-for="(group, groupIndex) in editorGroups" :key="groupIndex"><h4 v-if="isSupplierPage || isContactPage || isFollowUpPage || isParameterPage || isCertificatePage" class="supplier-group-title">{{ editorGroupTitles[groupIndex] }}</h4><p v-if="isSupplierPage && groupIndex === 2" class="field-help">可供分类用于筛选；具体 SKU 的供应来源仍需在供货档案中维护。</p><h4 v-if="isCustomerPage && groupIndex === 1" class="optional-heading">补充信息</h4><div class="form-grid"><div v-for="field in group.filter(visibleEditorField)" :key="field[0]" class="field" :role="isCertificatePage ? 'group' : undefined" :aria-label="isCertificatePage ? editorFieldLabel(field) : undefined" :class="{ full: ['textarea', 'remote_multi', 'payment_terms', 'file'].includes(field[2]) || (isCertificatePage && field[0] === 'file_url') || (isSupplierPage && field[0] === 'payment_terms') || (isFollowUpPage && ['subject', 'content', 'result', 'next_follow_up_mode'].includes(field[0])), 'finance-amount-field': isTransactionPage && ['amount', 'exchange_rate'].includes(field[0]) }">
        <label>{{ editorFieldLabel(field) }} <em v-if="field[3]">*</em></label><p v-if="optionErrors[field[4]]" class="option-load-error" role="alert">{{ optionErrors[field[4]] }} <button type="button" @click="retryRemoteOption(field)">重新加载</button></p>
        <div v-if="field[2] === 'followup_schedule'" class="follow-up-schedule" role="radiogroup" aria-label="下次跟进安排">
          <label v-for="(label, mode) in { keep: '保留当前计划', set: '设置新的跟进日期', clear: '暂不安排后续跟进' }" :key="mode"><input v-model="form.next_follow_up_mode" type="radio" name="next_follow_up_mode" :value="mode" @change="changeFollowUpMode" /> {{ label }}</label>
          <p v-if="form.next_follow_up_mode === 'keep'" class="field-help">当前计划：{{ currentFollowUpPlan || '暂无跟进日期' }}</p>
          <p v-else-if="form.next_follow_up_mode === 'clear'" class="field-help">这会清除该客户当前的下次跟进日期。</p>
        </div>
        <textarea :maxlength="isSupplierPage && field[0] === 'payment_terms' ? 200 : undefined" :aria-label="isSupplierPage || isCrmPage || isParameterPage || isCertificatePage ? editorFieldLabel(field) : undefined" v-else-if="field[2] === 'textarea' || (isSupplierPage && field[0] === 'payment_terms')" v-model="form[field[0]]" :required="field[3]" :disabled="isInherited(field[0])" />
        <SimpleRichTextEditor v-else-if="field[2] === 'richtext'" v-model="form[field[0]]" :label="isCrmPage ? editorFieldLabel(field) : ''" @paste-files="addFollowUpFiles" />
        <ComboInput v-else-if="field[2] === 'combo'" v-model="form[field[0]]" :options="options[field[4]] || []" :label="isCrmPage || (isCustomerPage && field[0] === 'country') ? editorFieldLabel(field) : ''" :placeholder="isCustomerPage && field[0] === 'country' ? '搜索名称、中文或代码后选择' : undefined" :required="field[3]" :allow-custom="!(isCustomerPage && field[0] === 'country')" :disabled="isInherited(field[0]) || Boolean(optionErrors[field[4]])" />
        <select v-else-if="field[2] === 'select'" v-model="form[field[0]]" :aria-label="isCrmPage || isParameterPage || isCertificatePage ? editorFieldLabel(field) : undefined" :required="field[3]" :disabled="isInherited(field[0])"><option v-for="(label,key) in field[4]" :key="key" :value="key">{{ label }}</option></select>
        <CategoryMultiPicker v-else-if="field[2] === 'remote_multi'" v-model="form[field[0]]" :categories="options[field[4]] || []" />
        <div v-else-if="field[2] === 'file'" class="private-file-input"><input :aria-label="editorFieldLabel(field)" type="file" @change="onCertificateFileSelected" /><small v-if="currentCertificateFileUrl"><a :href="certificateFileUrl(currentCertificateFileUrl)" target="_blank" rel="noopener noreferrer">查看当前私有文件</a></small><small v-else>可选；保存后按权限查看。</small></div>
        <select v-else-if="field[2] === 'remote'" v-model="form[field[0]]" :aria-label="isCrmPage || isParameterPage || isCertificatePage ? editorFieldLabel(field) : undefined" :required="field[3]" :disabled="isInherited(field[0]) || Boolean(optionErrors[field[4]]) || (field[0] === 'owner_profile' && ownerProfileReadOnly)" @change="onFieldChange(field)"><option value="">请选择</option><option v-for="option in visibleOptions(field)" :key="option.id" :value="option.id">{{ option[field[5]] }}</option></select>
        <label v-else-if="field[2] === 'checkbox'" class="checkbox-line"><input v-model="form[field[0]]" type="checkbox" :disabled="isInherited(field[0])" /> 是</label>
        <div v-else-if="config.endpoint === 'follow-ups' && field[0] === 'next_follow_up'" class="follow-up-date-control">
          <input v-model="followUpDays" type="number" min="0" step="1" placeholder="天数" aria-label="下次跟进天数" @input="updateFollowUpDate" />
          <span>天后</span>
          <SegmentedDateInput :model-value="form.next_follow_up" @update:model-value="setFollowUpDate" />
        </div>
        <SegmentedDateInput v-else-if="field[2] === 'date' || field[2] === 'datetime-local'" :model-value="form[field[0]]" :required="field[3]" :with-time="field[2] === 'datetime-local'" @update:model-value="value => onDateFieldChange(field, value)" />
        <input v-else :aria-label="isSupplierPage || isCrmPage || isParameterPage || isCertificatePage ? editorFieldLabel(field) : undefined" v-model="form[field[0]]" :type="field[2] === 'readonly' || ['website', 'store_url'].includes(field[0]) ? 'text' : (field[2] || 'text')" :readonly="field[2] === 'readonly'" :placeholder="field[0] === 'store_url' ? 'https://...' : isCustomerPage && field[0] === 'name' ? '输入客户名称' : undefined" :class="{ 'readonly-input': field[2] === 'readonly', 'field-invalid': config.endpoint === 'suppliers' && field[0] === 'code' && supplierCodeError }" :aria-invalid="config.endpoint === 'suppliers' && field[0] === 'code' && supplierCodeError ? 'true' : undefined" :min="isParameterPage && field[0] === 'sort_order' ? 0 : undefined" :step="field[2] === 'number' ? (isParameterPage ? '1' : '0.0001') : undefined" :maxlength="isSupplierPage ? { name:200,code:2,country:100,main_products:300,contact_name:100,phone:50,email:254,store_url:500 }[field[0]] : undefined" :pattern="config.endpoint === 'suppliers' && field[0] === 'code' ? '[A-Za-z]{2}' : undefined" :required="field[3]" :disabled="isInherited(field[0])" @input="config.endpoint === 'suppliers' && field[0] === 'code' && normalizeSupplierCode()" />
        <p v-if="isCustomerPage && field[0] === 'country'" class="field-help">请选择标准英文名称 / 两位代码；历史文本需人工确认。</p><div v-if="isContactPage && field[0] === 'name' && (contactDuplicateLoading || contactDuplicateError || contactDuplicateHint)" class="field-help crm-duplicate-hint" role="status"><span v-if="contactDuplicateLoading">正在检查该客户的全部联系人…</span><span v-else-if="contactDuplicateError">{{ contactDuplicateError }}可继续保存。</span><template v-else><span>{{ contactDuplicateHint }}</span><ul class="crm-duplicate-list"><li v-for="match in contactDuplicateMatches" :key="match.id"><span>{{ match.name }}（{{ match.matchReasons.join('、') }}）</span><a :href="contactDetailUrl(match)" target="_blank" rel="noopener noreferrer">查看联系人</a></li></ul><small>这是非阻断提醒；确认无误后仍可继续创建。</small></template></div>
        <p v-if="isSupplierPage && field[0] === 'payment_terms'" class="field-help">仅供沟通参考，不生成付款计划。</p><p v-if="config.endpoint === 'suppliers' && field[0] === 'code'" class="field-help" :class="{ error: supplierCodeError }">{{ supplierCodeError || '填写两个英文字母，用于供应商 SKU 编码。' }}</p>
      </div></div>
        <section v-if="isCustomerCreate && groupIndex === 0" class="contact-create-section">
          <div class="contact-create-head">
            <div><span>联系人信息</span><p>至少登记一位联系人，可指定默认联系人。</p></div>
            <span class="contact-count">{{ customerContacts.length }} 位</span>
          </div>
          <div v-for="(contact, index) in customerContacts" :key="index" class="contact-create-card">
            <div class="contact-card-head">
              <strong>联系人 {{ index + 1 }}</strong>
              <div class="contact-card-actions">
                <label class="primary-switch">
                  <input type="checkbox" :checked="contact.is_primary" @change="setPrimaryContact(index)" />
                  <span class="switch-track"><i /></span>
                  <span>默认联系人</span>
                </label>
                <button v-if="customerContacts.length > 1" type="button" class="mini-btn danger" aria-label="删除联系人" @click="removeCustomerContact(index)"><Trash2 :size="14" /></button>
              </div>
            </div>
            <div class="contact-fields">
              <div class="field"><label>姓名 <em>*</em></label><input v-model.trim="contact.name" required /></div>
              <div class="field"><label>职位</label><input v-model.trim="contact.title" /></div>
              <div class="field"><label>邮箱</label><input v-model.trim="contact.email" type="email" /></div>
              <div class="field"><label>电话</label><input v-model.trim="contact.phone" /></div>
              <div class="field"><label>WhatsApp</label><input v-model.trim="contact.whatsapp" /></div>
              <div class="field"><label>备注</label><input v-model.trim="contact.notes" /></div>
            </div>
          </div>
          <button type="button" class="add-contact-btn" @click="addCustomerContact"><UserRoundPlus :size="16" /> 新增联系人</button>
        </section>
      </template>

        <section v-if="config.endpoint === 'follow-ups'" class="follow-up-attachment-editor" @dragover.prevent @drop.prevent="onFollowUpFileDrop">
          <div class="follow-up-attachment-editor-head">
            <div><strong><Paperclip :size="16" /> 附件</strong><span>支持在编辑器中粘贴图片或附件，也可拖拽、选择文件</span></div>
            <label class="follow-up-attachment-picker"><Paperclip :size="14" /> 添加附件<input ref="followUpFileInput" type="file" multiple @change="onFollowUpFileInput" /></label>
          </div>
          <div v-if="followUpAttachments.length || pendingFollowUpFiles.length" class="follow-up-attachment-editor-list">
            <strong v-if="followUpAttachments.length" class="follow-up-attachment-editor-group-title">已保存附件</strong>
            <div v-for="attachment in followUpAttachments" :key="`saved-${attachment.id}`" class="follow-up-attachment-editor-item saved">
              <Paperclip :size="16" />
              <span><strong>{{ attachment.name }}</strong><small>已上传 · {{ formatAttachmentSize(attachment.size) }}</small></span>
              <div class="follow-up-attachment-editor-actions"><a :href="attachment.url || attachment.file" target="_blank" rel="noreferrer">查看</a><button type="button" :aria-label="`删除已保存附件 ${attachment.name}`" @click="deleteSavedFollowUpAttachment(attachment)">删除</button></div>
            </div>
            <strong v-if="pendingFollowUpFiles.length" class="follow-up-attachment-editor-group-title">待上传附件</strong>
            <div v-for="(file, index) in pendingFollowUpFiles" :key="`pending-${file.name}-${file.size}-${file.lastModified}`" class="follow-up-attachment-editor-item"><Paperclip :size="16" /><span><strong>{{ file.name }}</strong><small>待上传 · {{ formatAttachmentSize(file.size) }}</small></span><button type="button" aria-label="移除待上传附件" @click="removePendingFollowUpFile(index)">移除</button></div>
          </div>
          <div v-else class="follow-up-attachment-editor-empty"><Paperclip :size="16" /> 尚未添加附件</div>
        </section>


      </div>
      <div class="modal-foot" :class="{ 'follow-up-attachment-failed': isFollowUpPage && attachmentSaveError }"><p v-if="isFollowUpPage && followUpSaveAttempted && followUpScheduleError" class="follow-up-validation" role="alert">{{ followUpScheduleError }}</p><p v-if="isFollowUpPage && attachmentSaveError" class="follow-up-validation" role="alert">{{ attachmentSaveError }}</p><button type="button" class="btn btn-secondary" :disabled="saving" @click="closeModal">取消</button><button v-if="can(accessModule, editingId ? 'update' : 'create')" class="btn btn-primary" :disabled="saving || !optionsReady || (isSupplierPage && !!supplierCodeError)">{{ saving ? '保存中…' : saveLabel }}</button></div>
    </form></div>

    <Transition name="detail-drawer" appear>
      <EntityDetailModal v-if="detailId" :entity="config.endpoint" :id="detailId" :refresh-key="detailRefresh" @close="closeDetail" @edit="editFromDetail" @changed="handleDetailChanged" />
    </Transition>
    <InventoryPagination v-if="(isMovementPage || isSupplierPage || isPaginatedListPage || isCertificatePage) && hasLoaded" :label="isCertificatePage ? '证书列表分页' : isContactPage ? '联系人列表分页' : isFollowUpPage ? '跟进记录分页' : isCustomerPage ? '客户列表分页' : isSupplierPage ? '供应商列表分页' : '库存列表分页'" :total="visibleRows.length" :page="ledgerPage" @change="page => (isCrmPage ? updateCrmQuery({ page: page > 1 ? String(page) : undefined }) : updateLedgerQuery({ page: page > 1 ? String(page) : undefined }))" />
    <div v-if="toast.show" :role="toast.error ? 'alert' : 'status'" class="toast" :class="{ error: toast.error }">{{ toast.message }}</div>
  </div>
</template>

<style scoped>
.follow-up-schedule { display: flex; flex-wrap: wrap; gap: 12px 20px; }
.follow-up-schedule label { display: flex; align-items: center; gap: 6px; white-space: nowrap; }
.follow-up-schedule input[type="radio"] { width: 16px; min-width: 16px; height: 16px; min-height: 16px; flex: 0 0 16px; padding: 0; }
.follow-up-attachment-failed { flex-wrap: wrap; }
.follow-up-attachment-failed .follow-up-validation { flex-basis: 100%; }
.follow-up-validation { flex: 1; min-width: 0; align-self: center; margin: 0; color: #a23b32; font-size: var(--text-body); }
.follow-up-schedule .field-help { flex-basis: 100%; margin: 0; }

.customer-editor .form-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.customer-editor textarea{min-height:58px;height:58px}
.customer-editor .modal-body{padding-bottom:24px}.optional-heading{margin:24px 0 16px;font-size:var(--text-section)}
@media(max-width:760px){.customer-editor .form-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:520px){.customer-editor .form-grid{grid-template-columns:1fr}}
.certificate-filters{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}

.contact-create-section{margin-top:26px;padding-top:22px;border-top:1px solid var(--line)}
.follow-up-date-control{display:flex;align-items:center;gap:6px}.follow-up-date-control>input{flex:0 0 10ch!important;width:10ch!important;min-width:0}.follow-up-date-control>span{color:#70817b;font-size:var(--text-body);white-space:nowrap}.follow-up-date-control :deep(.segmented-date){flex:1 1 auto;min-width:0}
.follow-up-attachment-editor{margin-top:24px;padding-top:20px;border-top:1px solid var(--line)}
.follow-up-attachment-editor-head{display:flex;align-items:center;justify-content:space-between;gap:16px}.follow-up-attachment-editor-head>div{min-width:0}.follow-up-attachment-editor-head strong{display:flex;align-items:center;gap:7px;color:var(--ink);font-size:var(--text-body)}.follow-up-attachment-editor-head strong svg{color:var(--green-2)}.follow-up-attachment-editor-head span{display:block;margin-top:4px;color:var(--muted);font-size:var(--text-body)}
.follow-up-attachment-picker{display:flex;align-items:center;gap:6px;flex:none;padding:8px 11px;border:1px solid #c8ddd4;border-radius:7px;background:#f1f8f4;color:var(--green-2);font-size:var(--text-body);font-weight:600;cursor:pointer}.follow-up-attachment-picker:hover{background:#e6f3ec}.follow-up-attachment-picker input{display:none}
.follow-up-attachment-editor-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:12px}.follow-up-attachment-editor-item{display:flex;align-items:center;gap:8px;min-width:0;padding:9px 10px;border:1px solid #dfe9e4;border-radius:8px;background:#fbfdfc;color:#315a4c}.follow-up-attachment-editor-item>svg{flex:none;color:#5e9c86}.follow-up-attachment-editor-item>span{display:grid;flex:1;min-width:0;gap:2px}.follow-up-attachment-editor-item strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:var(--text-body)}.follow-up-attachment-editor-item small{color:#81938b;font-size:var(--text-caption)}.follow-up-attachment-editor-item.saved{background:#f3faf6}.follow-up-attachment-editor-item button{display:grid;place-items:center;flex:none;padding:3px;border:0;background:transparent;color:#9a6b6b;cursor:pointer}.follow-up-attachment-editor-empty{display:flex;align-items:center;justify-content:center;gap:7px;min-height:60px;margin-top:12px;border:1px dashed #bfd4ca;border-radius:8px;background:#fbfdfc;color:#879991;font-size:var(--text-body)}.follow-up-attachment-editor-empty svg{color:#abc1b7}
.follow-up-attachment-editor-group-title{grid-column:1/-1;margin-top:5px;color:#64776f;font-size:var(--text-secondary)}.follow-up-attachment-editor-actions{display:flex;align-items:center;gap:8px;flex:none}.follow-up-attachment-editor-actions a,.follow-up-attachment-editor-actions button,.follow-up-attachment-editor-item>button{display:inline-flex!important;align-items:center;justify-content:center;padding:5px 8px!important;border:1px solid #d5e4dc!important;border-radius:6px;background:#fff!important;color:#28634f!important;font-size:var(--text-caption);line-height:1.2;text-decoration:none;white-space:nowrap}.follow-up-attachment-editor-actions button,.follow-up-attachment-editor-item>button{border-color:#ecd8d8!important;color:#985656!important}.follow-up-attachment-editor-actions a:hover{background:#eef7f2!important}.follow-up-attachment-editor-actions button:hover,.follow-up-attachment-editor-item>button:hover{background:#fff4f4!important}
.contact-create-head,.contact-card-head,.contact-card-actions,.primary-switch{display:flex;align-items:center}
.contact-create-head,.contact-card-head{justify-content:space-between;gap:16px}
.contact-create-head>div>span{font-size:var(--text-section);font-weight:700;color:var(--ink)}
.contact-create-head p{margin:4px 0 0;color:var(--muted);font-size:var(--text-body)}
.contact-count{flex:none;padding:4px 9px;border-radius:20px;background:#edf3f0;color:#47665c;font-size:var(--text-body);font-weight:600}
.contact-create-card{margin-top:14px;padding:16px;border:1px solid #dce5e0;border-radius:12px;background:#fbfcfb}
.contact-card-head strong{font-size:var(--text-body);color:#314740}
.contact-card-actions{gap:10px}
.primary-switch{gap:7px;margin:0;color:#53655f;font-size:var(--text-body);cursor:pointer}
.primary-switch input{position:absolute;opacity:0;pointer-events:none}
.switch-track{width:34px;height:19px;border-radius:20px;background:#cbd6d1;padding:2px;transition:.2s}
.switch-track i{display:block;width:15px;height:15px;border-radius:50%;background:white;box-shadow:0 1px 4px #173d3633;transition:.2s}
.primary-switch input:checked+.switch-track{background:var(--green-2)}
.primary-switch input:checked+.switch-track i{transform:translateX(15px)}
.contact-fields{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:14px}
.mini-btn.danger{color:var(--danger)}
.add-contact-btn{width:100%;margin-top:12px;padding:11px;border:1px dashed #aac2ba;border-radius:9px;background:#f7faf8;color:var(--green-2);display:flex;align-items:center;justify-content:center;gap:7px;font-size:var(--text-body);font-weight:600}
.add-contact-btn:hover{background:#edf5f1;border-color:#719d8f}
.readonly-input{background:#f1f5f3!important;color:#557068!important;cursor:not-allowed}
.field-invalid{border-color:#d85b5b!important;background:#fff8f8!important;box-shadow:0 0 0 3px #fbe4e4!important}
.field-help.error{color:#c33f3f;font-size:var(--text-caption);font-weight:600}
.finance-resource-page{font-family:var(--font-sans)}
.finance-resource-page .page-head h2,.finance-resource-page .page-head p,.finance-resource-page .data-table,.finance-resource-page .modal{font-family:inherit}
.finance-resource-page .data-table th{background:#f8faf8;color:#81908b}
.finance-resource-page .data-table td{color:#43504c}
.finance-resource-page .data-table .direction{font-weight:700}
.finance-resource-page .data-table .direction.income{color:#267255}
.finance-resource-page .data-table .direction.expense{color:#bd4e4e}
.finance-resource-page .numeric-cell{text-align:right;white-space:nowrap}
.finance-resource-page .numeric-cell .amount{display:inline-block;min-width:7.5ch;text-align:right;font-variant-numeric:tabular-nums}
.finance-resource-page .data-table td:nth-last-child(2){padding-right:22px}
.finance-resource-page .finance-amount-field input{font-variant-numeric:tabular-nums}
.finance-resource-page .modal .field label{letter-spacing:.01em}
@media(max-width:760px){.contact-fields{grid-template-columns:1fr 1fr}.follow-up-attachment-editor-head{align-items:flex-start;flex-direction:column}.follow-up-attachment-picker{width:100%;justify-content:center}.follow-up-attachment-editor-list{grid-template-columns:1fr}}
@media(max-width:520px){.contact-create-head,.contact-card-head{align-items:flex-start}.contact-card-head{flex-direction:column}.contact-fields{grid-template-columns:1fr}.contact-card-actions{width:100%;justify-content:space-between}}
.supply-category-options{display:flex;flex-wrap:wrap;gap:10px;max-height:190px;overflow:auto;padding:12px;border:1px solid #dce7e1;border-radius:8px}.supply-category-options label{display:flex;align-items:center;gap:6px}.supply-category-options small{flex-basis:100%;color:#71857b}
.follow-up-due-context{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 14px;padding:9px 12px;border:1px solid #c8d8ed;border-radius:9px;background:#f4f8fd;color:#42546b;font-size:13px}.follow-up-due-context strong{color:#173f70}.follow-up-due-context button{padding:2px 0;border:0;background:transparent;color:#245b91;font:inherit;cursor:pointer}.follow-up-due-context button:hover{text-decoration:underline}
.customer-filter-bar{display:grid;grid-template-columns:minmax(240px,2fr) repeat(3,minmax(140px,1fr)) auto auto;gap:10px 12px;align-items:end;margin:18px 0 12px}.customer-filter-bar label{display:grid;gap:6px;min-width:0;color:#71817b;font-size:var(--text-caption)}.customer-filter-bar input,.customer-filter-bar select{width:100%;min-width:0;min-height:42px;padding:9px 11px;border:1px solid #d7e3dd;border-radius:8px;background:#fff;color:#31594c;font:inherit;font-size:var(--text-body)}.customer-filter-bar input:focus,.customer-filter-bar select:focus{outline:2px solid #b8d8cb;outline-offset:1px}.customer-filter-bar>.btn{min-height:42px;white-space:nowrap}.crm-filter-bar{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px 12px;align-items:end;margin:18px 0 12px}.crm-filter-bar label{display:grid;gap:6px;min-width:0;color:#71817b;font-size:var(--text-caption)}.crm-filter-bar .crm-search{grid-column:span 2}.crm-filter-bar input,.crm-filter-bar select{width:100%;min-width:0;min-height:42px;padding:9px 11px;border:1px solid #d7e3dd;border-radius:8px;background:#fff;color:#31594c;font:inherit;font-size:var(--text-body)}.crm-filter-bar input:focus,.crm-filter-bar select:focus{outline:2px solid #b8d8cb;outline-offset:1px}.crm-filter-bar>.btn{min-height:42px;white-space:nowrap}.follow-up-filter-bar{grid-template-columns:repeat(6,minmax(0,1fr))}.crm-secondary{display:block;margin-top:5px;color:#7b8b84;font-size:var(--text-caption);font-weight:400;line-height:1.45;overflow-wrap:anywhere}.crm-customer-link{padding:0;border:0;background:transparent;color:#28634f;font:inherit;font-weight:600;text-align:left;cursor:pointer}.crm-customer-link:hover{text-decoration:underline}.crm-primary-badge{display:inline-flex;align-items:center;padding:4px 9px;border-radius:999px;background:#eaf5ef;color:#28634f;font-size:var(--text-secondary);font-weight:600;white-space:nowrap}.crm-primary-badge.inactive{background:#f1f3f2;color:#6e7a75}.crm-duplicate-hint{color:#8b6428;line-height:1.55}.contact-list-table{min-width:980px;table-layout:fixed}.contact-list-table th:nth-child(1){width:220px}.contact-list-table th:nth-child(2){width:210px}.contact-list-table th:nth-child(3){width:330px}.contact-list-table th:nth-child(4){width:150px}.contact-list-table th:last-child{width:110px}.contact-list-table td{white-space:normal;overflow-wrap:anywhere;vertical-align:top}.contact-list-table td:nth-child(3) a{color:#28634f;text-decoration:none}.contact-list-table td:nth-child(3) a:hover{text-decoration:underline}.follow-up-list-table{min-width:1320px;table-layout:fixed}.follow-up-list-table th:nth-child(1){width:210px}.follow-up-list-table th:nth-child(2){width:155px}.follow-up-list-table th:nth-child(3){width:180px}.follow-up-list-table th:nth-child(4){width:390px}.follow-up-list-table th:nth-child(5){width:290px}.follow-up-list-table th:last-child{width:110px}.follow-up-list-table td{white-space:normal;overflow-wrap:anywhere;vertical-align:top;line-height:1.5}.follow-up-list-table td:nth-child(2){white-space:nowrap}.follow-up-list-table th:last-child,.follow-up-list-table td:last-child{position:sticky;right:0;background:#fff;box-shadow:-4px 0 10px #173d3210}.follow-up-list-table td:last-child{z-index:2}.follow-up-list-table th:last-child{z-index:3}.crm-editor{width:min(1080px,calc(100vw - 40px));max-height:min(92vh,900px)}.crm-editor .form-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 18px}.crm-editor .supplier-group-title{margin-top:18px}.crm-editor .modal-body{padding-bottom:22px}.crm-editor .modal-foot{position:sticky;bottom:0;background:#fff;z-index:1}.crm-editor .field{min-width:0}.crm-editor .field input,.crm-editor .field select,.crm-editor textarea{min-width:0;max-width:100%}.crm-editor .contact-list-table td.primary-cell{white-space:normal}
.contact-list-table th:last-child,.contact-list-table td:last-child{position:sticky;right:0;background:#fff;box-shadow:-4px 0 10px #173d3210}.contact-list-table td:last-child{z-index:2}.contact-list-table th:last-child{z-index:3}
@media(max-width:1100px){.customer-filter-bar{grid-template-columns:repeat(3,minmax(0,1fr))}.customer-filter-bar .customer-search{grid-column:span 2}.follow-up-filter-bar{grid-template-columns:repeat(4,minmax(0,1fr))}.follow-up-filter-bar .crm-search{grid-column:span 2}}
@media(max-width:760px){.customer-filter-bar,.crm-filter-bar,.follow-up-filter-bar{grid-template-columns:repeat(2,minmax(0,1fr))}.customer-filter-bar .customer-search,.crm-filter-bar .crm-search,.follow-up-filter-bar .crm-search{grid-column:1/-1}.crm-editor .form-grid{grid-template-columns:1fr}.customer-filter-bar>.btn,.follow-up-filter-bar>.btn{justify-self:stretch}}
@media(max-width:520px){.customer-filter-bar,.crm-filter-bar,.follow-up-filter-bar{grid-template-columns:1fr}.customer-filter-bar .customer-search,.crm-filter-bar .crm-search,.follow-up-filter-bar .crm-search{grid-column:auto}.customer-filter-bar>.btn,.crm-filter-bar>.btn{width:100%}.follow-up-due-context{align-items:flex-start;flex-direction:column}}
.ledger-filter-bar{display:flex;flex-wrap:wrap;gap:12px;align-items:end;margin-bottom:12px}.ledger-filter-bar label{display:grid;gap:6px;color:#71817b;font-size:var(--text-caption)}.ledger-filter-bar label:first-child{flex:1;min-width:260px}.ledger-filter-bar input,.ledger-filter-bar select{padding:9px 11px;border:1px solid #d7e3dd;border-radius:8px;background:#fff;color:#31594c;font:inherit}.ledger-help{color:#71817b;font-size:12px;line-height:1.6}.ledger-secondary{display:block;color:#82928b;margin-top:4px;font-size:var(--text-caption)}.ledger-source{display:inline-block;padding:4px 8px;border-radius:12px;white-space:nowrap}.ledger-source.automatic{background:#eef3f6;color:#55717c}.ledger-source.manual{background:#eef7f2;color:#2d6a56}.ledger-source.reversal{background:#fff2e8;color:#8a5d2e}
.inventory-ledger-page .data-table{min-width:1300px}.inventory-ledger-page .data-table th{white-space:nowrap}.inventory-ledger-page .data-table td:nth-child(1),.inventory-ledger-page .data-table td:nth-child(2),.inventory-ledger-page .data-table td:nth-child(4),.inventory-ledger-page .data-table td:nth-child(5){white-space:nowrap}.inventory-ledger-page .data-table td:nth-child(3){min-width:180px}.inventory-ledger-page .data-table td:nth-child(8){min-width:170px}.inventory-ledger-page .data-table th:last-child,.inventory-ledger-page .data-table td:last-child{position:sticky;right:0;background:#fff;box-shadow:-4px 0 8px #143f3308}.inventory-ledger-page .data-table td .tag{white-space:nowrap}
.parameter-filter-bar{display:flex;flex-wrap:wrap;align-items:end;gap:12px;margin:12px 0}.parameter-filter-bar label{display:grid;gap:6px;min-width:0;flex:1 1 300px}.parameter-filter-bar select{width:100%;min-width:0;padding:10px;border:1px solid var(--line);border-radius:8px;background:white}.parameter-list-table{min-width:760px;table-layout:fixed}.parameter-list-table td{white-space:normal;overflow-wrap:anywhere}.parameter-list-table th:first-child{width:230px}.parameter-list-table th:last-child,.parameter-list-table td:last-child{position:sticky;right:0;background:white;width:100px}.parameter-editor{width:min(820px,calc(100vw - 40px))}.parameter-editor .field{min-width:0}.parameter-editor .modal-foot{position:sticky;bottom:0;background:white}
.supplier-list-table th:nth-child(2){width:90px}.supplier-list-table th:nth-child(3){width:230px}.supplier-list-table th:nth-child(4){width:180px}.supplier-list-table th:nth-child(5){width:240px}.supplier-list-table th:nth-child(6){width:220px}.supplier-list-table th:last-child{width:128px}.supplier-lifecycle-btn{width:auto!important;min-width:42px;padding:0 7px!important;color:var(--green-2)}
</style>

<style scoped>
.crm-duplicate-hint{display:grid;gap:5px;color:#8b6428;line-height:1.55}.crm-duplicate-hint small{color:#8b6428}.crm-duplicate-list{display:grid;gap:4px;margin:0;padding-left:18px}.crm-duplicate-list li{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;min-width:0}.crm-duplicate-list li>span{min-width:0;overflow-wrap:anywhere}.crm-duplicate-list a{flex:none;color:#28634f;text-decoration:underline}
</style>

<style scoped>
.supplier-filter-bar{display:grid;grid-template-columns:minmax(220px,2fr) minmax(160px,1fr) minmax(150px,1fr) auto auto;gap:12px;align-items:end;margin:18px 0 10px}.supplier-filter-bar label{display:grid;gap:6px;color:#71817b;font-size:var(--text-caption)}.supplier-filter-bar input,.supplier-filter-bar select{width:100%;min-width:0;min-height:42px;padding:10px 12px;border:1px solid #dce6e1;border-radius:8px;background:#fff;color:#294a41;font:inherit;font-size:var(--text-body)}.supplier-filter-bar input:focus,.supplier-filter-bar select:focus{outline:2px solid #b8d8cb;outline-offset:1px}.supplier-rule-note{color:#567168;font-size:var(--text-body);line-height:1.6}.supplier-list-table{min-width:1150px;table-layout:fixed}.supplier-list-table th:nth-child(1){width:230px}.supplier-list-table th:nth-child(2){width:230px}.supplier-list-table th:nth-child(3){width:180px}.supplier-list-table th:nth-child(4){width:240px}.supplier-list-table th:nth-child(5){width:220px}.supplier-list-table th:last-child{width:108px}.supplier-list-table td{white-space:normal;overflow-wrap:anywhere;vertical-align:top}.supplier-list-table th:last-child,.supplier-list-table td:last-child{position:sticky;right:0;background:#fff;box-shadow:-4px 0 10px #173d3210}.supplier-list-table td:last-child{z-index:2}.supplier-list-table th:last-child{z-index:3}.supplier-secondary{display:block;margin-top:6px;color:#7b8b84;font-size:var(--text-caption);font-weight:400}.supplier-excerpt{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.supplier-editor{width:min(960px,calc(100vw - 40px))}.supplier-editor .modal-body{display:block}.supplier-editor .form-grid{margin-bottom:22px}.supplier-group-title{margin:12px 0;color:#21483d;font-size:var(--text-section)}.supplier-editor .modal-foot{position:sticky;bottom:0;background:#fff;z-index:1}.supplier-editor .field{min-width:0}.supplier-save-error{color:#a44343;padding:12px;border:1px solid #efc6c2;background:#fff9f8;border-radius:8px;overflow-wrap:anywhere}@media(max-width:1100px){.supplier-filter-bar{grid-template-columns:minmax(220px,2fr) minmax(150px,1fr) minmax(150px,1fr)}.supplier-filter-bar .btn{justify-self:start}}@media(max-width:650px){.supplier-filter-bar{grid-template-columns:1fr 1fr}.supplier-filter-bar label:first-child{grid-column:1/-1}.supplier-editor .form-grid{grid-template-columns:1fr}}
.parameter-filter-bar{display:flex;flex-wrap:wrap;align-items:end;gap:12px;margin:12px 0}.parameter-filter-bar label{display:grid;gap:6px;min-width:0;flex:1 1 300px}.parameter-filter-bar select{width:100%;min-width:0;padding:10px;border:1px solid var(--line);border-radius:8px;background:white}.parameter-list-table{min-width:760px;table-layout:fixed}.parameter-list-table td{white-space:normal;overflow-wrap:anywhere}.parameter-list-table th:first-child{width:230px}.parameter-list-table th:last-child,.parameter-list-table td:last-child{position:sticky;right:0;background:white;width:100px}.parameter-editor{width:min(820px,calc(100vw - 40px))}.parameter-editor .field{min-width:0}.parameter-editor .modal-foot{position:sticky;bottom:0;background:white}
</style>

<style scoped>
.certificate-controls{display:flex;flex-wrap:wrap;align-items:end;gap:12px;margin:12px 0}.certificate-controls label{display:grid;gap:6px;min-width:0;flex:1 1 240px}.certificate-controls select{padding:10px;border:1px solid var(--line);border-radius:8px;min-width:0;background:white}.certificate-list-table{min-width:1120px;table-layout:fixed}.certificate-list-table th:first-child{width:240px}.certificate-list-table th:nth-child(2){width:200px}.certificate-list-table th:nth-child(3){width:160px}.certificate-list-table th:last-child,.certificate-list-table td:last-child{position:sticky;right:0;background:white;width:128px}.certificate-list-table td{white-space:normal;overflow-wrap:anywhere}
</style>
