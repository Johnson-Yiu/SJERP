// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ResourcePage from '../src/views/ResourcePage.vue'
import { resourceConfigs } from '../src/resourceConfigs'

const mocks = vi.hoisted(() => ({
  listAll: vi.fn(),
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
}))
vi.mock('../src/api', () => ({
  api: mocks.api,
  listAll: mocks.listAll,
  listData: response => response.data?.results || response.data || [],
}))
vi.mock('../src/dialogs', () => ({ confirmDialog: vi.fn(), inputDialog: vi.fn() }))

function deferred() {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}

let wrapper
let router
let savedRecord
let listRefresh
let deferListRefresh

beforeEach(async () => {
  vi.resetAllMocks()
  deferListRefresh = false
  listRefresh = deferred()
  savedRecord = {
    id: 7,
    customer: 1,
    contact: 2,
    followed_at: '2026-11-05T10:30:00+08:00',
    type: 'phone',
    subject: 'ISS007 回访',
    content: '修复前保存的沟通正文',
    result: '客户确认收到资料',
    next_action: '发送规格表',
    next_follow_up_mode: 'keep',
    next_follow_up: null,
    owner: '开发身份',
    attachments: [],
  }
  mocks.listAll.mockImplementation(url => {
    if (url === '/follow-ups/') {
      if (deferListRefresh) return listRefresh.promise
      // The list row is intentionally the summary shape used by the table;
      // body text and saved attachments come from the detail endpoint.
      return Promise.resolve([{
        id: 7,
        followed_at: savedRecord.followed_at,
        customer_name: '测试客户',
        subject: savedRecord.subject,
        type_display: '电话',
        result: savedRecord.result,
        owner: savedRecord.owner,
      }])
    }
    if (url === '/customers/') return Promise.resolve([{ id: 1, name: '测试客户' }])
    if (url === '/contacts/') return Promise.resolve([{ id: 2, name: '测试联系人' }])
    return Promise.resolve([])
  })
  mocks.api.get.mockImplementation(async url => {
    if (url === '/follow-ups/7/') return { data: structuredClone(savedRecord) }
    return { data: [] }
  })
  mocks.api.put.mockImplementation(async (_url, payload) => {
    savedRecord = { ...savedRecord, ...payload }
    return { data: { id: 7 } }
  })
  mocks.api.post.mockImplementation(async url => {
    if (url.endsWith('/attachments/')) {
      const attachment = { id: 88, name: 'ISS007-沟通纪要.txt', size: 18 }
      savedRecord = { ...savedRecord, attachments: [attachment] }
      return { data: [attachment] }
    }
    return { data: { id: 7 } }
  })

  router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/follow-ups', component: { template: '<main />' } }],
  })
  await router.push('/follow-ups?edit=7')
  wrapper = mount(ResourcePage, {
    props: { config: resourceConfigs['follow-ups'] },
    global: { plugins: [router], stubs: { Teleport: true } },
  })
  await flushPromises()
})

afterEach(() => wrapper?.unmount())

it('reopens the just-saved follow-up during list refresh with its detail and uploaded attachment intact', async () => {
  expect(wrapper.find('.modal').exists()).toBe(true)
  expect(wrapper.vm.form.content).toBe('修复前保存的沟通正文')

  wrapper.vm.form.content = '保存后的沟通正文'
  wrapper.vm.form.result = '客户确认收到并已阅读资料'
  wrapper.vm.pendingFollowUpFiles = [new File(['会议纪要内容'], 'ISS007-沟通纪要.txt', { type: 'text/plain' })]
  deferListRefresh = true

  await wrapper.get('form').trigger('submit')
  await flushPromises()

  expect(wrapper.text()).toContain('跟进记录已更新')
  expect(wrapper.find('.modal').exists()).toBe(false)
  expect(savedRecord.content).toBe('保存后的沟通正文')
  expect(savedRecord.attachments).toEqual([{ id: 88, name: 'ISS007-沟通纪要.txt', size: 18 }])

  // The old table summary is still visible while the post-save list request is
  // held. Reopening must hydrate from the saved record, not that stale summary.
  await wrapper.get('button[aria-label="编辑跟进记录"]').trigger('click')
  await flushPromises()

  expect(wrapper.find('.modal').exists()).toBe(true)
  expect(wrapper.vm.form.content).toBe('保存后的沟通正文')
  expect(wrapper.vm.form.result).toBe('客户确认收到并已阅读资料')
  expect(wrapper.vm.followUpAttachments).toEqual([{ id: 88, name: 'ISS007-沟通纪要.txt', size: 18 }])

  listRefresh.resolve([{
    id: 7,
    followed_at: savedRecord.followed_at,
    customer_name: '测试客户',
    subject: savedRecord.subject,
    type_display: '电话',
    result: savedRecord.result,
    owner: savedRecord.owner,
  }])
  await flushPromises()
  expect(wrapper.vm.form.content).toBe('保存后的沟通正文')
  expect(wrapper.vm.followUpAttachments).toEqual([{ id: 88, name: 'ISS007-沟通纪要.txt', size: 18 }])
})
