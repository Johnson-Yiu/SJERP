import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PurchasePaymentModal from './PurchasePaymentModal.vue'

const { api } = vi.hoisted(() => ({ api: { post: vi.fn() } }))
vi.mock('../composables/useWorkspaceApi', () => ({ useWorkspaceApi: () => ({ api }) }))
vi.mock('../composables/useUnsavedChangesGuard', () => ({ useUnsavedChangesGuard: () => ({ markClean: vi.fn(), requestClose: callback => callback() }) }))

describe('purchase payment retry identity', () => {
  afterEach(() => { window.sessionStorage.clear(); vi.clearAllMocks() })

  it('reuses the original payment after an unknown response and a reopen', async () => {
    api.post.mockRejectedValueOnce(new Error('connection lost')).mockResolvedValueOnce({ data: { id: 1 } })
    const purchase = { id: 42, purchase_no: 'PO-SYNTH', supplier_name: '合成供应商', currency: 'USD', exchange_rate: '7.2', unpaid_amount: 100, paid_amount: 0 }
    const first = mount(PurchasePaymentModal, { props: { purchase } })
    await first.get('input[type="number"]').setValue('50')
    await first.get('input[aria-label="本次实际汇率"]').setValue('7.2')
    await first.get('form').trigger('submit.prevent')
    await flushPromises()
    expect(first.text()).toContain('付款结果待确认')
    const firstCall = api.post.mock.calls[0]
    expect(firstCall[2].headers['Idempotency-Key']).toMatch(/^PURCHASE-PAY-/)
    first.unmount()
    const reopened = mount(PurchasePaymentModal, { props: { purchase: { ...purchase, unpaid_amount: 0, paid_amount: 100 } } })
    expect(reopened.text()).toContain('上次付款结果待确认')
    await reopened.get('form').trigger('submit.prevent')
    await flushPromises()
    expect(api.post.mock.calls[1]).toEqual(firstCall)
    expect(reopened.emitted('saved')).toBeTruthy()
    expect(window.sessionStorage.getItem('finance-purchase-payment-42')).toBeNull()
    reopened.unmount()
  })
})
