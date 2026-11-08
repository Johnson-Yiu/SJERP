// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CashEventEntryForm from '../src/components/CashEventEntryForm.vue'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('../src/composables/useWorkspaceApi', () => ({ useWorkspaceApi: () => ({ api }) }))
vi.mock('../src/composables/useWorkspaceNavigation', () => ({ useWorkspaceNavigation: () => ({ workspace: null, storageKey: value => value }) }))
vi.mock('../src/composables/useUnsavedChangesGuard', () => ({ useUnsavedChangesGuard: () => ({ markClean: vi.fn(), requestClose: vi.fn() }) }))
vi.mock('../src/accessControl', () => ({ useAccessControl: () => ({ can: () => true }) }))
let wrapper
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks() })

it('gives a saved receipt stable event identity and requires re-verification after partial conversion edits', async () => {
  api.get.mockImplementation(url => Promise.resolve({ data: { results: url.includes('/sources/') ? [{ id: 7, transaction_no: 'SYNTH-RECEIPT', remaining_candidate_amount: '985.00', currency: 'USD', kind: 'customer_receipt' }] : [] } }))
  wrapper = mount(CashEventEntryForm, { props: { mode: 'linked', receipt: { id: 7, transaction_no: 'SYNTH-RECEIPT', currency: 'USD' } } })
  await flushPromises()
  const states = () => wrapper.emitted('state-change').map(event => event[0])
  const initial = states().at(-1)
  expect(initial.event_no).toMatch(/^P2B-EVENT-[A-Za-z0-9_-]+$/)
  expect(initial.request_key).toMatch(/^P2B-REQUEST-[A-Za-z0-9_-]+$/)
  await wrapper.get('input[aria-label="本次兑换原币金额"]').setValue('500')
  await flushPromises()
  const edited = states().at(-1)
  expect(edited.event_no).toBe(initial.event_no)
  expect(edited.request_key).toBe(initial.request_key)
  expect(Number(edited.allocations[0].amount)).toBe(500)
  expect(edited.allocations[0].verified).toBe(false)
  expect(api.post).not.toHaveBeenCalled()
})
