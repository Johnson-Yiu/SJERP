import { createMemoryHistory, createRouter } from 'vue-router'
import { createWorkspaceManager } from '../workspaceManager'
import { workspaceKey, workspaceManagerKey } from '../composables/useWorkspaceNavigation'
import { loadAccessControl, setAccessOperator } from '../accessControl'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PurchasePaymentModal from './PurchasePaymentModal.vue'

const financeAccount = id => setAccessOperator({ authenticated: true, user_id: id, has_all_permissions: true })
const savedKey = key => `sunjack:finance-attempt:v2:user:101:${key}`
beforeEach(() => { window.localStorage.clear(); financeAccount(101) })

import { api } from '../api'
beforeEach(() => {
  vi.spyOn(api, 'post')
  vi.spyOn(api, 'get')
})
afterEach(() => vi.restoreAllMocks())
vi.mock('../composables/useUnsavedChangesGuard', () => ({ useUnsavedChangesGuard: () => ({ markClean: vi.fn(), requestClose: callback => callback() }) }))

describe('purchase payment retry identity', () => {
  afterEach(() => { window.sessionStorage.clear(); vi.clearAllMocks() })

  it('reuses the original payment after an unknown response and a reopen', async () => {
    api.post.mockRejectedValueOnce(new Error('connection lost')).mockResolvedValueOnce({ data: { id: 1 } })
    const purchase = { id: 42, purchase_no: 'PO-SYNTH', supplier_name: '合成供应商', currency: 'USD', exchange_rate: '7.2', unpaid_amount: 100, paid_amount: 0 }
    const route = { path: '/purchase-orders', query: { detail: '42' } }
    const router = createRouter({ history: createMemoryHistory(), routes: ['/', route.path].map(path => ({ path, component: { template: '<div />' } })) })
    await router.push(route)
    const manager = createWorkspaceManager(router)
    async function openFor(userId, row = purchase) {
      financeAccount(userId)
      manager.reset(String(userId))
      const workspace = await manager.open(route, { sync: false })
      return { workspace, wrapper: mount(PurchasePaymentModal, { props: { purchase: row },
        global: { provide: { [workspaceKey]: workspace, [workspaceManagerKey]: manager } } }) }
    }
    const original = await openFor(101)
    const first = original.wrapper
    window.sessionStorage.setItem('finance-purchase-payment-42', JSON.stringify({ key: 'legacy', payload: { amount: '99' } }))
    await first.get('input[type="number"]').setValue('50')
    await first.get('input[aria-label="本次实际汇率"]').setValue('7.2')
    await first.get('input[placeholder="填写转账流水号（可选）"]').setValue('BANK-ONLY-A')
    await first.get('textarea').setValue('NOTE-ONLY-A')
    await first.get('form').trigger('submit.prevent')
    await flushPromises()
    expect(first.text()).toContain('付款结果待确认')
    const firstCall = api.post.mock.calls[0]
    expect(firstCall[2].headers['Idempotency-Key']).toMatch(/^PURCHASE-PAY-/)
    first.unmount()
    expect(await manager.close([original.workspace.id])).toBe(true)
    expect(original.workspace.closed).toBe(true)
    const other = await openFor(202)
    expect(other.wrapper.text()).not.toContain('上次付款结果待确认')
    expect(other.wrapper.get('input[type="number"]').element.value).toBe('')
    expect(other.wrapper.get('input[placeholder="填写转账流水号（可选）"]').element.value).toBe('')
    expect(other.wrapper.get('textarea').element.value).toBe('')
    expect(other.wrapper.text()).toContain('旧版待核对记录')
    other.wrapper.unmount()
    const recovered = await openFor(101, { ...purchase, unpaid_amount: 0, paid_amount: 100 })
    const reopened = recovered.wrapper
    expect(recovered.workspace.id).not.toBe(original.workspace.id)
    expect(reopened.get('textarea').element.value).toBe('NOTE-ONLY-A')
    expect(reopened.text()).toContain('上次付款结果待确认')
    await reopened.get('form').trigger('submit.prevent')
    await flushPromises()
    expect(api.post.mock.calls[1].slice(0, 2)).toEqual(firstCall.slice(0, 2))
    expect(api.post.mock.calls[1][2].headers).toEqual(firstCall[2].headers)
    expect(reopened.emitted('saved')).toBeTruthy()
    expect(window.localStorage.getItem(savedKey('finance-purchase-payment-42'))).toBeNull()
    expect(window.sessionStorage.getItem('finance-purchase-payment-42')).toContain('legacy')
    reopened.unmount()
    const next = await openFor(101)
    api.post.mockResolvedValueOnce({ data: { id: 2 } })
    await next.wrapper.get('input[type="number"]').setValue('10')
    await next.wrapper.get('input[aria-label="本次实际汇率"]').setValue('7.2')
    await next.wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.post.mock.calls[2][2].headers['Idempotency-Key']).not.toBe(firstCall[2].headers['Idempotency-Key'])
    next.wrapper.unmount()
    manager.destroy()
  })
})

const row = { id: 42, purchase_no: 'PO-A2', currency: 'CNY', unpaid_amount: 100 }
const key = savedKey('finance-purchase-payment-42')
const submit = wrapper => wrapper.get('form').trigger('submit')
const enter = (wrapper, amount) => wrapper.get('input[type=number]').setValue(amount)
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

async function openWorkspaces() {
  const router = createRouter({ history: createMemoryHistory(), routes: ['/purchase-orders', '/payables'].map(path => ({ path, component: { template: '<div />' } })) })
  const manager = createWorkspaceManager(router)
  manager.reset('101')
  async function open(path, beforeMount = () => {}) {
    const workspace = await manager.open({ path }, { sync: false })
    beforeMount()
    const wrapper = mount(PurchasePaymentModal, { props: { purchase: row },
      global: { provide: { [workspaceKey]: workspace, [workspaceManagerKey]: manager } } })
    return { workspace, wrapper }
  }
  return { manager, open }
}

it.each(['success', 'failure'])('keeps a newer payment after late %s and recovers it in a new workspace', async outcome => {
  api.post.mockReset()
  const late = deferred()
  api.post.mockReturnValueOnce(late.promise).mockResolvedValueOnce({ data: {} }).mockRejectedValueOnce(new Error('lost B'))
  const { open, manager } = await openWorkspaces()
  const old = await open('/purchase-orders')
  await enter(old.wrapper, '25')
  await submit(old.wrapper)
  const original = JSON.parse(localStorage.getItem(key))
  const replay = await open('/payables')
  await submit(replay.wrapper)
  await flushPromises()
  expect(api.post.mock.calls[1][2].headers['Idempotency-Key']).toBe(original.key)
  expect(localStorage.getItem(key)).toBeNull()
  replay.wrapper.unmount()
  await manager.close([replay.workspace.id])
  const newer = await open('/payables')
  await enter(newer.wrapper, '35')
  await submit(newer.wrapper)
  await flushPromises()
  const saved = localStorage.getItem(key)
  expect(JSON.parse(saved).key).not.toBe(original.key)
  if (outcome === 'success') late.resolve({ data: {} })
  else late.reject({ response: { status: 400, data: { detail: '旧付款被拒绝' } } })
  await flushPromises()
  expect(localStorage.getItem(key)).toBe(saved)
  newer.wrapper.unmount()
  await manager.close([newer.workspace.id])
  const restored = await open('/payables')
  expect(restored.wrapper.text()).toContain('上次付款结果待确认')
  expect(restored.wrapper.get('input[type=number]').element.value).toBe('35')
  old.wrapper.unmount()
  restored.wrapper.unmount()
  manager.destroy()
})

it.each(['same', 'failure', 'other'])('handles a real account refresh finishing with %s', async outcome => {
  api.post.mockReset().mockResolvedValue({ data: {} })
  const lookup = deferred()
  api.get.mockReset().mockResolvedValue({ data: { authenticated: true, user_id: 101, has_all_permissions: true } })
  let refresh
  const { open, manager } = await openWorkspaces()
  const { wrapper } = await open('/purchase-orders', () => {
    api.get.mockReturnValueOnce(lookup.promise)
    refresh = loadAccessControl({ force: true }).catch(() => {})
  })
  await enter(wrapper, '12')
  await submit(wrapper)
  expect(api.post).not.toHaveBeenCalled()
  expect(wrapper.text()).toContain('正在核对账号权限')
  if (outcome === 'failure') lookup.reject(new Error('session lookup failed'))
  else lookup.resolve({ data: { authenticated: true, user_id: outcome === 'same' ? 101 : 202, has_all_permissions: true } })
  await refresh
  await submit(wrapper)
  await flushPromises()
  if (outcome === 'same') expect(api.post).toHaveBeenCalledTimes(1)
  else {
    expect(api.post).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain(outcome === 'failure' ? '账号权限核对失败' : '当前账号已切换')
    expect(wrapper.get('input[type=number]').element.value).toBe('12')
  }
  wrapper.unmount()
  manager.destroy()
})
