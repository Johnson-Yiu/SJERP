import { setAccessOperator } from '../src/accessControl'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import PaymentPlanPage from '../src/views/PaymentPlanPage.vue'

const financeAccount = id => setAccessOperator({ authenticated: true, user_id: id, has_all_permissions: true })
const savedKey = key => `sunjack:finance-attempt:v2:user:101:${key}`
beforeEach(() => { window.localStorage.clear(); financeAccount(101) })

const mocks = vi.hoisted(() => ({ listAll: vi.fn(), get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api: mocks, listAll: mocks.listAll }))

const options = { global: { directives: { 'money-input': {} } } }
const receivable = { id: 1, direction: 'receivable', contract_no: 'SO-2026-00032', counterparty_name: 'Alpha GmbH', due_date: '2026-10-15', currency: 'USD', planned_amount: '100', settled_amount: '0', remaining_amount: '100', remaining_rmb: 700, status: 'open', is_overdue: false }
const settled = { ...receivable, id: 2, contract_no: 'SO-2026-00033', counterparty_name: 'Beta GmbH', status: 'settled', settled_amount: '100', remaining_amount: '0' }

async function mountPage(direction = 'receivable') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/receivables', component: { template: '<main />' } },
      { path: '/payables', component: { template: '<main />' } },
    ],
  })
  await router.push(direction === 'payable' ? '/payables' : '/receivables')
  await router.isReady()
  return { wrapper: mount(PaymentPlanPage, { ...options, props: { direction }, global: { plugins: [router], ...options.global } }), router }
}

beforeEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
  window.sessionStorage.clear()
  mocks.listAll.mockResolvedValue([])
  mocks.post.mockResolvedValue({ data: {} })
  mocks.patch.mockResolvedValue({ data: {} })
})

describe('payment plan list filters', () => {
  it('recovers a possibly saved plan receipt with its original request identity', async () => {
    mocks.listAll.mockResolvedValue([receivable])
    mocks.post.mockRejectedValueOnce(new Error('connection lost')).mockResolvedValueOnce({ data: { id: 10 } })
    const first = await mountPage('receivable')
    await flushPromises()
    const action = first.wrapper.findAll('button').find(button => button.text() === '登记收款')
    await action.trigger('click')
    await first.wrapper.get('.dialog input[type="number"]').setValue('20')
    await first.wrapper.get('.dialog').trigger('submit.prevent')
    await flushPromises()
    const original = mocks.post.mock.calls[0]
    expect(original[2].headers['Idempotency-Key']).toMatch(/^PLAN-/)
    first.wrapper.unmount()

    mocks.listAll.mockResolvedValue([])
    mocks.get.mockResolvedValue({ data: { ...receivable, status: 'settled', remaining_amount: '0' } })
    const reopened = await mountPage('receivable')
    await flushPromises()
    expect(reopened.wrapper.text()).toContain('结果待确认')
    const recover = reopened.wrapper.findAll('button').find(button => button.text() === '按原内容核对')
    await recover.trigger('click')
    await flushPromises()
    await reopened.wrapper.get('.dialog').trigger('submit.prevent')
    await flushPromises()
    expect(mocks.post.mock.calls[1]).toEqual(original)
    expect(window.localStorage.getItem(savedKey('finance-plan-settle-1'))).toBeNull()
    reopened.wrapper.unmount()
  })

  it('always requests the active direction and reloads when direction changes', async () => {
    mocks.listAll.mockResolvedValue([receivable])
    const { wrapper } = await mountPage('receivable')
    await flushPromises()

    expect(mocks.listAll).toHaveBeenLastCalledWith('/payment-plans/', { params: { direction: 'receivable', status: 'open' } })
    expect(wrapper.find('input[aria-label="搜索往来方或合同号"]').attributes('placeholder')).toBe('搜索客户或销售订单号…')
    await wrapper.setProps({ direction: 'payable' })
    await flushPromises()

    expect(mocks.listAll).toHaveBeenLastCalledWith('/payment-plans/', { params: { direction: 'payable', status: 'open' } })
    expect(wrapper.find('input[aria-label="搜索往来方或合同号"]').attributes('placeholder')).toBe('搜索供应商或采购单号…')
    expect(mocks.listAll.mock.calls.every(([url]) => url === '/payment-plans/')).toBe(true)
    wrapper.unmount()
  })

  it('applies counterparty search and combined filters with a refreshable URL', async () => {
    const { wrapper, router } = await mountPage('payable')
    await flushPromises()
    await wrapper.find('select[aria-label="收付款计划状态"]').setValue('settled')
    await wrapper.find('input[aria-label="仅看逾期"]').setValue(true)
    await wrapper.find('input[aria-label="计划到期日从"]').setValue('2026-10-01')
    await wrapper.find('input[aria-label="计划到期日至"]').setValue('2026-10-31')
    await flushPromises()

    await wrapper.find('input[aria-label="搜索往来方或合同号"]').setValue('Supplier North')
    await wrapper.find('form.filters').trigger('submit')
    await flushPromises()

    expect(mocks.listAll.mock.calls.some(([url, config]) => url === '/payment-plans/' && JSON.stringify(config.params) === JSON.stringify({
      direction: 'payable', status: 'settled', overdue: 'true', search: 'Supplier North',
      due_from: '2026-10-01', due_to: '2026-10-31',
    }))).toBe(true)
    expect(router.currentRoute.value.query).toEqual({ search: 'Supplier North', status: 'settled', overdue: 'true', due_from: '2026-10-01', due_to: '2026-10-31' })
    expect(wrapper.find('input[aria-label="搜索往来方或合同号"]').attributes('placeholder')).toBe('搜索供应商或采购单号…')
    wrapper.unmount()
  })

  it('reset restores default filters for the active direction', async () => {
    const { wrapper } = await mountPage('receivable')
    await flushPromises()
    await wrapper.find('input[aria-label="搜索往来方或合同号"]').setValue('SO-2026-00032')
    await wrapper.find('select[aria-label="收付款计划状态"]').setValue('settled')
    await wrapper.find('input[aria-label="仅看逾期"]').setValue(true)
    await wrapper.find('input[aria-label="计划到期日从"]').setValue('2026-10-01')
    await wrapper.find('input[aria-label="计划到期日至"]').setValue('2026-10-31')
    await wrapper.find('form.filters').trigger('submit')
    await flushPromises()
    const callsBeforeReset = mocks.listAll.mock.calls.length
    await wrapper.find('button.filter-reset').trigger('click')
    await flushPromises()

    expect(wrapper.find('input[aria-label="搜索往来方或合同号"]').element.value).toBe('')
    expect(wrapper.find('select[aria-label="收付款计划状态"]').element.value).toBe('open')
    expect(wrapper.find('input[aria-label="仅看逾期"]').element.checked).toBe(false)
    expect(wrapper.find('input[aria-label="计划到期日从"]').element.value).toBe('')
    expect(wrapper.find('input[aria-label="计划到期日至"]').element.value).toBe('')
    expect(mocks.listAll.mock.calls.slice(callsBeforeReset).some(([url, config]) => url === '/payment-plans/' && config.params.direction === 'receivable' && config.params.status === 'open')).toBe(true)
    wrapper.unmount()
  })

  it('shows server-returned rows as-is and prevents an invalid date range request', async () => {
    mocks.listAll.mockResolvedValue([receivable, settled])
    const { wrapper } = await mountPage('receivable')
    await flushPromises()
    expect(wrapper.text()).toContain('SO-2026-00032')
    expect(wrapper.text()).toContain('SO-2026-00033')

    await wrapper.find('input[aria-label="计划到期日至"]').setValue('2026-10-01')
    await flushPromises()
    const requestCount = mocks.listAll.mock.calls.length
    await wrapper.find('input[aria-label="计划到期日从"]').setValue('2026-10-31')
    await flushPromises()

    expect(wrapper.text()).toContain('到期日开始日期不能晚于结束日期。')
    expect(mocks.listAll).toHaveBeenCalledTimes(requestCount)
    wrapper.unmount()
  })
})
