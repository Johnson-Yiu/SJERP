import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import HistoryPreflightPage from './HistoryPreflightPage.vue'

const mocks = vi.hoisted(() => ({ post: vi.fn() }))
vi.mock('../api', () => ({ api: mocks }))
const originalCreateObjectURL = URL.createObjectURL
const originalRevokeObjectURL = URL.revokeObjectURL

const result = {
  preflight_only: true,
  approval_or_migration: false,
  business_write_performed: false,
  notice: '预检通过仅表示当前规则检查通过，不代表已审批或已迁移。',
  summary: { total_rows: 3, passed: 1, warnings: 1, blocked: 1, manual_review: 0, overall_status: '阻断' },
  groups: [{ group_id: 'SYN-G1', status: '阻断', coverage_status: 'complete' }],
  results: [
    { sheet: '分组', row: 2, group_id: 'SYN-G1', status: '通过', reasons: [], suggested_actions: [] },
    { sheet: '销售订单', row: 2, source_record_id: 'SYN-SO-1', group_id: 'SYN-G1', status: '阻断', reasons: [{ message: '存在重复来源记录。' }], suggested_actions: ['核对原始编号和凭证。'] },
    { sheet: '销售明细', row: 2, source_record_id: 'SYN-L1', group_id: 'SYN-G1', status: '警告', reasons: [{ message: '历史名称与当前主档不同。' }], suggested_actions: ['保留历史快照。'] },
  ],
}

function workbookResult(name, totalRows) {
  return {
    ...result,
    summary: { ...result.summary, total_rows: totalRows },
    results: [{
      sheet: '销售订单', row: 2, source_record_id: `${name}-SO-1`, group_id: `${name}-G1`, status: '警告',
      reasons: [{ message: `${name} 的专属预检结果。` }], suggested_actions: [`核对 ${name} 工作簿。`],
    }],
  }
}

function deferred() {
  let resolve
  let reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

function mountPage() {
  return mount(HistoryPreflightPage, {
    global: {
      stubs: {
        RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
      },
    },
  })
}

async function selectWorkbook(wrapper, name = 'synthetic-history.xlsx') {
  const file = new File(['synthetic workbook'], name, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const input = wrapper.find('input[type="file"]')
  Object.defineProperty(input.element, 'files', { configurable: true, value: [file] })
  await input.trigger('change')
  return file
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  if (originalCreateObjectURL) Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: originalCreateObjectURL })
  else delete URL.createObjectURL
  if (originalRevokeObjectURL) Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: originalRevokeObjectURL })
  else delete URL.revokeObjectURL
  vi.restoreAllMocks()
})

describe('history preflight page', () => {
  it('uploads an XLSX only to the read-only preflight endpoint and shows summary and row issues', async () => {
    mocks.post.mockResolvedValue({ data: result })
    const wrapper = mountPage()
    const file = await selectWorkbook(wrapper)
    await wrapper.get('button.preflight-primary').trigger('click')
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledTimes(1)
    expect(mocks.post.mock.calls[0][0]).toBe('/import/history-preflight/')
    expect(mocks.post.mock.calls[0][1].get('file')).toBe(file)
    expect(wrapper.text()).toContain('历史资料预检')
    expect(wrapper.text()).toContain('预检汇总')
    expect(wrapper.text()).toContain('数据行')
    expect(wrapper.text()).toContain('存在重复来源记录。')
    expect(wrapper.text()).toContain('核对原始编号和凭证。')
    expect(wrapper.text()).not.toContain('当前没有行级问题。')
    expect(wrapper.get('a[href="/history-takeover"]').text()).toContain('进入历史资料承接')

    await wrapper.get('button.preflight-text-button').trigger('click')
    expect(wrapper.text()).toContain('SYN-G1')
    wrapper.unmount()
  })

  it('requests the API CSV response and triggers a named browser download', async () => {
    const csv = new Blob(['\ufeff工作表,原行号\n销售订单,2'], { type: 'text/csv;charset=utf-8' })
    mocks.post.mockImplementation(async (url, body) => url.includes('report=csv')
      ? { data: csv }
      : { data: workbookResult(body.get('file').name.replace('.xlsx', ''), 1) })
    const createUrl = vi.fn(() => 'blob:synthetic-csv')
    const revokeUrl = vi.fn()
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createUrl })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeUrl })
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const wrapper = mountPage()

    const workbookA = await selectWorkbook(wrapper, 'workbook-A.xlsx')
    await wrapper.get('button.preflight-primary').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('workbook-A-SO-1')

    const selected = await selectWorkbook(wrapper, 'workbook-B.xlsx')
    expect(wrapper.find('.preflight-summary').exists()).toBe(false)
    expect(wrapper.findAll('button').some(button => button.text().includes('下载 CSV 清单'))).toBe(false)
    await wrapper.get('button.preflight-primary').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('workbook-B-SO-1')
    await wrapper.findAll('button').find(button => button.text().includes('下载 CSV 清单')).trigger('click')
    await flushPromises()

    const csvCall = mocks.post.mock.calls.find(([url]) => url.includes('report=csv'))
    expect(csvCall?.[0]).toBe('/import/history-preflight/?report=csv')
    expect(csvCall?.[1].get('file')).toBe(selected)
    expect(csvCall?.[1].get('file')).not.toBe(workbookA)
    expect(csvCall?.[2]).toEqual({ responseType: 'blob' })
    expect(createUrl).toHaveBeenCalledWith(csv)
    expect(click).toHaveBeenCalledOnce()
    expect(click.mock.contexts[0]?.download).toBe('history-preflight.csv')
    wrapper.unmount()
  })

  it('lets the user start B after changing files while A is still being checked', async () => {
    const pendingA = deferred()
    const pendingB = deferred()
    mocks.post.mockImplementation((_url, body) => body.get('file').name === 'workbook-A.xlsx' ? pendingA.promise : pendingB.promise)
    const wrapper = mountPage()

    await selectWorkbook(wrapper, 'workbook-A.xlsx')
    await wrapper.get('button.preflight-primary').trigger('click')
    expect(wrapper.get('button.preflight-primary').element.disabled).toBe(true)

    await selectWorkbook(wrapper, 'workbook-B.xlsx')
    expect(wrapper.find('.preflight-summary').exists()).toBe(false)
    expect(wrapper.get('button.preflight-primary').element.disabled).toBe(false)
    await wrapper.get('button.preflight-primary').trigger('click')
    expect(mocks.post).toHaveBeenCalledTimes(2)
    expect(mocks.post.mock.calls[1][1].get('file').name).toBe('workbook-B.xlsx')

    pendingB.resolve({ data: workbookResult('workbook-B', 27) })
    await flushPromises()
    expect(wrapper.get('.preflight-summary').text()).toContain('27')
    expect(wrapper.text()).toContain('workbook-B-SO-1')
    pendingA.resolve({ data: workbookResult('workbook-A', 11) })
    await flushPromises()
    expect(wrapper.get('.preflight-summary').text()).toContain('27')
    expect(wrapper.text()).toContain('workbook-B-SO-1')
    expect(wrapper.text()).not.toContain('workbook-A-SO-1')
    wrapper.unmount()
  })

  it('ignores A when its response arrives after B has replaced it', async () => {
    const pendingA = deferred()
    const pendingB = deferred()
    mocks.post.mockImplementation((_url, body) => body.get('file').name === 'workbook-A.xlsx' ? pendingA.promise : pendingB.promise)
    const wrapper = mountPage()

    await selectWorkbook(wrapper, 'workbook-A.xlsx')
    await wrapper.get('button.preflight-primary').trigger('click')
    await selectWorkbook(wrapper, 'workbook-B.xlsx')
    await wrapper.get('button.preflight-primary').trigger('click')
    pendingB.resolve({ data: workbookResult('workbook-B', 27) })
    await flushPromises()
    expect(wrapper.text()).toContain('workbook-B-SO-1')

    pendingA.resolve({ data: workbookResult('workbook-A', 11) })
    await flushPromises()
    expect(wrapper.get('.preflight-summary').text()).toContain('27')
    expect(wrapper.text()).toContain('workbook-B-SO-1')
    expect(wrapper.text()).not.toContain('workbook-A-SO-1')
    expect(wrapper.text()).toContain('workbook-B.xlsx')
    wrapper.unmount()
  })

  it('shows API validation errors for an invalid workbook response', async () => {
    mocks.post.mockRejectedValue(new Error('仅支持本任务提供的 .xlsx 模板格式。'))
    const wrapper = mountPage()
    await selectWorkbook(wrapper, 'not-a-workbook.csv')
    await wrapper.get('button.preflight-primary').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('仅支持本任务提供的 .xlsx 模板格式。')
    expect(wrapper.find('.preflight-summary').exists()).toBe(false)
    wrapper.unmount()
  })
})
