// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { reactive, defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { provideUnsavedChangesScope, useUnsavedChangesGuard } from '../src/composables/useUnsavedChangesGuard'
import QuoteEditorModal from '../src/components/QuoteEditorModal.vue'
import OrderDraftModal from '../src/components/OrderDraftModal.vue'
import ProcurementDraftModal from '../src/components/ProcurementDraftModal.vue'
import DocumentPage from '../src/views/DocumentPage.vue'
import PurchaseOrderPage from '../src/views/PurchaseOrderPage.vue'
import SKUPage from '../src/views/SKUPage.vue'
import ResourcePage from '../src/views/ResourcePage.vue'
import RelatedCreateModal from '../src/components/RelatedCreateModal.vue'
import { resourceConfigs } from '../src/resourceConfigs'

const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, listAll: vi.fn(), confirmDialog: vi.fn() }))
vi.mock('../src/api', () => ({ api: mocks.api, listAll: mocks.listAll, listData: r => r.data, downloadQuoteExport: vi.fn() }))
vi.mock('../src/dialogs', () => ({ confirmDialog: mocks.confirmDialog }))
let wrapper, router
const customers = [{ id: 1, name: 'UAT Buyer' }]
const skus = [{ id: 2, sku: 'SKU', unit: 'pcs', currency: 'USD', default_price: '9.90', trade_units: [] }]
const stubs = { Teleport: true, SkuPickerPanel: true, EntityDetailModal: true, TradeUnitPicker: true }
beforeEach(() => {
  vi.clearAllMocks()
  mocks.confirmDialog.mockResolvedValue(false)
  mocks.listAll.mockImplementation(async url => url === '/customers/' ? customers : url === '/skus/' ? skus : [])
  mocks.api.get.mockResolvedValue({ data: [] })
  mocks.api.post.mockImplementation(async url => ({ data: url.includes('sales-rules') ? [] : { id: 3 } }))
})
afterEach(() => wrapper?.unmount())
async function mountAt(component, props = {}, path = '/quotes') {
  router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { template: '<main />' } }] })
  await router.push(path)
  wrapper = mount(component, { props, global: { plugins: [router], stubs, directives: { 'money-input': {} } } })
  await flushPromises()
}
const quoteProps = { mode: 'create', customers, skus }
it('fresh Quote closes clean; edited Quote cancel preserves fields and discard closes', async () => {
  await mountAt(QuoteEditorModal, quoteProps)
  await wrapper.get('[aria-label="关闭报价编辑器"]').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  expect(wrapper.emitted('close')).toHaveLength(1)
  await wrapper.find('textarea').setValue('UAT unsaved')
  await wrapper.get('[aria-label="关闭报价编辑器"]').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledWith(expect.objectContaining({ title: '未保存修改', cancelText: '继续编辑', confirmText: '放弃修改', danger: true }))
  expect(wrapper.emitted('close')).toHaveLength(1)
  expect(wrapper.find('textarea').element.value).toBe('UAT unsaved')
  mocks.confirmDialog.mockResolvedValue(true)
  await wrapper.get('[aria-label="关闭报价编辑器"]').trigger('click'); await flushPromises()
  expect(wrapper.emitted('close')).toHaveLength(2)
})
it('adding Quote items is dirty, failed save stays dirty, successful save navigates without another prompt', async () => {
  await mountAt(QuoteEditorModal, { ...quoteProps, quote: { customer: 1 } })
  wrapper.findComponent({ name: 'SkuPickerPanel' }).vm.$emit('update:modelValue', ['2']); await flushPromises()
  await wrapper.get('[aria-label="关闭报价编辑器"]').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
  mocks.api.post.mockRejectedValueOnce(new Error('save failed'))
  await wrapper.get('form').trigger('submit'); await flushPromises()
  await wrapper.get('[aria-label="关闭报价编辑器"]').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(2)
  mocks.confirmDialog.mockClear()
  await wrapper.get('form').trigger('submit'); await flushPromises()
  await router.push('/orders?detail=3')
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  expect(wrapper.emitted('saved')).toHaveLength(1)
})
it('Direct Order sidebar navigation cancel preserves route; discard completes navigation', async () => {
  await mountAt(DocumentPage, { type: 'orders' }, '/orders?create=1&customer=1')
  wrapper.vm.form.notes = 'unsaved order'; await flushPromises()
  await router.push('/suppliers')
  expect(router.currentRoute.value.fullPath).toBe('/orders?create=1&customer=1')
  expect(wrapper.vm.form.notes).toBe('unsaved order')
  mocks.confirmDialog.mockResolvedValue(true)
  await router.push('/suppliers')
  expect(router.currentRoute.value.path).toBe('/suppliers')
})
it('Purchase price changes protect backdrop, cancellation preserves every line', async () => {
  await mountAt(PurchaseOrderPage, {}, '/purchase-orders?create=1&supplier=1&order=2')
  await wrapper.get('.purchase-create-backdrop').trigger('mousedown'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  await wrapper.vm.startCreate()
  wrapper.vm.draft.items = [{ sku: 2, quantity: 1, unit_price: '5' }]
  await wrapper.get('.purchase-create-backdrop').trigger('mousedown'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  await wrapper.findAll('.purchase-create-backdrop button').find(button => button.text() === '取消').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
  expect(wrapper.vm.draft.items[0].unit_price).toBe('5')
  expect(wrapper.find('.purchase-create-backdrop').exists()).toBe(true)
})
it('SKU loaded packaging stays clean, changed packaging is protected', async () => {
  const product = { id: 1, name: 'UAT Product', sku_definitions: [] }
  mocks.listAll.mockImplementation(async url => url === '/products/' ? [product] : url === '/suppliers/' ? [{ id: 1, name: 'UAT Supplier' }] : [])
  await mountAt(SKUPage, {}, '/skus')
  await wrapper.vm.openEdit({ id: 2, product: 1, unit: 'pcs', currency: 'USD', active: true, parameter_values: {}, packaging: { template: 5, effective_qty_per_carton: 12 } })
  await flushPromises()
  expect(wrapper.vm.guard.dirty.value).toBe(false)
  wrapper.vm.details = [{ packaging_template: 5, carton_quantity: 24 }]
  await wrapper.get('[aria-label="关闭 SKU 窗口"]').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
  expect(wrapper.vm.details[0].carton_quantity).toBe(24)
})
it('Quote SKU-default packaging has its own clean baseline and protects dirty close and parent close', async () => {
  mocks.listAll.mockImplementation(async url => url === '/customers/' ? customers : url === '/skus/' ? skus : url === '/packaging-templates/' ? [{ id: 5, name: 'UAT Carton', active: true }] : [])
  mocks.api.put.mockResolvedValue({ data: { effective: { template: 5, effective_qty_per_carton: 12 } } })
  await mountAt(QuoteEditorModal, quoteProps)
  wrapper.findComponent({ name: 'SkuPickerPanel' }).vm.$emit('update:modelValue', ['2']); await flushPromises()
  await wrapper.findAll('button').find(button => button.text().includes('生成预计装箱方案')).trigger('click')
  await wrapper.findAll('button').find(button => button.text().includes('补充默认包装')).trigger('click'); await flushPromises()
  await wrapper.find('.packaging-config-modal').findAll('button').find(button => button.text() === '取消').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  expect(wrapper.find('.packaging-config-modal').exists()).toBe(false)

  await wrapper.findAll('button').find(button => button.text().includes('补充默认包装')).trigger('click'); await flushPromises()
  const quantity = wrapper.find('.packaging-config-modal input[type="number"]')
  await quantity.setValue('12')
  await wrapper.find('.packaging-config-backdrop').trigger('mousedown'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  await wrapper.findAll('.packaging-config-modal button').find(button => button.text() === '取消').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
  expect(wrapper.find('.packaging-config-modal input[type="number"]').element.value).toBe('12')
  expect(wrapper.find('.packaging-config-modal').exists()).toBe(true)

  mocks.confirmDialog.mockResolvedValue(false)
  wrapper.vm.guard.markClean()
  await wrapper.get('[aria-label="关闭报价编辑器"]').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(2)
  expect(wrapper.find('.packaging-config-modal').exists()).toBe(true)
  expect(wrapper.emitted('close')).toBeUndefined()
})
it('Quote packaging save marks only the child clean before closing', async () => {
  mocks.listAll.mockImplementation(async url => url === '/customers/' ? customers : url === '/skus/' ? skus : url === '/packaging-templates/' ? [{ id: 5, name: 'UAT Carton', active: true }] : [])
  mocks.api.put.mockResolvedValue({ data: { effective: { template: 5, effective_qty_per_carton: 12 } } })
  await mountAt(QuoteEditorModal, quoteProps)
  wrapper.findComponent({ name: 'SkuPickerPanel' }).vm.$emit('update:modelValue', ['2']); await flushPromises()
  await wrapper.findAll('button').find(button => button.text().includes('生成预计装箱方案')).trigger('click')
  await wrapper.findAll('button').find(button => button.text().includes('补充默认包装')).trigger('click'); await flushPromises()
  wrapper.vm.guard.markClean()
  await wrapper.find('.packaging-config-modal select').setValue('5')
  const fields = wrapper.findAll('.packaging-config-modal input[type="number"]')
  await fields[0].setValue('12'); await fields[1].setValue('0.25')
  await wrapper.find('.packaging-config-modal').trigger('submit'); await flushPromises()
  expect(mocks.api.put).toHaveBeenCalledWith('/skus/2/packaging/', expect.objectContaining({ packaging_template: 5, qty_per_carton_override: 12, unit_net_weight: 0.25 }))
  expect(wrapper.find('.packaging-config-modal').exists()).toBe(false)
  await wrapper.get('[aria-label="关闭报价编辑器"]').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  expect(wrapper.emitted('close')).toHaveLength(1)
})
it('SKU supplier-source child cancel preserves input, and dirty child blocks its parent close', async () => {
  const product = { id: 1, name: 'UAT Product', sku_definitions: [] }
  mocks.listAll.mockImplementation(async url => url === '/products/' ? [product] : url === '/suppliers/' ? [{ id: 1, name: 'UAT Supplier' }] : [])
  await mountAt(SKUPage, {}, '/skus')
  await wrapper.vm.openEdit({ id: 2, product: 1, unit: 'pcs', currency: 'USD', active: true, parameter_values: {} }); await flushPromises()
  wrapper.vm.guard.markClean()
  await wrapper.findAll('button').find(button => button.text().includes('添加供应商来源')).trigger('click'); await flushPromises()
  await wrapper.findAll('.supplier-source-modal button').find(button => button.text() === '取消').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  await wrapper.findAll('button').find(button => button.text().includes('添加供应商来源')).trigger('click'); await flushPromises()
  await wrapper.find('.supplier-source-modal input[maxlength="100"]').setValue('SUP-UAT')
  await wrapper.findAll('.supplier-source-modal button').find(button => button.text() === '取消').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
  expect(wrapper.find('.supplier-source-modal input[maxlength="100"]').element.value).toBe('SUP-UAT')
  expect(wrapper.find('.supplier-source-modal').exists()).toBe(true)
  await router.push('/customers')
  expect(router.currentRoute.value.path).toBe('/skus')
  expect(wrapper.find('.supplier-source-modal input[maxlength="100"]').element.value).toBe('SUP-UAT')
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(2)
  await wrapper.get('[aria-label="关闭 SKU 窗口"]').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(3)
  expect(wrapper.find('.supplier-source-modal').exists()).toBe(true)
  expect(wrapper.vm.modalOpen).toBe(true)
})
it('new SKU packaging protects dirty backdrop and a successful supplier-source save closes cleanly', async () => {
  const product = { id: 1, name: 'UAT Product', sku_definitions: [] }
  mocks.listAll.mockImplementation(async url => url === '/products/' ? [product] : url === '/suppliers/' ? [{ id: 1, name: 'UAT Supplier' }] : [])
  await mountAt(SKUPage, {}, '/skus')
  await wrapper.vm.openEdit({ id: 2, product: 1, unit: 'pcs', currency: 'USD', active: true, parameter_values: {} }); await flushPromises()
  wrapper.vm.guard.markClean()
  await wrapper.vm.openPackagingCreate(wrapper.vm.details[0]); await flushPromises()
  await wrapper.findAll('.inline-packaging-modal button').find(button => button.text() === '取消').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  await wrapper.vm.openPackagingCreate(wrapper.vm.details[0]); await flushPromises()
  await wrapper.find('.inline-packaging-modal input').setValue('UAT carton')
  const backdrop = wrapper.find('.packaging-dialog-backdrop')
  await backdrop.trigger('mousedown'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  await wrapper.findAll('.inline-packaging-modal button').find(button => button.text() === '取消').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
  expect(wrapper.find('.inline-packaging-modal input').element.value).toBe('UAT carton')
  expect(wrapper.find('.inline-packaging-modal').exists()).toBe(true)
  mocks.confirmDialog.mockResolvedValue(true)
  await wrapper.findAll('.inline-packaging-modal button').find(button => button.text() === '取消').trigger('click'); await flushPromises()
  expect(wrapper.find('.inline-packaging-modal').exists()).toBe(false)

  await wrapper.findAll('button').find(button => button.text().includes('添加供应商来源')).trigger('click'); await flushPromises()
  await wrapper.find('.supplier-source-modal select').setValue('1')
  await wrapper.find('.supplier-source-modal input[maxlength="100"]').setValue('SUP-SAVE')
  wrapper.vm.guard.markClean()
  mocks.confirmDialog.mockResolvedValue(false)
  mocks.api.post.mockRejectedValueOnce(new Error('temporary failure'))
  await wrapper.find('.supplier-source-modal').trigger('submit'); await flushPromises()
  expect(wrapper.find('.supplier-source-modal').exists()).toBe(true)
  await wrapper.findAll('.supplier-source-modal button').find(button => button.text() === '取消').trigger('click'); await flushPromises()
  expect(wrapper.find('.supplier-source-modal').exists()).toBe(true)
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(3)
  mocks.api.post.mockResolvedValue({ data: { id: 9 } })
  await wrapper.find('.supplier-source-modal').trigger('submit'); await flushPromises()
  expect(mocks.api.post).toHaveBeenCalledWith('/supplier-skus/', expect.objectContaining({ supplier_sku_code: 'SUP-SAVE' }))
  expect(wrapper.find('.supplier-source-modal').exists()).toBe(false)
  await wrapper.get('[aria-label="关闭 SKU 窗口"]').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(3)
  expect(wrapper.vm.modalOpen).toBe(false)
})
it('generic Customer editor protects nested contacts and route leave', async () => {
  await mountAt(ResourcePage, { config: resourceConfigs.customers }, '/customers?create=1')
  wrapper.vm.customerContacts[0].name = 'unsaved contact'; await flushPromises()
  await router.push('/orders')
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
  expect(router.currentRoute.value.path).toBe('/customers')
  expect(wrapper.vm.customerContacts[0].name).toBe('unsaved contact')
})
it('RelatedCreate prefill closes clean; FollowUp changes protect Cancel', async () => {
  await mountAt(RelatedCreateModal, { entity: 'follow-ups', query: { customer: 1 } })
  await wrapper.findAll('button').find(b => b.text() === '取消').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  wrapper.vm.form.content = 'called customer'
  await wrapper.findAll('button').find(b => b.text() === '取消').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
  expect(wrapper.vm.form.content).toBe('called customer')
})
it('Quote-derived Order draft prefill is clean and line changes are dirty', async () => {
  await mountAt(OrderDraftModal, { draft: { customer: 1, quote: 2, order_date: '2026-10-11', currency: 'USD', exchange_rate: '7.2', items: [{ sku: 2, quantity: 1, unit_price: 10 }] }, customers, skus })
  await wrapper.get('[aria-label="关闭订单草稿"]').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  wrapper.vm.form.items[0].quantity = 2
  await wrapper.get('[aria-label="关闭订单草稿"]').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
})
it('Order-derived Purchase prefill is clean, and price changes protect cancellation', async () => {
  await mountAt(ProcurementDraftModal, { orderId: 1, plan: { groups: [{ supplier: 1, currency: 'CNY', items: [2] }], items: [{ order_item: 2, draftable_quantity: 4, reference_purchase_price: 5 }] } })
  await wrapper.get('[aria-label="关闭"]').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  wrapper.vm.groups[0].items[0].unit_price = '12'
  await wrapper.findAll('button').find(b => b.text() === '取消').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
  expect(wrapper.vm.groups[0].items[0].unit_price).toBe('12')
})
it('beforeunload exists only while dirty and is removed on clean/unmount', async () => {
  const state = reactive({ items: [] })
  let guard
  wrapper = mount(defineComponent({ setup() { guard = useUnsavedChangesGuard({ data: () => state }); guard.markClean(); return () => h('div') } }))
  const unload = () => { const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); return event.defaultPrevented }
  expect(unload()).toBe(false)
  state.items.push({ quantity: 2 })
  expect(unload()).toBe(true)
  guard.markClean()
  expect(unload()).toBe(false)
  state.items[0].quantity = 3
  wrapper.unmount()
  expect(unload()).toBe(false)
})
it('parent close protects an embedded editor while a readonly scope closes without a prompt', async () => {
  const state = reactive({ packaging: { quantity: 10 } })
  let scope
  const close = vi.fn()
  const Child = defineComponent({ setup() { const guard = useUnsavedChangesGuard({ data: () => state }); guard.markClean(); return () => h('div') } })
  wrapper = mount(defineComponent({ setup() { scope = provideUnsavedChangesScope(); return () => h(Child) } }))
  await scope.requestClose(close)
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  state.packaging.quantity = 12
  await scope.requestClose(close)
  expect(close).toHaveBeenCalledTimes(1)
  expect(state.packaging.quantity).toBe(12)
  mocks.confirmDialog.mockResolvedValue(true)
  await scope.requestClose(close)
  expect(close).toHaveBeenCalledTimes(2)
})
it('a canceled later route guard keeps changes dirty, and browser Back is also protected', async () => {
  await mountAt(DocumentPage, { type: 'orders' }, '/orders?create=1')
  wrapper.vm.form.notes = 'keep draft'
  mocks.confirmDialog.mockResolvedValue(true)
  const remove = router.beforeEach(() => false)
  await router.push('/customers')
  expect(wrapper.vm.guard.dirty.value).toBe(true)
  remove()
  mocks.confirmDialog.mockResolvedValue(false)
  router.back(); await flushPromises()
  expect(router.currentRoute.value.path).toBe('/orders')
  expect(wrapper.vm.form.notes).toBe('keep draft')
})
it('FollowUp attachment failure leaves saved main fields clean', async () => {
  await mountAt(RelatedCreateModal, { entity: 'follow-ups', query: { customer: 1 } })
  wrapper.vm.form.content = 'communication saved'
  wrapper.vm.pendingFollowUpFiles = [new File(['test'], 'uat.txt')]
  mocks.api.post.mockImplementation(async url => { if (url.includes('attachments')) throw new Error('upload failed'); return { data: { id: 3 } } })
  await wrapper.get('form').trigger('submit'); await flushPromises()
  expect(wrapper.text()).toContain('记录已保存')
  await wrapper.findAll('button').find(b => b.text() === '取消').trigger('click'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
})
