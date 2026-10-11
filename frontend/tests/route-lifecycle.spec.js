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
import { resolveDialog } from '../src/dialogs'
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
  const draftMatch = url.match(/^\/quotes\/(\d+)\/order-draft\/$/)
  if (draftMatch) {
    const quote = quoteRows.find(row => row.id === Number(draftMatch[1]))
    return { data: { ...quote, quote: quote.id, order_date: '2026-10-10', expected_ship_date: '2026-10-20', exchange_rate: '7.2', shipping_fee: '0', discount: '0', notes: '', items: [] } }
  }
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

describe('query route lifecycle', () => {
  it('keeps the orders page, search input, filtered rows, and scroll element through open and close', async () => {
    vi.useFakeTimers()
    await mountAt('/orders', 'orders')
    const search = wrapper.find('input[placeholder*="搜索订单号"]')
    const searchElement = search.element
    await search.setValue('SO-2026-00026')
    await vi.advanceTimersByTimeAsync(301)
    await flushPromises()

    const table = wrapper.find('.table-wrap').element
    table.scrollTop = 123
    const listCallsBeforeDetail = mocks.listAll.mock.calls.filter(([url]) => url === '/orders/').length
    await router.push({ path: '/orders', query: { ...router.currentRoute.value.query, detail: '26' } })
    await flushPromises()

    expect(wrapper.find('[data-test="order-detail"]').text()).toContain('26')
    expect(wrapper.find('input[placeholder*="搜索订单号"]').element).toBe(searchElement)
    expect(searchElement.value).toBe('SO-2026-00026')
    expect(wrapper.find('.table-wrap').element).toBe(table)
    expect(table.scrollTop).toBe(123)
    expect(wrapper.text()).toContain('SO-2026-00026')
    expect(mocks.listAll.mock.calls.filter(([url]) => url === '/orders/')).toHaveLength(listCallsBeforeDetail)

    await wrapper.find('[data-test="order-detail"] button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query.detail).toBeUndefined()
    expect(searchElement.value).toBe('SO-2026-00026')
    expect(wrapper.find('.table-wrap').element).toBe(table)
    expect(table.scrollTop).toBe(123)
  })

  it('switches order details for direct URLs and Back/Forward without reloading the page', async () => {
    await mountAt('/orders?detail=4', 'orders')
    expect(wrapper.find('[data-test="order-detail"]').text()).toContain('4')
    await router.push('/orders?detail=5')
    await flushPromises()
    expect(wrapper.find('[data-test="order-detail"]').text()).toContain('5')
    await router.back()
    await flushPromises()
    expect(router.currentRoute.value.query.detail).toBe('4')
    expect(wrapper.find('[data-test="order-detail"]').text()).toContain('4')
    await router.forward()
    await flushPromises()
    expect(router.currentRoute.value.query.detail).toBe('5')
    expect(wrapper.find('[data-test="order-detail"]').text()).toContain('5')
  })

  it('filters Orders by SKU and preserves SKU context when closing detail or clearing the context', async () => {
    await mountAt('/orders?sku=12&status=production&todo=unshipped&detail=30', 'orders')
    const orderCalls = mocks.listAll.mock.calls.filter(([url]) => url === '/orders/')
    expect(orderCalls.at(-1)[1].params).toMatchObject({ sku: '12', status: 'production', todo: 'unshipped' })
    expect(wrapper.text()).toContain('当前 SKU 筛选：SKU-CTX-12')
    expect(wrapper.text()).toContain('SO-2026-00030')
    expect(wrapper.text()).not.toContain('SO-2026-00026')

    await wrapper.find('[data-test="order-detail"] button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ sku: '12', status: 'production', todo: 'unshipped' })
    await wrapper.find('.sku-context-banner button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ status: 'production', todo: 'unshipped' })
    expect(mocks.listAll.mock.calls.filter(([url]) => url === '/orders/').at(-1)[1].params).not.toHaveProperty('sku')
  })

  it('filters Inventory Movements by SKU and preserves unrelated state on detail close and context clear', async () => {
    await mountAt('/inventory-movements?sku=12&source_type=manual&detail=55', 'movements')
    const movementCalls = mocks.listAll.mock.calls.filter(([url]) => url === '/inventory-movements/')
    expect(movementCalls.at(-1)[1].params).toMatchObject({ sku: '12', source_type: 'manual' })
    expect(wrapper.text()).toContain('当前 SKU 筛选：SKU-CTX-12')
    expect(wrapper.text()).toContain('IM-CTX-55')
    expect(wrapper.text()).not.toContain('IM-CTX-56')

    await wrapper.find('[data-test="entity-detail"] button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ sku: '12', source_type: 'manual' })
    await wrapper.find('.sku-context-banner button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ source_type: 'manual' })
  })

  it('loads direct current-due URLs, opens details, and clears only due while preserving customer context', async () => {
    await mountAt('/follow-ups?due=true&customer=5&detail=10', 'follow-ups')
    const calls = mocks.listAll.mock.calls.filter(([url]) => url === '/follow-ups/')
    expect(calls.at(-1)[1].params).toMatchObject({ due: 'true', customer: '5', search: '' })
    expect(calls.at(-1)[1].params).not.toHaveProperty('detail')
    expect(wrapper.text()).toContain('当前筛选：今日及逾期待跟进')
    expect(wrapper.text()).toContain('ABC annual forecast')
    expect(wrapper.text()).not.toContain('Historical future plan')
    expect(wrapper.find('[data-test="entity-detail"]').text()).toContain('follow-ups:10')

    await wrapper.find('[data-test="entity-detail"] button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ due: 'true', customer: '5' })
    expect(wrapper.text()).toContain('当前筛选：今日及逾期待跟进')

    await wrapper.find('.follow-up-due-context button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ customer: '5' })
    expect(mocks.listAll.mock.calls.filter(([url]) => url === '/follow-ups/').at(-1)[1].params).toMatchObject({ customer: '5' })
    expect(mocks.listAll.mock.calls.filter(([url]) => url === '/follow-ups/').at(-1)[1].params).not.toHaveProperty('due')
    expect(wrapper.text()).toContain('Historical future plan')
  })

  it('combines local search with due=true and leaves due active when search is cleared', async () => {
    vi.useFakeTimers()
    await mountAt('/follow-ups?due=true', 'follow-ups')
    expect(wrapper.text()).toContain('当前筛选：今日及逾期待跟进')
    expect(wrapper.text()).toContain('ABC annual forecast')
    expect(wrapper.text()).toContain('Beta overdue task')
    expect(wrapper.text()).not.toContain('Historical future plan')

    const search = wrapper.find('input[placeholder="搜索当前列表..."]')
    await search.setValue('Alpha')
    await vi.advanceTimersByTimeAsync(301)
    await flushPromises()
    let request = mocks.listAll.mock.calls.filter(([url]) => url === '/follow-ups/').at(-1)[1]
    expect(request.params).toMatchObject({ due: 'true', search: 'Alpha' })
    expect(wrapper.text()).toContain('ABC annual forecast')
    expect(wrapper.text()).not.toContain('Beta overdue task')

    await search.setValue('')
    await vi.advanceTimersByTimeAsync(301)
    await flushPromises()
    request = mocks.listAll.mock.calls.filter(([url]) => url === '/follow-ups/').at(-1)[1]
    expect(request.params).toMatchObject({ due: 'true', search: '' })
    expect(wrapper.text()).toContain('当前筛选：今日及逾期待跟进')
    expect(wrapper.text()).toContain('Beta overdue task')
    expect(wrapper.text()).not.toContain('Historical future plan')
  })

  it('restores current-due state through Back and Forward and leaves the ordinary list historical', async () => {
    await mountAt('/follow-ups', 'follow-ups')
    expect(wrapper.text()).not.toContain('当前筛选：今日及逾期待跟进')
    expect(wrapper.text()).toContain('Historical future plan')
    expect(mocks.listAll.mock.calls.filter(([url]) => url === '/follow-ups/').at(-1)[1].params).not.toHaveProperty('due')

    await router.push('/follow-ups?due=true')
    await flushPromises()
    expect(router.currentRoute.value.query.due).toBe('true')
    expect(wrapper.text()).toContain('当前筛选：今日及逾期待跟进')
    expect(wrapper.text()).not.toContain('Historical future plan')
    expect(mocks.listAll.mock.calls.filter(([url]) => url === '/follow-ups/').at(-1)[1].params.due).toBe('true')

    await router.back()
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/follow-ups')
    expect(wrapper.text()).not.toContain('当前筛选：今日及逾期待跟进')
    expect(wrapper.text()).toContain('Historical future plan')

    await router.forward()
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/follow-ups?due=true')
    expect(wrapper.text()).toContain('当前筛选：今日及逾期待跟进')
    expect(wrapper.text()).not.toContain('Historical future plan')
    expect(mocks.listAll.mock.calls.filter(([url]) => url === '/follow-ups/').at(-1)[1].params.due).toBe('true')
  })

  it('opens quote detail from a direct query URL', async () => {
    await mountAt('/quotes?detail=14', 'quotes')
    expect(wrapper.find('[data-test="quote-detail"]').text()).toContain('14')
  })

  it('restores the order detail after the app remounts at the same URL', async () => {
    await mountAt('/orders?detail=4', 'orders')
    expect(wrapper.find('[data-test="order-detail"]').text()).toContain('4')

    wrapper.unmount()
    wrapper = mount(App, { global: { plugins: [router], stubs, directives: { 'money-input': {} } } })
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/orders?detail=4')
    expect(wrapper.find('[data-test="order-detail"]').text()).toContain('4')
  })

  it('opens create query dynamically, prefills customer, and preserves customer/status context on close', async () => {
    await mountAt('/quotes', 'quotes')
    await router.push('/quotes?create=1&customer=5&status=accepted')
    await flushPromises()
    expect(wrapper.find('[data-test="quote-editor"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="quote-customer"]').text()).toBe('5')
    await wrapper.find('[data-test="quote-editor"] button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ customer: '5', status: 'accepted' })
    expect(router.currentRoute.value.query.create).toBeUndefined()
  })

  it('updates only order create prefills when customer or quote query values change', async () => {
    await mountAt('/orders', 'orders')
    const search = wrapper.find('input[placeholder*="搜索订单号"]')
    await search.setValue('SO-2026-00026')
    await vi.waitFor(() => expect(wrapper.text()).toContain('SO-2026-00026'))

    await router.push('/orders?create=1&customer=5&quote=14')
    await flushPromises()
    const customerSelect = wrapper.find('.modal select')
    const quoteSelect = wrapper.findAll('.modal select')[1]
    expect(customerSelect.element.value).toBe('5')
    expect(quoteSelect.element.value).toBe('14')
    await router.push('/orders?create=1&customer=6&quote=15')
    await flushPromises()
    expect(customerSelect.element.value).toBe('6')
    expect(quoteSelect.element.value).toBe('15')
    expect(search.element.value).toBe('SO-2026-00026')
  })

  it('updates a route-controlled quote customer prefill without reopening unrelated manual modals', async () => {
    await mountAt('/quotes', 'quotes')
    await router.push('/quotes?create=1&customer=5')
    await flushPromises()
    expect(wrapper.find('[data-test="quote-customer"]').text()).toBe('5')
    await router.push('/quotes?create=1&customer=6')
    await flushPromises()
    expect(wrapper.find('[data-test="quote-customer"]').text()).toBe('6')
  })

  it('updates configured ResourcePage prefills only for route-controlled create modals', async () => {
    await mountAt('/follow-ups', 'resources')
    await router.push('/follow-ups?create=1&customer=5&contact=1')
    await flushPromises()
    let selects = wrapper.findAll('.modal select')
    expect(selects[0].element.value).toBe('5')
    expect(selects[1].element.value).toBe('1')

    await router.push('/follow-ups?create=1&customer=6&contact=2')
    await flushPromises()
    selects = wrapper.findAll('.modal select')
    expect(selects[0].element.value).toBe('6')
    expect(selects[1].element.value).toBe('2')

    await wrapper.find('.modal-backdrop button').trigger('click')
    await flushPromises()
    await router.replace('/follow-ups')
    await flushPromises()
    await wrapper.find('.page-head .btn-primary').trigger('click')
    await flushPromises()
    selects = wrapper.findAll('.modal select')
    await selects[0].setValue('5')
    const navigation = router.push('/follow-ups?customer=5')
    await flushPromises()
    resolveDialog(false)
    await navigation
    await flushPromises()
    expect(wrapper.findAll('.modal select')[0].element.value).toBe('5')
  })

  it('uses the production modal guard to retain origin context through modal history and close', async () => {
    await mountAt('/customers?detail=5&status=active', 'customers')
    await router.push({ path: '/purchase-orders', query: { create: '1', order: '8' } })
    await flushPromises()
    expect(router.currentRoute.value.query.returnTo).toBe('/customers?detail=5&status=active')

    await router.back()
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/customers?detail=5&status=active')
    await router.forward()
    await flushPromises()
    expect(router.currentRoute.value.query.returnTo).toBe('/customers?detail=5&status=active')

    await wrapper.find('.purchase-create-modal button[aria-label="关闭"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/customers?detail=5&status=active')
  })

  it('preserves FollowUp edit returnTo through Back/Forward and removes stale action query on close', async () => {
    await mountAt('/follow-ups?detail=10&customer=5', 'resources')
    const returnTo = '/follow-ups?detail=10&customer=5'
    await router.push({ path: '/follow-ups', query: { edit: '10', returnTo } })
    await flushPromises()
    expect(router.currentRoute.value.query.returnTo).toBe(returnTo)
    expect(wrapper.find('.modal-backdrop').exists()).toBe(true)

    await router.back()
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe(returnTo)
    await router.forward()
    await flushPromises()
    expect(router.currentRoute.value.query.edit).toBe('10')
    expect(router.currentRoute.value.query.returnTo).toBe(returnTo)

    await wrapper.find('.modal-backdrop button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe(returnTo)
    expect(router.currentRoute.value.query.edit).toBeUndefined()
    expect(router.currentRoute.value.query.returnTo).toBeUndefined()
  })

  it('leaves a directly opened modal without an invented predecessor', async () => {
    await mountAt('/purchase-orders?create=1&order=8', 'purchases')
    expect(router.currentRoute.value.query.returnTo).toBeUndefined()
    await wrapper.find('.purchase-create-modal button[aria-label="关闭"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/purchase-orders?order=8')
  })

  it('opens edit queries dynamically and updates the same modal when the id changes', async () => {
    await mountAt('/follow-ups', 'resources')
    await router.push('/follow-ups?edit=10')
    await flushPromises()
    expect(wrapper.find('.modal-backdrop').exists()).toBe(true)
    expect(wrapper.findAll('.modal input').map(input => input.element.value)).toContain('跟进主题 10')

    await router.push('/follow-ups?edit=11')
    await flushPromises()
    expect(wrapper.findAll('.modal input').map(input => input.element.value)).toContain('跟进主题 11')
    expect(mocks.api.get).toHaveBeenCalledWith('/follow-ups/11/')
  })

  it('dynamically opens purchase create with order and supplier prefills and retains context on close', async () => {
    await mountAt('/purchase-orders', 'purchases')
    await router.push('/purchase-orders?create=1&order=8')
    await flushPromises()
    let selects = wrapper.findAll('.purchase-create-modal select')
    expect(selects[1].element.value).toBe('8')

    await router.push('/purchase-orders?create=1&supplier=9')
    await flushPromises()
    selects = wrapper.findAll('.purchase-create-modal select')
    expect(selects[0].element.value).toBe('9')
    expect(selects[1].element.value).toBe('')

    await wrapper.find('.purchase-create-modal button[aria-label="关闭"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query.create).toBeUndefined()
    expect(router.currentRoute.value.query.supplier).toBe('9')
    expect(wrapper.find('.purchase-create-modal').exists()).toBe(false)
  })
})

describe('sales document list filters', () => {
  it('restores order status and todo controls from a direct filtered URL after remount', async () => {
    await mountAt('/orders?status=production&todo=due&customer=5&quote=14', 'orders')
    const status = wrapper.find('select[aria-label="按订单状态筛选"]')
    const todo = wrapper.find('select[aria-label="按订单待办筛选"]')
    expect(status.element.value).toBe('production')
    expect(todo.element.value).toBe('due')
    expect(wrapper.findAll('.data-table tbody tr').map(row => row.find('.primary-cell').text())).toEqual(['SO-2026-00030'])
    expect(mocks.listAll.mock.calls.filter(([url]) => url === '/orders/').at(-1)[1].params).toMatchObject({
      status: 'production', todo: 'due', customer: '5', quote: '14',
    })

    wrapper.unmount()
    wrapper = mount(App, { global: { plugins: [router], stubs, directives: { 'money-input': {} } } })
    await flushPromises()
    expect(wrapper.find('select[aria-label="按订单状态筛选"]').element.value).toBe('production')
    expect(wrapper.find('select[aria-label="按订单待办筛选"]').element.value).toBe('due')
    expect(wrapper.findAll('.data-table tbody tr').map(row => row.find('.primary-cell').text())).toEqual(['SO-2026-00030'])
  })

  it('keeps order URL, controls, and rows synchronized through Back and Forward', async () => {
    await mountAt('/orders', 'orders')
    await wrapper.find('select[aria-label="按订单状态筛选"]').setValue('production')
    await flushPromises()
    expect(router.currentRoute.value.query.status).toBe('production')
    expect(wrapper.findAll('.data-table tbody tr').map(row => row.find('.primary-cell').text())).toEqual(['SO-2026-00030', 'SO-2026-00035'])

    await wrapper.find('select[aria-label="按订单待办筛选"]').setValue('due')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ status: 'production', todo: 'due' })
    expect(wrapper.findAll('.data-table tbody tr').map(row => row.find('.primary-cell').text())).toEqual(['SO-2026-00030'])

    await router.back()
    await flushPromises()
    expect(router.currentRoute.value.query.status).toBe('production')
    expect(router.currentRoute.value.query.todo).toBeUndefined()
    expect(wrapper.find('select[aria-label="按订单待办筛选"]').element.value).toBe('')
    expect(wrapper.findAll('.data-table tbody tr')).toHaveLength(2)

    await router.forward()
    await flushPromises()
    expect(router.currentRoute.value.query.todo).toBe('due')
    expect(wrapper.find('select[aria-label="按订单待办筛选"]').element.value).toBe('due')
    expect(wrapper.findAll('.data-table tbody tr')).toHaveLength(1)
  })

  it('combines local order search with a route todo filter', async () => {
    vi.useFakeTimers()
    await mountAt('/orders', 'orders')
    const search = wrapper.find('input[placeholder*="搜索订单号"]')
    await search.setValue('SO-2026-00030')
    await vi.advanceTimersByTimeAsync(301)
    await flushPromises()
    await wrapper.find('select[aria-label="按订单待办筛选"]').setValue('due')
    await flushPromises()

    expect(mocks.listAll.mock.calls.filter(([url]) => url === '/orders/').at(-1)[1].params).toMatchObject({
      search: 'SO-2026-00030', todo: 'due',
    })
    expect(wrapper.findAll('.data-table tbody tr').map(row => row.find('.primary-cell').text())).toEqual(['SO-2026-00030'])
  })

  it('preserves search and route filters while opening and closing an order detail', async () => {
    vi.useFakeTimers()
    await mountAt('/orders', 'orders')
    const search = wrapper.find('input[placeholder*="搜索订单号"]')
    await search.setValue('SO-2026-00030')
    await vi.advanceTimersByTimeAsync(301)
    await wrapper.find('select[aria-label="按订单状态筛选"]').setValue('production')
    await flushPromises()
    await wrapper.find('select[aria-label="按订单待办筛选"]').setValue('due')
    await flushPromises()
    const listCallsBeforeDetail = mocks.listAll.mock.calls.filter(([url]) => url === '/orders/').length

    await wrapper.find('.data-table tbody tr').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ status: 'production', todo: 'due', detail: '30' })
    expect(wrapper.find('[data-test="order-detail"]').text()).toContain('30')
    expect(search.element.value).toBe('SO-2026-00030')
    expect(wrapper.find('select[aria-label="按订单状态筛选"]').element.value).toBe('production')
    expect(wrapper.find('select[aria-label="按订单待办筛选"]').element.value).toBe('due')
    expect(mocks.listAll.mock.calls.filter(([url]) => url === '/orders/')).toHaveLength(listCallsBeforeDetail)

    await wrapper.find('[data-test="order-detail"] button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query.detail).toBeUndefined()
    expect(router.currentRoute.value.query).toMatchObject({ status: 'production', todo: 'due' })
    expect(search.element.value).toBe('SO-2026-00030')
    expect(wrapper.findAll('.data-table tbody tr').map(row => row.find('.primary-cell').text())).toEqual(['SO-2026-00030'])
  })

  it('resets only order search and filters while preserving customer, quote, and detail context', async () => {
    vi.useFakeTimers()
    await mountAt('/orders?status=production&todo=unshipped&customer=5&quote=14&detail=30', 'orders')
    const search = wrapper.find('input[placeholder*="搜索订单号"]')
    await search.setValue('SO-2026')
    await wrapper.find('button.filter-reset').trigger('click')
    await flushPromises()

    expect(search.element.value).toBe('')
    expect(router.currentRoute.value.query).toMatchObject({ customer: '5', quote: '14', detail: '30' })
    expect(router.currentRoute.value.query.status).toBeUndefined()
    expect(router.currentRoute.value.query.todo).toBeUndefined()
    expect(wrapper.find('select[aria-label="按订单状态筛选"]').element.value).toBe('')
    expect(wrapper.find('select[aria-label="按订单待办筛选"]').element.value).toBe('')
  })

  it('keeps quote search, status, customer, sorting, and reset behavior unchanged', async () => {
    vi.useFakeTimers()
    await mountAt('/quotes', 'quotes')
    const search = wrapper.find('input[placeholder*="搜索报价单号"]')
    await search.setValue('QT-2026')
    await vi.advanceTimersByTimeAsync(301)
    await flushPromises()
    await wrapper.find('select[aria-label="按报价状态筛选"]').setValue('accepted')
    await flushPromises()
    await wrapper.find('select[aria-label="按客户筛选"]').setValue('6')
    await flushPromises()
    await wrapper.find('select[aria-label="报价排序"]').setValue('quote_date')
    await flushPromises()

    expect(mocks.listAll.mock.calls.filter(([url]) => url === '/quotes/').at(-1)[1].params).toMatchObject({
      search: 'QT-2026', status: 'accepted', customer: '6', ordering: 'quote_date',
    })
    expect(wrapper.findAll('.quote-tree-row .quote-tree-copy strong').map(node => node.text())).toEqual(['QT-2026-00010'])
    await wrapper.find('button.filter-reset').trigger('click')
    await flushPromises()
    expect(search.element.value).toBe('')
    expect(wrapper.find('select[aria-label="按报价状态筛选"]').element.value).toBe('')
    expect(wrapper.find('select[aria-label="按客户筛选"]').element.value).toBe('')
    expect(wrapper.find('select[aria-label="报价排序"]').element.value).toBe('-updated_at')
    expect(wrapper.findAll('.quote-tree-row .quote-tree-copy strong').map(node => node.text())).toEqual([
      'QT-2026-00020', 'QT-2026-00030', 'QT-2026-00010',
    ])
  })

  it('renders each backend Quote ordering while keeping revisions nested and expandable', async () => {
    await mountAt('/quotes', 'quotes')
    const rootA = 'QT-2026-00020'
    const rootB = 'QT-2026-00010'
    const rootC = 'QT-2026-00030'
    const revision = 'QT-2026-00001-R1'
    const visibleOrder = () => wrapper.findAll('.quote-tree-row .quote-tree-copy strong').map(node => node.text())

    await wrapper.find(`button[aria-label="展开 ${rootA} 的修订报价"]`).trigger('click')
    expect(visibleOrder()).toEqual([rootA, revision, rootC, rootB])

    const sort = wrapper.find('select[aria-label="报价排序"]')
    for (const [ordering, expected] of [
      ['updated_at', [rootB, rootC, rootA, revision]],
      ['-quote_date', [rootC, rootB, rootA, revision]],
      ['quote_date', [rootA, revision, rootB, rootC]],
      ['-updated_at', [rootA, revision, rootC, rootB]],
    ]) {
      await sort.setValue(ordering)
      await flushPromises()
      expect(visibleOrder()).toEqual(expected)
    }

    await wrapper.find('button[aria-label="收起 QT-2026-00020 的修订报价"]').trigger('click')
    expect(visibleOrder()).toEqual([rootA, rootC, rootB])
  })
})
