// @vitest-environment jsdom
import { expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ImportPage from '../src/views/ImportPage.vue'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), confirm: vi.fn() }))
vi.mock('../src/api', () => ({ api: { get: mocks.get, post: mocks.post } }))
vi.mock('../src/dialogs', () => ({ confirmDialog: mocks.confirm }))

it('invalidates the preview after a state conflict and requires a fresh preview', async () => {
  mocks.get.mockResolvedValue({ data: { customers: ['code', 'name'] } })
  mocks.confirm.mockResolvedValue(true)
  const preview = { total: 1, created: 1, updated: 0, errors: [], preview_token: 'old-token' }
  mocks.post.mockResolvedValueOnce({ data: preview })
    .mockRejectedValueOnce(new Error('数据状态已发生变化，请重新预览后再导入。'))
    .mockResolvedValueOnce({ data: { ...preview, preview_token: 'new-token' } })
  const wrapper = mount(ImportPage)
  try {
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [new File(['code,name\nA,Buyer'], 'test.csv')] })
    await input.trigger('change')
    const button = text => wrapper.findAll('button').find(item => item.text() === text)
    await button('预览并校验').trigger('click')
    await flushPromises()
    await button('确认执行导入').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('数据状态已发生变化，请重新预览后再导入。')
    expect(button('确认执行导入')).toBeUndefined()
    expect(wrapper.text()).not.toContain('将新增')
    expect(mocks.post.mock.calls[1][1].get('preview_token')).toBe('old-token')
    await button('预览并校验').trigger('click')
    await flushPromises()
    expect(button('确认执行导入')).toBeDefined()
    expect(mocks.post.mock.calls[2][0]).toBe('/import/csv/preview/')
  } finally { wrapper.unmount() }
})
