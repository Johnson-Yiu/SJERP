// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { reactive } from 'vue'

const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() }, confirmDialog: vi.fn(), downloadPackingListExport: vi.fn() }))
vi.mock('../src/api', () => ({ api: mocks.api, downloadPackingListExport: mocks.downloadPackingListExport }))
vi.mock('../src/dialogs', () => ({ confirmDialog: mocks.confirmDialog }))
vi.mock('../src/accessControl', () => ({ useAccessControl: () => ({ can: () => true }) }))
import ShipmentActualPacking from '../src/components/ShipmentActualPacking.vue'
import OrderDetailModal from '../src/components/OrderDetailModal.vue'
import { packingSummary } from '../src/utils/actualPacking'

const shipment = { id: 55, shipment_no: 'SH-UAT-55', shipment_date: '2026-10-07', status: 'confirmed', items: [
  { id: 1, sku: 10, sku_code: 'SAVED-A', display_name: 'Saved A', quantity: '6', base_unit: 'pcs' },
  { id: 2, sku: 10, sku_code: 'SAVED-A', display_name: 'Saved A', quantity: '4', base_unit: 'pcs' },
  { id: 3, sku: 20, sku_code: 'SAVED-B', display_name: 'Saved B', quantity: '8', base_unit: 'm' },
] }
const carton = { id: 81, carton_no: 3, length: '40.00', width: '30.00', height: '20.00', actual_net_weight: '0.100', actual_gross_weight: '0.200', actual_cbm: '0.024000', notes: 'Existing note', items: [{ id: 1, sku: 10, quantity: '6' }] }
let wrappers = []
async function component({ rows = [shipment], packages = [], hasPlan = true, cache = reactive({}) } = {}) {
  mocks.api.get.mockResolvedValue({ data: structuredClone(packages) })
  const wrapper = mount(ShipmentActualPacking, { props: { shipments: structuredClone(rows), hasPlan, cache }, attachTo: document.body })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}
async function click(wrapper, name) { await wrapper.findAll('button').find(b => b.text() === name).trigger('click'); await flushPromises() }
const form = () => document.querySelector('.actual-packing-editor')
async function input(label, value) {
  const element = [...form().querySelectorAll('input, select, textarea')].find(el => el.getAttribute('aria-label') === label || el.closest('label')?.textContent.trim() === label)
  element.value = value
  element.dispatchEvent(new Event(element.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }))
  await flushPromises()
}
async function submit() { form().dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); await flushPromises() }
beforeEach(() => { vi.clearAllMocks(); mocks.confirmDialog.mockResolvedValue(true); mocks.api.post.mockResolvedValue({ data: [] }); mocks.api.delete.mockResolvedValue({}); mocks.downloadPackingListExport.mockResolvedValue(undefined); wrappers = [] })
afterEach(() => { wrappers.forEach(w => w.unmount()); document.body.innerHTML = '' })

describe('Actual packing by Shipment', () => {
  it('keeps expected packing and actual packing clearly separated in Order workspace', async () => {
    mocks.api.get.mockImplementation(async url => ({ data: url.endsWith('/workbench/') ? { order: { id: 1, status: 'confirmed' }, items: [], payments: [], inventory: [], payment_summary: {}, fulfillment_summary: {}, profit_summary: {} } : url.endsWith('/fulfillment/') ? { items: [], shipments: [shipment], purchase_orders: [] } : url.endsWith('/packing-plan/') ? { total_cartons: 1, total_net_weight: '1', total_gross_weight: '2', total_cbm: '0.024', cartons: [{ id: 1, carton_no: 1, items: [] }] } : url.endsWith('/packages/') ? [] : {} }))
    const w = mount(OrderDetailModal, { props: { id: 1 }, global: { stubs: { RouterLink: true, OperationLogPanel: true, SupplierAllocationModal: true, ProcurementDraftModal: true, ContractAmountAdjustments: true } } })
    wrappers.push(w)
    await flushPromises()
    expect(mocks.api.get.mock.calls.some(([url]) => url.endsWith('/packages/'))).toBe(false)
    await click(w, '装箱')
    expect(w.text()).toContain('预计装箱')
    expect(w.text()).toContain('实际装箱')
    expect(w.text()).toContain('重新生成预计装箱方案')
    expect(w.find('.packing-carton-card').exists()).toBe(true)
    expect(mocks.api.get.mock.calls.filter(([url]) => url.endsWith('/packages/'))).toHaveLength(1)
    await click(w, '概览'); await click(w, '装箱')
    expect(mocks.api.get.mock.calls.filter(([url]) => url.endsWith('/packages/'))).toHaveLength(1)
  })
  it('shows shipment number, date, status and aggregates shipped SKU lines', async () => {
    const w = await component()
    expect(w.text()).toContain('SH-UAT-55'); expect(w.text()).toContain('2026-10-07'); expect(w.text()).toContain('已确认')
    expect(w.text()).toContain('发货 10 pcs')
  })
  it('loads package data only from its Shipment URL', async () => { await component(); expect(mocks.api.get).toHaveBeenCalledWith('/shipments/55/packages/') })
  it('confirmed Shipment allows package management', async () => { const w = await component({ packages: [carton] }); expect(w.text()).toContain('新增箱'); expect(w.text()).toContain('编辑'); expect(w.text()).toContain('删除') })
  it('cancelled Shipment keeps history and exposes no mutations', async () => {
    const w = await component({ rows: [{ ...shipment, status: 'cancelled' }], packages: [carton] })
    expect(w.text()).toContain('发货已冲销 · 实际箱单仅供历史查看'); expect(w.text()).toContain('第 3 箱')
    expect(w.findAll('button')).toHaveLength(0)
  })
  it('new package opens one editor with max carton number plus one', async () => { const w = await component({ packages: [carton] }); await click(w, '新增箱'); expect(form().textContent).toContain('新增实际箱单'); expect(form().querySelector('input').value).toBe('4') })
  it('SKU selector contains only unique target Shipment SKUs', async () => { const w = await component(); await click(w, '新增箱'); expect([...form().querySelector('select').options].map(o => o.value)).toEqual(['', '10', '20']) })
  it('submits mixed SKU carton quantities to the scoped API and reloads', async () => {
    const w = await component(); await click(w, '新增箱'); await input('SKU 1', '10'); await input('实际装箱数量 1', '5')
    const add = [...form().querySelectorAll('button')].find(b => b.textContent === '添加 SKU 明细'); add.click(); await flushPromises()
    await input('SKU 2', '20'); await input('实际装箱数量 2', '2'); await submit()
    expect(mocks.api.post).toHaveBeenCalledWith('/shipments/55/packages/', expect.objectContaining({ carton_no: 1, items: [{ sku: 10, quantity: '5' }, { sku: 20, quantity: '2' }] }))
    expect(mocks.api.get).toHaveBeenCalledTimes(2); expect(form()).toBeNull()
  })
  it('edit preloads fields and sends replacement data to existing endpoint', async () => {
    const w = await component({ packages: [carton] }); await click(w, '编辑')
    expect(form().querySelector('textarea').value).toBe('Existing note'); expect(form().querySelector('select').value).toBe('10')
    await input('实际装箱数量 1', '7'); await input('长 cm', '45'); await submit()
    expect(mocks.api.post).toHaveBeenCalledWith('/shipments/55/packages/81/', expect.objectContaining({ length: '45', items: [{ sku: 10, quantity: '7' }] }))
  })
  it('delete uses App confirmation then scoped DELETE and reload', async () => {
    const w = await component({ packages: [carton] }); await click(w, '删除')
    expect(mocks.confirmDialog).toHaveBeenCalledWith(expect.objectContaining({ title: '删除第 3 箱？', message: expect.stringContaining('库存及订单数量均不受影响') }))
    expect(mocks.api.delete).toHaveBeenCalledWith('/shipments/55/packages/81/'); expect(mocks.api.get).toHaveBeenCalledTimes(2)
  })
  it('delete cancellation makes no request', async () => { mocks.confirmDialog.mockResolvedValue(false); const w = await component({ packages: [carton] }); await click(w, '删除'); expect(mocks.api.delete).not.toHaveBeenCalled() })
  it('summary uses decimal safe quantity, weight and CBM arithmetic', () => {
    const result = packingSummary(shipment, [carton, { ...carton, actual_net_weight: '0.200', actual_gross_weight: '0.300', actual_cbm: '0.002001', items: [{ sku: 10, quantity: '0.10' }] }])
    expect(result).toMatchObject({ count: 2, net: '0.3', gross: '0.5', cbm: '0.026001' }); expect(result.rows[0]).toMatchObject({ packed: '6.1', shipped: '10', remaining: '3.9' })
    expect(packingSummary(shipment, [{ ...carton, actual_net_weight: '9999999999999.999' }, { ...carton, actual_net_weight: '0.001' }]).net).toBe('10000000000000')
  })
  it('partial progress displays packed shipped and remaining by SKU', async () => { const w = await component({ packages: [carton] }); expect(w.text()).toContain('尚未装箱完成'); expect(w.text()).toContain('已装 6 / 发货 10 pcs'); expect(w.text()).toContain('未装箱 4 pcs') })
  it('fully packed state is clearly shown', async () => { const w = await component({ packages: [{ ...carton, items: [{ sku: 10, quantity: '10' }, { sku: 20, quantity: '8' }] }] }); expect(w.find('.packing-progress').text()).toContain('装箱完成'); expect(w.find('.packing-progress').text()).not.toContain('未装箱') })
  it('keeps Packing List export disabled until every shipped SKU is packed', async () => { const w = await component({ packages: [carton] }); const button = w.findAll('button').find(b => b.text() === '导出 Packing List'); expect(button.exists()).toBe(true); expect(button.attributes('disabled')).toBeDefined(); expect(mocks.downloadPackingListExport).not.toHaveBeenCalled() })
  it('exports a fully packed confirmed Shipment through the scoped helper', async () => { const w = await component({ packages: [{ ...carton, items: [{ sku: 10, quantity: '10' }, { sku: 20, quantity: '8' }] }] }); await click(w, '导出 Packing List'); expect(mocks.downloadPackingListExport).toHaveBeenCalledWith(55, 'SH-UAT-55') })
  it('copy requires a plan and confirmed status', async () => { const w = await component({ hasPlan: false }); expect(w.findAll('button').find(b => b.text() === '从预计装箱复制').attributes('disabled')).toBeDefined() })
  it('copy without existing packages sends no replacement flag', async () => { const w = await component(); await click(w, '从预计装箱复制'); expect(mocks.confirmDialog).not.toHaveBeenCalled(); expect(mocks.api.post).toHaveBeenCalledWith('/shipments/55/copy-estimated-packing/', {}) })
  it('partial shipment copy shows server business explanation', async () => { mocks.api.post.mockRejectedValue({ response: { data: { detail: '预计装箱对应整张订单，本次发货数量与预计装箱不一致，请手工录入本次实际箱单。' } } }); const w = await component(); await click(w, '从预计装箱复制'); expect(w.text()).toContain('请手工录入本次实际箱单') })
  it('existing actual packing replacement confirms once and sends replace true', async () => { const w = await component({ packages: [carton] }); await click(w, '从预计装箱复制'); expect(mocks.confirmDialog).toHaveBeenCalledTimes(1); expect(mocks.api.post).toHaveBeenCalledWith('/shipments/55/copy-estimated-packing/', { replace: true }) })
  it('cancelled replacement preserves packages and sends no request', async () => { mocks.confirmDialog.mockResolvedValue(false); const w = await component({ packages: [carton] }); await click(w, '从预计装箱复制'); expect(mocks.api.post).not.toHaveBeenCalled(); expect(w.text()).toContain('第 3 箱') })
  it('failed save retains usable editor and original data', async () => {
    mocks.api.post.mockRejectedValue({ response: { data: { items: ['累计装箱数量不能超过本次发货数量。'] } } })
    const w = await component({ packages: [carton] }); await click(w, '编辑'); await input('实际装箱数量 1', '11'); await submit()
    expect(form().textContent).toContain('累计装箱数量不能超过'); expect(form().querySelector('[aria-label="实际装箱数量 1"]').value).toBe('11'); expect(w.text()).toContain('第 3 箱'); expect(form().querySelector('button[type="submit"]').disabled).toBe(false)
  })
  it('renders nested validation errors as Chinese text without object placeholders', async () => {
    mocks.api.post.mockRejectedValue({ response: { data: { items: { quantity: ['SKU ACT-ROLL 按不可拆分的 5 m 交易单位装箱，数量必须是其整数倍；当前为 2.5。'] } } } })
    const w = await component({ packages: [carton] }); await click(w, '编辑'); await input('实际装箱数量 1', '2.5'); await submit()
    expect(form().textContent).toContain('不可拆分的 5 m'); expect(form().textContent).not.toContain('[object Object]'); expect(form().querySelector('[aria-label="实际装箱数量 1"]').value).toBe('2.5')
  })
  it('failed package load offers retry without mutation controls', async () => { mocks.api.get.mockRejectedValueOnce(new Error('network failure')); const w = await component(); expect(w.text()).toContain('network failure'); expect(w.text()).not.toContain('新增箱'); await click(w, '重试'); expect(w.text()).toContain('新增箱') })
  it('editor rejects duplicate SKU, partial dimensions and invalid weights without sending', async () => {
    const w = await component(); await click(w, '新增箱'); await input('SKU 1', '10'); await input('实际装箱数量 1', '1'); await input('长 cm', '20'); await submit()
    expect(form().textContent).toContain('须同时填写'); await input('长 cm', ''); await input('实际净重 kg', '2'); await submit(); expect(form().textContent).toContain('毛重不得低于净重')
    await input('实际毛重 kg', '2'); [...form().querySelectorAll('button')].find(b => b.textContent === '添加 SKU 明细').click(); await flushPromises(); await input('SKU 2', '10'); await input('实际装箱数量 2', '1'); await submit(); expect(form().textContent).toContain('不能重复填写'); expect(mocks.api.post).not.toHaveBeenCalled()
  })
})
