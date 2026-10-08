// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { fulfillmentItemState, fulfillmentMetrics, purchaseArrivalState } from '../src/utils/orderFulfillment.js'
const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn() }, listAll: vi.fn() }))
vi.mock('../src/api.js', () => ({ ...mocks }))
import OrderDetailModal from '../src/components/OrderDetailModal.vue'

const base = { sku: 10, sku_code: 'SKU-A', display_name: '灯带', base_unit: 'm', supplier_name: '', quantity: 100, allocated_quantity: 30, to_procure_quantity: 70, draftable_quantity: 60, draft_procurement_quantity: 10, purchased_quantity: 20, arrived_quantity: 5, in_transit_quantity: 15, shipped_quantity: 10, unshipped_quantity: 90 }
let wrapper, lines, purchases, status
beforeEach(() => {
  lines = [{ ...base, id: 701 }, { ...base, id: 702 }, { ...base, id: 703, sku: 20, sku_code: 'SKU-B', draftable_quantity: 0, unshipped_quantity: 0 }]
  purchases = [{ id: 41, purchase_no: 'PO-41', supplier_name: '供应商', status: 'ordered', status_display: '已下单', currency: 'CNY', total_amount: 300, expected_arrival_date: '2026-10-01', items: [{ sku_code: 'SKU-A', quantity: 20 }] }]
  status = 'confirmed'
  mocks.api.get.mockImplementation(async url => ({ data: url.endsWith('/workbench/') ? { order: { id: 321, status, order_no: 'SO-321', currency: 'USD' }, items: [], payments: [], inventory: [], payment_summary: {}, fulfillment_summary: {}, profit_summary: {} } : url.endsWith('/fulfillment/') ? { items: lines, purchase_orders: purchases, shipments: [] } : url.endsWith('/procurement-plan/') ? { items: lines } : url.startsWith('/skus/') ? { id: 10, unit: 'm', trade_units: [] } : {} }))
  mocks.listAll.mockResolvedValue([])
})
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks() })
async function setup() {
  const router = createRouter({ history: createMemoryHistory(), routes: ['/orders','/purchase-orders'].map(path=>({path,component:{template:'<main />'}})) })
  await router.push('/orders?search=SO-321&status=confirmed&detail=321'); await router.isReady()
  wrapper = mount(OrderDetailModal, { props: { id: 321 }, global: { plugins: [router], stubs: { Teleport: true, SupplierAllocationModal: true, ProcurementDraftModal: true, ContractAmountAdjustments: true, OperationLogPanel: true } } })
  await flushPromises()
  await wrapper.get('.fulfillment-overview button').trigger('click'); await flushPromises()
  return router
}
it('counts unique procurement SKUs but counts shipment OrderItems and preserves each business row', async () => {
  await setup()
  expect(fulfillmentMetrics(lines).map(x=>[x.label,x.value])).toEqual([['待采购 SKU',1],['采购中 SKU',2],['待发货明细',2],['已完成明细',1]])
  expect(wrapper.findAll('.fulfillment-summary article').map(x=>x.text())).toEqual(['待采购 SKU1','采购中 SKU2','待发货明细2','已完成明细1'])
  expect(wrapper.findAll('.fulfillment-table tbody tr').map(x=>x.attributes('data-order-item-id'))).toEqual(['701','702','703'])
  expect(wrapper.findAll('.fulfillment-table th').map(x=>x.text())).toEqual(['SKU / 当前状态','采购来源','订单需求','采购进度','到货进度','发货进度','操作'])
})
it.each([
  [{ unshipped_quantity: 0 }, 'completed'],
  [{}, 'needs_supplier'],
  [{ supplier_name: '供应商' }, 'needs_procurement'],
  [{ draftable_quantity: 0 }, 'purchasing'],
  [{ draftable_quantity: 0, purchased_quantity: 5, in_transit_quantity: 0 }, 'ready_to_ship'],
  [{ draftable_quantity: 0, purchased_quantity: 0, in_transit_quantity: 0, allocated_quantity: 0 }, 'waiting_stock'],
])('derives ordered state priority without changing any quantities: %s', (values,state) => {
  const item = { ...base, ...values }; const original = { ...item }
  expect(fulfillmentItemState(item)).toBe(state); expect(item).toEqual(original)
})
it('retains every quantity with labels, purchase history and completed shipment', async () => {
  await setup()
  const row = wrapper.get('[data-order-item-id="701"]')
  for (const label of ['订单 100 m','已预留 30 m','待采购 70 m','可建草稿 60 m','采购草稿 10 m','已采购 20 m','已到 5 m','在途 15 m','已发 10 m','待发 90 m']) expect(row.text()).toContain(label)
  expect(wrapper.get('[data-order-item-id="703"]').text()).toContain('已全部发货')
  const purchase = wrapper.get('.purchase-history-card')
  for (const label of ['PO-41','供应商','已下单','CNY 300.00','预计到货 2026-10-01','SKU-A × 20']) expect(purchase.text()).toContain(label)
  expect(purchase.findAll('a')).toHaveLength(1)
})
it('passes exact OrderItem to allocation and preselects only that ID for shipment', async () => {
  await setup()
  await wrapper.get('[data-order-item-id="702"] .fulfillment-source-action').trigger('click')
  expect(wrapper.findComponent({ name: 'SupplierAllocationModal' }).props('orderItem')).toEqual(lines[1])
  await wrapper.get('[data-order-item-id="702"] .fulfillment-ship-action').trigger('click'); await flushPromises()
  const selected = wrapper.findAll('.shipment-line-toggle input').filter(x=>x.element.checked)
  expect(selected).toHaveLength(1)
  expect(wrapper.findAll('.shipment-batch-line').filter(x=>x.find('input').element.checked)[0].text()).toContain('明细 #702')
  expect(mocks.api.post).not.toHaveBeenCalled()
})
it('keeps exact purchase navigation and Back restores the original order query', async () => {
  const router = await setup()
  expect(wrapper.get('.purchase-navigation-link').attributes('href')).toBe('/purchase-orders?detail=41')
  await wrapper.get('.purchase-navigation-link').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query.detail).toBe('41')
  router.back(); await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe('/orders?search=SO-321&status=confirmed&detail=321&tab=fulfillment')
})
it.each(['ordered','placed','partial'])('uses local business dates for purchase ETA (%s)', status => {
  const now = new Date(2026,9,7,23,59)
  for (const [date,kind,label] of [['2026-10-08','future','预计 1 天后到货'],['2026-10-07','today','预计今日到货'],['2026-10-06','overdue','到货逾期 1 天']]) expect(purchaseArrivalState({status,expected_arrival_date:date},now)).toEqual({kind,label})
})
it('excludes closed purchases from ETA warnings and handles empty dates', () => {
  for (const status of ['draft','completed','cancelled']) expect(purchaseArrivalState({status,expected_arrival_date:'2020-01-01'})).toBeNull()
  expect(purchaseArrivalState({status:'ordered',expected_arrival_date:''})).toBeNull()
})
it('shows state-specific empty history and hides unavailable shipment actions', async () => {
  purchases = []; lines = [{ ...base, id: 701, draftable_quantity: 0, to_procure_quantity: 0, purchased_quantity: 0, arrived_quantity: 0, in_transit_quantity: 0 }]; status = 'completed'
  await setup()
  expect(wrapper.get('.purchase-history').text()).toContain('当前无需关联采购单')
  expect(wrapper.get('.shipment-history').text()).toContain('待订单具备可发库存后，可从上方明细确认发货。')
  expect(wrapper.findAll('.fulfillment-ship-action')).toHaveLength(0)
  expect(wrapper.get('.fulfillment-table').text()).toContain('无需采购')
})
