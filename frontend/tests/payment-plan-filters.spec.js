import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import PaymentPlanPage from '../src/views/PaymentPlanPage.vue'

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
  mocks.listAll.mockResolvedValue([])
  mocks.post.mockResolvedValue({ data: {} })
  mocks.patch.mockResolvedValue({ data: {} })
})

describe('payment plan list filters', () => {
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

  it('debounces counterparty search and combines it with status, overdue, and due dates', async () => {
    vi.useFakeTimers()
    const { wrapper } = await mountPage('payable')
    await flushPromises()
    await wrapper.find('select[aria-label="收付款计划状态"]').setValue('settled')
    await wrapper.find('input[aria-label="仅看逾期"]').setValue(true)
    await wrapper.find('input[aria-label="到期日从"]').setValue('2026-10-01')
    await wrapper.find('input[aria-label="到期日至"]').setValue('2026-10-31')
    await flushPromises()

    const callsBeforeSearch = mocks.listAll.mock.calls.length
    await wrapper.find('input[aria-label="搜索往来方或合同号"]').setValue('Supplier North')
    await flushPromises()
    await vi.advanceTimersByTimeAsync(299)
    expect(mocks.listAll).toHaveBeenCalledTimes(callsBeforeSearch)
    await vi.advanceTimersByTimeAsync(1)
    await flushPromises()

    expect(mocks.listAll).toHaveBeenLastCalledWith('/payment-plans/', { params: {
      direction: 'payable', status: 'settled', overdue: 'true', search: 'Supplier North',
      due_from: '2026-10-01', due_to: '2026-10-31',
    } })
    expect(wrapper.find('input[aria-label="搜索往来方或合同号"]').attributes('placeholder')).toBe('搜索供应商或采购单号…')
    wrapper.unmount()
  })

  it('reset restores default filters for the active direction', async () => {
    vi.useFakeTimers()
    const { wrapper } = await mountPage('receivable')
    await flushPromises()
    await wrapper.find('input[aria-label="搜索往来方或合同号"]').setValue('SO-2026-00032')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    await wrapper.find('select[aria-label="收付款计划状态"]').setValue('settled')
    await wrapper.find('input[aria-label="仅看逾期"]').setValue(true)
    await wrapper.find('input[aria-label="到期日从"]').setValue('2026-10-01')
    await wrapper.find('input[aria-label="到期日至"]').setValue('2026-10-31')
    await flushPromises()
    await wrapper.find('button.filter-reset').trigger('click')
    await flushPromises()

    expect(wrapper.find('input[aria-label="搜索往来方或合同号"]').element.value).toBe('')
    expect(wrapper.find('select[aria-label="收付款计划状态"]').element.value).toBe('open')
    expect(wrapper.find('input[aria-label="仅看逾期"]').element.checked).toBe(false)
    expect(wrapper.find('input[aria-label="到期日从"]').element.value).toBe('')
    expect(wrapper.find('input[aria-label="到期日至"]').element.value).toBe('')
    expect(mocks.listAll).toHaveBeenLastCalledWith('/payment-plans/', { params: { direction: 'receivable', status: 'open' } })
    const resetCallCount = mocks.listAll.mock.calls.length
    await vi.advanceTimersByTimeAsync(300)
    expect(mocks.listAll).toHaveBeenCalledTimes(resetCallCount)
    wrapper.unmount()
  })

  it('shows server-returned rows as-is and prevents an invalid date range request', async () => {
    mocks.listAll.mockResolvedValue([receivable, settled])
    const { wrapper } = await mountPage('receivable')
    await flushPromises()
    expect(wrapper.text()).toContain('SO-2026-00032')
    expect(wrapper.text()).toContain('SO-2026-00033')

    await wrapper.find('input[aria-label="到期日至"]').setValue('2026-10-01')
    await flushPromises()
    const requestCount = mocks.listAll.mock.calls.length
    await wrapper.find('input[aria-label="到期日从"]').setValue('2026-10-31')
    await flushPromises()

    expect(wrapper.text()).toContain('到期日开始日期不能晚于结束日期。')
    expect(mocks.listAll).toHaveBeenCalledTimes(requestCount)
    wrapper.unmount()
  })
})
