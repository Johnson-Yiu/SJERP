import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import CashEventEntryForm from './CashEventEntryForm.vue'

const { api, requestClose, markClean } = vi.hoisted(() => ({
  api: {
    get: vi.fn(async url => ({ data: { results: [], ...(url.endsWith('/accounts/') ? { configured: false } : {}) } })),
    post: vi.fn(async () => ({ data: {} })),
  },
  requestClose: vi.fn(callback => callback()),
  markClean: vi.fn(),
}))

vi.mock('../composables/useWorkspaceApi', () => ({ useWorkspaceApi: () => ({ api }) }))
vi.mock('../composables/useWorkspaceNavigation', () => ({ useWorkspaceNavigation: () => ({ workspace: null, storageKey: key => key }) }))
vi.mock('../accessControl', () => ({ useAccessControl: () => ({ can: () => true }) }))
vi.mock('../composables/useUnsavedChangesGuard', () => ({ useUnsavedChangesGuard: () => ({ requestClose, markClean }) }))

describe('CashEventEntryForm outside-click behavior', () => {
  afterEach(() => { document.body.innerHTML = ''; vi.clearAllMocks() })

  it('keeps the dialog open and preserves entered values when the backdrop is clicked', async () => {
    const wrapper = mount(CashEventEntryForm, { attachTo: document.body })
    await flushPromises()
    const reference = wrapper.get('input[maxlength="120"]')
    await reference.setValue('BANK-REF-KEEP')

    const mask = wrapper.get('.cash-entry-mask')
    await mask.trigger('mousedown')
    await mask.trigger('click')
    await flushPromises()

    expect(wrapper.get('.cash-entry-dialog').exists()).toBe(true)
    expect(wrapper.get('input[maxlength="120"]').element.value).toBe('BANK-REF-KEEP')
    expect(requestClose).not.toHaveBeenCalled()
    expect(wrapper.emitted('close')).toBeUndefined()

    await wrapper.get('[aria-label="关闭资金表单"]').trigger('click')
    expect(requestClose).toHaveBeenCalledTimes(1)
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
