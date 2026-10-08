// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

const mocks = vi.hoisted(() => ({
  api: {
    get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn(),
  },
  listAll: vi.fn(),
  downloadQuoteExport: vi.fn(),
}))

vi.mock('../src/api.js', () => ({
  api: mocks.api,
  listAll: mocks.listAll,
  downloadQuoteExport: mocks.downloadQuoteExport,
  listData: response => response.data.results || response.data,
}))

import App from '../src/App.vue'
import DocumentPage from '../src/views/DocumentPage.vue'
import PurchaseOrderPage from '../src/views/PurchaseOrderPage.vue'
import ResourcePage from '../src/views/ResourcePage.vue'
import { resourceConfigs } from '../src/resourceConfigs.js'
import { installModalNavigationGuard } from '../src/utils/modalNavigation.js'

const orderRows = [
  { id: 4, order_no: 'SO-2026-00004', customer: 5, customer_name: '森爵客户', order_date: '2026-01-04', expected_ship_date: '2026-11-01', status: 'draft', status_display: '草稿', currency: 'USD', total_amount: '40', balance_amount: '40', items: [] },
  { id: 26, order_no: 'SO-2026-00026', customer: 5, customer_name: '森爵客户', order_date: '2026-01-26', expected_ship_date: '2026-11-01', status: 'draft', status_display: '草稿', currency: 'USD', total_amount: '260', balance_amount: '260', items: [{ id: 1, sku: 12, sku_code: 'SKU-CTX-12', quantity: '1' }] },
  { id: 30, order_no: 'SO-2026-00030', customer: 5, customer_name: '森爵客户', order_date: '2026-01-30', expected_ship_date: '2026-10-05', status: 'production', status_display: '生产中', currency: 'USD', total_amount: '300', balance_amount: '300', items: [{ id: 2, sku: 12, sku_code: 'SKU-CTX-12', quantity: '1' }] },
  { id: 31, order_no: 'SO-2026-00031', customer: 5, customer_name: '森爵客户', order_date: '2026-01-31', expected_ship_date: '2026-10-05', status: 'confirmed', status_display: '已确认', currency: 'USD', total_amount: '310', balance_amount: '310', items: [] },
  { id: 32, order_no: 'SO-2026-00032', customer: 5, customer_name: '森爵客户', order_date: '2026-02-01', expected_ship_date: '2026-10-01', status: 'shipped', status_display: '已发货', currency: 'USD', total_amount: '320', balance_amount: '320', items: [] },
  { id: 33, order_no: 'SO-2026-00033', customer: 5, customer_name: '森爵客户', order_date: '2026-02-02', expected_ship_date: '2026-10-01', status: 'completed', status_display: '已完成', currency: 'USD', total_amount: '330', balance_amount: '330', items: [] },
  { id: 34, order_no: 'SO-2026-00034', customer: 5, customer_name: '森爵客户', order_date: '2026-02-03', expected_ship_date: '2026-10-01', status: 'cancelled', status_display: '已取消', currency: 'USD', total_amount: '340', balance_amount: '340', items: [] },
  { id: 35, order_no: 'SO-2026-00035', customer: 5, customer_name: '森爵客户', order_date: '2026-02-04', expected_ship_date: '2026-10-20', status: 'production', status_display: '生产中', currency: 'USD', total_amount: '350', balance_amount: '350', items: [] },
]
const quoteRows = [
  { id: 14, quote_no: 'QT-2026-00020', customer: 5, customer_name: '森爵客户', quote_date: '2026-01-10', updated_at: '2026-03-30T00:00:00Z', status: 'draft', status_display: '草稿', currency: 'USD', total_amount: '14', items: [] },
  { id: 16, quote_no: 'QT-2026-00001-R1', parent_quote: 14, parent_quote_no: 'QT-2026-00020', revision_summary: '排序验收修订版', customer: 5, customer_name: '森爵客户', quote_date: '2026-04-10', updated_at: '2026-04-10T00:00:00Z', status: 'draft', status_display: '草稿', currency: 'USD', total_amount: '16', items: [] },
  { id: 15, quote_no: 'QT-2026-00010', customer: 6, customer_name: '备用客户', quote_date: '2026-02-10', updated_at: '2026-01-10T00:00:00Z', status: 'accepted', status_display: '已接受', currency: 'USD', total_amount: '15', items: [] },
  { id: 17, quote_no: 'QT-2026-00030', customer: 5, customer_name: '森爵客户', quote_date: '2026-03-10', updated_at: '2026-02-20T00:00:00Z', status: 'sent', status_display: '已发送', currency: 'USD', total_amount: '17', items: [] },
]
const customers = [{ id: 5, name: '森爵客户' }, { id: 6, name: '备用客户' }]
const contacts = [{ id: 1, name: '主联系人', customer: 5 }, { id: 2, name: '备用联系人', customer: 6 }]
const suppliers = [{ id: 9, name: '森爵供应商' }]
const orders = [{ id: 8, order_no: 'SO-2026-00008', customer_name: '森爵客户', status: 'confirmed' }]
const movementRows = [
  { id: 55, movement_no: 'IM-CTX-55', sku: 12, sku_code: 'SKU-CTX-12', movement_date: '2026-10-05', type_display: '盘盈入库', signed_quantity: '1', warehouse: '默认仓' },
  { id: 56, movement_no: 'IM-CTX-56', sku: 13, sku_code: 'SKU-CTX-13', movement_date: '2026-10-05', type_display: '盘盈入库', signed_quantity: '2', warehouse: '默认仓' },
]
const EntityDetailStub = defineComponent({
  name: 'EntityDetailModal',
  props: { entity: String, id: [String, Number] },
  emits: ['close'],
  setup(props, { emit }) {
    return () => h('aside', { 'data-test': 'entity-detail' }, [
      h('span', `${props.entity}:${props.id}`),
      h('button', { onClick: () => emit('close') }, '关闭详情'),
    ])
  },
})

const OrderDetailStub = defineComponent({
  name: 'OrderDetailModal',
  props: { id: [String, Number] },
  emits: ['close'],
  setup(props, { emit }) {
    return () => h('aside', { 'data-test': 'order-detail' }, [
      h('span', String(props.id)),
      h('button', { onClick: () => emit('close') }, '关闭详情'),
    ])
  },
})

const QuoteDetailStub = defineComponent({
  name: 'QuoteDetailModal',
  props: { id: [String, Number] },
  emits: ['close'],
  setup(props, { emit }) {
    return () => h('aside', { 'data-test': 'quote-detail' }, [
      h('span', String(props.id)),
      h('button', { onClick: () => emit('close') }, '关闭详情'),
    ])
  },
})

const QuoteEditorStub = defineComponent({
  name: 'QuoteEditorModal',
  props: { quote: Object },
  emits: ['close', 'saved'],
  setup(props, { emit }) {
    return () => h('section', { 'data-test': 'quote-editor' }, [
      h('span', { 'data-test': 'quote-customer' }, String(props.quote?.customer || '')),
      h('button', { onClick: () => emit('close') }, '关闭报价编辑'),
    ])
  },
})

const stubs = {
  AppDialogHost: true,
  SummaryCards: true,
  TradeUnitPicker: true,
  SkuPickerPanel: true,
  SegmentedDateInput: true,
  OrderDraftModal: true,
  QuoteDetailModal: QuoteDetailStub,
  OrderDetailModal: OrderDetailStub,
  QuoteEditorModal: QuoteEditorStub,
  EntityDetailModal: EntityDetailStub,
  SimpleRichTextEditor: true,
  ComboInput: true,
  CategoryMultiPicker: true,
  InventoryMovementCreateModal: true,
  PurchasePaymentModal: true,
  PurchaseCostAllocationModal: true,
  PurchaseSupplierPicker: true,
  ContractAmountAdjustments: true,
}

function followUpRow(id, overrides = {}) {
  return {
    id,
    customer: 5,
    customer_name: '森爵客户',
    contact: null,
    followed_at: '2026-10-05T09:00:00+08:00',
    type: 'email',
    subject: `跟进主题 ${id}`,
    content: '',
    result: '',
    next_action: '',
    next_follow_up: '2026-10-06',
    owner: '开发身份',
    attachments: [],
    ...overrides,
  }
}

const followUpRows = [
  followUpRow(10, { customer_name: 'Alpha Lighting', subject: 'ABC annual forecast', next_follow_up: '2026-10-05' }),
  followUpRow(11, { customer: 6, customer_name: 'Beta Lighting', subject: 'Beta overdue task', next_follow_up: '2026-10-01' }),
  followUpRow(12, { customer_name: 'Alpha Lighting', subject: 'Historical future plan', next_follow_up: '2026-10-20' }),
]

function responseFor(url) {
  if (url === '/session/current-operator/') return { data: { name: '开发身份', role: '开发超级管理员', development_superadmin: true, has_all_permissions: true } }
  const editMatch = url.match(/^\/(follow-ups|orders|quotes)\/(\d+)\/$/)
  if (editMatch) {
    const [, endpoint, rawId] = editMatch
    const id = Number(rawId)
    if (endpoint === 'follow-ups') return { data: followUpRow(id) }
    if (endpoint === 'orders') return { data: orderRows.find(row => row.id === id) || { ...orderRows[0], id } }
    return { data: quoteRows.find(row => row.id === id) || { ...quoteRows[0], id } }
  }
  return { data: [] }
}

function rowsFor(url, params = {}) {
  if (url === '/orders/') {
    if (!Object.keys(params).length) return orders
    const search = String(params.search || '').toLowerCase()
    return orderRows.filter(row =>
      (!search || row.order_no.toLowerCase().includes(search)) &&
      (!params.sku || row.items.some(item => String(item.sku) === String(params.sku))) &&
      (!params.status || row.status === params.status) &&
      (!params.customer || String(row.customer) === String(params.customer)) &&
      (!params.todo || (params.todo === 'unshipped' && ['confirmed', 'production'].includes(row.status)) ||
        (params.todo === 'due' && ['confirmed', 'production'].includes(row.status) && row.expected_ship_date && row.expected_ship_date <= '2026-10-05')),
    )
  }
  if (url === '/quotes/') {
    const search = String(params.search || '').toLowerCase()
    const matchingRows = quoteRows.filter(row =>
      (!search || row.quote_no.toLowerCase().includes(search)) &&
      (!params.status || row.status === params.status) &&
      (!params.customer || String(row.customer) === String(params.customer)),
    )
    const ordering = String(params.ordering || '-updated_at')
    const descending = ordering.startsWith('-')
    const field = descending ? ordering.slice(1) : ordering
    return matchingRows.sort((a, b) => {
      const comparison = String(a[field] || '').localeCompare(String(b[field] || ''))
      return (descending ? -comparison : comparison) || a.id - b.id
    })
  }
  if (url === '/follow-ups/') {
    const search = String(params.search || '').toLowerCase()
    return followUpRows.filter(row =>
      (params.due !== 'true' || (row.next_follow_up && row.next_follow_up <= '2026-10-05')) &&
      (!params.customer || String(row.customer) === String(params.customer)) &&
      (!search || [row.subject, row.content, row.customer_name, row.owner].some(value => String(value || '').toLowerCase().includes(search))),
    )
  }
  if (url === '/customers/') return customers
  if (url === '/contacts/') return contacts
  if (url === '/suppliers/') return suppliers
  if (url === '/purchase-orders/') return []
  if (url === '/skus/') return []
  if (url === '/inventory-movements/') return movementRows.filter(row => !params.sku || String(row.sku) === String(params.sku))
  if (url === '/orders/options/') return orders
  return []
}

let wrapper
let router

async function mountAt(path, pageType) {
  const StubPage = defineComponent({ template: '<div />' })
  const routes = [
    { path: '/', component: StubPage, meta: { title: 'Home', eyebrow: 'Home' } },
    { path: '/orders', component: DocumentPage, props: { type: 'orders' }, meta: { title: 'Orders', eyebrow: 'Sales' } },
    { path: '/quotes', component: DocumentPage, props: { type: 'quotes' }, meta: { title: 'Quotes', eyebrow: 'Sales' } },
    { path: '/customers', component: ResourcePage, props: { config: resourceConfigs.customers }, meta: { title: 'Customers', eyebrow: 'CRM' } },
    { path: '/follow-ups', component: ResourcePage, props: { config: resourceConfigs['follow-ups'] }, meta: { title: 'Follow ups', eyebrow: 'CRM' } },
    { path: '/purchase-orders', component: PurchaseOrderPage, meta: { title: 'Purchases', eyebrow: 'Procurement' } },
    { path: '/inventory-movements', component: ResourcePage, props: { config: resourceConfigs['inventory-movements'] }, meta: { title: 'Inventory', eyebrow: 'Inventory' } },
    { path: '/:pathMatch(.*)*', component: StubPage, meta: { title: 'Stub', eyebrow: 'Stub' } },
  ]
  router = createRouter({ history: createMemoryHistory(), routes })
  installModalNavigationGuard(router)
  await router.push(path)
  await router.isReady()
  wrapper = mount(App, { global: { plugins: [router], stubs, directives: { 'money-input': {} } } })
  await flushPromises()
  return { wrapper, router, pageType }
}

beforeEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
  mocks.api.get.mockImplementation(async url => responseFor(url))
  mocks.listAll.mockImplementation(async (url, config = {}) => rowsFor(url, config.params || {}))
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  router = undefined
  vi.useRealTimers()
})


describe('Quote module UX', () => {
 const requestCalls=()=>mocks.listAll.mock.calls.filter(([url])=>url==='/quotes/')
 it('counts roots, all versions, draft/sent and accepted without currency aggregation',async()=>{quoteRows[2].currency='EUR';quoteRows[2].total_amount='9000';await mountAt('/quotes');expect(wrapper.findAll('.quote-metrics article span').map(e=>e.text())).toEqual(['报价项目','报价版本','进行中','已接受']);expect(wrapper.findAll('.quote-metrics article strong').map(e=>e.text())).toEqual(['3','4','3','1']);expect(wrapper.get('.quote-metrics').text()).not.toMatch(/USD|已接受金额/);expect(wrapper.get('.quote-metrics').text()).toContain('含所有修订版')})
 it('root with revisions opens exact detail; chevron only expands; revision opens exact detail',async()=>{await mountAt('/quotes');await wrapper.findAll('.quote-tree-row').find(r=>r.text().includes('QT-2026-00020')).trigger('click');await flushPromises();expect(router.currentRoute.value.query.detail).toBe('14');await wrapper.get('[data-test="quote-detail"] button').trigger('click');await flushPromises();await wrapper.get('button[aria-label="展开 QT-2026-00020 的修订报价"]').trigger('click');expect(wrapper.find('[data-test="quote-detail"]').exists()).toBe(false);expect(router.currentRoute.value.query.detail).toBeUndefined();await wrapper.findAll('.quote-tree-row').find(r=>r.text().includes('QT-2026-00001-R1')).trigger('click');await flushPromises();expect(router.currentRoute.value.query.detail).toBe('16')})
 it('root without revisions opens exact detail',async()=>{await mountAt('/quotes');await wrapper.findAll('.quote-tree-row').find(r=>r.text().includes('QT-2026-00010')).trigger('click');await flushPromises();expect(router.currentRoute.value.query.detail).toBe('15')})
 it('direct URL activates filters and sends exact route params after remount',async()=>{const url='/quotes?status=sent&customer=5&ordering=-quote_date';await mountAt(url);for(let attempt=0;attempt<2;attempt++){expect(wrapper.get('[aria-label="按报价状态筛选"]').element.value).toBe('sent');expect(wrapper.get('[aria-label="按客户筛选"]').element.value).toBe('5');expect(wrapper.get('[aria-label="报价排序"]').element.value).toBe('-quote_date');expect(requestCalls().at(-1)[1].params).toMatchObject({status:'sent',customer:'5',ordering:'-quote_date'});if(!attempt){wrapper.unmount();await mountAt(url)}}})
 it('filter changes push query once, preserve detail/unrelated context and keep master customer choices',async()=>{await mountAt('/quotes?detail=14&scope=crm');for(const [label,value,key] of [['按报价状态筛选','sent','status'],['按客户筛选','5','customer'],['报价排序','quote_date','ordering']]){const before=requestCalls().length;await wrapper.get(`select[aria-label="${label}"]`).setValue(value);await flushPromises();expect(router.currentRoute.value.query[key]).toBe(value);expect(router.currentRoute.value.query).toMatchObject({detail:'14',scope:'crm'});expect(requestCalls()).toHaveLength(before+1)}expect(wrapper.get('[aria-label="按客户筛选"]').findAll('option').map(o=>o.text())).toEqual(['全部客户','备用客户','森爵客户']);expect(wrapper.get('[data-test="quote-detail"]').text()).toContain('14')})
 it('reset removes only quote filter query and default ordering returns',async()=>{await mountAt('/quotes?status=sent&customer=5&ordering=quote_date&detail=14&scope=crm');await wrapper.get('button.filter-reset').trigger('click');await flushPromises();expect(router.currentRoute.value.query).toEqual({detail:'14',scope:'crm'});expect(requestCalls().at(-1)[1].params.ordering).toBe('-updated_at')})
 it('reset preserves create, edit and returnTo query keys',async()=>{await mountAt('/quotes?status=sent&customer=5&ordering=quote_date&create=1&edit=14&returnTo=%2Fcustomers%3Fdetail%3D5');await wrapper.get('button.filter-reset').trigger('click');await flushPromises();expect(router.currentRoute.value.query).toMatchObject({create:'1',edit:'14',returnTo:'/customers?detail=5'});expect(router.currentRoute.value.query.status).toBeUndefined()})
})
