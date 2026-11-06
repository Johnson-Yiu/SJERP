// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), can: vi.fn(() => true) }))
vi.mock('../src/api', () => ({ api: { get: mocks.get, post: mocks.post }, listAll: vi.fn(async () => [{ id: 42, name: '合成目标客户', code: 'SYN' }]), downloadQuoteExport: vi.fn() }))
vi.mock('../src/accessControl', () => ({ useAccessControl: () => ({ can: mocks.can }) }))
import QuoteDetailModal from '../src/components/QuoteDetailModal.vue'

const base = { name: '原客户', country: 'Germany', address: '原地址', contact: '原联系人', phone: '', email: '', tax_id: null }
let state, wrapper, router, quoteStatus
const quote = id => ({ id, quote_no: `Q-${id}`, buyer_company_name: '原客户', customer_name: '当前主档', status: quoteStatus, status_display: '测试状态', currency: 'USD', exchange_rate: '1', total_amount: '10', items: [] })

beforeEach(() => {
  mocks.get.mockReset(); mocks.post.mockReset(); mocks.can.mockReset().mockReturnValue(true)
  quoteStatus = 'sent'
  state = { baseline: { snapshot: { ...base }, fingerprint: 'base-hash' }, requests: [], current_user_id: 7 }
  mocks.get.mockImplementation(async url => {
    const match = url.match(/^\/quotes\/(\d+)\/workbench\/$/)
    if (match) return { data: { quote: quote(Number(match[1])), root_quote_no: 'Q-1', revisions: [], orders: [], important_notes: [] } }
    if (url.endsWith('/party-change/')) return { data: structuredClone(state) }
    return { data: [] }
  })
})
afterEach(() => wrapper?.unmount())

async function open() {
  router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/quotes', component: { template: '<div />' } }] })
  await router.push('/quotes?detail=1'); await router.isReady()
  wrapper = mount(QuoteDetailModal, { props: { id: 1 }, global: { plugins: [router], stubs: { OperationLogPanel: true, RichTextEditor: true } } })
  await flushPromises()
  await wrapper.findAll('button').find(button => button.text() === '主体更正').trigger('click')
  await flushPromises()
}
const button = text => wrapper.findAll('button').find(element => element.text() === text)

describe('quote party correction', () => {
  it('shows changed buyer and seller details with unknown and explicit blank values', async () => {
    const before = { buyer: { address: null, tax_id: '旧税号', contact: '不变' }, seller: { billing_address: '', phone: '旧电话' } }
    const after = { buyer: { address: '', tax_id: '新税号', contact: '不变' }, seller: { billing_address: null, phone: '新电话' } }
    state.requests = [{ id: 9, status: 'pending', initiator_id: 8, change_type: 'correction', base_snapshot: { ...base, party_details: before }, proposed_snapshot: { ...base, party_details: after } }]
    await open()
    const comparison = wrapper.get('.party-details-changes').text()
    expect(comparison).toContain('买方地址未知 → 已留空')
    expect(comparison).toContain('买方税号旧税号 → 新税号')
    expect(comparison).toContain('卖方账单地址已留空 → 未知')
    expect(comparison).toContain('卖方电话旧电话 → 新电话')
    expect(comparison).not.toContain('买方联系人')
  })

  it('preserves unknown tax and submits only correction with the baseline fingerprint', async () => {
    mocks.post.mockResolvedValue({ data: {} })
    await open()
    expect(wrapper.text()).toContain('历史未记录')
    expect(wrapper.text()).not.toContain('当前主档参考：当前主档 →')
    await wrapper.get('#party-address').setValue('更正地址')
    await wrapper.findAll('.party-form-fields textarea')[0].setValue('资料更正')
    await wrapper.findAll('.party-form-fields textarea')[1].setValue('合成依据')
    await wrapper.get('.party-legal-confirm input').setValue(true)
    await button('提交更正申请').trigger('click'); await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/quotes/1/party-change/', {
      expected_base_fingerprint: 'base-hash', proposed_snapshot: { ...base, address: '更正地址' },
      change_type: 'correction', reason: '资料更正', evidence: '合成依据', source_trust: 'unverified',
    })
  })

  it('changes unknown tax to blank only after an explicit action', async () => {
    mocks.post.mockResolvedValue({ data: {} })
    await open()
    await wrapper.get('#party-tax_id').setValue('0012')
    await wrapper.get('#party-tax_id').setValue('')
    await wrapper.findAll('.party-form-fields textarea')[0].setValue('更正')
    await wrapper.findAll('.party-form-fields textarea')[1].setValue('依据')
    await wrapper.get('.party-legal-confirm input').setValue(true)
    await button('提交更正申请').trigger('click'); await flushPromises()
    expect(mocks.post.mock.calls[0][1].proposed_snapshot.tax_id).toBe('')
  })

  it('blocks anonymous actions and self approval, and does not offer replacement application', async () => {
    state.current_user_id = null
    await open()
    expect(wrapper.text()).toContain('两个不同的已认证账号')
    expect(button('提交更正申请').attributes('disabled')).toBeDefined()
    wrapper.unmount(); wrapper = null
    state.current_user_id = 7
    state.requests = [
      { id: 10, initiator_id: 7, change_type: 'correction', base_snapshot: base, proposed_snapshot: base, reason: '原因', evidence: '依据', source_trust: 'unverified', approval: null, application: null },
      { id: 11, initiator_id: 8, change_type: 'replacement', base_snapshot: base, proposed_snapshot: base, reason: '原因', evidence: '依据', source_trust: 'unverified', approval: { approver_id: 9, note: '同意' }, application: null },
    ]
    await open()
    expect(wrapper.text()).toContain('申请人不能审批自己的申请')
    expect(button('批准更正')).toBeUndefined()
    expect(button('生成报价草稿')).toBeUndefined()
    expect(mocks.post).not.toHaveBeenCalled()
  })

  it('submits approval fingerprint then applies approved correction and navigates', async () => {
    state.requests = [{ id: 12, initiator_id: 8, change_type: 'correction', base_snapshot: base, proposed_snapshot: { ...base, address: '新地址' }, reason: '原因', evidence: '依据', source_trust: 'unverified', content_fingerprint: 'content-hash', approval: null, application: null }]
    mocks.post.mockImplementation(async url => {
      if (url.endsWith('/approve/')) { state.requests[0].approval = { id: 3, approver_id: 7, note: '核对' }; return { data: {} } }
      if (url.endsWith('/apply/')) return { data: { result_quote_id: 2 } }
      throw new Error('unexpected')
    })
    await open()
    await wrapper.get('.party-approval-note input').setValue('核对')
    await button('批准更正').trigger('click'); await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/quotes/1/party-change/12/approve/', { expected_content_fingerprint: 'content-hash', note: '核对' })
    await button('生成报价草稿').trigger('click'); await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/quotes/1/party-change/12/apply/')
    expect(router.currentRoute.value.query.detail).toBe('2')
    expect(wrapper.emitted('status-updated')).toHaveLength(1)
  })

  it('shows service failure and does not navigate', async () => {
    state.requests = [{ id: 12, initiator_id: 8, change_type: 'correction', base_snapshot: base, proposed_snapshot: base, reason: '原因', evidence: '依据', source_trust: 'unverified', approval: { approver_id: 7, note: '核对' }, application: null }]
    mocks.post.mockRejectedValue({ response: { data: { detail: '基准快照已变更' } } })
    await open()
    await button('生成报价草稿').trigger('click'); await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('基准快照已变更')
    expect(router.currentRoute.value.query.detail).toBe('1')
  })

  it('fails closed when the baseline omits a field and allows retry', async () => {
    delete state.baseline.snapshot.tax_id
    await open()
    expect(wrapper.get('[role="alert"]').text()).toContain('资料不完整')
    expect(button('提交更正申请')).toBeUndefined()
    state.baseline.snapshot.tax_id = null
    await button('重试').trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('历史未记录')
  })

  it('keeps the authenticated account guidance visible when the service rejects anonymous access', async () => {
    const original = mocks.get.getMockImplementation()
    mocks.get.mockImplementation(url => url.endsWith('/party-change/') ? Promise.reject(new Error('需要登录')) : original(url))
    await open()
    expect(wrapper.text()).toContain('匿名开发身份不能操作')
    expect(wrapper.get('[role="alert"]').text()).toContain('需要登录')
    expect(button('提交更正申请')).toBeUndefined()
  })

  it('renders structured field errors and permits retry with the same draft', async () => {
    mocks.post.mockRejectedValueOnce({ response: { status: 400, data: { proposed_snapshot: { tax_id: ['税号格式有误'], address: ['地址需核对'] }, evidence: ['请提供依据'] } } }).mockResolvedValue({ data: {} })
    await open()
    await wrapper.get('#party-address').setValue('新地址')
    await wrapper.findAll('.party-form-fields textarea')[0].setValue('更正')
    await wrapper.findAll('.party-form-fields textarea')[1].setValue('依据')
    await wrapper.get('.party-legal-confirm input').setValue(true)
    await button('提交更正申请').trigger('click'); await flushPromises()
    const error = wrapper.get('[role="alert"]').text()
    expect(error).toContain('税号格式有误')
    expect(error).toContain('地址需核对')
    expect(error).toContain('请提供依据')
    expect(error).not.toContain('[object Object]')
    expect(wrapper.get('#party-address').element.value).toBe('新地址')
    await button('提交更正申请').trigger('click'); await flushPromises()
    expect(mocks.post).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('renders DRF arrays and login errors on load with a working retry', async () => {
    const original = mocks.get.getMockImplementation()
    let attempts = 0
    mocks.get.mockImplementation(url => {
      if (!url.endsWith('/party-change/')) return original(url)
      attempts += 1
      if (attempts === 1) return Promise.reject({ response: { status: 401, data: ['请使用真实认证会话。', '请重新登录。'] } })
      return original(url)
    })
    await open()
    const error = wrapper.get('[role="alert"]').text()
    expect(error).toContain('请先登录已认证账号')
    expect(error).toContain('请使用真实认证会话')
    expect(error).toContain('请重新登录')
    expect(error).not.toContain('[object Object]')
    await button('重试').trigger('click'); await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(button('提交更正申请')).toBeTruthy()
  })

  it('shows actor and timestamps, including safe fallbacks for old records', async () => {
    state.requests = [
      { id: 21, initiator_id: 8, created_at: '2026-11-05T08:00:00Z', change_type: 'correction', base_snapshot: base, proposed_snapshot: base, reason: '原因', evidence: '依据', source_trust: 'unverified', approval: { approver_id: 9, created_at: '2026-11-05T09:00:00Z', note: '同意' }, application: { result_quote_id: 2, applied_by_id: 10, created_at: '2026-11-05T10:00:00Z' } },
      { id: 22, initiator_id: 8, change_type: 'correction', base_snapshot: base, proposed_snapshot: base, reason: '原因', evidence: '依据', source_trust: 'unknown', approval: { approver_id: 9 }, application: { result_quote_id: 3 } },
    ]
    await open()
    const records = wrapper.findAll('.party-request')
    expect(records[0].text()).toContain('申请时间：')
    expect(records[0].text()).toContain('审批时间：')
    expect(records[0].text()).toContain('生效操作账号 ID：10')
    expect(records[0].text()).toContain('生效时间：')
    expect(records[0].text()).not.toContain('申请时间：未记录')
    expect(records[0].text()).not.toContain('审批时间：未记录')
    expect(records[0].text()).not.toContain('生效时间：未记录')
    expect(records[1].text()).toContain('申请时间：未记录')
    expect(records[1].text()).toContain('审批时间：未记录')
    expect(records[1].text()).toContain('生效操作账号 ID：未记录')
    expect(records[1].text()).toContain('生效时间：未记录')
  })

  it.each([['unknown', '来源未知'], ['unverified', '来源未核验']])('shows %s provenance without claiming historical verification', async (sourceTrust, label) => {
    state.origin = { source_quote_id: 14, request_id: 28, source_trust: sourceTrust }
    await open()
    expect(wrapper.text()).toContain('来源报价版本 ID：14')
    expect(wrapper.text()).toContain('来源更正申请 ID：28')
    expect(wrapper.text()).toContain(label)
    expect(wrapper.text()).toContain('批准不代表历史资料已核实')
  })

  it('requires staff confirmation and evidence without claiming automatic verification', async () => {
    mocks.post.mockResolvedValue({ data: {} })
    await open()
    expect(wrapper.text()).toContain('仅用于同一法律主体的资料更正；更换法律主体不能使用')
    expect(wrapper.text()).toContain('系统不会自动核实法律主体是否变更')
    await wrapper.findAll('.party-form-fields textarea')[0].setValue('更正')
    await wrapper.findAll('.party-form-fields textarea')[1].setValue('依据')
    await button('提交更正申请').trigger('click')
    expect(wrapper.get('[role="alert"]').text()).toContain('请确认法律主体未变')
    expect(mocks.post).not.toHaveBeenCalled()
    await wrapper.get('.party-legal-confirm input').setValue(true)
    await wrapper.findAll('.party-form-fields textarea')[1].setValue('   ')
    await button('提交更正申请').trigger('click')
    expect(wrapper.get('[role="alert"]').text()).toContain('请填写原因和依据')
    expect(mocks.post).not.toHaveBeenCalled()
    await wrapper.findAll('.party-form-fields textarea')[1].setValue('人工核对的登记文件')
    await button('提交更正申请').trigger('click'); await flushPromises()
    expect(mocks.post).toHaveBeenCalledTimes(1)
    expect(wrapper.get('.party-legal-confirm input').element.checked).toBe(false)
  })

  it('requires a scoped target and explicit proposed replacement facts', async () => {
    mocks.post.mockResolvedValue({ data: {} })
    await open()
    await wrapper.get('.party-change-type select').setValue('replacement')
    await flushPromises()
    expect(wrapper.text()).toContain('请选择新的法律主体')
    expect(wrapper.find('.party-legal-confirm').exists()).toBe(false)
    await button('提交替换申请').trigger('click')
    expect(wrapper.get('[role="alert"]').text()).toContain('请选择目标')
    expect(mocks.post).not.toHaveBeenCalled()
    await wrapper.get('.replacement-form select').setValue('42')
    for (const field of wrapper.findAll('.replacement-form button').filter(item => item.text() === '确认留空')) await field.trigger('click')
    await wrapper.findAll('.replacement-form textarea')[0].setValue('拟更换主体')
    await wrapper.findAll('.replacement-form textarea')[1].setValue('合成依据')
    await button('提交替换申请').trigger('click'); await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/quotes/1/party-change/', expect.objectContaining({ change_type: 'replacement', replacement_target_id: 42, reason: '拟更换主体', evidence: '合成依据', proposed_snapshot: { name: '合成目标客户', country: '', address: '', contact: '', phone: '', email: '', tax_id: '' } }))
  })

  it.each(['draft', 'rejected', 'expired'])('disables all changes for %s while keeping historical records visible', async status => {
    quoteStatus = status
    state.requests = [
      { id: 12, initiator_id: 8, change_type: 'correction', base_snapshot: base, proposed_snapshot: base, reason: '历史原因', evidence: '依据', source_trust: 'unknown', content_fingerprint: 'hash', approval: null, application: null },
      { id: 13, initiator_id: 8, change_type: 'correction', base_snapshot: base, proposed_snapshot: base, reason: '已批准原因', evidence: '依据', source_trust: 'unknown', approval: { approver_id: 9, note: '同意' }, application: null },
    ]
    await open()
    expect(wrapper.text()).toContain('仅已发送或已接受的报价')
    expect(wrapper.text()).toContain('历史原因')
    expect(button('提交更正申请').attributes('disabled')).toBeDefined()
    expect(button('批准更正').attributes('disabled')).toBeDefined()
    expect(button('生成报价草稿').attributes('disabled')).toBeDefined()
    expect(wrapper.get('#party-address').attributes('disabled')).toBeDefined()
    expect(mocks.post).not.toHaveBeenCalled()
  })

  it('requires both quote creation and update permission to generate a draft', async () => {
    mocks.can.mockImplementation((module, action) => !(module === 'quotes' && action === 'create'))
    state.requests = [{ id: 13, initiator_id: 8, change_type: 'correction', base_snapshot: base, proposed_snapshot: base, reason: '原因', evidence: '依据', source_trust: 'unknown', approval: { approver_id: 9, note: '同意' }, application: null }]
    await open()
    expect(button('生成报价草稿').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('生成报价草稿需要报价创建和修改权限')
    expect(mocks.post).not.toHaveBeenCalled()
  })

  it.each([
    ['withdraw', '撤回申请', 7, 'pending', null, 'withdrawn', '已撤回'],
    ['reject', '拒绝申请', 8, 'pending', null, 'rejected', '已拒绝'],
    ['invalidate', '标记失效', 8, 'approved', { approver_id: 9, note: '核对' }, 'invalidated', '已失效'],
  ])('%s requires a reason, sends it, refreshes and displays the recorded actor', async (operation, label, initiator, status, approval, resultStatus, resultLabel) => {
    state.requests = [{ id: 30, initiator_id: initiator, status, change_type: 'correction', base_snapshot: base, proposed_snapshot: base, reason: '原申请', evidence: '依据', source_trust: 'unverified', content_fingerprint: 'hash', approval, application: null, terminal_event: null }]
    mocks.post.mockImplementation(async () => {
      state.requests[0].status = resultStatus
      state.requests[0].terminal_event = { actor_id: 7, note: '人工处理原因', created_at: '2026-11-05T10:00:00Z' }
      return { data: {} }
    })
    await open()
    await button(label).trigger('click')
    expect(wrapper.get('[role="alert"]').text()).toContain('请填写处理原因')
    expect(mocks.post).not.toHaveBeenCalled()
    await wrapper.get('.party-request .party-approval-note:last-of-type input').setValue('人工处理原因')
    await button(label).trigger('click'); await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith(`/quotes/1/party-change/30/${operation}/`, { note: '人工处理原因' })
    const record = wrapper.get('.party-request').text()
    expect(record).toContain(resultLabel)
    expect(record).toContain('操作账号 ID：7')
    expect(record).toContain('原因：人工处理原因')
    expect(button(label)).toBeUndefined()
    expect(button('批准更正')).toBeUndefined()
    expect(button('生成报价草稿')).toBeUndefined()
  })

  it('only offers withdrawal to the initiator and rejection to another authenticated account', async () => {
    state.requests = [
      { id: 31, initiator_id: 7, status: 'pending', change_type: 'correction', base_snapshot: base, proposed_snapshot: base, approval: null, application: null },
      { id: 32, initiator_id: 8, status: 'pending', change_type: 'correction', base_snapshot: base, proposed_snapshot: base, approval: null, application: null },
    ]
    await open()
    const rows = wrapper.findAll('.party-request')
    expect(rows[0].text()).toContain('撤回申请')
    expect(rows[0].text()).not.toContain('拒绝申请')
    expect(rows[1].text()).toContain('拒绝申请')
    expect(rows[1].text()).not.toContain('撤回申请')
    expect(rows[0].text()).toContain('标记失效')
    expect(rows[1].text()).toContain('标记失效')
  })

  it('allows a different account to approve a replacement record without offering application', async () => {
    state.requests = [{ id: 35, initiator_id: 8, status: 'pending', change_type: 'replacement', base_snapshot: base, proposed_snapshot: base, reason: '拟更换', evidence: '依据', source_trust: 'unverified', content_fingerprint: 'replacement-hash', approval: null, application: null, terminal_event: null }]
    mocks.post.mockImplementation(async () => {
      state.requests[0].status = 'approved'
      state.requests[0].approval = { approver_id: 7, note: '已核对' }
      return { data: {} }
    })
    await open()
    await wrapper.findAll('.party-request .party-approval-note input')[0].setValue('已核对')
    await button('批准主体替换记录').trigger('click'); await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/quotes/1/party-change/35/approve/', { expected_content_fingerprint: 'replacement-hash', note: '已核对' })
    expect(wrapper.text()).toContain('已批准')
    expect(button('生成报价草稿')).toBeUndefined()
    expect(button('标记失效')).toBeTruthy()
  })

  it('does not allow an initiator to approve their replacement record', async () => {
    state.requests = [{ id: 36, initiator_id: 7, status: 'pending', change_type: 'replacement', base_snapshot: base, proposed_snapshot: base, reason: '拟更换', evidence: '依据', source_trust: 'unverified', approval: null, application: null, terminal_event: null }]
    await open()
    expect(wrapper.text()).toContain('申请人不能审批自己的申请')
    expect(button('批准主体替换记录')).toBeUndefined()
    expect(button('生成报价草稿')).toBeUndefined()
  })

  it.each(['applied', 'rejected', 'withdrawn', 'invalidated', 'unexpected'])('never offers lifecycle actions for %s', async status => {
    state.requests = [{ id: 33, initiator_id: 7, status, change_type: 'correction', base_snapshot: base, proposed_snapshot: base, approval: { approver_id: 8, note: '同意' }, application: status === 'applied' ? { result_quote_id: 2 } : null, terminal_event: ['rejected', 'withdrawn', 'invalidated'].includes(status) ? { actor_id: 8, note: '终止原因' } : null }]
    await open()
    for (const label of ['撤回申请', '拒绝申请', '标记失效', '批准更正', '生成报价草稿']) expect(button(label)).toBeUndefined()
    if (status !== 'applied' && status !== 'unexpected') expect(wrapper.text()).toContain('操作账号 ID：8')
  })

  it('fails closed if status conflicts with an applied or terminated record', async () => {
    state.requests = [
      { id: 37, initiator_id: 7, status: 'pending', change_type: 'correction', base_snapshot: base, proposed_snapshot: base, approval: null, application: { result_quote_id: 2 }, terminal_event: null },
      { id: 38, initiator_id: 8, status: 'pending', change_type: 'correction', base_snapshot: base, proposed_snapshot: base, approval: null, application: null, terminal_event: { actor_id: 9, note: 'Synthetic' } },
      { id: 39, initiator_id: 7, status: 'pending', change_type: 'correction', base_snapshot: base, proposed_snapshot: base, approval: { approver_id: 9, note: 'Synthetic' }, application: null, terminal_event: null },
    ]
    await open()
    for (const label of ['撤回申请', '拒绝申请', '标记失效', '批准更正', '生成报价草稿']) expect(button(label)).toBeUndefined()
    expect(wrapper.text()).toContain('已终止')
  })

  it('keeps the processing reason after server failure for a retry', async () => {
    state.requests = [{ id: 34, initiator_id: 7, status: 'pending', change_type: 'correction', base_snapshot: base, proposed_snapshot: base, approval: null, application: null }]
    mocks.post.mockRejectedValueOnce({ response: { status: 400, data: { note: ['请核实原因'] } } }).mockResolvedValue({ data: {} })
    await open()
    await wrapper.get('.party-request .party-approval-note input').setValue('保留原因')
    await button('撤回申请').trigger('click'); await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('请核实原因')
    expect(wrapper.get('.party-request .party-approval-note input').element.value).toBe('保留原因')
    await button('撤回申请').trigger('click'); await flushPromises()
    expect(mocks.post).toHaveBeenCalledTimes(2)
  })
})
