// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ResourcePage from '../src/views/ResourcePage.vue'
import RelatedCreateModal from '../src/components/RelatedCreateModal.vue'
import { resourceConfigs } from '../src/resourceConfigs'

const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, listAll: vi.fn() }))
vi.mock('../src/api', () => ({ api: mocks.api, listAll: mocks.listAll, listData: response => response.data?.results || response.data || [] }))
let wrapper
beforeEach(() => {
  vi.clearAllMocks()
  mocks.listAll.mockImplementation(async url => url === '/customers/' ? [{ id: 1, name: 'UAT Buyer', next_follow_up: '2026-10-20' }] : [])
  mocks.api.get.mockResolvedValue({ data: { name: 'Development' } })
  mocks.api.post.mockResolvedValue({ data: { id: 123 } })
})
afterEach(() => { wrapper?.unmount() })
async function open() {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/follow-ups', component: { template: '<div />' } }] })
  await router.push('/follow-ups?create=1&customer=1')
  wrapper = mount(ResourcePage, { props: { config: resourceConfigs['follow-ups'] }, global: { plugins: [router] } })
  await flushPromises()
}
async function submit() { await wrapper.get('form.modal').trigger('submit'); await flushPromises() }
it('blocks blank communication before POST and accepts result only', async () => {
  await open()
  await submit()
  expect(mocks.api.post).not.toHaveBeenCalled()
  expect(wrapper.text()).toContain('请至少填写跟进记录或客户回复，避免保存空白跟进。')
  await wrapper.findAll('textarea')[1].setValue('客户已确认规格')
  await submit()
  expect(mocks.api.post).toHaveBeenCalledWith('/follow-ups/', expect.objectContaining({ result: '客户已确认规格', next_follow_up_mode: 'keep', next_follow_up: null }))
})
it('defaults to keep, shows the current plan and hides the date input', async () => {
  await open()
  expect(wrapper.get('input[value="keep"]').element.checked).toBe(true)
  expect(wrapper.text()).toContain('当前计划：2026-10-20')
  expect(wrapper.find('[aria-label="下次跟进天数"]').exists()).toBe(false)
})
it('set requires a date and submits the chosen schedule', async () => {
  await open()
  await wrapper.findAll('textarea')[0].setValue('发送产品资料')
  await wrapper.get('input[value="set"]').setValue()
  await submit()
  expect(mocks.api.post).not.toHaveBeenCalled()
  expect(wrapper.text()).toContain('请填写新的跟进日期。')
  await wrapper.get('[aria-label="下次跟进天数"]').setValue('15')
  await submit()
  expect(mocks.api.post).toHaveBeenCalledWith('/follow-ups/', expect.objectContaining({ next_follow_up_mode: 'set', next_follow_up: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/) }))
})
it('clear is explicit, discards a set date and posts a null date', async () => {
  await open()
  await wrapper.findAll('textarea')[0].setValue('客户暂不需要后续跟进')
  await wrapper.get('input[value="set"]').setValue()
  await wrapper.get('[aria-label="下次跟进天数"]').setValue('15')
  await wrapper.get('input[value="clear"]').setValue()
  expect(wrapper.text()).toContain('这会清除该客户当前的下次跟进日期。')
  expect(wrapper.find('[aria-label="下次跟进天数"]').exists()).toBe(false)
  await submit()
  expect(mocks.api.post).toHaveBeenCalledWith('/follow-ups/', expect.objectContaining({ next_follow_up_mode: 'clear', next_follow_up: null }))
})
it('customer detail quick-create uses the same safety decisions and blocks empty communication', async () => {
  mocks.api.get.mockImplementation(async url => ({ data: url === '/customers/' ? [{ id: 1, name: 'UAT Buyer', next_follow_up: '2026-10-20' }] : url === '/session/current-operator/' ? { name: 'Development' } : [] }))
  wrapper = mount(RelatedCreateModal, { props: { entity: 'follow-ups', query: { customer: 1 } }, global: { stubs: { Teleport: true } } })
  await flushPromises()
  expect(wrapper.text()).toContain('当前计划：2026-10-20')
  await wrapper.get('form').trigger('submit')
  expect(mocks.api.post).not.toHaveBeenCalled()
  expect(wrapper.get('[role="alert"]').text()).toContain('请至少填写跟进记录或客户回复')
  await wrapper.findAll('textarea')[0].setValue('已沟通资料')
  await wrapper.get('input[value="set"]').setValue()
  await wrapper.get('form').trigger('submit')
  expect(mocks.api.post).not.toHaveBeenCalled()
  expect(wrapper.get('[role="alert"]').text()).toContain('请填写新的跟进日期')
  await wrapper.get('[aria-label="下次跟进天数"]').setValue('15')
  await wrapper.get('input[value="clear"]').setValue()
  expect(wrapper.text()).toContain('这会清除该客户当前的下次跟进日期。')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(mocks.api.post).toHaveBeenCalledWith('/follow-ups/', expect.objectContaining({ next_follow_up_mode: 'clear', next_follow_up: null }))
})

it('keeps a saved follow-up open when attachment upload fails and retries only the attachment', async () => {
  await open()
  await wrapper.findAll('textarea')[0].setValue('附件上传重试验收')
  wrapper.vm.pendingFollowUpFiles = [new File(['retry'], 'iss007-retry.txt', { type: 'text/plain' })]
  mocks.api.post.mockImplementation(async url => {
    if (url.includes('/attachments/')) throw new Error('上传暂时失败')
    return { data: { id: 123 } }
  })

  await submit()

  expect(wrapper.find('.modal').exists()).toBe(true)
  expect(wrapper.get('[role="alert"]').text()).toContain('附件上传失败')
  expect(wrapper.text()).toContain('iss007-retry.txt')
  expect(mocks.api.post.mock.calls.filter(([url]) => url.includes('/attachments/'))).toHaveLength(1)

  mocks.api.put.mockResolvedValue({ data: { id: 123 } })
  mocks.api.post.mockImplementation(async url => {
    if (url.includes('/attachments/')) return { data: [{ id: 88, name: 'iss007-retry.txt' }] }
    return { data: { id: 123 } }
  })
  await submit()

  expect(mocks.api.put).toHaveBeenCalledWith('/follow-ups/123/', expect.anything())
  expect(mocks.api.post.mock.calls.filter(([url]) => url.includes('/attachments/'))).toHaveLength(2)
  expect(wrapper.find('.modal').exists()).toBe(false)
})
