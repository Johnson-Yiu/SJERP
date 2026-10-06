// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), listAll: vi.fn() }))
vi.mock('../src/api.js', () => ({ api: mocks, listAll: mocks.listAll }))

import OrderDetailModal from '../src/components/OrderDetailModal.vue'

function createRouterForOrder() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/orders', component: { template: '<main />' } },
      { path: '/receivables', component: { template: '<main />' } },
    ],
  })
}

async function mountOrder({ status = 'confirmed', balance = '25.00' } = {}) {
  const router = createRouterForOrder()
  await router.push('/orders?detail=123')
  await router.isReady()
  mocks.get.mockImplementation(async url => {
    if (url.endsWith('/workbench/')) return { data: {
      order: { id: 123, order_no: 'SO-2026-00123', customer_name: 'PCR-020 UAT Customer', order_date: '2026-10-06', currency: 'USD', total_amount: '100.00', status, status_display: status },
      items: [], payments: [], payment_summary: { planned_amount: '100.00', paid_amount: String(100 - Number(balance)), balance_amount: String(balance) },
      fulfillment_summary: { ordered_quantity: 1, shipped_quantity: 1 }, profit_summary: {}, inventory: [], advance_allocations: [],
    } }
    if (url.endsWith('/fulfillment/')) return { data: { items: [], purchase_orders: [], shipments: [] } }
    if (url.endsWith('/packing-plan/')) return { data: null }
    if (url.endsWith('/procurement-plan/')) return { data: { items: [] } }
    if (url === '/operation-logs/') return { data: [] }
    if (url === '/session/current-operator/') return { data: {} }
    return { data: {} }
  })
  const wrapper = mount(OrderDetailModal, {
    props: { id: 123 },
    global: { plugins: [router], stubs: { OperationLogPanel: true, SupplierAllocationModal: true, ProcurementDraftModal: true, ContractAmountAdjustments: true, TradeUnitPicker: true } },
  })
  await flushPromises()
  return { wrapper, router }
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('OrderDetailModal receivable navigation', () => {
  it.each([
    ['confirmed', '25.00', true],
    ['shipped', '25.00', true],
    ['completed', '25.00', true],
    ['confirmed', '0.00', false],
    ['draft', '25.00', false],
    ['cancelled', '25.00', false],
  ])('shows receivable CTA for status=%s balance=%s: %s', async (status, balance, visible) => {
    const { wrapper } = await mountOrder({ status, balance })
    expect(wrapper.find('.receivable-cta').exists()).toBe(visible)
    wrapper.unmount()
  })

  it('routes the CTA to receivables scoped by the current Order ID', async () => {
    const { wrapper, router } = await mountOrder({ status: 'shipped', balance: '25.00' })
    const cta = wrapper.get('a.receivable-cta')
    expect(cta.text()).toBe('查看 / 登记本单应收')
    expect(cta.attributes('href')).toBe('/receivables?order=123')
    await cta.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/receivables?order=123')
    wrapper.unmount()
  })
})
