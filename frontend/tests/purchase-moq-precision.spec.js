// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import PurchaseOrderPage from '../src/views/PurchaseOrderPage.vue'
import PurchaseSupplierPicker from '../src/components/PurchaseSupplierPicker.vue'
import SkuPickerPanel from '../src/components/SkuPickerPanel.vue'

const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, listAll: vi.fn() }))
vi.mock('../src/api', () => ({ api: mocks.api, listAll: mocks.listAll, listData: response => response.data }))

let wrapper, sources, sku
const warnings = () => wrapper.findAll('[data-testid="draft-moq-warning"]')
const lines = () => wrapper.findAll('.purchase-line')

async function click(label) {
  await wrapper.findAll('button').find(button => button.text() === label).trigger('click')
  await flushPromises()
}

async function openDraft() {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/purchase-orders', component: PurchaseOrderPage },
    { path: '/:pathMatch(.*)*', component: { template: '<div />' } },
  ] })
  await router.push('/purchase-orders')
  wrapper = mount(PurchaseOrderPage, {
    global: {
      plugins: [router], directives: { 'money-input': {} },
      stubs: { ContractAmountAdjustments: true, PurchaseCostAllocationModal: true, PurchasePaymentModal: true, PurchaseSupplierPicker: true },
    },
  })
  await flushPromises()
  await click('新建采购单')
  await wrapper.get('[aria-label="供应商"]').setValue('9')
  wrapper.getComponent(SkuPickerPanel).vm.$emit('update:modelValue', ['3'])
  await flushPromises()
  await lines()[0].get('select:not([aria-label])').setValue('20')
}

beforeEach(() => {
  vi.clearAllMocks()
  sku = { id: 3, sku_code: 'MOQ-SKU', display_name_cn: 'MOQ 回归商品', unit: 'pcs', trade_units: [
    { id: 1, name: '100 件箱', unit: 'box', base_unit: 'pcs', factor: '100', active: true, is_default: true, allow_fraction: true },
  ] }
  sources = [20, 21].map(id => ({ id, supplier_model: `来源 ${id}`, supplier_sku_code: `SOURCE-${id}`, purchase_price: '2', currency: 'CNY', moq: '58.00' }))
  mocks.listAll.mockImplementation(async url => url === '/suppliers/' ? [{ id: 9, name: 'MOQ 供应商' }] : url === '/skus/' ? [sku] : [])
  mocks.api.get.mockImplementation(async () => ({ data: sources }))
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  vi.restoreAllMocks()
})

describe('采购草稿 MOQ 基础数量精度', () => {
  it('shows a real shortage but does not warn at or above MOQ after trade-unit conversion', async () => {
    await openDraft()
    const quantity = lines()[0].get('input[placeholder="采购数量"]')
    await quantity.setValue('0.57')
    expect(warnings()).toHaveLength(1)
    expect(warnings()[0].text()).toContain('实际 57.00 pcs，MOQ 58.00 pcs，差额 1.00 pcs')
    await quantity.setValue('0.58')
    expect(warnings()).toHaveLength(0)
    expect(lines()[0].get('.line-business-grid .line-field small').text()).toBe('折合 58.00 pcs')
    await quantity.setValue('0.59')
    expect(warnings()).toHaveLength(0)
  })

  it('aggregates the same supplier source across separate trade-unit lines before checking MOQ', async () => {
    await openDraft()
    await lines()[0].get('input[placeholder="采购数量"]').setValue('0.29')
    expect(warnings()).toHaveLength(1)
    await click('增加同 SKU 规格行')
    expect(lines()).toHaveLength(2)
    expect(warnings()).toHaveLength(0)
  })

  it('does not combine separate supplier sources merely because the SKU is the same', async () => {
    await openDraft()
    await lines()[0].get('input[placeholder="采购数量"]').setValue('0.29')
    await click('增加同 SKU 规格行')
    await lines()[1].get('select:not([aria-label])').setValue('21')
    expect(warnings()).toHaveLength(2)
    for (const warning of warnings()) expect(warning.text()).toContain('实际 29.00 pcs，MOQ 58.00 pcs，差额 29.00 pcs')
  })

  it('keeps a valid one-hundredth shortage visible', async () => {
    sku.trade_units[0].factor = '3'
    sources[0].moq = '1.00'
    await openDraft()
    await lines()[0].get('input[placeholder="采购数量"]').setValue('0.33')
    expect(warnings()).toHaveLength(1)
    expect(warnings()[0].text()).toContain('实际 0.99 pcs，MOQ 1.00 pcs，差额 0.01 pcs')
  })

  it.each(['0.00', null, 'invalid'])('does not invent a threshold for an absent or invalid MOQ (%s)', async moq => {
    sources[0].moq = moq
    await openDraft()
    await lines()[0].get('input[placeholder="采购数量"]').setValue('0.01')
    expect(warnings()).toHaveLength(0)
  })

  it('reports unavailable source data during a reload or failure and restores the check after retry', async () => {
    await openDraft()
    await lines()[0].get('input[placeholder="采购数量"]').setValue('0.57')
    expect(warnings()).toHaveLength(1)
    let rejectReload
    mocks.api.get.mockImplementationOnce(() => new Promise((resolve, reject) => { rejectReload = reject }))
    await click('更换供应商来源')
    wrapper.getComponent(PurchaseSupplierPicker).vm.$emit('selected', { supplier: 9, supplier_sku: 20 })
    await flushPromises()
    expect(warnings()).toHaveLength(0)
    expect(wrapper.get('.moq-check-unavailable').text()).toContain('正在加载，暂无法判断 MOQ')
    rejectReload(new Error('供货档案暂不可用'))
    await flushPromises()
    expect(warnings()).toHaveLength(0)
    expect(wrapper.get('.moq-check-unavailable').text()).toContain('加载失败，暂时无法判断 MOQ')
    await click('重试')
    expect(wrapper.find('.moq-check-unavailable').exists()).toBe(false)
    expect(warnings()).toHaveLength(1)
    expect(warnings()[0].text()).toContain('差额 1.00 pcs')
  })
})
