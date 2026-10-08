// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'

const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }, listAll: vi.fn() }))
vi.mock('../src/api.js', () => ({ ...mocks, downloadQuoteExport: vi.fn(), listData: r => r.data?.results || r.data || [] }))
import DocumentPage from '../src/views/DocumentPage.vue'
import ResourcePage from '../src/views/ResourcePage.vue'
import PurchaseOrderPage from '../src/views/PurchaseOrderPage.vue'
import { resourceConfigs } from '../src/resourceConfigs'

const customer = { id: 501, name: 'UAT Customer', code: 'C501', status: 'customer' }
const quote = { id: 14, quote_no: 'QT-14', customer: 501, customer_name: customer.name, status: 'accepted', status_display: '已接受', currency: 'USD', items: [], total_amount: '100' }
const order = { id: 34, order_no: 'SO-34', customer: 501, customer_name: customer.name, status: 'completed', status_display: '已完成', currency: 'USD', items: [], total_amount: '100', balance_amount: '0' }
const purchase = { id: 13, purchase_no: 'PO-13', supplier_name: 'UAT Supplier', status: 'completed', currency: 'USD', items: [], related_orders: [order], total_amount: '100', unpaid_amount: '0', paid_amount: '100' }
const section = (key, title, entity, rows = [], columns = []) => ({ key, title, entity, rows, columns })
const customerContext = {
  entity: 'customers', title: customer.name, metrics: [], info: [], sections: [
    section('followups', '跟进记录', 'follow-ups'), section('quotes', '报价记录', 'quotes', [quote], [['quote_no', '报价单号']]),
    section('orders', '订单', 'orders', [order]), section('contacts', '联系人', 'contacts'),
    section('purchases', '成交商品记录', 'orders'), section('cash', '财务流水', 'transactions'),
  ],
}
const quoteContext = { entity: 'quotes', title: quote.quote_no, metrics: [], info: [], sections: [] }
let wrapper
const stubs = { ContractAmountAdjustments: true, OperationLogPanel: true, QuotePreviewModal: true, RelatedCreateModal: true, ShipmentActualPacking: true, SkuPickerPanel: true, TradeUnitPicker: true, SummaryCards: true }
async function setup(url) {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/customers', component: ResourcePage, props: { config: resourceConfigs.customers } },
    { path: '/quotes', component: DocumentPage, props: { type: 'quotes' } },
    { path: '/orders', component: DocumentPage, props: { type: 'orders' } },
    { path: '/purchase-orders', component: PurchaseOrderPage },
    { path: '/inventory-movements', component: ResourcePage, props: { config: resourceConfigs['inventory-movements'] } },
  ] })
  await router.push(url)
  wrapper = mount(defineComponent({ components: { RouterView }, template: '<RouterView :key="$route.path" />' }), { global: { plugins: [router], stubs, directives: { 'money-input': {} } } })
  await flushPromises()
  return router
}
const click = async label => { await wrapper.findAll('button').find(b => b.text() === label).trigger('click'); await flushPromises() }
const active = () => wrapper.findAll('.workbench-tabs button.active, .detail-tabs button.active').map(b => b.text()).join(' ')
beforeEach(() => {
  mocks.listAll.mockImplementation(async url => ({ '/customers/': [customer, { ...customer, id: 502, name: 'Next Customer' }], '/quotes/': [quote, { ...quote, id: 15, quote_no: 'QT-15' }], '/orders/': [order, { ...order, id: 35, order_no: 'SO-35' }], '/purchase-orders/': [purchase, { ...purchase, id: 16, purchase_no: 'PO-16' }] }[url] || []))
  mocks.api.get.mockImplementation(async url => {
    if (url.startsWith('/context/customers/')) return { data: customerContext }
    if (url.startsWith('/context/quotes/')) return { data: quoteContext }
    if (url.startsWith('/context/inventory-movements/')) return { data: { entity: 'inventory-movements', title: 'IM-1', metrics: [], info: [], sections: [] } }
    if (url === '/inventory-movements/1/') return { data: { movement_no: 'IM-1', quantity: 1, type: 'adjust_in' } }
    if (/\/quotes\/\d+\/workbench/.test(url)) return { data: { quote, root_quote_no: quote.quote_no, revisions: [quote], orders: [{ ...order, source_quote_no: quote.quote_no }], important_notes: [] } }
    if (/\/orders\/\d+\/workbench/.test(url)) return { data: { order, items: [], payments: [], inventory: [], payment_summary: {}, fulfillment_summary: {}, profit_summary: {} } }
    if (url.endsWith('/fulfillment/')) return { data: { items: [], purchase_orders: [purchase], shipments: [] } }
    if (url.endsWith('/packing-plan/') || url.endsWith('/procurement-plan/')) return { data: { items: [] } }
    if (/\/purchase-orders\/\d+\//.test(url)) return { data: purchase }
    return { data: [] }
  })
})
afterEach(() => { wrapper?.unmount(); vi.useRealTimers(); vi.clearAllMocks() })

it('P0: Quote Orders opens the exact Order route and Back restores the same quote tab', async () => {
  const router = await setup('/quotes?search=QT&detail=14&tab=orders')
  await click('查看订单')
  expect(router.currentRoute.value.fullPath).toBe('/orders?detail=34')
  expect(wrapper.find('[aria-label="订单工作台"]').exists()).toBe(true)
  router.back(); await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe('/quotes?search=QT&detail=14&tab=orders')
  expect(active()).toContain('订单')
})
it('Customer quotes route restores, click updates root tab, and nested drill does not overwrite it', async () => {
  const router = await setup('/customers?detail=501&tab=quotes&search=UAT')
  expect(active()).toContain('报价记录')
  await wrapper.get('.detail-tabs button').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query.tab).toBe('followups')
  await click('报价记录 1')
  await wrapper.get('.detail-content tbody tr').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query.tab).toBe('quotes')
  await wrapper.get('.detail-actions a').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.path).toBe('/quotes')
  router.back(); await flushPromises()
  expect(router.currentRoute.value.query).toEqual({ detail: '501', tab: 'quotes', search: 'UAT' })
  expect(active()).toContain('报价记录')
})
it('Customer invalid tab falls back to followups and actual sold-item/cash/log keys remain supported', async () => {
  const router = await setup('/customers?detail=501&tab=invalid')
  expect(active()).toContain('跟进记录')
  for (const [key, label] of [['purchases', '成交商品记录'], ['cash', '财务流水'], ['operation_logs', '操作日志']]) {
    await router.replace({ path: '/customers', query: { detail: '501', tab: key } }); await flushPromises()
    expect(active()).toContain(label)
  }
})
it.each([
  ['/quotes', '14', 'orders', '报价明细 (0)', 'items'],
  ['/orders', '34', 'fulfillment', '订单明细 (0)', 'items'],
  ['/purchase-orders', '13', 'receipt', '付款', 'payment'],
])('%s restores tabs on remount and writes tab clicks without losing filters', async (path, id, tab, label, next) => {
  const router = await setup(`${path}?detail=${id}&tab=${tab}&search=UAT&status=completed&sku=1`)
  expect(router.currentRoute.value.query.tab).toBe(tab)
  expect(wrapper.find('.workbench-tabs button.active').exists()).toBe(true)
  await click(label)
  expect(router.currentRoute.value.query).toEqual({ detail: id, tab: next, search: 'UAT', status: 'completed', sku: '1' })
  const url = router.currentRoute.value.fullPath
  wrapper.unmount(); await setup(url)
  expect(wrapper.get('.workbench-tabs button.active').text()).toBe(label)
})
it('Order to Purchase and Back restores exact fulfillment context', async () => {
  const router = await setup('/orders?detail=34&tab=fulfillment&status=completed')
  await wrapper.get('a.purchase-navigation-link').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.path).toBe('/purchase-orders')
  router.back(); await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe('/orders?detail=34&tab=fulfillment&status=completed')
  expect(active()).toBe('采购与发货')
})
it('Purchase to Order and Back restores exact associated-orders context', async () => {
  const router = await setup('/purchase-orders?detail=13&tab=orders&search=PO')
  await wrapper.get('.related-order-panel a').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe('/orders?detail=34')
  router.back(); await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe('/purchase-orders?detail=13&tab=orders&search=PO')
  expect(active()).toBe('关联订单')
})
it.each([
  ['/customers', '501', 'quotes', '502', 'followups', '.detail-nav-start .detail-close'],
  ['/quotes', '14', 'orders', '15', 'overview', '[aria-label="关闭报价详情"]'],
  ['/orders', '34', 'fulfillment', '35', 'overview', '[aria-label="关闭订单详情"]'],
  ['/purchase-orders', '13', 'receipt', '16', 'overview', '[aria-label="关闭采购详情"]'],
])('%s closes detail/tab only and new list records start on the default', async (path, id, tab, nextId, expected, close) => {
  const router = await setup(`${path}?detail=${id}&tab=${tab}&search=UAT&status=completed&todo=due&customer=501&ordering=-updated_at&sku=1&attention=1`)
  const preserved = { ...router.currentRoute.value.query }; delete preserved.detail; delete preserved.tab
  await wrapper.get(close).trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query).toEqual(preserved)
  await wrapper.findAll('.data-table tbody tr').at(1).trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query.detail).toBe(nextId)
  expect(router.currentRoute.value.query.tab).toBe(expected)
})
it.each(['/customers', '/quotes'])('%s search initializes, debounces and restores without losing context', async path => {
  const id = path === '/customers' ? '501' : '14'
  const router = await setup(`${path}?search=UAT&detail=${id}&tab=quotes&status=accepted&customer=501&ordering=-updated_at&create=0&edit=0&returnTo=/customers`)
  expect(wrapper.get('.search-box input').element.value).toBe('UAT')
  const previous = { ...router.currentRoute.value.query }
  vi.useFakeTimers()
  await wrapper.get('.search-box input').setValue('new search')
  await vi.advanceTimersByTimeAsync(299); expect(router.currentRoute.value.query.search).toBe('UAT')
  await vi.advanceTimersByTimeAsync(1); await flushPromises()
  expect(router.currentRoute.value.query).toEqual({ ...previous, search: 'new search' })
  const url = router.currentRoute.value.fullPath
  vi.useRealTimers(); wrapper.unmount(); await setup(url)
  expect(wrapper.get('.search-box input').element.value).toBe('new search')
})
it('Quote reset removes only search/status/customer/ordering', async () => {
  const router = await setup('/quotes?search=QT&status=accepted&customer=501&ordering=quote_date&detail=14&tab=orders&create=0&edit=0&returnTo=/customers&sku=1')
  await wrapper.get('.filter-reset').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query).toEqual({ detail: '14', tab: 'orders', create: '0', edit: '0', returnTo: '/customers', sku: '1' })
})
it.each([['/customers?detail=501&tab=quotes', '关闭详情'], ['/quotes?detail=14', '关闭报价详情'], ['/inventory-movements?detail=1&sku=7', '关闭详情']])('%s has one Close action', async (url, label) => {
  await setup(url)
  expect(wrapper.findAll(`.detail-header [aria-label="${label}"]`)).toHaveLength(1)
  if (url.startsWith('/inventory-movements')) {
    expect(wrapper.get('.detail-nav-start').text()).toContain('库存流水详情')
    expect(wrapper.get('.detail-actions a').text()).toContain('返回库存流水')
    expect(wrapper.get('.detail-actions a').attributes('href')).toBe('/inventory-movements?sku=7')
  }
})
it('nested EntityDetail Back retains its behavior and root quote tab', async () => {
  const router = await setup('/customers?detail=501&tab=quotes')
  await wrapper.get('.detail-content tbody tr').trigger('click'); await flushPromises()
  await wrapper.get('.detail-back').trigger('click'); await flushPromises()
  expect(wrapper.get('.detail-identity h2').text()).toBe(customer.name)
  expect(active()).toContain('报价记录')
  expect(router.currentRoute.value.query.tab).toBe('quotes')
})
it.each([['/quotes', '14'], ['/orders', '34'], ['/purchase-orders', '13']])('%s rejects invalid and multi-value tab queries', async (path, id) => {
  const router = await setup(`${path}?detail=${id}&tab=bogus&sku=1`)
  expect(router.currentRoute.value.query).toEqual({ detail: id, tab: 'overview', sku: '1' })
  expect(active()).toBe('概览')
  await router.replace({ path, query: { detail: id, tab: ['items', 'overview'], sku: '1' } }); await flushPromises()
  expect(router.currentRoute.value.query.tab).toBe('overview')
})
it('Inventory Movement return action preserves SKU and closes detail', async () => {
  const router = await setup('/inventory-movements?detail=1&sku=7')
  await wrapper.get('.detail-actions a').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe('/inventory-movements?sku=7')
  expect(wrapper.find('.detail-modal').exists()).toBe(false)
})
it('post-create Quote Order path goes to Orders and Back keeps the originating tab', async () => {
  const router = await setup('/quotes?detail=14&tab=orders')
  const page = wrapper.getComponent(DocumentPage)
  await page.vm.handleOrderDraftSaved(order); await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe('/orders?detail=34')
  router.back(); await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe('/quotes?detail=14&tab=orders')
})
it('switching Quote versions updates the source detail ID before cross-module navigation', async () => {
  const original = mocks.api.get.getMockImplementation()
  const revision = { ...quote, id: 15, quote_no: 'QT-15', revision_no: 1, parent_quote: 14 }
  mocks.api.get.mockImplementation(async url => {
    if (/\/quotes\/\d+\/workbench/.test(url)) return { data: { quote: url.includes('/15/') ? revision : quote, root_quote_no: quote.quote_no, revisions: [quote, revision], orders: [order], important_notes: [] } }
    return original(url)
  })
  const router = await setup('/quotes?detail=14&tab=overview&search=QT')
  await wrapper.findAll('.summary-version-actions button').find(b => b.text() === '查看详情' && !b.element.disabled).trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query).toEqual({ detail: '15', tab: 'overview', search: 'QT' })
  expect(wrapper.get('.detail-identity h2').text()).toBe('QT-15')
  await click('订单 (1)'); await click('查看订单')
  router.back(); await flushPromises()
  expect(router.currentRoute.value.query).toEqual({ detail: '15', tab: 'orders', search: 'QT' })
  expect(wrapper.get('.detail-identity h2').text()).toBe('QT-15')
})
