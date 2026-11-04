// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import PurchaseOrderPage from '../src/views/PurchaseOrderPage.vue'

const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn() }, listAll: vi.fn() }))
vi.mock('../src/api', () => ({ api: mocks.api, listAll: mocks.listAll, listData: response => response.data }))
let wrapper
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks() })
async function openReceipt() {
  const purchase = { id: 41, purchase_no: 'UX-PO-41', supplier: 9, status: 'ordered', currency: 'CNY', items: [{ id: 71, sku: 3, sku_code: 'UX-SKU', quantity: '10', received_quantity: '0', remaining_quantity: '10', unit_price: '2', receipts: [] }], related_orders: [] }
  mocks.listAll.mockImplementation(async url => url === '/purchase-orders/' ? [purchase] : url === '/skus/' ? [{ id: 3, sku_code: 'UX-SKU', unit: 'pcs', trade_units: [] }] : [])
  mocks.api.get.mockResolvedValue({ data: purchase })
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/purchase-orders', component: PurchaseOrderPage }] })
  await router.push('/purchase-orders?detail=41')
  wrapper = mount(PurchaseOrderPage, { global: { plugins: [router], directives: { 'money-input': {} }, stubs: { PurchasePaymentModal: true, PurchaseCostAllocationModal: true } } })
  await flushPromises()
  for (const label of ['收货', '验货入库']) {
    await wrapper.findAll('button').find(b => b.text() === label).trigger('click')
    await flushPromises()
  }
  await wrapper.get('.inspection-acknowledgement input').setValue(true)
}
it('clears the previous rejected receipt message when a retry succeeds', async () => {
  await openReceipt()
  mocks.api.post.mockRejectedValueOnce({ response: { data: { detail: '合成收货拒绝，请重试' } } }).mockResolvedValueOnce({ data: {} })
  await wrapper.get('.goods-receipt-dialog').trigger('submit'); await flushPromises()
  expect(wrapper.text()).toContain('合成收货拒绝，请重试')
  await wrapper.get('.goods-receipt-dialog').trigger('submit'); await flushPromises()
  expect(wrapper.text()).toContain('验货入库已完成')
  expect(wrapper.text()).not.toContain('合成收货拒绝，请重试')
  const requests = mocks.api.post.mock.calls
  expect(requests).toHaveLength(2)
  expect(requests[0][2].headers['Idempotency-Key']).toBe(requests[1][2].headers['Idempotency-Key'])
})
it('keeps a pending receipt visible and ignores a duplicate submit', async () => {
  await openReceipt()
  let resolve
  mocks.api.post.mockImplementationOnce(() => new Promise(done => { resolve = done }))
  await wrapper.get('.goods-receipt-dialog').trigger('submit'); await flushPromises()
  await wrapper.get('.goods-receipt-dialog').trigger('submit'); await flushPromises()
  expect(mocks.api.post).toHaveBeenCalledTimes(1)
  const cancel = wrapper.get('.goods-receipt-dialog footer .btn-secondary')
  expect(cancel.attributes('disabled')).toBeDefined()
  resolve({ data: {} }); await flushPromises()
  expect(wrapper.find('.goods-receipt-dialog').exists()).toBe(false)
})
