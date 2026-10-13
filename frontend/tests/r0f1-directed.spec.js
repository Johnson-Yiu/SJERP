import { beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import PaymentPlanPage from '../src/views/PaymentPlanPage.vue'
import TransactionPage from '../src/views/TransactionPage.vue'
const api = vi.hoisted(() => ({ listAll: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api, listAll: api.listAll }))
const plan = { id: 1, contract_no: 'SO-F1-0001', counterparty_name: '验收客户', currency: 'CNY', planned_amount: '100', remaining_amount: '100', remaining_rmb: '100', settled_amount: '0', status: 'open' }
async function page(component, path, props = {}) {
  const router = createRouter({ history: createMemoryHistory(), routes: ['/receivables','/payables','/transactions'].map(path => ({ path, component: { template: '<main />' } })) })
  await router.push(path)
  const wrapper = mount(component, { props, global: { plugins: [router], directives: { 'money-input': {} } } })
  await flushPromises()
  return { wrapper, router }
}
const click = (w, text) => w.findAll('button').find(b => b.text() === text).trigger('click')
beforeEach(() => { vi.resetAllMocks(); api.listAll.mockResolvedValue([plan]); api.post.mockResolvedValue({}); api.patch.mockResolvedValue({}) })
it.each([['receivable','收款'],['payable','付款']])('uses clear %s success feedback and clears stale feedback before a failed operation', async (direction, noun) => {
  const {wrapper:w} = await page(PaymentPlanPage, direction === 'receivable' ? '/receivables' : '/payables', {direction})
  await click(w, `登记${noun}`); await w.get('form.dialog').trigger('submit'); await flushPromises()
  expect(w.get('.notice').text()).toBe(`${noun}登记成功`)
  await click(w, '调整计划'); expect(w.find('.notice').exists()).toBe(false)
  api.patch.mockRejectedValueOnce(new Error('fail')); await w.get('form.dialog').trigger('submit'); await flushPromises()
  expect(w.get('form.dialog [role=alert]').text()).toBe('fail')
  expect(w.find('.notice').exists()).toBe(false)
  w.unmount()
})
it('restores all plan filters on initial URL and subsequent navigation', async () => {
  const {wrapper:w,router} = await page(PaymentPlanPage, '/payables?search=Supplier&status=settled&overdue=true&due_from=2026-10-01&due_to=2026-10-31', {direction:'payable'})
  expect(w.get('.plan-search input').element.value).toBe('Supplier')
  expect(w.get('.plan-status select').element.value).toBe('settled')
  expect(w.get('.plan-overdue input').element.checked).toBe(true)
  expect(w.findAll('.plan-date input').map(e=>e.element.value)).toEqual(['2026-10-01','2026-10-31'])
  expect(api.listAll).toHaveBeenCalledWith('/payment-plans/', {params:{direction:'payable', search:'Supplier',status:'settled',overdue:'true',due_from:'2026-10-01',due_to:'2026-10-31'}})
  await router.push('/payables?status=all'); await flushPromises()
  expect(w.get('.plan-status select').element.value).toBe(''); expect(w.get('.plan-search input').element.value).toBe('')
  w.unmount()
})
it('retains the complete selected order number after clearing candidates and resets selection on new search', async () => {
  api.listAll.mockImplementation(async url => url === '/orders/' ? [{id:23,order_no:'SO-2026-FULL-000023',status:'confirmed',currency:'CNY',exchange_rate:'1'}] : [])
  const {wrapper:w} = await page(TransactionPage,'/transactions')
  await click(w,'新增记账'); await w.get('.dialog select').setValue('customer_receipt')
  await w.get('.dialog input[placeholder="客户或订单号"]').setValue('SO'); await flushPromises()
  await w.get('button.order').trigger('click'); await flushPromises()
  expect(w.findAll('button.order')).toHaveLength(0)
  expect(w.text()).toContain('已选择订单：SO-2026-FULL-000023')
  expect(w.text()).not.toContain('已选择订单：23')
  await w.get('.dialog input[type=number]').setValue('10'); await w.get('form.dialog').trigger('submit'); await flushPromises()
  expect(api.post).toHaveBeenCalledWith('/transactions/',expect.objectContaining({order:23}))
  expect(w.get('.notice').text()).toBe('财务流水已保存。')
  await click(w,'新增记账'); expect(w.find('.notice').exists()).toBe(false)
  await w.get('.dialog select').setValue('customer_receipt'); expect(w.text()).not.toContain('已选择订单：')
  w.unmount()
})
it('clears save and allocation success before void failure and retries without conflicting feedback', async () => {
  const row = {id:9,transaction_no:'FIN-QA-9',transaction_date:'2026-10-14',kind:'unallocated_advance',direction:'income',status:'confirmed',amount:'100',allocated_amount:'0',rmb_amount:'100',currency:'CNY',customer:2,allocations:[]}
  api.listAll.mockImplementation(async url => url === '/transactions/' ? [row] : url === '/payment-plans/' ? [{...plan,order:4,customer_id:2,direction:'receivable'}] : [])
  const {wrapper:w} = await page(TransactionPage,'/transactions')
  await click(w,'核销'); await flushPromises(); await w.get('form.dialog select').setValue('1'); await w.get('form.dialog').trigger('submit'); await flushPromises()
  expect(w.get('.notice').text()).toBe('核销已保存。')
  await click(w,'作废'); expect(w.find('.notice').exists()).toBe(false)
  await w.get('form.dialog textarea').setValue('验收作废')
  api.post.mockRejectedValueOnce(new Error('作废被拒绝')); await w.get('form.dialog').trigger('submit'); await flushPromises()
  expect(w.get('form.dialog [role=alert]').text()).toBe('作废被拒绝'); expect(w.find('.notice').exists()).toBe(false)
  await w.get('form.dialog').trigger('submit'); await flushPromises()
  expect(w.get('.notice').text()).toContain('财务流水已作废')
  await click(w,'核销'); await flushPromises(); expect(w.find('.notice').exists()).toBe(false); expect(w.find('[role=alert]').exists()).toBe(false)
  w.unmount()
})
