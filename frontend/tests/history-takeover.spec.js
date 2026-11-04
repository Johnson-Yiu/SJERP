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
  mocks.get.mockImplementation(async url => url === '/import/history-takeovers/'
    ? { data: { results: [summary(value)] } }
    : { data: value })
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
  it('explains the approval boundary and prevents anonymous or under-scoped intake from being presented as ready', async () => {
    mocks.get.mockResolvedValue({ data: { results: [] } })
    const wrapper = mount(HistoryTakeoverPage)
    await flushPromises()
    expect(wrapper.text()).toContain('预检通过不代表已批准或已迁移')
    expect(wrapper.text()).toContain('模拟或待核实资料只留在暂存区')
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

  it('shows source evidence and warns that finance, inventory and fulfillment handoffs are not connected', async () => {
    const value = detail('executed')
    value.groups[0].execution_result = { orders: [{}], purchase_orders: [{}], finance_records_posted: 0, inventory_movements_posted: 0, fulfillment_records_posted: 0 }
    const wrapper = await mountPage(value)
    expect(wrapper.text()).toContain('来源凭证：synthetic://voucher')
    expect(wrapper.text()).toContain('正式资金、库存流水、履约记录、采购成本分配均为 0')
    expect(wrapper.text()).toContain('提交追溯更正申请')
    wrapper.unmount()
  })
})
