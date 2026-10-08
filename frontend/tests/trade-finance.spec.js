import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PaymentPlanPage from '../src/views/PaymentPlanPage.vue'
import TransactionPage from '../src/views/TransactionPage.vue'
import PurchaseOrderPage from '../src/views/PurchaseOrderPage.vue'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), listAll: vi.fn() }))
vi.mock('../src/api', () => ({ api: mocks, listAll: mocks.listAll, listData: response => response.data.results || response.data }))
import { createRouter, createMemoryHistory } from 'vue-router'
async function purchaseRouter() {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/purchase-orders', component: { template: '<div />' } }] })
  await router.push('/purchase-orders')
  return router
}
const plan = { id: 1, direction: 'receivable', customer_id: 4, order: 3, contract_no: 'SO-3', counterparty_name: '客户甲', planned_amount: '100', settled_amount: '0', remaining_amount: '100', remaining_rmb: 700, exchange_rate: '7', currency: 'USD', status: 'open' }
const options = { global: { directives: { 'money-input': {} } } }

beforeEach(() => {
  vi.clearAllMocks()
  mocks.post.mockResolvedValue({ data: {} })
  mocks.patch.mockResolvedValue({ data: {} })
  mocks.listAll.mockResolvedValue([])
})

describe('trade finance interactions', () => {
  it('settles a populated plan with inherited currency and exchange rate', async () => {
    mocks.listAll.mockResolvedValue([plan])
    const wrapper = mount(PaymentPlanPage, { ...options, global: { ...options.global, plugins: [await purchaseRouter()] }, props: { direction: 'receivable' } })
    await flushPromises()
    expect(wrapper.text()).toContain('700.00')
    await wrapper.findAll('button').find(button => button.text() === '登记收款').trigger('click')
    const dialog = wrapper.find('form.dialog')
    expect(dialog.findAll('input[type="number"]')[1].element.value).toBe('7')
    await dialog.find('input[type="number"]').setValue('10')
    await dialog.trigger('submit')
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/payment-plans/1/settle/', expect.objectContaining({ amount: 10, currency: 'USD', exchange_rate: '7' }))
    expect(wrapper.find('.mask').exists()).toBe(false)
    wrapper.unmount()
  })

  it('retains the selected supplier when saving an unallocated payment', async () => {
    mocks.listAll.mockImplementation(async url => url === '/suppliers/' ? [{ id: 8, name: '供应商乙' }] : [])
    const wrapper = mount(TransactionPage, options)
    await flushPromises()
    await wrapper.findAll('button').find(button => button.text() === '新增记账').trigger('click')
    await wrapper.find('.dialog select').setValue('unallocated_payment')
    await wrapper.find('.dialog input[type="number"]').setValue('50')
    await wrapper.findAll('.dialog select')[2].setValue('8')
    await wrapper.find('form.dialog').trigger('submit')
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/transactions/', expect.objectContaining({ kind: 'unallocated_payment', supplier: 8, direction: 'expense', amount: 50 }))
    expect(mocks.post.mock.calls[0][1]).not.toHaveProperty('transaction_no')
    wrapper.unmount()
  })

  it('requires a reason for root transaction void and hides child void actions', async () => {
    const rows = [
      { id: 11, transaction_date: '2026-09-01', transaction_no: 'FIN-11', direction: 'income', direction_display: '收入', kind: 'customer_receipt', amount: '30', currency: 'USD', rmb_amount: '210', status: 'confirmed', status_display: '已确认', customer_name: '客户甲', order_no: 'SO-11', allocations: [], allocated_amount: '0' },
      { id: 12, transaction_date: '2026-09-01', transaction_no: 'FIN-12', direction: 'income', direction_display: '收入', kind: 'customer_receipt', amount: '20', currency: 'USD', rmb_amount: '140', status: 'confirmed', status_display: '已确认', customer_name: '客户甲', order_no: 'SO-11', split_from: 11, allocations: [], allocated_amount: '0' },
    ]
    mocks.listAll.mockImplementation(async url => url === '/transactions/' ? rows : [])
    const wrapper = mount(TransactionPage, options)
    await flushPromises()
    expect(wrapper.findAll('button').filter(button => button.text() === '作废')).toHaveLength(1)
    await wrapper.findAll('button').find(button => button.text() === '作废').trigger('click')
    expect(wrapper.text()).toContain('该操作将同时作废相关拆分流水，并恢复对应收付款计划。')
    const dialog = wrapper.find('form.dialog')
    await dialog.find('textarea').setValue('收款金额录入错误')
    await dialog.trigger('submit')
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/transactions/11/void/', { reason: '收款金额录入错误' })
    wrapper.unmount()
  })

  it('requires inspection acknowledgement and submits accepted quantity with notes', async () => {
    const purchase = { id: 2, purchase_no: 'PO-2', status: 'ordered', currency: 'USD', items: [{ id: 7, sku_code: 'SKU-7', quantity: '10', received_quantity: '0', remaining_quantity: '10', unit_price: '3' }] }
    mocks.listAll.mockImplementation(async url => url === '/purchase-orders/' ? [purchase] : [])
    const wrapper = mount(PurchaseOrderPage, { ...options, global: { ...options.global, plugins: [await purchaseRouter()], stubs: { RouterLink: true, ContractAmountAdjustments: true } } })
    await flushPromises()
    await wrapper.get('.purchase-list-row').trigger('click')
    await flushPromises()
    await wrapper.findAll('.workbench-tabs button').find(button => button.text() === '收货').trigger('click'); await flushPromises()
    await wrapper.findAll('button').find(button => button.text() === '验货入库').trigger('click')
    const dialog = wrapper.find('form.receipt-dialog')
    expect(dialog.findAll('button').at(-1).attributes('disabled')).toBeDefined()
    await dialog.find('input[type="number"]').setValue('8')
    await dialog.find('textarea').setValue('拒收破损 2 件，等待补货')
    await dialog.find('input[type="checkbox"]').setValue(true)
    await dialog.trigger('submit')
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/purchase-orders/2/receive/', expect.objectContaining({ purchase_item: 7, quantity: 8, notes: expect.stringContaining('拒收破损 2 件') }))
    wrapper.unmount()
  })
})
