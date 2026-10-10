// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import PurchaseOrderPage from '../src/views/PurchaseOrderPage.vue'
import PurchaseSupplierPicker from '../src/components/PurchaseSupplierPicker.vue'
import SkuPickerPanel from '../src/components/SkuPickerPanel.vue'
const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn() }, listAll: vi.fn(), confirmDialog: vi.fn() }))
vi.mock('../src/api', () => ({ api: mocks.api, listAll: mocks.listAll, listData: r => r.data }))
vi.mock('../src/dialogs', () => ({ confirmDialog: mocks.confirmDialog, inputDialog: vi.fn() }))
let wrapper
const source = { id: 20, currency: 'USD', purchase_price: '2' }
const line = { sku: 3, supplier_sku: 20, quantity: '4', unit_price: '20', trade_unit: 1, trade_snapshot: { factor: '10', unit: 'box' } }
const purchase = { id: 41, purchase_no: 'PO-41', status: 'draft', currency: 'USD', exchange_rate: '7', supplier: 9, items: [{ ...line, unit_price: '0' }] }
beforeEach(() => {
  vi.clearAllMocks(); mocks.confirmDialog.mockResolvedValue(true)
  mocks.listAll.mockImplementation(async url => url === '/suppliers/' ? [{ id: 9, name: 'Old' }, { id: 10, name: 'New' }] : url === '/purchase-orders/' ? [purchase] : url === '/skus/' ? [{ id: 3, sku: 'SKU-3', unit: 'pcs', trade_units: [] }] : [])
  mocks.api.get.mockImplementation(async (url, config) => ({ data: url === '/supplier-skus/' ? Number(config.params.supplier) === 9 ? [source] : [] : purchase }))
  mocks.api.post.mockResolvedValue({ data: {} })
})
afterEach(() => wrapper?.unmount())
async function editor() {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/purchase-orders', component: { template: '<main />' } }] })
  await router.push('/purchase-orders')
  wrapper = mount(PurchaseOrderPage, { global: { plugins: [router], directives: { 'money-input': {} }, stubs: { PurchaseSupplierPicker: true, SkuPickerPanel: true, TradeUnitPicker: true, ContractAmountAdjustments: true } } })
  await flushPromises()
  await wrapper.findAll('button').find(b => b.text() === '新建采购单').trigger('click')
  wrapper.vm.draft.supplier = 9; wrapper.vm.draft.currency = 'USD'; wrapper.vm.draft.exchange_rate = '7'; wrapper.vm.draft.items = [structuredClone(line)]
  await wrapper.vm.loadSupplierSkuOptions(wrapper.vm.draft.items[0]); await flushPromises()
}
it.each([false, true])('supplier change protects source/price/trade data until confirmation (%s)', async accept => {
  await editor(); const before = JSON.stringify(wrapper.vm.draft); mocks.confirmDialog.mockResolvedValueOnce(accept); mocks.api.get.mockClear()
  await wrapper.get('[aria-label="供应商"]').setValue('10'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledWith(expect.objectContaining({ message: expect.stringContaining('更换供应商将清除') }))
  if (!accept) { expect(JSON.stringify(wrapper.vm.draft)).toBe(before); expect(mocks.api.get).not.toHaveBeenCalled(); expect(wrapper.get('[aria-label="供应商"]').element.value).toBe('9') }
  else { expect(wrapper.vm.draft.supplier).toBe('10'); expect(wrapper.vm.draft.items[0]).toMatchObject({ supplier_sku: '', unit_price: '', trade_unit: null, trade_snapshot: {} }); expect(mocks.api.get).toHaveBeenCalledWith('/supplier-skus/', expect.objectContaining({ params: expect.objectContaining({ supplier: '10' }) })) }
})
it('other supplier picker uses the same cancel/confirm rule', async () => {
  await editor(); const before = JSON.stringify(wrapper.vm.draft)
  await wrapper.findAll('button').find(b => b.text() === '查找其他供应商').trigger('click'); await flushPromises()
  mocks.confirmDialog.mockResolvedValueOnce(false)
  wrapper.getComponent(PurchaseSupplierPicker).vm.$emit('selected', { supplier: 10, supplier_sku: '' }); await flushPromises()
  expect(JSON.stringify(wrapper.vm.draft)).toBe(before)
  wrapper.getComponent(PurchaseSupplierPicker).vm.$emit('selected', { supplier: 10, supplier_sku: '' }); await flushPromises()
  expect(wrapper.vm.draft.items[0]).toMatchObject({ unit_price: '', trade_unit: null }); expect(wrapper.vm.draft.supplier).toBe(10)
})
it.each(['CNY', 'EUR'])('currency cancellation preserves contract and confirmation resets safely (%s)', async currency => {
  await editor(); const before = JSON.stringify(wrapper.vm.draft)
  mocks.confirmDialog.mockResolvedValueOnce(false)
  await wrapper.get('[aria-label="采购币种"]').setValue(currency); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledWith(expect.objectContaining({ message: expect.stringContaining('原价格不会自动换汇') }))
  expect(JSON.stringify(wrapper.vm.draft)).toBe(before)
  await wrapper.get('[aria-label="采购币种"]').setValue(currency); await flushPromises()
  expect(wrapper.vm.draft.currency).toBe(currency); expect(wrapper.vm.draft.exchange_rate).toBe(currency === 'CNY' ? '1' : '')
  expect(wrapper.vm.draft.items[0].unit_price).toBe('')
})
it('currency reseeds only a matching supplier reference and permits empty-price changes', async () => {
  await editor(); wrapper.vm.draft.items[0].unit_price = ''; wrapper.vm.draft.currency = 'EUR'
  await wrapper.get('[aria-label="采购币种"]').setValue('USD'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled(); expect(wrapper.vm.draft.items[0].unit_price).toBe(20); expect(wrapper.vm.draft.exchange_rate).toBe('')
})
it('zero-price placement warns explicitly and still posts after confirmation', async () => {
  await editor(); await wrapper.vm.place(purchase); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledWith(expect.objectContaining({ message: expect.stringContaining('1 条 0 单价商品，请确认这是赠品、样品') }))
  expect(mocks.api.post).toHaveBeenCalledWith('/purchase-orders/41/place/')
  mocks.api.post.mockClear(); mocks.confirmDialog.mockResolvedValueOnce(false)
  await wrapper.vm.place(purchase); expect(mocks.api.post).not.toHaveBeenCalled()
})
it('hides supplier matcher while the custom confirmation is pending and restores it on cancel', async () => {
  await editor(); await wrapper.findAll('button').find(b => b.text() === '查找其他供应商').trigger('click'); await flushPromises()
  let resolve
  mocks.confirmDialog.mockImplementationOnce(() => new Promise(done => { resolve = done }))
  wrapper.getComponent(PurchaseSupplierPicker).vm.$emit('selected', { supplier: 10, supplier_sku: '' }); await flushPromises()
  expect(wrapper.findComponent(PurchaseSupplierPicker).exists()).toBe(false)
  expect(wrapper.get('.editor-actions .btn-primary').attributes('disabled')).toBeDefined()
  resolve(false); await flushPromises()
  expect(wrapper.findComponent(PurchaseSupplierPicker).exists()).toBe(true)
  expect(wrapper.vm.draft.supplier).toBe(9)
})
