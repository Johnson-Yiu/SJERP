// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), listAll: vi.fn() }))
vi.mock('../src/api.js', () => ({ api: mocks, listAll: mocks.listAll }))

import PaymentPlanPage from '../src/views/PaymentPlanPage.vue'

const scopedPlan = {
  id: 88, direction: 'receivable', order: 123, contract_no: 'SO-2026-00123', counterparty_name: 'UAT Buyer',
  due_date: '2026-10-20', currency: 'USD', planned_amount: '100.00', settled_amount: '25.00',
  remaining_amount: '75.00', remaining_rmb: 525, exchange_rate: '7', status: 'open', is_overdue: false,
}

async function mountPage(path = '/receivables?order=123') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/receivables', component: { template: '<main />' } },
      { path: '/payables', component: { template: '<main />' } },
      { path: '/orders', component: { template: '<main />' } },
    ],
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(PaymentPlanPage, {
    props: { direction: router.currentRoute.value.path === '/payables' ? 'payable' : 'receivable' },
    global: { plugins: [router], directives: { 'money-input': {} } },
  })
  await flushPromises()
  return { wrapper, router }
}

beforeEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
  mocks.get.mockImplementation(async url => {
    if (url === '/orders/123/') return { data: { id: 123, order_no: 'SO-2026-00123' } }
    if (url === '/orders/456/') return { data: { id: 456, order_no: 'SO-2026-00456' } }
    return { data: {} }
  })
  mocks.listAll.mockResolvedValue([scopedPlan])
  mocks.post.mockResolvedValue({ data: {} })
  mocks.patch.mockResolvedValue({ data: {} })
})

afterEach(() => vi.useRealTimers())

describe('receivable Order context', () => {
  it('loads direct URLs from the backend with the Order filter and shows trusted context', async () => {
    const { wrapper } = await mountPage('/receivables?order=123')
    expect(mocks.listAll).toHaveBeenCalledWith('/payment-plans/', { params: { direction: 'receivable', order: '123', status: 'open' } })
    expect(wrapper.find('.order-context-banner').exists()).toBe(true)
    expect(wrapper.find('.order-context-banner').text()).toContain('当前仅显示订单：SO-2026-00123')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(wrapper.text()).toContain('SO-2026-00123')
    wrapper.unmount()
  })

  it('opens the exact Order workspace from the context banner', async () => {
    const { wrapper, router } = await mountPage('/receivables?order=123')
    await wrapper.get('.order-context-banner a').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/orders?detail=123')
    wrapper.unmount()
  })

  it('preserves Order context across status, overdue, date, and search filters', async () => {
    vi.useFakeTimers()
    const { wrapper, router } = await mountPage('/receivables?order=123&source=order-workspace')
    mocks.listAll.mockClear()

    await wrapper.find('select[aria-label="收付款计划状态"]').setValue('settled')
    await flushPromises()
    expect(mocks.listAll).toHaveBeenLastCalledWith('/payment-plans/', { params: { direction: 'receivable', order: '123', status: 'settled' } })
    await wrapper.find('input[aria-label="仅看逾期"]').setValue(true)
    await wrapper.find('input[aria-label="到期日从"]').setValue('2026-10-01')
    await wrapper.find('input[aria-label="到期日至"]').setValue('2026-10-31')
    await flushPromises()
    expect(mocks.listAll).toHaveBeenLastCalledWith('/payment-plans/', { params: {
      direction: 'receivable', order: '123', status: 'settled', overdue: 'true', due_from: '2026-10-01', due_to: '2026-10-31',
    } })

    await wrapper.find('input[aria-label="搜索往来方或合同号"]').setValue('UAT Buyer')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    expect(mocks.listAll).toHaveBeenLastCalledWith('/payment-plans/', { params: {
      direction: 'receivable', order: '123', status: 'settled', overdue: 'true', search: 'UAT Buyer', due_from: '2026-10-01', due_to: '2026-10-31',
    } })
    expect(router.currentRoute.value.query).toEqual({ order: '123', source: 'order-workspace' })
    wrapper.unmount()
  })

  it('clears only the Order query and reloads the ordinary Receivables list', async () => {
    const { wrapper, router } = await mountPage('/receivables?order=123&source=dashboard')
    await wrapper.get('.order-context-banner button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ source: 'dashboard' })
    expect(wrapper.find('.order-context-banner').exists()).toBe(false)
    expect(mocks.listAll).toHaveBeenLastCalledWith('/payment-plans/', { params: { direction: 'receivable', status: 'open' } })
    wrapper.unmount()
  })

  it('handles malformed context safely and lets the user clear it', async () => {
    const { wrapper, router } = await mountPage('/receivables?order=not-an-id')
    expect(wrapper.find('.order-context-banner').text()).toContain('订单筛选编号无效')
    expect(mocks.get).not.toHaveBeenCalled()
    expect(mocks.listAll).not.toHaveBeenCalled()
    await wrapper.get('.order-context-banner button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({})
    expect(mocks.listAll).toHaveBeenLastCalledWith('/payment-plans/', { params: { direction: 'receivable', status: 'open' } })
    wrapper.unmount()
  })

  it('shows a recoverable error for a numeric Order that cannot be fetched', async () => {
    mocks.get.mockRejectedValue(new Error('not found'))
    const { wrapper } = await mountPage('/receivables?order=999')
    expect(wrapper.text()).toContain('无法加载订单信息')
    expect(wrapper.find('.order-context-banner button').exists()).toBe(true)
    expect(mocks.listAll).toHaveBeenLastCalledWith('/payment-plans/', { params: { direction: 'receivable', order: '999', status: 'open' } })
    wrapper.unmount()
  })

  it('does not apply a sales Order query to Payables', async () => {
    const { wrapper } = await mountPage('/payables?order=123')
    expect(mocks.get).not.toHaveBeenCalled()
    expect(mocks.listAll).toHaveBeenCalledWith('/payment-plans/', { params: { direction: 'payable', status: 'open' } })
    expect(wrapper.find('.order-context-banner').exists()).toBe(false)
    wrapper.unmount()
  })

  it('keeps the existing settlement form available for the scoped plan', async () => {
    const { wrapper } = await mountPage('/receivables?order=123')
    await wrapper.findAll('button').find(button => button.text() === '登记收款').trigger('click')
    expect(wrapper.get('form.dialog p').text()).toContain('SO-2026-00123')
    expect(wrapper.get('form.dialog p').text()).toContain('UAT Buyer')
    await wrapper.find('form.dialog footer button[type="button"]').trigger('click')
    expect(wrapper.find('form.dialog').exists()).toBe(false)
    expect(mocks.post).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})
