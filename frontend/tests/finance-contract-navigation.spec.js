import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PaymentPlanPage from '../src/views/PaymentPlanPage.vue'
import TransactionPage from '../src/views/TransactionPage.vue'
import FinanceDashboardPage from '../src/views/FinanceDashboardPage.vue'

const { listAll, get } = vi.hoisted(() => ({ listAll: vi.fn(), get: vi.fn() }))

vi.mock('../src/api', () => ({
  api: { get, post: vi.fn(), patch: vi.fn() },
  listAll,
}))

const routeTargets = ['/receivables', '/payables', '/transactions', '/finance', '/orders', '/purchase-orders']

async function mountOn(page, path, props = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: routeTargets.map(route => ({ path: route, component: { template: '<main />' } })),
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(page, { props, global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

const planRow = overrides => ({
  id: 1, order: null, purchase_order: null, contract_no: 'CUSTOM-CONTRACT',
  due_date: '2026-10-05', counterparty_name: 'UAT Counterparty', currency: 'USD',
  planned_amount: '10.0000', settled_amount: '0.0000', remaining_amount: '10.0000',
  status: 'open', is_overdue: false, ...overrides,
})

const transactionRows = [
  { id: 1, order: 41, order_no: 'CUSTOM-SALES-41', purchase_order: null, purchase_no: '', customer_name: 'Buyer', kind: 'customer_receipt', direction: 'income', transaction_date: '2026-10-05', transaction_no: 'TX-1', currency: 'USD', amount: '10', rmb_amount: '70', status: 'confirmed', status_display: '已确认', allocations: [] },
  { id: 2, order: null, order_no: '', purchase_order: 52, purchase_no: 'CUSTOM-PURCHASE-52', supplier_name: 'Supplier', kind: 'supplier_payment', direction: 'expense', transaction_date: '2026-10-05', transaction_no: 'TX-2', currency: 'USD', amount: '10', rmb_amount: '70', status: 'confirmed', status_display: '已确认', allocations: [] },
  { id: 3, order: null, order_no: 'SO-STALE-WITHOUT-ID', purchase_order: null, purchase_no: '', kind: 'other_income', direction: 'income', transaction_date: '2026-10-05', transaction_no: 'TX-3', currency: 'USD', amount: '10', rmb_amount: '70', status: 'confirmed', status_display: '已确认', allocations: [] },
  { id: 4, order: null, order_no: '', purchase_order: null, purchase_no: '', kind: 'unallocated_advance', direction: 'income', transaction_date: '2026-10-05', transaction_no: 'TX-4', currency: 'USD', amount: '20', allocated_amount: '15', rmb_amount: '140', status: 'confirmed', status_display: '已确认', allocations: [
    { id: 401, contract_no: 'CUSTOM-ALLOC-SALES', order: 61, purchase_order: null, amount: '5.0000', is_active: true },
    { id: 402, contract_no: 'CUSTOM-ALLOC-PURCHASE', order: null, purchase_order: 72, amount: '10.0000', is_active: false },
    { id: 403, contract_no: 'SO-HISTORICAL-NO-ID', order: null, purchase_order: null, amount: '1.0000', is_active: false },
  ] },
]

describe('finance contract navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    listAll.mockImplementation(async path => {
      if (path === '/payment-plans/') return []
      if (path === '/transactions/') return transactionRows
      return []
    })
    get.mockResolvedValue({ data: { metrics: {}, due_items: [], monthly_cash: [], categories: [] } })
  })

  it('routes a receivable contract by its order ID and leaves a missing ID as text', async () => {
    listAll.mockResolvedValueOnce([
      planRow({ id: 11, order: 31, contract_no: 'CUSTOM-SALES-31' }),
      planRow({ id: 12, order: null, contract_no: 'SO-LEGACY-NO-ID' }),
    ])
    const { wrapper } = await mountOn(PaymentPlanPage, '/receivables', { direction: 'receivable' })
    expect(wrapper.find('a[href="/orders?detail=31"]').text()).toBe('CUSTOM-SALES-31')
    expect(wrapper.find('a').exists()).toBe(true)
    expect(wrapper.find('tbody tr:nth-child(2) td:nth-child(2) a').exists()).toBe(false)
    expect(wrapper.find('tbody tr:nth-child(2) td:nth-child(2)').text()).toBe('SO-LEGACY-NO-ID')
  })

  it('routes a payable contract by its purchase order ID', async () => {
    listAll.mockResolvedValueOnce([planRow({ id: 13, purchase_order: 44, contract_no: 'CUSTOM-BUY-44' })])
    const { wrapper } = await mountOn(PaymentPlanPage, '/payables', { direction: 'payable' })
    expect(wrapper.find('a[href="/purchase-orders?detail=44"]').text()).toBe('CUSTOM-BUY-44')
  })

  it('routes direct transactions and allocation history by IDs, including inactive history', async () => {
    const { wrapper } = await mountOn(TransactionPage, '/transactions')
    expect(wrapper.find('a[href="/orders?detail=41"]').text()).toBe('CUSTOM-SALES-41')
    expect(wrapper.find('a[href="/purchase-orders?detail=52"]').text()).toBe('CUSTOM-PURCHASE-52')
    expect(wrapper.text()).toContain('未关联合同')
    expect(wrapper.find('tbody tr:nth-child(3) td:nth-child(3) a').exists()).toBe(false)
    expect(wrapper.find('a[href="/orders?detail=61"]').text()).toBe('CUSTOM-ALLOC-SALES')
    const inactive = wrapper.find('a[href="/purchase-orders?detail=72"]')
    expect(inactive.text()).toBe('CUSTOM-ALLOC-PURCHASE')
    expect(inactive.element.parentElement.textContent).toContain('10.00 已撤回')
    expect(wrapper.find('tbody tr:nth-child(4) td:nth-child(6)').text()).toContain('SO-HISTORICAL-NO-ID：1.00 已撤回')
    expect(wrapper.find('tbody tr:nth-child(4) td:nth-child(6) a[href*="detail="]').exists()).toBe(true)
    expect(wrapper.findAll('a[href*="SO-HISTORICAL-NO-ID"]').length).toBe(0)
  })

  it('keeps Finance Dashboard due links for both contract directions', async () => {
    get.mockResolvedValueOnce({ data: { metrics: {}, monthly_cash: [], categories: [], due_items: [
      { id: 1, direction: 'receivable', order: 83, purchase_order: null, contract_no: 'CUSTOM-DUE-SALES', counterparty_name: 'Buyer', due_date: '2026-10-05', currency: 'USD', remaining_amount: 1 },
      { id: 2, direction: 'payable', order: null, purchase_order: 94, contract_no: 'CUSTOM-DUE-PURCHASE', counterparty_name: 'Supplier', due_date: '2026-10-05', currency: 'USD', remaining_amount: 1 },
    ] } })
    const { wrapper } = await mountOn(FinanceDashboardPage, '/finance')
    expect(wrapper.find('a[href="/orders?detail=83"]').text()).toBe('CUSTOM-DUE-SALES')
    expect(wrapper.find('a[href="/purchase-orders?detail=94"]').text()).toBe('CUSTOM-DUE-PURCHASE')
  })
})
