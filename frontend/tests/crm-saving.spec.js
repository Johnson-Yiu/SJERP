// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, reactive } from 'vue'
import { createMemoryHistory, createRouter, isNavigationFailure } from 'vue-router'
import ResourcePage from '../src/views/ResourcePage.vue'
import { resourceConfigs } from '../src/resourceConfigs'
import { installModalNavigationGuard } from '../src/utils/modalNavigation'
import { useUnsavedChangesGuard } from '../src/composables/useUnsavedChangesGuard'

const mocks = vi.hoisted(() => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, listAll: vi.fn(), confirmDialog: vi.fn(),
}))
vi.mock('../src/api', () => ({ api: mocks.api, listAll: mocks.listAll, listData: r => r.data }))
vi.mock('../src/dialogs', () => ({ confirmDialog: mocks.confirmDialog, inputDialog: vi.fn() }))

function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
let wrapper, router, records
const customer = { id: 1, name: 'Isolated CRM buyer', next_follow_up: '2026-10-20' }
const contact = { id: 7, customer: 1, customer_name: customer.name, name: 'Existing contact', title: 'Buyer', is_primary: true }
const followUp = { id: 7, customer: 1, customer_name: customer.name, subject: 'Existing follow-up', followed_at: '2026-10-15T09:00:00+08:00', type: 'email', content: 'Existing content', next_follow_up_mode: 'keep', attachments: [] }
beforeEach(() => {
  vi.clearAllMocks()
  records = []
  mocks.confirmDialog.mockResolvedValue(true)
  mocks.listAll.mockImplementation(async url => url === '/customers/' ? [customer] : url === '/contacts/' ? records : url === '/follow-ups/methods/' ? [{ value: 'email', label: '邮件' }] : records)
  mocks.api.get.mockImplementation(async url => ({ data: url.includes('current-operator') ? { name: 'Isolated developer' } : url.startsWith('/contacts/') ? contact : followUp }))
})
afterEach(() => wrapper?.unmount())

async function open(entity, edit = false) {
  router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { template: '<main />' } }] })
  installModalNavigationGuard(router)
  await router.push('/origin')
  await router.push(`/${entity}?customer=1`)
  await router.push(`/${entity}?customer=1&${edit ? 'edit=7' : 'create=1'}`)
  wrapper = mount(ResourcePage, { props: { config: resourceConfigs[entity] }, global: { plugins: [router], stubs: { Teleport: true, EntityDetailModal: true } } })
  await flushPromises()
  if (entity === 'contacts') await wrapper.get('[aria-label="姓名"]').setValue('Pending contact')
  else {
    await wrapper.get('[aria-label="主题"]').setValue('Pending follow-up')
    await wrapper.get('[aria-label="沟通记录"]').setValue('Pending content retained after failure')
    await wrapper.get('[aria-label="跟进方式"]').setValue('邮件')
  }
  await flushPromises()
}
async function tryLeaveWhileSaving(entity) {
  const original = router.currentRoute.value.fullPath
  await wrapper.get('.modal-backdrop').trigger('mousedown')
  await wrapper.vm.closeModal()
  expect(wrapper.get('.modal-head button').attributes('disabled')).toBeDefined()
  expect(wrapper.get('.modal-foot .btn-secondary').attributes('disabled')).toBeDefined()
  expect(wrapper.find('.modal').exists()).toBe(true)
  expect(isNavigationFailure(await router.push('/origin'))).toBe(true)
  expect(router.currentRoute.value.fullPath).toBe(original)
  await new Promise(resolve => {
    const stop = router.afterEach(() => { stop(); resolve() })
    router.back()
  })
  await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe(original)
  expect(wrapper.find('.modal').exists()).toBe(true)
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  expect(wrapper.get(entity === 'contacts' ? '[aria-label="姓名"]' : '[aria-label="主题"]').element.value).toBe(entity === 'contacts' ? 'Pending contact' : 'Pending follow-up')
}

for (const entity of ['contacts', 'follow-ups']) describe(`${entity} saving lifecycle`, () => {
  for (const edit of [false, true]) {
    it(`${edit ? 'PUT' : 'POST'} blocks backdrop, close, navigation and Back until success, then refreshes once`, async () => {
      await open(entity, edit)
      const request = deferred()
      const write = edit ? mocks.api.put : mocks.api.post
      write.mockReturnValueOnce(request.promise)
      const readsBefore = mocks.listAll.mock.calls.filter(([url]) => url === `/${entity}/`).length
      await wrapper.get('form.modal').trigger('submit')
      await wrapper.get('form.modal').trigger('submit')
      expect(write).toHaveBeenCalledTimes(1)
      await tryLeaveWhileSaving(entity)
      records = [{ ...(entity === 'contacts' ? contact : followUp), name: 'Pending contact', subject: 'Pending follow-up' }]
      request.resolve({ data: { id: 7 } })
      await flushPromises()
      expect(wrapper.find('.modal').exists()).toBe(false)
      expect(router.currentRoute.value.fullPath).toBe(`/${entity}?customer=1`)
      expect(mocks.listAll.mock.calls.filter(([url]) => url === `/${entity}/`).length).toBe(readsBefore + 1)
      expect(wrapper.text()).toContain(entity === 'contacts' ? 'Pending contact' : 'Pending follow-up')
      expect(mocks.confirmDialog).not.toHaveBeenCalled()
      await router.push('/origin')
      expect(router.currentRoute.value.path).toBe('/origin')
    })
    it(`${edit ? 'PUT' : 'POST'} failure preserves inputs and permits one retry`, async () => {
      await open(entity, edit)
      const request = deferred()
      const retry = deferred()
      const write = edit ? mocks.api.put : mocks.api.post
      write.mockReturnValueOnce(request.promise).mockReturnValueOnce(retry.promise)
      await wrapper.get('form.modal').trigger('submit')
      await tryLeaveWhileSaving(entity)
      request.reject(new Error('Controlled save failure'))
      await flushPromises()
      expect(wrapper.text()).toContain('Controlled save failure')
      expect(wrapper.get(entity === 'contacts' ? '[aria-label="姓名"]' : '[aria-label="主题"]').element.value).toBe(entity === 'contacts' ? 'Pending contact' : 'Pending follow-up')
      expect(wrapper.get('.modal-foot .btn-primary').attributes('disabled')).toBeUndefined()
      await wrapper.get('form.modal').trigger('submit')
      await wrapper.get('form.modal').trigger('submit')
      expect(write).toHaveBeenCalledTimes(2)
      expect(write.mock.calls[1][1]).toEqual(write.mock.calls[0][1])
      retry.resolve({ data: { id: 7 } })
      await flushPromises()
      expect(wrapper.find('.modal').exists()).toBe(false)
      expect(mocks.confirmDialog).not.toHaveBeenCalled()
    })
  }
  it('a discard confirmation opened before saving cannot close the now-busy editor', async () => {
    await open(entity)
    const confirmation = deferred(), request = deferred()
    mocks.confirmDialog.mockReturnValueOnce(confirmation.promise)
    const closing = wrapper.vm.closeModal()
    mocks.api.post.mockReturnValueOnce(request.promise)
    await wrapper.get('form.modal').trigger('submit')
    confirmation.resolve(true)
    await closing
    expect(wrapper.find('.modal').exists()).toBe(true)
    expect(mocks.api.post).toHaveBeenCalledTimes(1)
    request.resolve({ data: { id: 7 } })
    await flushPromises()
    expect(wrapper.find('.modal').exists()).toBe(false)
  })
})

it('follow-up navigation stays locked after the record becomes clean while attachment upload is pending', async () => {
  await open('follow-ups')
  wrapper.vm.pendingFollowUpFiles = [new File(['isolated'], 'saving.txt', { type: 'text/plain' })]
  const record = deferred(), attachment = deferred()
  mocks.api.post.mockReturnValueOnce(record.promise).mockReturnValueOnce(attachment.promise)
  await wrapper.get('form.modal').trigger('submit')
  record.resolve({ data: { id: 7 } })
  await flushPromises()
  expect(mocks.api.post).toHaveBeenCalledTimes(2)
  expect(mocks.api.post.mock.calls[1][0]).toBe('/follow-ups/7/attachments/')
  await tryLeaveWhileSaving('follow-ups')
  attachment.resolve({ data: [] })
  await flushPromises()
  expect(wrapper.find('.modal').exists()).toBe(false)
})

it('a clean editor still protects document unload while its save is busy', async () => {
  const state = reactive({ busy: true, input: 'unchanged' })
  wrapper = mount(defineComponent({
    setup() {
      const guard = useUnsavedChangesGuard({ data: () => state.input, busy: () => state.busy })
      guard.markClean()
      return () => null
    },
  }))
  const pendingUnload = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(pendingUnload)
  expect(pendingUnload.defaultPrevented).toBe(true)
  state.busy = false
  await flushPromises()
  const finishedUnload = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(finishedUnload)
  expect(finishedUnload.defaultPrevented).toBe(false)
})
