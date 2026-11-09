import { beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PurchasePaymentModal from '../src/components/PurchasePaymentModal.vue'
import PurchaseOrderPage from '../src/views/PurchaseOrderPage.vue'
const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), listAll: vi.fn() }))
vi.mock('../src/api', () => ({ api: mocks, listAll: mocks.listAll, listData: r => r.data }))
import { createRouter, createMemoryHistory } from 'vue-router'
async function purchaseRouter() {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/purchase-orders', component: { template: '<div />' } }] })
  await router.push('/purchase-orders')
  return router
}
const purchase = { id: 2, purchase_no: 'PO-2', supplier_name: 'Supplier', currency: 'USD', exchange_rate: '7', total_amount: '100', paid_amount: '20', unpaid_amount: '80', status: 'ordered', items: [] }
beforeEach(() => { window.sessionStorage.clear(); vi.clearAllMocks(); mocks.listAll.mockImplementation(async url => url === '/purchase-orders/' ? [purchase] : []); mocks.post.mockResolvedValue({ data: {} }) })
const paymentIdentity = expect.objectContaining({ headers: expect.objectContaining({ 'Idempotency-Key': expect.stringMatching(/^PURCHASE-PAY-/) }) })
it('opens payment from the purchase row and submits the verified actual rate', async () => {
  const wrapper = mount(PurchaseOrderPage, { global: { plugins: [await purchaseRouter()], directives: { 'money-input': {} }, stubs: { ContractAmountAdjustments: true } } })
  await flushPromises()
  await wrapper.get('.purchase-list-row').trigger('click')
  await flushPromises()
  await wrapper.findAll('button').find(b => b.text() === '登记付款').trigger('click')
  expect(wrapper.find('[aria-labelledby="payment-title"]').exists()).toBe(true)
  await wrapper.find('.payment-modal input[type="number"]').setValue('30')
  await wrapper.get('[aria-label="本次实际汇率"]').setValue('7')
  await wrapper.find('.payment-modal form').trigger('submit')
  await flushPromises()
  expect(mocks.post).toHaveBeenCalledWith('/purchase-orders/2/pay/', expect.objectContaining({ amount: 30, currency: 'USD', exchange_rate: 7 }), paymentIdentity)
  expect(wrapper.find('.payment-modal').exists()).toBe(false)
  expect(wrapper.text()).toContain('供应商付款已登记为支出流水')
  wrapper.unmount()
})
it('rejects overpayment and preserves input on server failure', async () => {
  const wrapper = mount(PurchasePaymentModal, { props: { purchase } })
  await wrapper.find('input[type="number"]').setValue('81')
  await wrapper.find('form').trigger('submit')
  expect(mocks.post).not.toHaveBeenCalled()
  expect(wrapper.find('[role="alert"]').text()).toContain('不能超过')
  await wrapper.find('input[type="number"]').setValue('10')
  await wrapper.get('[aria-label="本次实际汇率"]').setValue('7')
  mocks.post.mockRejectedValue({ response: { data: { detail: '余额已更新，请刷新' } } })
  await wrapper.find('form').trigger('submit'); await flushPromises()
  expect(wrapper.find('[role="alert"]').text()).toContain('余额已更新')
  expect(wrapper.find('input').element.value).toBe('10')
  expect(wrapper.emitted('saved')).toBeUndefined()
  wrapper.unmount()
})
it('defaults new purchases to CNY and asks for a rate for foreign currency', async () => {
  const wrapper = mount(PurchaseOrderPage, { global: { plugins: [await purchaseRouter()], directives: { 'money-input': {} }, stubs: { ContractAmountAdjustments: true } } })
  await flushPromises()
  await wrapper.findAll('button').find(b => b.text() === '新建采购单').trigger('click')
  const currency = wrapper.findAll('.form-grid select').at(-1)
  expect(currency.element.value).toBe('CNY')
  expect(currency.findAll('option')).toHaveLength(9)
  await currency.setValue('USD')
  expect(wrapper.find('.form-grid input[type="number"]').element.value).toBe('')
  expect(wrapper.find('.form-grid input[type="number"]').attributes('required')).toBeDefined()
  wrapper.unmount()
})

it('foreign payment uses the entered actual rate without changing the purchase contract', async () => {
  const wrapper = mount(PurchasePaymentModal, { props: { purchase } })
  expect(wrapper.get('[aria-label="本次实际汇率"]').element.value).toBe('')
  await wrapper.find('input[type="number"]').setValue('10')
  await wrapper.get('[aria-label="本次实际汇率"]').setValue('7.45')
  await wrapper.get('form').trigger('submit'); await flushPromises()
  expect(mocks.post).toHaveBeenCalledWith('/purchase-orders/2/pay/', expect.objectContaining({ exchange_rate: 7.45 }), paymentIdentity)
  expect(purchase.exchange_rate).toBe('7'); wrapper.unmount()
})
it('CNY actual payment rate is readonly 1 regardless of historical contract input', async () => {
  const wrapper = mount(PurchasePaymentModal, { props: { purchase: { ...purchase, currency: 'CNY', exchange_rate: '7' } } })
  expect(wrapper.get('[aria-label="本次实际汇率"]').element.value).toBe('1')
  expect(wrapper.get('[aria-label="本次实际汇率"]').attributes('readonly')).toBeDefined()
  await wrapper.find('input[type="number"]').setValue('10'); await wrapper.get('form').trigger('submit'); await flushPromises()
  expect(mocks.post).toHaveBeenCalledWith('/purchase-orders/2/pay/', expect.objectContaining({ currency: 'CNY', exchange_rate: 1 }), paymentIdentity); wrapper.unmount()
})
it.each(['0', '-1', ''])('rejects an invalid actual payment rate (%s)', async rate => {
  const wrapper = mount(PurchasePaymentModal, { props: { purchase } })
  await wrapper.find('input[type="number"]').setValue('10'); await wrapper.get('[aria-label="本次实际汇率"]').setValue(rate)
  await wrapper.get('form').trigger('submit'); await flushPromises()
  expect(mocks.post).not.toHaveBeenCalled(); expect(wrapper.get('[role="alert"]').text()).toContain('实际汇率必须大于 0'); wrapper.unmount()
})
