// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'

const mocks = vi.hoisted(() => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  listAll: vi.fn(),
  confirmDialog: vi.fn(),
}))

vi.mock('../src/api.js', () => ({ api: mocks.api, listAll: mocks.listAll }))
vi.mock('../src/dialogs.js', () => ({ confirmDialog: mocks.confirmDialog }))

import OrderDetailModal from '../src/components/OrderDetailModal.vue'

const baseLines = [
  { id: 701, sku: 10, sku_code: 'UAT-SKU-A', display_name: 'UAT Lamp A', base_unit: 'pcs', quantity: '6.00', allocated_quantity: '6.00', to_procure_quantity: '0', draft_procurement_quantity: '0', purchased_quantity: '0', arrived_quantity: '6', in_transit_quantity: '0', shipped_quantity: '0', unshipped_quantity: '6.00' },
  { id: 702, sku: 10, sku_code: 'UAT-SKU-A', display_name: 'UAT Lamp A alternate package', base_unit: 'pcs', quantity: '4.00', allocated_quantity: '4.00', to_procure_quantity: '0', draft_procurement_quantity: '0', purchased_quantity: '0', arrived_quantity: '4', in_transit_quantity: '0', shipped_quantity: '0', unshipped_quantity: '4.00' },
  { id: 703, sku: 20, sku_code: 'UAT-SKU-B', display_name: 'UAT Strip B', base_unit: 'm', quantity: '5.00', allocated_quantity: '5.00', to_procure_quantity: '0', draft_procurement_quantity: '0', purchased_quantity: '0', arrived_quantity: '5', in_transit_quantity: '0', shipped_quantity: '0', unshipped_quantity: '5.00' },
]

function currentWorkbench(status = 'confirmed') {
  return {
    order: { id: 321, order_no: 'SO-UAT-BATCH-321', customer_name: 'PCR-006 UAT Customer', order_date: '2026-10-06', currency: 'USD', total_amount: '100.00', status, status_display: status },
    items: baseLines.map(line => ({ id: line.id, sku: line.sku, quantity: line.quantity, trade_unit: null, trade_snapshot: { base_unit: line.base_unit, factor: '1' } })),
    payments: [], payment_summary: { planned_amount: '100', paid_amount: '0', balance_amount: '100' },
    fulfillment_summary: { ordered_quantity: 15, shipped_quantity: 0 }, profit_summary: {}, inventory: [], advance_allocations: [],
  }
}

function shipmentSku(id) {
  if (id === 10) return { id, sku: 'UAT-SKU-A', unit: 'pcs', trade_units: [{ id: 71, name: '双只装', unit: 'pack', factor: '2', base_unit: 'pcs', active: true, allow_fraction: false }] }
  return { id, sku: 'UAT-SKU-B', unit: 'm', trade_units: [] }
}

function setupApi({ status = 'confirmed', lines = baseLines, shipments = [], postError = null } = {}) {
  let fulfillmentLoads = 0
  mocks.api.get.mockImplementation(async (url) => {
    if (url.endsWith('/workbench/')) return { data: currentWorkbench(status) }
    if (url.endsWith('/fulfillment/')) {
      fulfillmentLoads += 1
      return { data: { items: lines.map(line => ({ ...line })), purchase_orders: [], shipments: shipments.map(row => ({ ...row, items: row.items.map(item => ({ ...item })) })) } }
    }
    if (url.endsWith('/packing-plan/')) return { data: null }
    if (url.endsWith('/procurement-plan/')) return { data: { items: [] } }
    if (url === '/operation-logs/') return { data: [] }
    if (url === '/session/current-operator/') return { data: {} }
    if (/^\/skus\/\d+\/$/.test(url)) return { data: shipmentSku(Number(url.match(/\d+/)[0])) }
    return { data: {} }
  })
  mocks.api.post.mockImplementation(async (url) => {
    if (url === '/orders/321/ship/' && postError) throw postError
    return { data: {} }
  })
  return () => fulfillmentLoads
}

let wrappers

async function settle() {
  await flushPromises()
  await nextTick()
  await flushPromises()
}

async function mountOrder(options = {}) {
  const wrapper = mount(OrderDetailModal, {
    props: { id: 321 },
    attachTo: document.body,
    global: { stubs: { OperationLogPanel: true, SupplierAllocationModal: true, ProcurementDraftModal: true, ContractAmountAdjustments: true, RouterLink: true } },
  })
  wrappers.push(wrapper)
  await settle()
  await wrapper.findAll('.workbench-tabs button').find(button => button.text().includes('采购与发货')).trigger('click')
  await settle()
  return wrapper
}

function dialog() { return document.body.querySelector('.shipment-batch-dialog') }
function shipmentPostCalls() { return mocks.api.post.mock.calls.filter(([url]) => url === '/orders/321/ship/') }
async function setDialogField(selector, value, eventName = 'input') {
  const field = dialog().querySelector(selector)
  field.value = value
  field.dispatchEvent(new Event(eventName, { bubbles: true }))
  await settle()
}
async function submitDialog() {
  dialog().dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  await settle()
}

beforeEach(() => {
  wrappers = []
  vi.clearAllMocks()
  mocks.listAll.mockResolvedValue([])
  mocks.confirmDialog.mockResolvedValue(true)
})

afterEach(() => {
  wrappers.forEach(wrapper => wrapper.unmount())
  document.body.innerHTML = ''
})

describe('OrderDetailModal batch shipment', () => {
  it('shows batch action for confirmed, production, and partially shipped orders with remaining lines', async () => {
    for (const status of ['confirmed', 'production', 'shipped']) {
      setupApi({ status })
      const wrapper = await mountOrder()
      expect(wrapper.text()).toContain('批量发货')
      wrapper.unmount()
      wrappers.pop()
    }
  })

  it('hides batch shipment if no lines remain or the order status does not permit shipping', async () => {
    setupApi({ lines: baseLines.map(line => ({ ...line, unshipped_quantity: '0.00' })) })
    const completedLines = await mountOrder()
    expect(completedLines.text()).not.toContain('批量发货')
    completedLines.unmount()
    wrappers.pop()
    for (const status of ['draft', 'cancelled', 'completed']) {
      setupApi({ status })
      const wrapper = await mountOrder()
      expect(wrapper.text()).not.toContain('批量发货')
      expect(wrapper.findAll('.fulfillment-ship-action')).toHaveLength(0)
      wrapper.unmount()
      wrappers.pop()
    }
  })

  it('opens the shared batch dialog with all shippable OrderItems selected and default quantities', async () => {
    const getFulfillmentLoads = setupApi()
    const wrapper = await mountOrder()
    await wrapper.findAll('button').find(button => button.text() === '批量发货').trigger('click')
    await settle()

    expect(dialog()).not.toBeNull()
    expect(dialog().querySelectorAll('.shipment-batch-line')).toHaveLength(3)
    expect([...dialog().querySelectorAll('.shipment-line-toggle input')].every(input => input.checked)).toBe(true)
    expect([...dialog().querySelectorAll('input[aria-label^="发货数量"]')].map(input => input.value)).toEqual(['6.00', '4.00', '5.00'])
    expect(dialog().textContent).toContain('已选 3 条明细')
    expect(dialog().querySelector('input[aria-label="发货日期"]').value).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(mocks.api.get.mock.calls.filter(([url]) => url === '/skus/10/')).toHaveLength(1)
    expect(mocks.api.get.mock.calls.filter(([url]) => url === '/skus/20/')).toHaveLength(1)
    expect(getFulfillmentLoads()).toBe(1)
  })

  it('omits unchecked lines, allows partial quantity, and submits one request with distinct same-SKU OrderItem IDs', async () => {
    setupApi()
    const wrapper = await mountOrder()
    await wrapper.findAll('button').find(button => button.text() === '批量发货').trigger('click')
    await settle()
    const checks = dialog().querySelectorAll('.shipment-line-toggle input')
    checks[2].click()
    await nextTick()
    await setDialogField('input[aria-label="发货数量 UAT-SKU-A 明细 #701"]', '2.5')
    await setDialogField('input[aria-label="发货日期"]', '2026-10-05')
    await submitDialog()

    expect(shipmentPostCalls()).toHaveLength(1)
    expect(shipmentPostCalls()[0][1]).toEqual({ shipment_date: '2026-10-05', items: [
      { order_item: 701, quantity: 2.5, trade_unit: null, overage_reason: '' },
      { order_item: 702, quantity: '4.00', trade_unit: null, overage_reason: '' },
    ] })
    expect(dialog()).toBeNull()
  })

  it('row-level shipment opens the same dialog with only the clicked OrderItem selected', async () => {
    setupApi()
    const wrapper = await mountOrder()
    await wrapper.findAll('.text-btn').find(button => button.text() === '确认发货').trigger('click')
    await settle()
    const selected = [...dialog().querySelectorAll('.shipment-line-toggle input')].map(input => input.checked)
    expect(selected).toEqual([true, false, false])
    expect(dialog().querySelectorAll('input[aria-label^="发货数量"]')).toHaveLength(1)
    expect(mocks.api.post).not.toHaveBeenCalledWith('/orders/321/ship/', expect.anything())
  })

  it('converts each selected line with the existing TradeUnitPicker and tradePayload behavior', async () => {
    setupApi()
    const wrapper = await mountOrder()
    await wrapper.findAll('button').find(button => button.text() === '批量发货').trigger('click')
    await settle()
    const tradeUnits = dialog().querySelectorAll('select[aria-label="交易单位与包装规格"]')
    await setDialogField('select[aria-label="交易单位与包装规格"]', '71', 'change')
    const firstQty = dialog().querySelector('input[aria-label="发货数量 UAT-SKU-A 明细 #701"]')
    expect(firstQty.value).toBe('3')
    await setDialogField('input[aria-label="发货数量 UAT-SKU-A 明细 #701"]', '2')
    await submitDialog()

    expect(tradeUnits).toHaveLength(3)
    expect(shipmentPostCalls()).toHaveLength(1)
    const items = shipmentPostCalls()[0][1].items
    expect(items[0]).toEqual({ order_item: 701, quantity: 2, trade_unit: 71, trade_quantity: 2, overage_reason: '' })
    expect(items[1].order_item).toBe(702)
    expect(items[1].trade_unit).toBeNull()
  })

  it('requires a reason per overage line and confirms all overages once through the app dialog', async () => {
    setupApi()
    const wrapper = await mountOrder()
    await wrapper.findAll('button').find(button => button.text() === '批量发货').trigger('click')
    await settle()
    await setDialogField('input[aria-label="发货数量 UAT-SKU-A 明细 #701"]', '7')
    await setDialogField('input[aria-label="发货数量 UAT-SKU-B 明细 #703"]', '6')
    expect(dialog().querySelector('button[type="submit"]').disabled).toBe(true)
    await setDialogField('select[aria-label="超发原因 UAT-SKU-A 明细 #701"]', 'customer_addon', 'change')
    await setDialogField('select[aria-label="超发原因 UAT-SKU-B 明细 #703"]', 'packing_variance', 'change')
    await submitDialog()

    expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
    expect(mocks.confirmDialog.mock.calls[0][0].message).toContain('客户追加')
    expect(mocks.confirmDialog.mock.calls[0][0].message).toContain('包装尾差')
    expect(shipmentPostCalls()).toHaveLength(1)
    expect(shipmentPostCalls()[0][1].items.map(line => line.overage_reason)).toEqual(['customer_addon', '', 'packing_variance'])
  })

  it('does not post when the single batch overage confirmation is cancelled', async () => {
    mocks.confirmDialog.mockResolvedValue(false)
    setupApi()
    const wrapper = await mountOrder()
    await wrapper.findAll('button').find(button => button.text() === '批量发货').trigger('click')
    await settle()
    await setDialogField('input[aria-label="发货数量 UAT-SKU-A 明细 #701"]', '7')
    await setDialogField('select[aria-label="超发原因 UAT-SKU-A 明细 #701"]', 'gift_or_sample', 'change')
    await submitDialog()
    expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
    expect(shipmentPostCalls()).toHaveLength(0)
    expect(dialog()).not.toBeNull()
  })

  it('keeps the whole batch dialog and entered values open when the API rejects any line', async () => {
    setupApi({ postError: { response: { data: { detail: '库存不足，不能确认发货。' } }, message: 'request failed' } })
    const wrapper = await mountOrder()
    await wrapper.findAll('button').find(button => button.text() === '批量发货').trigger('click')
    await settle()
    await setDialogField('input[aria-label="发货数量 UAT-SKU-A 明细 #701"]', '2.5')
    await submitDialog()
    expect(dialog()).not.toBeNull()
    expect(dialog().querySelector('[role="alert"]').textContent).toContain('库存不足')
    expect(dialog().querySelector('input[aria-label="发货数量 UAT-SKU-A 明细 #701"]').value).toBe('2.5')
    expect([...dialog().querySelectorAll('.shipment-line-toggle input')].every(input => input.checked)).toBe(true)
    expect(shipmentPostCalls()).toHaveLength(1)
  })

  it('closes and reloads after success; history displays one shipment card with all its lines', async () => {
    const shipment = { id: 91, shipment_no: 'SH-UAT-BATCH-91', shipment_date: '2026-10-06', status: 'confirmed', items: [
      { id: 801, sku_code: 'UAT-SKU-A', quantity: '6.00' }, { id: 802, sku_code: 'UAT-SKU-B', quantity: '2.00' },
    ] }
    const getFulfillmentLoads = setupApi({ shipments: [shipment] })
    const wrapper = await mountOrder()
    await wrapper.findAll('button').find(button => button.text() === '批量发货').trigger('click')
    await settle()
    await submitDialog()
    expect(dialog()).toBeNull()
    expect(getFulfillmentLoads()).toBe(2)
    expect(wrapper.findAll('.shipment-history-card')).toHaveLength(1)
    expect(wrapper.get('.shipment-history-card').text()).toContain('SH-UAT-BATCH-91')
    expect(wrapper.get('.shipment-history-card').text()).toContain('UAT-SKU-A × 6.00')
    expect(wrapper.get('.shipment-history-card').text()).toContain('UAT-SKU-B × 2.00')
  })
})
