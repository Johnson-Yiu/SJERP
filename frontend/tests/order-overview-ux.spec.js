// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { deliveryState } from '../src/utils/orderOverview.js'
const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn() }, listAll: vi.fn() }))
vi.mock('../src/api.js', () => ({ ...mocks, downloadQuoteExport: vi.fn() }))
import DocumentPage from '../src/views/DocumentPage.vue'
import OrderDetailModal from '../src/components/OrderDetailModal.vue'
let wrapper, status, balance
const items = [{ id: 1, sku: 10, draftable_quantity: 3, unshipped_quantity: 4 }]
const row = () => ({ id: 123, order_no: 'SO-123', customer_name: 'UAT', status, status_display: status, currency: 'USD', total_amount: 100, balance_amount: balance, order_date: '2026-10-01', expected_ship_date: '2026-10-07', updated_at: '2026-10-06T12:00:00Z', items: [] })
async function setup(component, url = '/orders?detail=123') {
  const router = createRouter({ history: createMemoryHistory(), routes: ['/orders', '/receivables'].map(path => ({ path, component: { template: '<main />' } })) })
  await router.push(url); await router.isReady()
  wrapper = mount(component, { props: component === DocumentPage ? { type: 'orders' } : { id: 123 }, global: { plugins: [router], stubs: { OrderDetailModal: true, ContractAmountAdjustments: true, OperationLogPanel: true, ShipmentActualPacking: true } } })
  await flushPromises()
  return router
}
beforeEach(() => {
  status = 'confirmed'; balance = 25
  mocks.listAll.mockImplementation(async url => url === '/orders/' ? [row(), { ...row(), id: 124, status: 'completed' }, { ...row(), id: 125, status: 'draft' }, { ...row(), id: 126, status: 'cancelled' }] : [])
  mocks.api.get.mockImplementation(async url => ({ data: url.endsWith('/workbench/') ? { order: row(), items: [], payments: [], inventory: [], payment_summary: { planned_amount: 100, paid_amount: 75, balance_amount: balance }, fulfillment_summary: { ordered_quantity: 10, shipped_quantity: 6, remaining_quantity: 4 }, profit_summary: { purchase_base_rmb: 200, purchase_additional_rmb: 30, estimated_gross_profit_rmb: 400 }, source_quote: { id: 9, quote_no: 'QT-9' } } : url.endsWith('/fulfillment/') ? { items, shipments: [] } : url.endsWith('/procurement-plan/') ? { items } : {} }))
})
afterEach(() => { wrapper?.unmount(); vi.useRealTimers(); vi.clearAllMocks() })
it('renders business date hierarchy and operational count cards', async () => {
  await setup(DocumentPage)
  expect(wrapper.findAll('th').map(x => x.text())).toEqual(['订单号', '客户', '订单日期', '预计交期', '履约状态', '明细', '订单金额', '已收 / 待收', '操作'])
  expect(wrapper.find('tbody tr').text()).toContain('2026-10-01')
  expect(wrapper.find('tbody tr').text()).not.toContain('12:00')
  expect(wrapper.findComponent({ name: 'SummaryCards' }).props('items').map(x => [x.label, x.value])).toEqual([['执行中',1], ['待出库',1], ['待收款',2], ['已完成',1]])
})
it('restores search, debounces one load, preserves context and resets only order filters', async () => {
  let router = await setup(DocumentPage, '/orders?search=SO&status=confirmed&todo=pending_shipment&detail=123&sku=10&customer=2&quote=9&extra=keep')
  const input = wrapper.get('.search-box input')
  expect(input.element.value).toBe('SO')
  expect(mocks.listAll.mock.calls[0][1].params.search).toBe('SO')
  mocks.listAll.mockClear(); vi.useFakeTimers()
  await input.setValue('SO-123'); await vi.advanceTimersByTimeAsync(299)
  expect(router.currentRoute.value.query.search).toBe('SO')
  await vi.advanceTimersByTimeAsync(1); await flushPromises(); vi.useRealTimers()
  expect(router.currentRoute.value.query).toMatchObject({search:'SO-123',status:'confirmed',todo:'pending_shipment',detail:'123'})
  expect(mocks.listAll.mock.calls.filter(x=>x[0]==='/orders/')).toHaveLength(1)
  await wrapper.get('[aria-label="按订单状态筛选"]').setValue('production'); await flushPromises()
  expect(router.currentRoute.value.query.search).toBe('SO-123')
  const url = router.currentRoute.value.fullPath
  wrapper.unmount(); router = await setup(DocumentPage, url)
  expect(wrapper.get('.search-box input').element.value).toBe('SO-123')
  await wrapper.get('.filter-reset').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query).toEqual({detail:'123',sku:'10',customer:'2',quote:'9',extra:'keep'})
})
it('shows local calendar delivery helpers only for active formal orders', () => {
  const now = new Date(2026,9,7,23,59)
  for (const [date,kind,label] of [['2026-10-08','future','还剩 1 天'],['2026-10-07','today','今日到期'],['2026-10-06','overdue','逾期 1 天']]) expect(deliveryState({status:'confirmed',expected_ship_date:date},now)).toEqual({kind,label})
  for (const status of ['draft','shipped','completed','cancelled']) expect(deliveryState({status,expected_ship_date:'2020-01-01'},now)).toBeNull()
  expect(deliveryState({status:'production',expected_ship_date:''},now)).toBeNull()
})
it('preserves a pending search when status changes before the debounce completes', async () => {
  const router = await setup(DocumentPage, '/orders?detail=123&todo=pending_shipment')
  vi.useFakeTimers()
  await wrapper.get('.search-box input').setValue('SO-123')
  await wrapper.get('[aria-label="按订单状态筛选"]').setValue('production')
  await flushPromises()
  await vi.advanceTimersByTimeAsync(300); await flushPromises()
  expect(router.currentRoute.value.query).toEqual({ detail: '123', todo: 'pending_shipment', status: 'production', search: 'SO-123' })
})
it.each(['draft','confirmed','production','shipped','completed','cancelled'])('derives tasks and header actions for %s', async value => {
  status = value; await setup(OrderDetailModal)
  expect(wrapper.findAll('.detail-header .detail-close')).toHaveLength(1)
  expect(wrapper.findAll('.workbench-tabs button').map(x=>x.text().replace(/ \(.*\)/,''))).toEqual(['概览','订单明细','采购与发货','回款','装箱','库存流水','操作日志'])
  expect(wrapper.get('.current-todo-card').text()).toContain('当前待办')
  const keys = wrapper.findAll('.task-row strong').map(x=>x.text())
  if (value === 'draft') expect(keys).toEqual(['订单待确认'])
  if (['confirmed','production'].includes(value)) expect(keys).toEqual(['待采购','待发货','待收款'])
  if (value === 'shipped') expect(keys).toContain('货物已全部发出')
  if (value === 'completed') { expect(keys).toEqual(['待收款']); expect(wrapper.get('.task-row a').attributes('href')).toBe('/receivables?order=123') }
  if (value === 'cancelled') { expect(wrapper.findAll('.task-row .task-action')).toHaveLength(0); expect(keys).toEqual(['订单已取消']) }
  expect(wrapper.find('.lifecycle-destructive').exists()).toBe(['draft','confirmed','production'].includes(value))
  expect(wrapper.find('.lifecycle-primary').exists()).toBe(['draft','confirmed','shipped'].includes(value))
})
it('separates payment/profit and retains fulfillment, quote and receivable navigation', async () => {
  const router = await setup(OrderDetailModal, '/orders?search=SO&status=confirmed&detail=123')
  expect(wrapper.get('.payment-card').text()).not.toMatch(/分配商品成本|分摊附加费用|预估毛利/)
  expect(wrapper.get('.cost-profit-card').text()).toMatch(/预估总成本.*230.00/)
  expect(wrapper.get('.cost-profit-card').text()).toContain('400.00')
  await wrapper.get('.source-quote-card button').trigger('click'); expect(wrapper.emitted('open-quote')).toEqual([[9]])
  await wrapper.get('.fulfillment-overview button').trigger('click'); await flushPromises(); expect(wrapper.get('.workbench-tabs button.active').text()).toBe('采购与发货')
  expect(wrapper.findComponent({ name: 'OperationLogPanel' }).exists()).toBe(false)
  await wrapper.findAll('.workbench-tabs button')[0].trigger('click'); await flushPromises()
  await wrapper.get('.task-list a').trigger('click'); await flushPromises(); expect(router.currentRoute.value.fullPath).toBe('/receivables?order=123')
  router.back(); await flushPromises(); expect(router.currentRoute.value.fullPath).toBe('/orders?search=SO&status=confirmed&detail=123&tab=overview')
  await wrapper.get('.task-list button').trigger('click'); await flushPromises(); expect(wrapper.get('.workbench-tabs button.active').text()).toBe('采购与发货')
  expect(mocks.api.post).not.toHaveBeenCalled()
})

it('shared document headers remain distinct when switching quote and order',async()=>{
 mocks.listAll.mockResolvedValue([{id:1,quote_no:'QT-HEADER',status:'draft',status_display:'草稿',currency:'USD',total_amount:'500',items:[]}])
 await setup(DocumentPage, '/orders');expect(wrapper.findAll('th').map(x=>x.text())).toContain('履约状态')
 await wrapper.setProps({type:'quotes'});await flushPromises()
 expect(wrapper.findAll('th').map(x=>x.text())).toContain('状态');expect(wrapper.findAll('th').map(x=>x.text())).not.toContain('履约状态')
 await wrapper.setProps({type:'orders'});await flushPromises()
 expect(wrapper.findAll('th').map(x=>x.text())).toContain('履约状态');expect(wrapper.findAll('th').map(x=>x.text())).not.toContain('状态')
})

it('list unknown debt is a review label rather than confirmed zero',async()=>{
 mocks.listAll.mockResolvedValue([{...row(),status:'completed',balance_amount:'0',receivable_state:'no_plans'}])
 await setup(DocumentPage,'/orders');expect(wrapper.get('tbody .owing').text()).toBe('应收计划待核对')
})
