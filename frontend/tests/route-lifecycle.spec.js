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

const orderRows = [
  { id: 4, order_no: 'SO-2026-00004', customer: 5, customer_name: '森爵客户', order_date: '2026-01-04', status: 'draft', currency: 'USD', total_amount: '40', balance_amount: '40', items: [] },
  { id: 26, order_no: 'SO-2026-00026', customer: 5, customer_name: '森爵客户', order_date: '2026-01-26', status: 'draft', currency: 'USD', total_amount: '260', balance_amount: '260', items: [] },
]
const quoteRows = [{ id: 14, quote_no: 'QT-2026-00014', customer: 5, customer_name: '森爵客户', quote_date: '2026-01-14', status: 'draft', currency: 'USD', total_amount: '14', items: [] }]
const customers = [{ id: 5, name: '森爵客户' }]
const suppliers = [{ id: 9, name: '森爵供应商' }]
const orders = [{ id: 8, order_no: 'SO-2026-00008', customer_name: '森爵客户', status: 'confirmed' }]

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
  EntityDetailModal: true,
  SimpleRichTextEditor: true,
  ComboInput: true,
  CategoryMultiPicker: true,
  InventoryMovementCreateModal: true,
  PurchasePaymentModal: true,
  PurchaseCostAllocationModal: true,
  PurchaseSupplierPicker: true,
  ContractAmountAdjustments: true,
}

function followUpRow(id) {
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
  }
}

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
    return orderRows.filter(row => !search || row.order_no.toLowerCase().includes(search))
  }
  if (url === '/quotes/') return quoteRows
  if (url === '/follow-ups/') return [followUpRow(10), followUpRow(11)]
  if (url === '/customers/') return customers
  if (url === '/suppliers/') return suppliers
  if (url === '/purchase-orders/') return []
  if (url === '/skus/') return []
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
    { path: '/follow-ups', component: ResourcePage, props: { config: resourceConfigs['follow-ups'] }, meta: { title: 'Follow ups', eyebrow: 'CRM' } },
    { path: '/purchase-orders', component: PurchaseOrderPage, meta: { title: 'Purchases', eyebrow: 'Procurement' } },
  ]
  router = createRouter({ history: createMemoryHistory(), routes })
  await router.push(path)
  await router.isReady()
  wrapper = mount(App, { global: { plugins: [router], stubs } })
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
    await router.push('/orders?detail=26')
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

  it('opens quote detail from a direct query URL', async () => {
    await mountAt('/quotes?detail=14', 'quotes')
    expect(wrapper.find('[data-test="quote-detail"]').text()).toContain('14')
  })

  it('restores the order detail after the app remounts at the same URL', async () => {
    await mountAt('/orders?detail=4', 'orders')
    expect(wrapper.find('[data-test="order-detail"]').text()).toContain('4')

    wrapper.unmount()
    wrapper = mount(App, { global: { plugins: [router], stubs } })
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
