// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import QuoteEditorModal from '../src/components/QuoteEditorModal.vue'

const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, listAll: vi.fn(), confirmDialog: vi.fn() }))
vi.mock('../src/api', () => ({ api: mocks.api, listAll: mocks.listAll, downloadQuoteExport: vi.fn() }))
vi.mock('../src/dialogs', () => ({ confirmDialog: mocks.confirmDialog }))

const customers = [{ id: 1, name: 'Synthetic quote buyer' }]
const skus = [{ id: 2, sku: 'SYNTH-QUOTE-2', unit: 'pcs', currency: 'USD', default_price: '9.90', trade_units: [] }]
let wrapper, router
function deferred() {
  let resolve, reject
  const promise = new Promise((done, fail) => { resolve = done; reject = fail })
  return { promise, resolve, reject }
}
beforeEach(() => {
  vi.clearAllMocks()
  mocks.confirmDialog.mockResolvedValue(true)
  mocks.api.get.mockResolvedValue({ data: [] })
  mocks.api.post.mockResolvedValue({ data: [] })
  mocks.listAll.mockImplementation(async url => url === '/packaging-templates/' ? [{ id: 5, name: 'Synthetic carton', active: true }] : [])
})
afterEach(() => wrapper?.unmount())

async function mountQuote(mode = 'create') {
  router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { template: '<main />' } }] })
  await router.push('/quotes')
  wrapper = mount(QuoteEditorModal, {
    props: { mode, customers, skus, quote: { customer: 1, ...(mode === 'revise' ? { id: 44, quote_no: 'SYNTH-QT-44' } : {}) } },
    global: { plugins: [router], stubs: { Teleport: true, SkuPickerPanel: true, TradeUnitPicker: true } },
  })
  await flushPromises()
  wrapper.findComponent({ name: 'SkuPickerPanel' }).vm.$emit('update:modelValue', ['2'])
  await flushPromises()
  if (mode === 'revise') await wrapper.get('.revision-summary textarea').setValue('Synthetic revision')
}

async function assertCloseBlocked() {
  expect(wrapper.get('[aria-label="关闭报价编辑器"]').element.disabled).toBe(true)
  expect(wrapper.get('.quote-action-cancel').element.disabled).toBe(true)
  await wrapper.vm.requestClose()
  await flushPromises()
  expect(wrapper.emitted('close')?.length || 0).toBe(0)
  await router.push('/customers')
  expect(router.currentRoute.value.path).toBe('/quotes')
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  const event = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(event)
  expect(event.defaultPrevented).toBe(true)
}

it.each(['create', 'revise'])('pending quote %s blocks close/navigation and a failed save preserves input for one retry', async mode => {
  const pending = deferred()
  const endpoint = mode === 'create' ? '/quotes/' : '/quotes/44/revise/'
  let writes = 0
  mocks.api.post.mockImplementation(url => url === endpoint
    ? (++writes === 1 ? pending.promise : Promise.resolve({ data: { id: 301, quote_no: 'SYNTH-QT-301' } }))
    : Promise.resolve({ data: [] }))
  await mountQuote(mode)
  const before = JSON.parse(JSON.stringify(wrapper.vm.draft))
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(writes).toBe(1)
  await assertCloseBlocked()
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(writes).toBe(1)

  pending.reject(new Error('Synthetic pending save failure'))
  await flushPromises()
  expect(wrapper.text()).toContain('Synthetic pending save failure')
  expect(wrapper.vm.draft).toEqual(before)
  expect(wrapper.get('[aria-label="关闭报价编辑器"]').element.disabled).toBe(false)
  expect(wrapper.emitted('saved')).toBeUndefined()
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(writes).toBe(2)
  expect(wrapper.emitted('saved')).toHaveLength(1)
  expect(wrapper.emitted('close')).toHaveLength(1)
  await router.push('/customers')
  expect(router.currentRoute.value.path).toBe('/customers')
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
})

it('pending child packaging save protects both child and parent, then failure and retry stay on the same SKU', async () => {
  const pending = deferred()
  mocks.api.put.mockReturnValueOnce(pending.promise).mockResolvedValue({ data: { effective: { template: 5, effective_qty_per_carton: 12, unit_net_weight: 0.25 } } })
  await mountQuote()
  wrapper.vm.guard.markClean()
  wrapper.vm.openPackaging(skus[0])
  await flushPromises()
  await wrapper.get('.packaging-config-modal select').setValue('5')
  const fields = wrapper.findAll('.packaging-config-modal input[type="number"]')
  await fields[0].setValue('12')
  await fields[1].setValue('0.25')
  await wrapper.get('.packaging-config-modal').trigger('submit')
  await flushPromises()
  expect(mocks.api.put).toHaveBeenCalledTimes(1)
  await assertCloseBlocked()
  await wrapper.vm.requestPackagingClose()
  await flushPromises()
  expect(wrapper.find('.packaging-config-modal').exists()).toBe(true)
  pending.reject(new Error('Synthetic packaging save failure'))
  await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('Synthetic packaging save failure')
  expect(wrapper.get('.packaging-config-modal select').element.value).toBe('5')
  expect(wrapper.get('.packaging-config-modal input[type="number"]').element.value).toBe('12')
  expect(wrapper.get('[aria-label="关闭报价编辑器"]').element.disabled).toBe(false)
  await wrapper.get('.packaging-config-modal').trigger('submit')
  await flushPromises()
  expect(mocks.api.put).toHaveBeenCalledTimes(2)
  expect(mocks.api.put).toHaveBeenLastCalledWith('/skus/2/packaging/', { packaging_template: 5, qty_per_carton_override: 12, unit_net_weight: 0.25 })
  expect(wrapper.find('.packaging-config-modal').exists()).toBe(false)
  await wrapper.vm.requestClose()
  expect(wrapper.emitted('close')).toHaveLength(1)
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
})
