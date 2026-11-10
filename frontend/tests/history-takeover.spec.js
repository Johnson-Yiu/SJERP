// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import HistoryTakeoverPage from '../src/views/HistoryTakeoverPage.vue'
import { setAccessOperator } from '../src/accessControl'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('../src/api', () => ({ api: mocks }))

function detail(status = 'pending') {
  return {
    id: 31,
    source_file_name: 'synthetic-history.xlsx',
    source_sha256: 'a'.repeat(64),
    status: 'in_review',
    created_by_label: '开发身份（非实名）',
    created_actor_kind: 'development',
    preflight_summary: { total_rows: 3, blocked: 0, manual_review: 1, warnings: 0, overall_status: '待人工核实' },
    groups: [{
      id: 41, source_group_id: 'SYN-1', source_system: 'Synthetic legacy', coverage_status: 'complete',
      truth_status: '真实', status, evidence_reference: 'synthetic://voucher',
      preflight_result: { status: '待人工核实', results: [{ sheet: '销售订单', row: 2, status: '待人工核实', reasons: [{ message: '请核实历史联系人快照。', status: '待人工核实' }] }] },
      source_rows: { '销售订单': [{ row: 2, data: { source_record_id: 'SO-1' } }] },
      remainder_snapshot: {}, execution_result: {}, handoffs: {}, verified_correction_ids: [],
    }],
    events: [],
  }
}

function summary(value) {
  return { id: value.id, source_file_name: value.source_file_name, source_sha256: value.source_sha256, status: value.status, groups: value.groups }
}

async function mountPage(value) {
  mocks.get.mockImplementation(async url => {
    if (url === '/import/history-takeovers/') return { data: { results: [summary(value)] } }
    if (url === '/import/history-products/') return { data: { results: [], count: 0 } }
    return { data: value }
  })
  const wrapper = mount(HistoryTakeoverPage)
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  setAccessOperator({ authenticated: true, has_all_permissions: true, development_superadmin: true, can_manage_permissions: true, permissions: {} })
  window.confirm = vi.fn(() => true)
  URL.createObjectURL = vi.fn(() => 'blob:template')
  URL.revokeObjectURL = vi.fn()
})

describe('controlled history takeover UI', () => {
  it.each([
    ['late_fact', '2024-08-12', '补录发货 1 件', '', '请选择迟到记录的实际发生日期。'],
    ['correction', '', '联系人由张三更正为李四', '', '请写明原值、更正值及涉及的字段。'],
    ['voucher_added', '', '', 'VCH-1', '请填写补交凭证的编号或存放位置。'],
  ])('submits %s through business fields and shows field errors', async (kind, date, description, voucher, fieldError) => {
    mocks.post.mockResolvedValue({ data: {} })
    const wrapper = await mountPage(detail('executed'))
    const form = wrapper.get('form.takeover-fields')
    await form.get('select').setValue(kind)
    await form.trigger('submit')
    expect(form.text()).toContain(fieldError)
    expect(form.text()).toContain('请填写提交原因。')
    expect(form.text()).not.toContain('JSON')
    expect(mocks.post).not.toHaveBeenCalled()
    const inputs = form.findAll('input')
    await inputs[0].setValue('SO-1')
    await inputs[1].setValue('PI-001')
    await inputs[2].setValue(date)
    await inputs[3].setValue(voucher)
    await form.findAll('textarea')[0].setValue(description)
    await form.findAll('textarea')[1].setValue('核对原件')
    await form.trigger('submit')
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/import/history-takeovers/31/groups/41/correction/', {
      kind, occurred_at: date, reason: '核对原件',
      details: {
        source_record_id: 'SO-1', source_document_no: 'PI-001',
        ...(description ? { description } : {}),
        ...(voucher ? { voucher_reference: voucher } : {}),
      },
    })
    wrapper.unmount()
  })

  it('lets the reviewer enter an audit note on the executed group', async () => {
    const value = detail('executed')
    value.events = [{ id: 51, group_id: 41, event_type: 'voucher_added_submitted',
      created_at: '2026-11-09T00:00:00Z', details: { details: { voucher_reference: 'VCH-1', fact_id: 720, lines: [{ old_value: 0, new_value: '12.50' }] } } }]
    mocks.post.mockResolvedValue({ data: {} })
    const wrapper = await mountPage(value)
    const audit = wrapper.get('.takeover-audit')
    expect(audit.text()).toContain('VCH-1')
    const legacy = audit.get('details')
    expect(legacy.get('summary').text()).toBe('旧版申请补充资料')
    expect(legacy.text()).toContain('历史事实编号720')
    expect(legacy.text()).toContain('lines / 第 1 项 / 原值0')
    expect(legacy.text()).toContain('lines / 第 1 项 / 更正值12.50')
    const approve = audit.findAll('button').find(button => button.text() === '核实并保留更正轨迹')
    expect(approve.element.disabled).toBe(true)
    await audit.get('textarea').setValue('原凭证已核实')
    await approve.trigger('click')
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/import/history-takeovers/31/groups/41/correction-review/', {
      event_id: 51, decision: 'approve', note: '原凭证已核实',
    })
    wrapper.unmount()
  })

  it('shows unknown internal states as 待核实 and hides full hashes and request identities', async () => {
    const value = detail('future-workflow-state')
    value.preflight_summary.overall_status = 'future-summary-state'
    value.events = [{ id: 9981, event_type: 'application_submitted', actor_label: 'codex-private-actor', actor_kind: 'development', created_at: '2026-11-09T00:00:00Z', details: { request_identity: 'internal-request-identity' } }]
    Object.assign(value.groups[0], {
      coverage_status: 'future-coverage-value', truth_status: 'future-truth-value',
      finance_handoff_status: 'future-finance-value', inventory_handoff_status: 'future-inventory-value',
      fulfillment_handoff_status: 'future-fulfillment-value', operational_overall: { state: 'future-operational-value' },
      execution_result: { orders: [], purchase_orders: [] },
      remainder_snapshot: { sales_orders: [{ source_record_id: 'SRC-1', source_document_no: 'SRC-1', source_lifecycle_state: 'future-lifecycle-value', lines: [] }] },
    })
    value.groups[0].preflight_result.results[0].status = 'future-row-state'
    const wrapper = await mountPage(value)
    const text = wrapper.text()
    expect(text).toContain('待核实')
    expect(text).not.toContain('future-')
    expect(text).not.toContain('a'.repeat(64))
    expect(text).not.toContain('codex-private-actor')
    expect(text).not.toContain('internal-request-identity')
    wrapper.unmount()
  })

  it('lets the reviewer search and select an existing customer while keeping internal field names out of the page', async () => {
    const value = detail()
    mocks.get.mockImplementation(async (url) => {
      if (url === '/import/history-takeovers/') return { data: { results: [summary(value)] } }
      if (url === '/import/history-takeovers/31/') return { data: value }
      if (url === '/customers/') return { data: { results: [{ id: 94, code: 'C-001', name: '合成客户甲' }] } }
      return { data: value }
    })
    mocks.post.mockResolvedValue({ data: {} })
    const wrapper = mount(HistoryTakeoverPage)
    await flushPromises()
    await wrapper.findAll('label').find(item => item.text().includes('搜索现有对象')).find('input').setValue('合成客户')
    await flushPromises()
    const selected = wrapper.findAll('label').find(item => item.text().includes('选择现有对象')).find('select')
    expect(selected.text()).toContain('合成客户甲 · C-001')
    await selected.setValue('C-001')
    await wrapper.findAll('label').find(item => item.text().includes('原资料行号')).find('input').setValue('2')
    await wrapper.findAll('label').find(item => item.text().includes('关联依据')).find('input').setValue('已对照历史合同')
    await wrapper.findAll('button').find(item => item.text().includes('保存关联并重新预检')).trigger('click')
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/import/history-takeovers/31/groups/41/resolve-master/', {
      sheet: '销售订单', row: 2, field: 'customer_code', target_code: 'C-001', note: '已对照历史合同',
    })
    expect(wrapper.text()).not.toContain('customer_code')
    expect(wrapper.text()).not.toContain('target_code')
    wrapper.unmount()
  })

  it('shows the historical SKU name with its business SKU label during inventory review', async () => {
    const value = detail('executed')
    mocks.post.mockImplementation(async url => url.endsWith('/inventory-status/') ? { data: {
      status: 'pending_review',
      sources: [{ source_id: 'SYN-STOCK-1', source: {
        sku_code: 'SYN-SKU-1', sku_name_snapshot: '合成灯具样本', counted_quantity: '4.00', unit_snapshot: 'pcs',
        warehouse_type: '自有仓', warehouse: '合成仓', lot_reference: '',
      } }],
    } } : { data: {} })
    const wrapper = await mountPage(value)
    await wrapper.findAll('button').find(item => item.text().includes('读取盘点来源')).trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('SKU 合成灯具样本 · SYN-SKU-1')
    await wrapper.findAll('button').find(item => item.text() === '打开历史商品关联').trigger('click')
    await flushPromises()
    expect(wrapper.get('details').element.open).toBe(true)
    expect(wrapper.get('details .history-products').exists()).toBe(true)
    wrapper.unmount()
  })

  it('explains the approval boundary and prevents anonymous or under-scoped intake from being presented as ready', async () => {
    mocks.get.mockResolvedValue({ data: { results: [] } })
    const wrapper = mount(HistoryTakeoverPage)
    await flushPromises()
    expect(wrapper.text()).toContain('预检通过不代表已批准或已入账')
    expect(wrapper.text()).toContain('合成或待核实资料留在申请区')
    expect(wrapper.text()).toContain('下载承接模板')
    expect(wrapper.text()).toContain('还没有历史承接申请')
    wrapper.unmount()
  })

  it('requires an explicit verification note and then exposes per-group execution only after approval', async () => {
    const value = detail()
    mocks.post.mockImplementation(async url => {
      if (url.endsWith('/review/')) value.groups[0].status = 'approved'
      if (url.endsWith('/execute/')) value.groups[0].status = 'executed'
      return { data: { group: value.groups[0] } }
    })
    const wrapper = await mountPage(value)
    expect(wrapper.text()).toContain('审核依据')
    const approve = wrapper.findAll('button').find(button => button.text().includes('批准本组'))
    expect(approve).toBeTruthy()
    await approve.trigger('click')
    expect(mocks.post).not.toHaveBeenCalled()
    await wrapper.find('textarea').setValue('已核对合成来源凭证与全部依赖。')
    await wrapper.find('input[type="checkbox"]').setValue(true)
    await approve.trigger('click')
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/import/history-takeovers/31/groups/41/review/', {
      decision: 'approve', note: '已核对合成来源凭证与全部依赖。', confirm_manual: true,
    })
    const execute = wrapper.findAll('button').find(button => button.text().includes('逐组执行'))
    expect(execute).toBeTruthy()
    await execute.trigger('click')
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/import/history-takeovers/31/groups/41/execute/', {})
    expect(window.confirm).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('separates archive completion from financial, inventory and fulfillment handoffs', async () => {
    const value = detail('executed')
    value.groups[0].execution_result = { orders: [{}], purchase_orders: [{}], finance_records_posted: 0, inventory_movements_posted: 0, fulfillment_records_posted: 0 }
    value.groups[0].finance_handoff_status = 'not_connected'
    value.groups[0].inventory_handoff_status = 'not_connected'
    value.groups[0].fulfillment_handoff_status = 'not_connected'
    const wrapper = await mountPage(value)
    expect(wrapper.text()).toContain('来源凭证：synthetic://voucher')
    expect(wrapper.text()).toContain('归档阶段未产生正式资金、库存流水或履约记录')
    expect(wrapper.text()).toContain('资金交接：尚未接续')
    expect(wrapper.text()).toContain('库存盘点基准')
    expect(wrapper.text()).toContain('历史资金接续')
    expect(wrapper.text()).toContain('提交追溯更正申请')
    wrapper.unmount()
  })

  it('requires explicit cash amount, account and voucher before saving the historical source', async () => {
    const value = detail('executed')
    mocks.get.mockImplementation(async url => {
      if (url === '/import/history-takeovers/') return { data: { results: [summary(value)] } }
      if (url === '/finance-ledger/') return { data: { accounts: [{ id: 7, code: 'TEST', name: '合成账户', ownership: 'own', currency: 'CNY', is_active: true }], vouchers: [{ id: 8, name: '凭证.pdf', sha256: 'a'.repeat(64) }] } }
      return { data: value }
    })
    mocks.post.mockImplementation(async url => url.endsWith('/finance-status/')
      ? { data: { sources: [{ source_id: 9, source_record_id: 'TX-1', status: 'unmapped', source: { amount: '40', currency: 'USD', direction: 'income' } }] } }
      : url.endsWith('/finance-preview/') ? { data: { items: [{ id: -12, type: 'bank_event', label: '银行参考号 ABC' }], token: 'opaque-token', restricted: false } }
      : { data: { instruction_id: 17, status: 'pending' } })
    const wrapper = mount(HistoryTakeoverPage)
    await flushPromises()
    await wrapper.findAll('button').find(button => button.text() === '读取资金来源、账户和凭证').trigger('click')
    await flushPromises()
    const field = label => wrapper.findAll('label').find(item => item.text().includes(label))
    await field('历史收付款来源').find('select').setValue('9')
    await field('自有人民币账户').find('select').setValue('7')
    await field('实际凭证').find('select').setValue('8')
    await field('实际发生日期').find('input').setValue('2024-09-03')
    await field('核实依据').find('input').setValue('已核对银行凭证')
    const submit = wrapper.findAll('button').find(button => button.text() === '保存资金指令')
    expect(submit.attributes('disabled')).toBeDefined()
    await field('实际人民币金额').find('input').setValue('287.43')
    await wrapper.findAll('button').find(button => button.text() === '核对可能重复的资金').trigger('click')
    await flushPromises()
    expect(submit.attributes('disabled')).toBeDefined()
    await field('核对结果').find('select').setValue('12')
    await field('核对说明').find('input').setValue('凭证为同一笔')
    await submit.trigger('click')
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/import/history-takeovers/31/groups/41/finance-submit/', {
      source_id: 9, mapping: { account: 7, voucher: 8, actual_date: '2024-09-03', amount: '287.43', reason: '已核对银行凭证', duplicate_review_token: 'opaque-token', duplicate_review_reason: '凭证为同一笔', same_legacy_event: 12 },
    })
    wrapper.unmount()
  })

  it('requires explicit goods ownership, cost and full-count confirmation for a stock baseline', async () => {
    const value = detail('executed')
    mocks.get.mockImplementation(async url => url === '/import/history-takeovers/'
      ? { data: { results: [summary(value)] } } : { data: value })
    mocks.post.mockImplementation(async url => url.endsWith('/inventory-status/')
      ? { data: { status: 'not_connected', baselines: [], sources: [{ source_id: 12, source: {
        sku_code: 'SYN-1', counted_quantity: '18', unit_snapshot: 'pcs', warehouse_type: '第三方仓', warehouse: '合成仓', lot_reference: 'LOT-1',
      } }] } } : { data: { status: 'pending_review' } })
    const wrapper = mount(HistoryTakeoverPage)
    await flushPromises()
    await wrapper.findAll('button').find(button => button.text() === '读取盘点来源').trigger('click')
    await flushPromises()
    const field = label => wrapper.findAll('label').find(item => item.text().includes(label))
    await field('货物所有权').find('select').setValue('own')
    await field('核实单位成本').find('input').setValue('3.25')
    await field('成本币种').find('input').setValue('USD')
    await field('盘点与成本依据').find('input').setValue('核对盘点和采购凭证')
    const submit = wrapper.findAll('button').find(button => button.text() === '保存基准申请')
    expect(submit.attributes('disabled')).toBeDefined()
    await field('已核实这些 SKU 的盘点范围完整').find('input').setValue(true)
    await submit.trigger('click')
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/import/history-takeovers/31/groups/41/inventory-propose/', {
      rows: [{ source_id: 12, goods_ownership: 'own', unit_cost: '3.25', cost_currency: 'USD', no_lot: false }],
      reason: '核对盘点和采购凭证', complete_sku_inventory: true,
    })
    wrapper.unmount()
  })
})
