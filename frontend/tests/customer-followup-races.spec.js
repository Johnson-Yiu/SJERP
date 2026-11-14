// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ResourcePage from '../src/views/ResourcePage.vue'
import { resourceConfigs } from '../src/resourceConfigs'

const mocks = vi.hoisted(() => ({ listAll: vi.fn(), api: { get: vi.fn() } }))
vi.mock('../src/api', () => ({ ...mocks, listData: r => r.data }))
vi.mock('../src/dialogs', () => ({ confirmDialog: vi.fn(), inputDialog: vi.fn() }))
let wrapper, router
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
beforeEach(() => {
  vi.resetAllMocks()
  mocks.listAll.mockResolvedValue([])
  mocks.api.get.mockResolvedValue({ data: { name: '开发身份' } })
})
afterEach(() => wrapper?.unmount())
it('reopens a complete but stale follow-up row using the saved attachment detail', async () => {
  await open('follow-ups')
  const stale = { ...Object.fromEntries(resourceConfigs['follow-ups'].fields.map(([key]) => [key, ''])), id: 7, subject: 'Saved follow-up', attachments: [] }
  const attachment = { id: 81, original_name: 'saved-evidence.txt', url: '/api/media/saved-evidence.txt' }
  mocks.api.get.mockResolvedValue({ data: { ...stale, attachments: [attachment] } })
  await wrapper.vm.openEdit(stale)
  await flushPromises()
  expect(mocks.api.get).toHaveBeenCalledWith('/follow-ups/7/')
  expect(wrapper.vm.followUpAttachments).toEqual([attachment])
  expect(wrapper.findAll('.follow-up-attachment-editor-item.saved')).toHaveLength(1)
})
it('keeps the newer direct editor and its input when an older detail arrives', async () => {
  await open('follow-ups')
  const first = deferred(), second = deferred()
  mocks.api.get.mockImplementation(url => url === '/follow-ups/1/' ? first.promise : second.promise)
  const openingFirst = wrapper.vm.openEdit({ id: 1, attachments: [] })
  const openingSecond = wrapper.vm.openEdit({ id: 2, attachments: [] })
  second.resolve({ data: { id: 2, subject: 'B', attachments: [] } })
  await openingSecond
  await wrapper.get('[aria-label="主题"]').setValue('B unsaved input')
  first.resolve({ data: { id: 1, subject: 'A', attachments: [] } })
  await openingFirst
  expect(wrapper.vm.editingId).toBe(2)
  expect(wrapper.get('[aria-label="主题"]').element.value).toBe('B unsaved input')
})
for (const action of ['create', 'close']) it(`invalidates a pending direct edit when the user chooses ${action}`, async () => {
  await open('follow-ups')
  const old = deferred()
  mocks.api.get.mockImplementation(url => url === '/follow-ups/1/' ? old.promise : Promise.resolve({ data: { name: 'Developer' } }))
  const opening = wrapper.vm.openEdit({ id: 1, attachments: [] })
  await wrapper.vm.openCreate()
  if (action === 'close') await wrapper.vm.closeModal()
  else await wrapper.get('[aria-label="主题"]').setValue('New draft input')
  old.resolve({ data: { id: 1, subject: 'Old saved row', attachments: [] } })
  await opening
  expect(wrapper.vm.editingId).toBeNull()
  expect(wrapper.vm.modalOpen).toBe(action === 'create')
  if (action === 'create') expect(wrapper.get('[aria-label="主题"]').element.value).toBe('New draft input')
})
async function open(entity, query = '') {
  router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { template: '<main />' } }] })
  await router.push(`/${entity}${query}`)
  wrapper = mount(ResourcePage, { props: { config: resourceConfigs[entity] }, global: { plugins: [router], stubs: { Teleport: true, EntityDetailModal: true } } })
  await flushPromises()
}
for (const outcome of ['success', 'failure']) it(`customer search ignores obsolete ${outcome} while latest request loads`, async () => {
  const old = deferred(), latest = deferred()
  mocks.listAll.mockImplementation(url => url === '/customers/' ? old.promise : Promise.resolve([]))
  await open('customers')
  mocks.listAll.mockImplementation(url => url === '/customers/' ? latest.promise : Promise.resolve([]))
  await router.push('/customers?search=最新客户')
  await flushPromises()
  if (outcome === 'success') old.resolve([{ id: 1, name: '过期客户' }])
  else old.reject(new Error('obsolete failure'))
  await flushPromises()
  expect(wrapper.vm.loading).toBe(true)
  expect(wrapper.vm.rows).toEqual([])
  expect(wrapper.vm.loadError).toBe('')
  latest.resolve([{ id: 2, name: '最新客户' }])
  await flushPromises()
  expect(wrapper.text()).toContain('最新客户')
  expect(wrapper.text()).not.toContain('过期客户')
  expect(wrapper.vm.loading).toBe(false)
})
for (const entity of ['customers', 'contacts', 'follow-ups']) it(`${entity} ignores obsolete empty-state probe`, async () => {
  const probe = deferred()
  let calls = 0
  mocks.listAll.mockImplementation(url => {
    if (url === `/${entity}/`) return ++calls === 2 ? probe.promise : Promise.resolve([])
    return Promise.resolve([])
  })
  await open(entity, '?search=old')
  await router.push(`/${entity}?search=new`)
  await flushPromises()
  expect(wrapper.vm.allRecordsExist).toBe(false)
  probe.resolve([{ id: 1 }])
  await flushPromises()
  expect(wrapper.vm.allRecordsExist).toBe(false)
})
it('obsolete customer next-code response cannot overwrite the current edit form', async () => {
  const code = deferred()
  mocks.api.get.mockImplementation(url => url === '/customers/next-code/' ? code.promise : Promise.resolve({ data: { id: 7, name: '正在编辑', code: 'CURRENT', owner_profile: 23 } }))
  await open('customers', '?create=1')
  await router.push('/customers?edit=7')
  await flushPromises()
  expect(wrapper.vm.form.code).toBe('CURRENT')
  code.resolve({ data: { code: 'OBSOLETE' } })
  await flushPromises()
  expect(wrapper.vm.form.code).toBe('CURRENT')
  expect(wrapper.vm.form.owner_profile).toBe(23)
})
it('obsolete follow-up operator response cannot replace the edited owner', async () => {
  const operator = deferred()
  mocks.api.get.mockImplementation(url => url.includes('current-operator') ? operator.promise : Promise.resolve({ data: { id: 7, subject: '当前跟进', owner: '历史跟进人', attachments: [] } }))
  await open('follow-ups', '?create=1')
  await router.push('/follow-ups?edit=7')
  await flushPromises()
  operator.resolve({ data: { name: '开发身份' } })
  await flushPromises()
  expect(wrapper.vm.form.owner).toBe('历史跟进人')
  expect(wrapper.vm.form.subject).toBe('当前跟进')
})
it('obsolete follow-up options completion cannot clear the edited attachments', async () => {
  const options = deferred()
  let customerReads = 0
  mocks.listAll.mockImplementation(url => url === '/customers/' && ++customerReads === 1 ? options.promise : Promise.resolve([]))
  const attachment = { id: 11, original_name: '历史附件.txt' }
  mocks.api.get.mockResolvedValue({ data: { id: 7, subject: '当前跟进', owner: '历史跟进人', attachments: [attachment] } })
  await open('follow-ups', '?create=1')
  await router.push('/follow-ups?edit=7')
  await flushPromises()
  expect(wrapper.vm.followUpAttachments).toEqual([attachment])
  options.resolve([])
  await flushPromises()
  expect(wrapper.vm.followUpAttachments).toEqual([attachment])
})
