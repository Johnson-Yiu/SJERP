// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

const mocks = vi.hoisted(() => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  listAll: vi.fn(),
}))

vi.mock('../src/api.js', () => ({
  api: mocks.api,
  listAll: mocks.listAll,
  listData: response => response.data?.results || response.data || [],
}))

import OrderDetailModal from '../src/components/OrderDetailModal.vue'
import PurchaseOrderPage from '../src/views/PurchaseOrderPage.vue'
import { routes } from '../src/router.js'

const sourceOrder = { id: 11, order_no: 'SO-UAT-SOURCE' }
const allocatedOrder = { id: 22, order_no: 'SO-UAT-ALLOC' }
const secondAllocatedOrder = { id: 33, order_no: 'SO-UAT-ALLOC-2' }

function purchase(overrides = {}) {
  return {
    id: 41,
    purchase_no: 'PO-UAT-NAV-41',
    supplier: 9,
    supplier_name: 'PCR-004 UAT Supplier',
    order: sourceOrder.id,
    order_no: sourceOrder.order_no,
    related_orders: [allocatedOrder],
    order_date: '2026-10-01',
    expected_arrival_date: '2026-10-12',
    currency: 'CNY',
    exchange_rate: '1',
    total_amount: '2.00',
    paid_amount: '0.00',
    unpaid_amount: '2.00',
    status: 'ordered',
    status_display: '已下单',
    items: [{
      id: 70,
      sku: 3,
      sku_code: 'UAT-SKU-3',
      display_name: 'UAT navigation item',
      quantity: '1.00',
      remaining_quantity: '1.00',
      received_quantity: '0.00',
      unit_price: '2.00',
      trade_unit: null,
      trade_snapshot: { base_unit: 'pcs', factor: 1 },
      receipts: [],
    }],
    ...overrides,
  }
}

function createTestRouter() {
  return createRouter({ history: createMemoryHistory(), routes })
}

async function mountPurchasePage(row, path = `/purchase-orders?detail=${row.id}`) {
  const router = createTestRouter()
  await router.push(path)
  mocks.listAll.mockImplementation(async url => {
    if (url === '/purchase-orders/') return [row]
    if (url === '/suppliers/') return [{ id: 9, name: row.supplier_name }]
    if (url === '/orders/') return [sourceOrder, allocatedOrder, secondAllocatedOrder]
    if (url === '/skus/') return []
    return []
  })
  const wrapper = mount(PurchaseOrderPage, {
    global: {
      plugins: [router],
      directives: { 'money-input': {} },
      stubs: {
        ContractAmountAdjustments: true,
        PurchaseCostAllocationModal: true,
        PurchasePaymentModal: true,
        PurchaseSupplierPicker: true,
        SkuPickerPanel: true,
        SummaryCards: true,
        TradeUnitPicker: true,
      },
    },
  })
  await flushPromises()
  return { wrapper, router }
}

async function recordReceipt(wrapper) {
  await wrapper.findAll('.workbench-tabs button').find(button => button.text() === '收货').trigger('click'); await flushPromises()
  await wrapper.findAll('.purchase-detail button').find(button => button.text().includes('验货入库')).trigger('click')
  await flushPromises()
  await wrapper.get('.receipt-dialog input[type="checkbox"]').setValue(true)
  await wrapper.get('form.receipt-dialog').trigger('submit')
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.api.post.mockResolvedValue({ data: {} })
  mocks.api.get.mockImplementation(async url => {
    if (url.endsWith('/workbench/')) return { data: {
      order: { id: 101, order_no: 'SO-UAT-ORDER', customer_name: 'PCR-004 UAT Customer', order_date: '2026-10-01', currency: 'USD', total_amount: '100', status: 'confirmed', status_display: '已确认' },
      items: [], payments: [], payment_summary: { planned_amount: '100', paid_amount: '0', balance_amount: '100' },
      fulfillment_summary: { ordered_quantity: 0, shipped_quantity: 0 }, profit_summary: {},
    } }
    if (url.endsWith('/fulfillment/')) return { data: {
      items: [],
      purchase_orders: [{ ...purchase(), related_orders: [allocatedOrder] }],
      shipments: [],
    } }
    if (url.endsWith('/packing-plan/')) return { data: null }
    if (url.endsWith('/procurement-plan/')) return { data: { items: [] } }
    if (url === '/operation-logs/') return { data: [] }
    if (url === '/session/current-operator/') return { data: {} }
    return { data: {} }
  })
  mocks.listAll.mockResolvedValue([])
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('purchase order navigation and receipt links', () => {
  it('opens the purchase detail from an order workbench and browser Back restores the order detail', async () => {
    const router = createTestRouter()
    await router.push('/orders?detail=101&edit=8&returnTo=%2Fquotes')
    const wrapper = mount(OrderDetailModal, {
      props: { id: 101 },
      global: {
        plugins: [router],
        stubs: { ContractAmountAdjustments: true, OperationLogPanel: true, ProcurementDraftModal: true, SupplierAllocationModal: true, TradeUnitPicker: true },
      },
    })
    await flushPromises()
    await wrapper.findAll('.workbench-tabs button').find(button => button.text().includes('采购与发货')).trigger('click'); await flushPromises()

    const purchaseLink = wrapper.get('a.purchase-navigation-link')
    expect(purchaseLink.attributes('href')).toMatch(/^\/purchase-orders\?detail=41&tab=overview&returnTo=/)
    await purchaseLink.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toMatch(/^\/purchase-orders\?detail=41&tab=overview&returnTo=/)
    expect(router.currentRoute.value.query).toMatchObject({ detail: '41', tab: 'overview' })

    await router.back()
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/orders?detail=101&edit=8&returnTo=/quotes&tab=fulfillment')
    wrapper.unmount()
  })

  it('keeps source order and allocated order distinct in the purchase detail', async () => {
    const row = purchase({ related_orders: [allocatedOrder, secondAllocatedOrder] })
    const { wrapper, router } = await mountPurchasePage(row)

  await wrapper.findAll('.workbench-tabs button').find(button => button.text() === '关联销售订单').trigger('click'); await flushPromises()
    const sourceLink = wrapper.get('a[aria-label="查看来源订单 SO-UAT-SOURCE"]')
    const relatedLinks = wrapper.findAll('.related-order-panel a.order-navigation-link')
    expect(sourceLink.attributes('href')).toMatch(/^\/orders\?detail=11&tab=overview&returnTo=/)
    expect(relatedLinks.map(link => link.text())).toEqual(['SO-UAT-ALLOC', 'SO-UAT-ALLOC-2'])
    expect(relatedLinks.map(link => new URL(link.attributes('href'), 'http://localhost').searchParams.get('detail'))).toEqual(['22', '33'])
    expect(relatedLinks.every(link => new URL(link.attributes('href'), 'http://localhost').searchParams.get('returnTo') === '/purchase-orders?detail=41&tab=orders')).toBe(true)

    await relatedLinks[0].trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toMatch(/^\/orders\?detail=22&tab=overview&returnTo=/)
    expect(router.currentRoute.value.query).toMatchObject({ detail: '22', tab: 'overview' })
    await router.back()
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/purchase-orders?detail=41&tab=orders')
    wrapper.unmount()
  })

  it('receipt success shows one CTA for one allocated order and none for inventory-only allocation', async () => {
    const allocated = purchase({ related_orders: [allocatedOrder] })
    const first = await mountPurchasePage(allocated)
    await recordReceipt(first.wrapper)
    expect(first.wrapper.get('.receipt-success').text()).toContain('验货入库已完成，库存、预留及在途数量已同步。')
    expect(first.wrapper.findAll('.receipt-success a.order-navigation-link').map(link => link.text())).toEqual(['查看关联订单 SO-UAT-ALLOC'])
    expect(first.wrapper.get('.receipt-success a.order-navigation-link').attributes('href')).toMatch(/^\/orders\?detail=22&tab=overview&returnTo=/)
    first.wrapper.unmount()

    vi.clearAllMocks()
    mocks.api.post.mockResolvedValue({ data: {} })
    const inventoryOnly = purchase({ related_orders: [] })
    const second = await mountPurchasePage(inventoryOnly)
    await recordReceipt(second.wrapper)
    expect(second.wrapper.get('.receipt-success').text()).toContain('验货入库已完成，库存、预留及在途数量已同步。')
    expect(second.wrapper.findAll('.receipt-success a.order-navigation-link')).toHaveLength(0)
    second.wrapper.unmount()
  })

  it('receipt success exposes each related order when allocations span multiple orders', async () => {
    const row = purchase({ related_orders: [allocatedOrder, secondAllocatedOrder] })
    const { wrapper } = await mountPurchasePage(row)
    await recordReceipt(wrapper)

    expect(wrapper.get('.receipt-success').text()).toContain('关联订单：')
    expect(wrapper.findAll('.receipt-success a.order-navigation-link').map(link => link.text())).toEqual([
      'SO-UAT-ALLOC', 'SO-UAT-ALLOC-2',
    ])
    expect(wrapper.findAll('.receipt-success a.order-navigation-link').map(link => new URL(link.attributes('href'), 'http://localhost').searchParams.get('detail'))).toEqual([
      '22', '33',
    ])
    wrapper.unmount()
  })
  it('opens existing cost and payment modals from the authoritative workbench', async () => {
    const row = purchase()
    const { wrapper } = await mountPurchasePage(row)
    await wrapper.findAll('button').find(button => button.text() === '分配采购成本 / 公共费用').trigger('click')
    expect(wrapper.getComponent({ name: 'PurchaseCostAllocationModal' }).props('purchase')).toEqual(row)
    await wrapper.findAll('button').find(button => button.text() === '登记付款').trigger('click')
    expect(wrapper.getComponent({ name: 'PurchasePaymentModal' }).props('purchase')).toEqual(row)
    wrapper.unmount()
  })

})
