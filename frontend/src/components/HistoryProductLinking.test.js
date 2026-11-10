// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { setAccessOperator } from '../accessControl'
import HistoryProductLinking from './HistoryProductLinking.vue'

const { api } = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn() } }))
vi.mock('../composables/useWorkspaceApi', () => ({ useWorkspaceApi: () => ({ api }) }))

const line = { id: 1, name: 'A2灯', code: 'A2', specification: '24W', unit: 'pcs', amount: '200', currency: 'CNY', quantity: '2', source_system: '来源一', source_number: '原单:1', status: 'pending' }
const target = { id: 2, code: 'B', name: '正式灯具', unit: 'pcs', specification: '24W' }

function button(wrapper, text) {
  return wrapper.findAll('button').find(node => node.text().includes(text))
}

async function open(wrapper) {
  await flushPromises()
  await wrapper.get('input[type="checkbox"]').setValue(true)
  await button(wrapper, '处理所选商品').trigger('click')
  await flushPromises()
  await wrapper.get('select[aria-label="正式 SKU"]').setValue('2')
  await button(wrapper, '生成预览').trigger('click')
  await flushPromises()
}

describe('HistoryProductLinking', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    Object.defineProperties(HTMLDialogElement.prototype, {
      showModal: { configurable: true, value() { this.setAttribute('open', '') } },
      close: { configurable: true, value() { this.removeAttribute('open'); this.dispatchEvent(new Event('close')) } },
    })
    api.get.mockImplementation(path => Promise.resolve({ data: path.endsWith('/targets/') ? [target] : { count: 1, results: [line] } }))
    api.post.mockResolvedValue({ data: { token: 'signed-preview', count: 1, target, rows: [line], quantities: { pcs: 2 }, amounts: { CNY: 200 } } })
  })

  it('clears a stale preview and lists the conflict', async () => {
    const wrapper = mount(HistoryProductLinking, { global: { stubs: ['RouterLink'] } })
    await open(wrapper)
    expect(wrapper.text()).toContain('影响 1 条明细')
    api.post.mockRejectedValueOnce({ response: { status: 409, data: { conflicts: [{ source_number: '原单:1', reason: '原关联已变化。' }] } } })
    await button(wrapper, '确认保存').trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('关联未保存')
    expect(wrapper.text()).toContain('原单:1 原关联已变化。')
    expect(button(wrapper, '确认保存')).toBeUndefined()
    wrapper.unmount()
  })

  it('keeps a preview on transient failure, guards duplicate writes and refreshes on success', async () => {
    const wrapper = mount(HistoryProductLinking, { global: { stubs: ['RouterLink'] } })
    await open(wrapper)
    api.post.mockRejectedValueOnce({ response: { status: 503 } })
    await button(wrapper, '确认保存').trigger('click')
    await flushPromises()
    let resolveWrite
    api.post.mockReturnValueOnce(new Promise(resolve => { resolveWrite = resolve }))
    await button(wrapper, '确认保存').trigger('click')
    expect(button(wrapper, '处理中').attributes('disabled')).toBeDefined()
    await button(wrapper, '处理中').trigger('click')
    expect(api.post.mock.calls.filter(([url]) => url.endsWith('/apply/'))).toHaveLength(2)
    resolveWrite({ data: { updated: 1 } })
    await flushPromises()
    expect(wrapper.text()).toContain('已更新 1 条历史商品。')
    expect(wrapper.emitted('saved')).toHaveLength(1)
    wrapper.unmount()
  })

  it('discards an old account response and its selection', async () => {
    const wrapper = mount(HistoryProductLinking, { global: { stubs: ['RouterLink'] } })
    await open(wrapper)
    let resolveOld
    api.post.mockReturnValueOnce(new Promise(resolve => { resolveOld = resolve }))
    await button(wrapper, '确认保存').trigger('click')
    api.get.mockResolvedValue({ data: { count: 0, results: [] } })
    setAccessOperator({ name: '新账号', authenticated: true, has_all_permissions: true })
    await flushPromises()
    resolveOld({ data: { updated: 1 } })
    await flushPromises()
    expect(wrapper.text()).toContain('没有符合条件的历史商品')
    expect(wrapper.emitted('saved')).toBeUndefined()
    expect(wrapper.get('dialog').attributes('open')).toBeUndefined()
    wrapper.unmount()
  })
})
