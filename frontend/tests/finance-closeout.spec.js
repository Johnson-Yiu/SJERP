import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import FinanceLedgerPage from '../src/views/FinanceLedgerPage.vue'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('../src/api', () => ({ api }))
vi.mock('../src/accessControl', () => ({ useAccessControl: () => ({ can: () => true }) }))
let wrapper
const empty = { accounts: [], vouchers: [], instructions: [], reviews: [], mappings: [], transfers: [] }
beforeEach(() => {
  window.sessionStorage.clear()
  vi.clearAllMocks()
  api.get.mockImplementation(url => Promise.resolve({ data: url.endsWith('/facts/') ? { facts: [], totals: { inflow: '0', outflow: '0', net: '0' } } : { ...empty } }))
  api.post.mockResolvedValue({ data: {} })
})
afterEach(() => { wrapper?.unmount(); vi.restoreAllMocks() })
async function openInstructions() {
  wrapper = mount(FinanceLedgerPage)
  await flushPromises()
  await wrapper.findAll('nav button').find(b => b.text() === '登记与复核').trigger('click')
  return wrapper.findAll('form')[1]
}

describe('account cash request identity', () => {
  it('blocks submission if browser storage cannot persist request identity', async () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('denied') })
    const form = await openInstructions()
    await form.trigger('submit'); await flushPromises()
    expect(api.post).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('请求身份需核查')
  })
  it('retains a failed request key and prevents an unknown outcome becoming a new operation', async () => {
    const form = await openInstructions()
    api.post.mockRejectedValue(new Error('response lost'))
    await form.trigger('submit'); await flushPromises()
    const first = api.post.mock.calls[0][1].request_key
    await form.trigger('submit'); await flushPromises()
    expect(api.post.mock.calls[1][1].request_key).toBe(first)
    await wrapper.findAll('button').find(b => b.text() === '开始独立新操作').trigger('click')
    expect(wrapper.text()).toContain('上次请求结果未知')
    expect(JSON.parse(sessionStorage.getItem('sunjack:finance-ledger:pending-request:v1')).key).toBe(first)
  })
  it('does not treat storage getter failure as permission to generate a fresh request', async () => {
    vi.spyOn(window, 'sessionStorage', 'get').mockImplementation(() => { throw new Error('disabled') })
    const form = await openInstructions()
    await form.trigger('submit'); await flushPromises()
    expect(api.post).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('请求身份需核查')
  })
})
