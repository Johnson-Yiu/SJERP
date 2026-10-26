// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { nextTick } from 'vue'

const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn() } }))
vi.mock('../src/api.js', () => ({ api: mocks.api }))
import { setAccessOperator } from '../src/accessControl.js'
import OrderDetailModal from '../src/components/OrderDetailModal.vue'

let wrapper

beforeEach(() => {
  setAccessOperator({
    rbac_enforcement: true,
    has_all_permissions: false,
    permissions: { orders: { view: true, update: true } },
  })
  mocks.api.get.mockImplementation(async url => {
    if (url.endsWith('/workbench/')) return { data: {
      order: { id: 1, order_no: 'SO-QTY-UI', status: 'confirmed', status_display: '已确认', currency: 'USD', total_amount: '1000.00', quantity_change_version: 0 },
      items: [{ id: 11, sku: 3, sku_code: 'SKU-QTY-UI', display_name: '数量变更测试 SKU', sales_model: '', quantity: '100.00', unit_price: '10.00', amount: '1000.00', cost_price: null, trade_unit: null, trade_snapshot: { base_unit: 'pcs' } }],
      payments: [], inventory: [], quantity_adjustments: [], payment_summary: {}, fulfillment_summary: { ordered_quantity: '100.00', shipped_quantity: '0', remaining_quantity: '100.00' }, profit_summary: {},
    } }
    if (url.endsWith('/fulfillment/')) return { data: { items: [], purchase_orders: [], shipments: [] } }
    if (url.endsWith('/packing-plan/')) return { data: null }
    if (url.endsWith('/procurement-plan/')) return { data: { items: [] } }
    if (url === '/operation-logs/') return { data: [] }
    if (url === '/session/current-operator/') return { data: {} }
    return { data: {} }
  })
  mocks.api.post.mockReset()
})

afterEach(() => {
  wrapper?.unmount()
  vi.clearAllMocks()
})

it('does not apply an outdated preview after the form changes during a pending request', async () => {
  await setup()
  await wrapper.findAll('button').find(button => button.text() === '调整数量').trigger('click')
  const dialog = wrapper.get('.quantity-adjustment-dialog')
  await dialog.get('input[type="number"]').setValue('150')
  await dialog.get('textarea').setValue('客户追加')
  let resolvePreview
  mocks.api.post.mockImplementationOnce(() => new Promise(resolve => { resolvePreview = resolve }))
  await dialog.trigger('submit')
  await dialog.get('input[type="number"]').setValue('120')
  resolvePreview({ data: { can_submit: true, lines: [], warnings: [], financial: { amount_delta: '500' } } })
  await flushPromises()
  expect(wrapper.find('.quantity-adjustment-preview').exists()).toBe(false)
  expect(mocks.api.post).toHaveBeenCalledTimes(1)
})

async function setup() {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/orders', component: { template: '<main />' } }] })
  await router.push('/orders?detail=1')
  await router.isReady()
  wrapper = mount(OrderDetailModal, {
    props: { id: 1 },
    global: {
      plugins: [router],
      stubs: {
        Teleport: true,
        ContractAmountAdjustments: true,
        OperationLogPanel: true,
        ShipmentActualPacking: true,
        SupplierAllocationModal: true,
        ProcurementDraftModal: true,
        TradeUnitPicker: true,
      },
    },
  })
  await flushPromises()
}

it('blocks a no-op quantity adjustment in the editor before making an API request', async () => {
  await setup()
  await wrapper.findAll('button').find(button => button.text() === '调整数量').trigger('click')

  const dialog = wrapper.get('.quantity-adjustment-dialog')
  expect(dialog.text()).toContain('数量没有变化。')
  const previewButton = dialog.findAll('button').find(button => button.text() === '预览影响')
  expect(previewButton.element.disabled).toBe(true)
  await dialog.trigger('submit')
  expect(mocks.api.post).not.toHaveBeenCalled()

  await dialog.get('input[aria-label="新的基础数量 SKU-QTY-UI"]').setValue('120')
  await dialog.get('textarea[placeholder="请说明客户或业务调整原因"]').setValue('测试数量变更')
  await nextTick()
  await flushPromises()
  expect(wrapper.findAll('button').find(button => button.text() === '预览影响').element.disabled).toBe(false)
})
