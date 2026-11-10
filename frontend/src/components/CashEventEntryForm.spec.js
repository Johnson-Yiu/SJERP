import { setAccessOperator } from '../accessControl'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import CashEventEntryForm from './CashEventEntryForm.vue'

const financeAccount = id => setAccessOperator({ authenticated: true, user_id: id, has_all_permissions: true })
const savedKey = key => `sunjack:finance-attempt:v2:user:101:${key}`
beforeEach(() => { window.localStorage.clear(); financeAccount(101) })

const { api, requestClose, markClean } = vi.hoisted(() => ({
  api: {
    get: vi.fn(async url => ({ data: { results: [], ...(url.endsWith('/accounts/') ? { configured: false } : {}) } })),
    post: vi.fn(async () => ({ data: {} })),
  },
  requestClose: vi.fn(callback => callback()),
  markClean: vi.fn(),
}))

vi.mock('../composables/useWorkspaceApi', () => ({ useWorkspaceApi: () => ({ api }) }))
vi.mock('../composables/useUnsavedChangesGuard', () => ({ useUnsavedChangesGuard: () => ({ requestClose, markClean }) }))

describe('CashEventEntryForm outside-click behavior', () => {
  afterEach(() => { document.body.innerHTML = ''; window.sessionStorage.clear(); vi.clearAllMocks() })

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

  it('starts linked conversion empty and permits a partial amount with all order references', async () => {
    api.get.mockImplementation(async url => ({ data: { results: url.endsWith('/sources/')
      ? [{ id: 11, transaction_no: 'FIN-SYNTH', kind: 'customer_receipt', remaining_candidate_amount: '985.00', blocked_reason: '' }]
      : [] } }))
    const wrapper = mount(CashEventEntryForm, { props: { mode: 'linked', receipt: {
      id: 11, currency: 'USD', transaction_no: 'FIN-SYNTH', allocations: [
        { is_active: true, contract_no: 'SO-A' }, { is_active: true, contract_no: 'SO-B' },
      ],
    } } })
    await flushPromises()
    const amount = wrapper.get('input[aria-label="本次兑换金额"]')
    expect(amount.element.value).toBe('')
    expect(wrapper.text()).toContain('SO-A、SO-B')
    await amount.setValue('500')
    await flushPromises()
    expect(wrapper.text()).toContain('USD 500.00')
    const snapshot = wrapper.emitted('state-change').at(-1)[0]
    expect(snapshot.allocations[0]).toMatchObject({ id: 11, amount: '500', verified: false })
    wrapper.unmount()
  })

  it('calculates partial conversion amounts and rate in decimal units', async () => {
    api.get.mockImplementation(async url => ({ data: { results: url.endsWith('/sources/') ? [{ id: 11, transaction_no: 'FIN-SYNTH', kind: 'customer_receipt', remaining_candidate_amount: '985.00', blocked_reason: '' }] : [] } }))
    const wrapper = mount(CashEventEntryForm, { props: { mode: 'linked', receipt: { id: 11, currency: 'USD', transaction_no: 'FIN-SYNTH' } } })
    await flushPromises()
    const label = name => wrapper.findAll('label').find(item => item.text().trim().startsWith(name))
    await wrapper.get('input[aria-label="本次兑换金额"]').setValue('500')
    await label('扣费前兑换额').get('input').setValue('3550.03')
    await label('手续费无').get('select').setValue('included')
    await label('手续费（CNY）').get('input').setValue('0.30')
    expect(label('银行净到账').get('input').element.value).toBe('3549.73')
    expect(label('实际汇率').get('input').element.value).toBe('7.100060')
    wrapper.unmount()
  })

  it('adds another verified receipt from the linked conversion', async () => {
    const original = { id: 11, transaction_no: 'FIN-A', kind: 'customer_receipt', direction: 'income', currency: 'USD', remaining_candidate_amount: '100.00', blocked_reason: '' }
    const other = { id: 12, transaction_no: 'FIN-B', customer_name: '合成客户', kind: 'customer_receipt', direction: 'income', currency: 'USD', remaining_candidate_amount: '200.00', blocked_reason: '' }
    api.get.mockImplementation(async (url, options) => ({ data: { results: url.endsWith('/sources/') ? (options?.params?.family_root ? [original] : [original, other]) : [] } }))
    const wrapper = mount(CashEventEntryForm, { props: { mode: 'linked', receipt: { id: 11, currency: 'USD', transaction_no: 'FIN-A' } } })
    await flushPromises()
    await wrapper.findAll('button').find(b => b.text() === '合并其他收款').trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('FIN-B')
    await wrapper.findAll('button').find(b => b.text() === '添加').trigger('click')
    const amounts = wrapper.findAll('input[aria-label="本次兑换金额"]')
    expect(amounts).toHaveLength(2)
    await amounts[0].setValue('40'); await amounts[1].setValue('60')
    expect(wrapper.text()).toContain('USD 100.00')
    wrapper.unmount()
  })

  it('replays the exact pending linked settlement after reopening', async () => {
    const payload = { event_no: 'P2B-EVENT-1', request_key: 'P2B-REQUEST-1', bank_date: '2026-10-18', currency: 'USD', gross_rmb_amount: '710.00', fee_amount: '0', bank_net_amount: '710.00', bank_reference: 'BANK-1', sources: [{ transaction_id: 11, amount: '100.00', verified: true }] }
    window.localStorage.setItem(savedKey('sunjack:cash-event:pending-receipt:11'), JSON.stringify({ payload }))
    api.get.mockImplementation(async () => ({ data: { results: [] } }))
    api.post.mockResolvedValueOnce({ data: { id: 5, event_no: payload.event_no, status: 'pending' } })
    const wrapper = mount(CashEventEntryForm, { props: { mode: 'linked', receipt: { id: 11, currency: 'USD' } } })
    await flushPromises()
    expect(wrapper.text()).toContain('结汇登记结果待确认')
    expect(wrapper.get('fieldset').attributes('disabled')).toBeDefined()
    await wrapper.findAll('button').find(b => b.text() === '按原内容核对').trigger('click'); await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/rmb-cash-events/', payload)
    expect(window.localStorage.getItem(savedKey('sunjack:cash-event:pending-receipt:11'))).toBeNull()
    expect(wrapper.emitted('created')[0][0].id).toBe(5)
    wrapper.unmount()
  })

  it('replays the exact bank confirmation review after reopening', async () => {
    const body = { voucher_checked: true, duplicate_token: 'candidate-token', duplicate_reason: '已核对为同一笔', same_fact: 9 }
    window.localStorage.setItem(savedKey('sunjack:cash-confirm:5'), JSON.stringify({ body }))
    api.get.mockImplementation(async () => ({ data: { results: [] } }))
    api.post.mockResolvedValueOnce({ data: { id: 5, event_no: 'P2B-5', status: 'confirmed', private_voucher: 1, sources: [] } })
    const wrapper = mount(CashEventEntryForm, { props: { initialEvent: { id: 5, event_no: 'P2B-5', status: 'pending', private_voucher: 1, sources: [] } } })
    await flushPromises()
    expect(wrapper.text()).toContain('银行确认结果待核对')
    await wrapper.findAll('button').find(b => b.text() === '按原内容核对确认').trigger('click'); await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/rmb-cash-events/5/confirm/', body)
    expect(window.localStorage.getItem(savedKey('sunjack:cash-confirm:5'))).toBeNull()
    wrapper.unmount()
  })
})
