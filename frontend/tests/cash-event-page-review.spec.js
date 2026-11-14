import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { reactive } from 'vue'
import CashEventPage from '../src/views/CashEventPage.vue'
import CashEventEntryForm from '../src/components/CashEventEntryForm.vue'
import { setAccessOperator } from '../src/accessControl'

const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn() }, route: null }))
vi.mock('../src/composables/useWorkspaceApi', () => ({ useWorkspaceApi: () => ({ api: mocks.api }) }))
vi.mock('vue-router', () => ({ useRoute: () => mocks.route, onBeforeRouteLeave: vi.fn() }))
vi.mock('../src/composables/useUnsavedChangesGuard', () => ({
  useUnsavedChangesGuard: () => ({ requestClose: callback => callback(), markClean: vi.fn() }),
}))

const event = (overrides = {}) => ({
  id: 71, event_no: 'SYNTH-REVIEW-71', status: 'pending', kind: 'bank_fee',
  direction: 'expense', currency: 'CNY', amount: '5.00', bank_net_amount: '5.00',
  bank_date: '2026-11-14', bank_reference: 'SYNTH-BANK-71', private_voucher: 7,
  fee_mode: 'none', fee_amount: '0', sources: [], orders: [], ...overrides,
})
const deferred = () => {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}
let wrapper
let listRows

beforeEach(() => {
  window.localStorage.clear()
  setAccessOperator({ authenticated: true, user_id: 101, has_all_permissions: true })
  mocks.route = reactive({ query: {} })
  listRows = []
  mocks.api.get.mockReset().mockImplementation(async url => ({ data:
    url.endsWith('/duplicate-candidates/') ? { count: 0, items: [] } : { results: listRows },
  }))
  mocks.api.post.mockReset().mockImplementation(async () => ({ data: event({ status: 'confirmed' }) }))
})
afterEach(() => { wrapper?.unmount(); document.body.innerHTML = ''; window.localStorage.clear() })

async function mountPage(query = {}) {
  mocks.route.query = query
  wrapper = mount(CashEventPage, { attachTo: document.body, global: { stubs: { RouterLink: true } } })
  await flushPromises()
}
const confirmButton = () => wrapper.findAll('button').find(button => button.text() === '确认银行凭证')

describe('bank event review survives list refresh', () => {
  it('opens the initial deep link after a failed first load is retried', async () => {
    listRows = [event()]
    mocks.api.get.mockRejectedValueOnce(new Error('Synthetic list unavailable'))
    await mountPage({ event: '71' })
    expect(wrapper.find('.cash-load-error').exists()).toBe(true)
    expect(wrapper.findComponent(CashEventEntryForm).exists()).toBe(false)
    await wrapper.get('.cash-load-error button').trigger('click')
    await flushPromises()
    expect(wrapper.findComponent(CashEventEntryForm).props('initialEvent').id).toBe(71)
    expect(wrapper.get('.review-confirm input').element.checked).toBe(false)
  })

  it('does not reopen the initial deep link after the user chooses a new event during loading', async () => {
    const initialList = deferred()
    mocks.api.get.mockImplementation(url => url === '/rmb-cash-events/'
      ? initialList.promise : Promise.resolve({ data: { results: [] } }))
    await mountPage({ event: '71' })
    await wrapper.findAll('button').find(button => button.text() === '新增资金事件').trigger('click')
    await flushPromises()
    await wrapper.get('[aria-label="关闭资金表单"]').trigger('click')
    initialList.resolve({ data: { results: [event()] } })
    await flushPromises()
    expect(wrapper.findComponent(CashEventEntryForm).exists()).toBe(false)
    expect(wrapper.find('.cash-detail-panel').exists()).toBe(false)
    expect(wrapper.get('.cash-table').text()).toContain('SYNTH-REVIEW-71')
  })

  for (const deepLink of [false, true]) {
    it(`preserves checked review while the ${deepLink ? 'deep-linked updated' : 'newly created'} event list arrives late`, async () => {
      listRows = deepLink ? [event()] : []
      await mountPage(deepLink ? { event: '71' } : {})
      if (!deepLink) {
        await wrapper.findAll('button').find(button => button.text() === '新增资金事件').trigger('click')
        await flushPromises()
      }
      const pendingList = deferred()
      mocks.api.get.mockImplementation(url => url === '/rmb-cash-events/'
        ? pendingList.promise : Promise.resolve({ data: { count: 0, items: [] } }))
      const saved = event({ bank_reference: 'SYNTH-AUTHORITATIVE-SAVE' })
      wrapper.findComponent(CashEventEntryForm).vm.$emit(deepLink ? 'updated' : 'created', saved)
      await flushPromises()
      const checkbox = wrapper.get('.review-confirm input')
      await checkbox.setValue(true)
      expect(confirmButton().element.disabled).toBe(false)

      // A list response is a separate object and may predate the save result.
      pendingList.resolve({ data: { results: [event({ bank_reference: 'SYNTH-OLDER-LIST' })] } })
      await flushPromises()
      expect(checkbox.element.checked).toBe(true)
      expect(wrapper.findComponent(CashEventEntryForm).props('initialEvent')).toEqual(saved)
      expect(confirmButton().element.disabled).toBe(false)
      await confirmButton().trigger('click')
      await flushPromises()
      expect(mocks.api.post).toHaveBeenCalledWith('/rmb-cash-events/71/confirm/', { voucher_checked: true })
      expect(wrapper.text()).toContain('已确认')
    })
  }

  it('opens an initial deep link but a manual list refresh does not reset active review', async () => {
    listRows = [event()]
    await mountPage({ event: '71' })
    expect(wrapper.findComponent(CashEventEntryForm).props('initialEvent').id).toBe(71)
    await wrapper.get('.review-confirm input').setValue(true)
    const pendingList = deferred()
    mocks.api.get.mockImplementation(() => pendingList.promise)
    await wrapper.findAll('button').find(button => button.text() === '刷新').trigger('click')
    pendingList.resolve({ data: { results: [event()] } })
    await flushPromises()
    expect(wrapper.get('.review-confirm input').element.checked).toBe(true)
    expect(confirmButton().element.disabled).toBe(false)
  })

  it('still opens an explicitly selected different event and requires its own voucher review', async () => {
    listRows = [event(), event({ id: 72, event_no: 'SYNTH-REVIEW-72', private_voucher: null })]
    await mountPage({ event: '71' })
    await wrapper.get('.review-confirm input').setValue(true)
    await wrapper.get('[aria-label="关闭资金表单"]').trigger('click')
    await wrapper.findAll('.cash-row .row-action')[1].trigger('click')
    await flushPromises()
    expect(wrapper.findComponent(CashEventEntryForm).props('initialEvent').id).toBe(72)
    expect(wrapper.get('.review-confirm input').element.checked).toBe(false)
    await wrapper.get('.review-confirm input').setValue(true)
    expect(confirmButton().element.disabled).toBe(true)
    expect(wrapper.text()).toContain('请先补传并校验实际银行凭证')
    expect(mocks.api.post).not.toHaveBeenCalled()
  })
})
