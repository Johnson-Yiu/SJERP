// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import QuoteDetailModal from '../src/components/QuoteDetailModal.vue'
import QuotePreviewModal from '../src/components/QuotePreviewModal.vue'
import QuoteEditorModal from '../src/components/QuoteEditorModal.vue'
import OrderDetailModal from '../src/components/OrderDetailModal.vue'
import PurchaseDetailModal from '../src/components/PurchaseDetailModal.vue'
import EntityDetailModal from '../src/components/EntityDetailModal.vue'
const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn() }, downloadQuoteExport: vi.fn() }))
vi.mock('../src/api', () => ({ ...mocks, listData: r => r.data.results || r.data, listAll: vi.fn(async () => []) }))
const item = { id: 1, sku: 4, sku_code: 'SKU-000004', product_name: '面板灯', quantity: '4.00', trade_quantity: '2.00', trade_unit: 4, trade_unit_price: '10', unit_price: '5', amount: '20', trade_snapshot: { name: '两件箱', unit: '箱', base_unit: 'pcs', factor: '2' }, unshipped_quantity: 4, draftable_quantity: 4, supplier_name: '供应商' }
let wrappers, quote, order, movement, fulfillment
const pi = { invoice_no: 'QT-47', buyer: { company_name: '历史客户', name: '历史联系人', address: '历史地址' }, products: [{ model: '历史型号', description: '历史说明', quantity: '2.00', unit: '箱', unit_price: '10', amount: '20' }], terms: { quote_date: '2026-10-09', lead_time_days: 11 }, totals: { currency: 'USD', subtotal: '20', shipping_fee: '0', discount: '0', total_amount: '20' }, payment_splits: { deposit_ratio: .3, balance_ratio: .7, deposit_amount: '6', balance_amount: '14' } }
beforeEach(() => {
  vi.clearAllMocks(); wrappers = []
  quote = { id: 47, quote_no: 'QT-47', status: 'draft', currency: 'USD', exchange_rate: '7.200000', total_amount: '20', items: [structuredClone(item)] }
  order = { id: 37, order_no: 'SO-37', status: 'draft', currency: 'USD', total_amount: '20', balance_amount: 10 }
  movement = { id: 96, movement_no: 'GR-96', type: 'purchase_in', unit_cost: '3.0000', quantity: '2', sku_code: 'SKU-000004' }
  fulfillment = { items: [structuredClone(item)], shipments: [] }
  mocks.api.get.mockImplementation(async url => ({ data:
    url === '/quotes/47/workbench/' ? { quote, revisions: [], orders: [] } :
    url === '/quotes/47/pi-data/' ? structuredClone(pi) :
    url === '/orders/37/workbench/' ? { order, items: [structuredClone(item)], payments: [], inventory: [], payment_summary: { balance_amount: 10 }, fulfillment_summary: {}, profit_summary: {} } :
    url === '/orders/37/fulfillment/' ? fulfillment :
    url === '/orders/37/procurement-plan/' ? { items: [] } :
    url === '/inventory-movements/96/' ? movement :
    url.startsWith('/context/') ? { entity: 'inventory-movements', title: 'GR-96', info: [], metrics: [], sections: [] } :
    url === '/session/current-operator/' ? {} : [] }))
})
afterEach(() => wrappers.forEach(w => w.unmount()))
async function setup(component, path, props) {
  const router = createRouter({ history: createMemoryHistory(), routes: ['/quotes','/orders','/purchase-orders','/inventory-movements','/receivables'].map(path => ({ path, component: { template: '<main />' } })) })
  await router.push(path); await router.isReady()
  const w = mount(component, { props, global: { plugins: [router], stubs: { OperationLogPanel: true, ContractAmountAdjustments: true, ShipmentActualPacking: true } } }); wrappers.push(w); await flushPromises(); return w
}
const quoteView = tab => setup(QuoteDetailModal, `/quotes?detail=47&tab=${tab || 'overview'}`, { id: 47 })
const orderView = tab => setup(OrderDetailModal, `/orders?detail=37&tab=${tab || 'overview'}`, { id: 37 })
const purchaseView = status => setup(PurchaseDetailModal, '/purchase-orders?detail=4', { purchase: { id: 4, purchase_no: 'PO-4', status, currency: 'USD', total_amount: 20, unpaid_amount: 10, items: [{ ...item, received_quantity: 0, remaining_quantity: 4 }] } })
const button = (w, label) => w.findAll('button').filter(b => b.text() === label)
it.each([['7.200000','7.2'],['34.1250','34.125'],['7.123456789012345678','7.123456789012345678']])('quote rate %s remains exact and readonly', async (raw, shown) => {
  quote.exchange_rate = raw; const before = structuredClone(quote); const w = await quoteView()
  expect(w.get('.data-list').text()).toContain(`USD / ${shown}`); expect(quote).toEqual(before); expect(mocks.api.post).not.toHaveBeenCalled()
})
it.each([['3.0000','3'],['0.000001','0.000001']])('movement cost %s remains exact and readonly', async (raw, shown) => {
  movement.unit_cost = raw; const w = await setup(EntityDetailModal, '/inventory-movements?detail=96', { entity: 'inventory-movements', id: 96 })
  expect(w.findAll('.info-grid > div').find(x => x.get('small').text() === '单位成本').get('span').text()).toBe(shown); expect(movement.unit_cost).toBe(raw)
})
it('order draft has one actionable confirmation and retains todo information', async () => {
  const w = await orderView(); expect(button(w,'确认订单')).toHaveLength(1); expect(button(w,'确认订单')[0].classes()).toContain('lifecycle-primary')
  expect(w.get('.current-todo-card').text()).toContain('订单待确认'); expect(w.get('.current-todo-card').text()).toContain('确认后生成库存预留和应收计划。')
})
it('purchase draft has one header confirmation and retains todo information', async () => {
  const w = await purchaseView('draft'); expect(button(w,'确认下单')).toHaveLength(1); expect(w.get('header').text()).toContain('确认下单'); expect(w.get('.current-todo').text()).toContain('采购单待确认'); expect(w.get('.current-todo').text()).toContain('确认后进入正式采购流程。')
})
it('active order procurement, shipment and receivable actions remain', async () => {
  order.status = 'confirmed'; const w = await orderView(); expect(button(w.get('.current-todo-card'),'查看采购与发货')).toHaveLength(2); expect(w.get('.task-row a').text()).toBe('查看 / 登记本单应收')
})
it('shipped order completion todo action remains', async () => {
  order.status = 'shipped'; const w = await orderView(); expect(w.get('.current-todo-card').text()).toContain('完成订单'); expect(w.findAll('.current-todo-card button').some(b => b.text() === '完成订单')).toBe(true)
})
it('purchase receipt and payment todo actions remain', async () => {
  const w = await purchaseView('ordered'); expect(w.get('.current-todo').text()).toContain('查看收货'); expect(w.get('.current-todo').text()).toContain('查看 / 登记付款')
})
it.each([['completed','订单履约已完成。'],['cancelled','订单已取消，仅保留历史履约记录。']])('%s fulfillment helper matches state', async (status, copy) => {
  order.status = status; const w = await orderView('fulfillment'); expect(w.text()).toContain(copy); expect(w.text()).not.toMatch(/当前采购缺口|采购草稿尚未下单/)
})
it.each([['4','采购草稿不计入已采购。'],['0','']])('active helper respects procurement gap %s', async (gap, copy) => {
  order.status = 'confirmed'; fulfillment.items[0].draftable_quantity = gap; const w = await orderView('fulfillment'); const heading = w.get('.section-heading').text(); expect(heading.includes('采购草稿不计入已采购。')).toBe(Boolean(copy)); expect(heading).not.toContain('当前采购缺口')
})
it('quote name/SKU and trade/base hierarchy preserve data and totals', async () => {
  const before = structuredClone(quote); const w = await quoteView('items'); const cells = w.findAll('tbody tr td'); expect(cells[1].get('small').text()).toBe('SKU-000004'); expect(cells[1].element.firstChild.textContent).toBe('面板灯'); expect(cells[3].element.firstChild.textContent).toBe('2.00'); expect(cells[3].get('small').text()).toBe('基础数量：4.00 pcs'); expect(w.get('.quote-totals').text()).toContain('USD 20.00'); expect(quote).toEqual(before)
})
it('order name/SKU and trade/base hierarchy preserve values', async () => {
  const w = await orderView('items'); const cells = w.findAll('tbody tr td'); expect(cells[1].get('small').text()).toBe('SKU-000004'); expect(cells[1].element.firstChild.textContent).toBe('面板灯'); expect(cells[4].element.firstChild.textContent).toBe('2.00'); expect(cells[4].get('small').text()).toBe('基础数量：4.00 pcs'); expect(item.quantity).toBe('4.00'); expect(item.trade_quantity).toBe('2.00')
})
it('unsaved preview retains editing caption by default', () => {
  const w = mount(QuotePreviewModal, { props: { draft: { ...pi, quote_no: pi.invoice_no, quote_date: pi.terms.quote_date, currency: 'USD' } } }); wrappers.push(w); expect(w.get('.quote-preview-toolbar').text()).toContain('当前未保存内容 · 关闭后可继续编辑')
})
it('QuoteEditor opens an unsaved preview and retains inputs after closing', async () => {
  mocks.api.post.mockImplementation(async url => ({ data: url === '/quotes/availability-preview/' ? { items: [] } : [] }))
  const w = await setup(QuoteEditorModal, '/quotes', { mode: 'create', quote: { ...quote, customer: 1 }, customers: [{ id: 1, name: '当前客户' }], skus: [{ id: 4, sku: 'SKU-000004', unit: 'pcs', trade_units: [{ id: 4, name: '两件箱', unit: '箱', base_unit: 'pcs', factor: '2', active: true }] }] })
  await button(w,'预览报价单')[0].trigger('click'); await flushPromises()
  const preview = w.getComponent(QuotePreviewModal); expect(preview.props('saved')).toBe(false); expect(preview.text()).toContain('当前未保存内容 · 关闭后可继续编辑'); expect(preview.props('draft').products[0]).toMatchObject({ quantity: '2.00', unit: '箱', amount: 20 })
  preview.vm.$emit('close'); await flushPromises(); expect(w.findComponent(QuotePreviewModal).exists()).toBe(false); expect(w.findAll('input').some(input => input.element.value === '2.00')).toBe(true); expect(mocks.api.post.mock.calls.some(([url]) => url === '/quotes/' || url.endsWith('/revise/'))).toBe(false)
})
it('saved workbench preview uses saved caption and exact historical PI/export behavior', async () => {
  const w = await quoteView(); await button(w,'预览 PI')[0].trigger('click'); await flushPromises(); const preview = w.getComponent(QuotePreviewModal)
  expect(preview.props('saved')).toBe(true); expect(preview.get('.quote-preview-toolbar').text()).toContain('已保存报价预览'); expect(preview.text()).not.toContain('当前未保存内容'); expect(preview.props('draft')).toMatchObject({ quote_no: 'QT-47', buyer: { company_name: '历史客户', address: '历史地址' }, products: [expect.objectContaining(pi.products[0])], totals: pi.totals, terms: pi.terms, payment_splits: pi.payment_splits })
  const print = vi.spyOn(window,'print').mockImplementation(() => {}); await button(preview,'导出预览 PDF')[0].trigger('click'); expect(print).toHaveBeenCalledOnce(); print.mockRestore()
  await button(w,'导出 Excel')[0].trigger('click'); expect(mocks.downloadQuoteExport).toHaveBeenCalledWith(47,'QT-47'); expect(mocks.api.post).not.toHaveBeenCalled(); expect(quote.status).toBe('draft')
})
