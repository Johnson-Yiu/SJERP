// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), can: vi.fn(() => true) }))
vi.mock('../src/api', () => ({ api: { get: mock.get, post: mock.post } }))
vi.mock('../src/accessControl', () => ({ useAccessControl: () => ({ can: mock.can }) }))
import DocumentPartyVersions from '../src/components/DocumentPartyVersions.vue'

const snapshot = { name: '合成供应商', address: '原地址', contact: '联系人', phone: '123', email: 'test@example.invalid' }
let state
beforeEach(() => {
  mock.get.mockReset(); mock.post.mockReset(); mock.can.mockReset().mockReturnValue(true)
  state = { baseline: { snapshot: { ...snapshot }, fingerprint: 'saved-fingerprint' }, requests: [], current_user_id: 7 }
  mock.get.mockImplementation(async () => ({ data: structuredClone(state) }))
  mock.post.mockResolvedValue({ data: {} })
})
async function open() {
  const wrapper = mount(DocumentPartyVersions, { props: { kind: 'purchase_order', id: 42 } })
  await wrapper.get('button').trigger('click'); await flushPromises()
  return wrapper
}
const button = (wrapper, name) => wrapper.findAll('button').find(item => item.text() === name)

describe('document party versions', () => {
  it('shows changed buyer and seller details with unknown and explicit blank values', async () => {
    const before = { buyer: { address: null, tax_id: '旧税号', contact: '不变' }, seller: { billing_address: '', phone: '旧电话' } }
    const after = { buyer: { address: '', tax_id: '新税号', contact: '不变' }, seller: { billing_address: null, phone: '新电话' } }
    state.requests = [{ id: 9, status: 'pending', initiator_id: 8, base_snapshot: { ...snapshot, party_details: before }, proposed_snapshot: { ...snapshot, party_details: after } }]
    const wrapper = await open()
    const comparison = wrapper.get('.party-details-changes').text()
    expect(comparison).toContain('买方地址未知 → 已留空')
    expect(comparison).toContain('买方税号旧税号 → 新税号')
    expect(comparison).toContain('卖方账单地址已留空 → 未知')
    expect(comparison).toContain('卖方电话旧电话 → 新电话')
    expect(comparison).not.toContain('买方联系人')
  })

  it('uses saved basis and records same-party correction only after explicit confirmation', async () => {
    const wrapper = await open()
    expect(mock.get).toHaveBeenCalledWith('/purchase-orders/42/party-change/')
    const fields = wrapper.findAll('.party-label input')
    await fields[1].setValue('更正地址')
    await wrapper.findAll('textarea')[0].setValue('更正原因')
    await wrapper.findAll('textarea')[1].setValue('合成依据')
    await button(wrapper, '提交更正申请').trigger('click')
    expect(wrapper.text()).toContain('请确认法律主体未变')
    expect(mock.post).not.toHaveBeenCalled()
    await wrapper.get('input[type="checkbox"]').setValue(true)
    await button(wrapper, '提交更正申请').trigger('click'); await flushPromises()
    expect(mock.post).toHaveBeenCalledWith('/purchase-orders/42/party-change/', expect.objectContaining({
      expected_base_fingerprint: 'saved-fingerprint', proposed_snapshot: { ...snapshot, address: '更正地址' }, change_type: 'correction',
    }))
  })
  it('does not offer self approval and displays terminal evidence', async () => {
    state.requests = [{ id: 9, status: 'pending', initiator_id: 7, reason: '原因', evidence: '依据', base_snapshot: snapshot, proposed_snapshot: snapshot }]
    const wrapper = await open()
    expect(button(wrapper, '批准更正')).toBeUndefined()
    expect(button(wrapper, '撤回申请')).toBeDefined()
    state.requests = [{ ...state.requests[0], status: 'rejected', terminal_event: { actor_id: 8, note: '拒绝原因' } }]
    await button(wrapper, '收起主体版本').trigger('click'); await button(wrapper, '查看主体版本与更正').trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('拒绝原因')
    expect(wrapper.text()).toContain('处理账号 ID：8')
    expect(button(wrapper, '撤回申请')).toBeUndefined()
  })
  it('distinguishes an explicitly blank proposal from an unrecorded original', async () => {
    state.requests = [{ id: 10, status: 'pending', initiator_id: 8, reason: '原因', evidence: '依据', base_snapshot: { ...snapshot, address: '' }, proposed_snapshot: { ...snapshot, address: '' } }]
    const wrapper = await open()
    expect(wrapper.text()).toContain('未记录 → 已留空')
  })
  it('includes edited full details in the signed proposal without changing the baseline', async () => {
    const keys = ['name', 'country', 'address', 'tax_id', 'contact', 'phone', 'email', 'billing_address', 'shipping_address', 'recipient']
    const side = Object.fromEntries(keys.map(key => [key, null])); side.billing_address = 'Old billing'
    state.baseline.snapshot.party_details = { schema: 'party-document-details-v1', buyer: side, seller: { ...side } }
    const wrapper = await open()
    const input = wrapper.findAll('label').find(label => label.text().includes('买方账单地址')).find('input')
    await input.setValue('New billing')
    await wrapper.findAll('textarea')[0].setValue('Reason')
    await wrapper.findAll('textarea')[1].setValue('Evidence')
    await wrapper.get('input[type="checkbox"]').setValue(true)
    await button(wrapper, '提交更正申请').trigger('click'); await flushPromises()
    expect(mock.post.mock.calls[0][1].proposed_snapshot.party_details.buyer.billing_address).toBe('New billing')
    expect(state.baseline.snapshot.party_details.buyer.billing_address).toBe('Old billing')
  })
})
