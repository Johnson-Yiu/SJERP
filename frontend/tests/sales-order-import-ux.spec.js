// @vitest-environment jsdom
import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import { workspaceKey, workspaceManagerKey } from '../src/composables/useWorkspaceNavigation'
import { setAccessOperator } from '../src/accessControl'
import ImportPage from '../src/views/ImportPage.vue'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), confirm: vi.fn() }))
vi.mock('../src/api', () => ({ api: { get: mocks.get, post: mocks.post } }))
vi.mock('../src/dialogs', () => ({ confirmDialog: mocks.confirm }))

const button = (wrapper, name) => wrapper.findAll('button').find(item => item.text() === name)
const orderFileInput = wrapper => wrapper.findAll('input[type="file"]').find(input => input.attributes('accept')?.includes('.xlsx'))
const mountPage = () => mount(ImportPage, { global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } } })
const preview = {
  total_rows: 3,
  total_orders: 2,
  valid_orders: 1,
  invalid_orders: 1,
  orders: [
    { source_order_no: 'SRC-OK', customer_code: 'C001', line_count: 2, currency: 'USD', total_amount: '25.00', valid: true },
    { source_order_no: 'SRC-BAD', customer_code: 'C001', line_count: 1, currency: 'USD', total_amount: '0.00', valid: false },
  ],
  errors: [{ row: 4, key: 'SRC-BAD', message: '找不到 SKU。' }],
  preview_token: 'sales-order-preview-token',
  business_write_performed: false,
}

beforeEach(() => {
  sessionStorage.clear()
  vi.resetAllMocks()
  setAccessOperator({ id: 'codex-test', username: 'codex-test', authenticated: true, has_all_permissions: true })
  mocks.get.mockResolvedValue({ data: { customers: ['code', 'name'] } })
  mocks.confirm.mockResolvedValue(true)
})

it('downloads the XLSX template and sends a selected workbook for preview', async () => {
  const create = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:sales-order-template')
  const wrapper = mountPage()
  try {
    await flushPromises()
    mocks.get.mockResolvedValueOnce({ data: new Blob(['xlsx bytes']) })
    await button(wrapper, '销售订单').trigger('click')
    await wrapper.findAll('button').find(item => item.text().startsWith('下载销售订单 XLSX 模板')).trigger('click')
    await flushPromises()
    expect(mocks.get).toHaveBeenCalledWith('/import/orders/template/', { responseType: 'blob' })
    expect(create).toHaveBeenCalled()

    const input = orderFileInput(wrapper)
    Object.defineProperty(input.element, 'files', { configurable: true, value: [new File(['xlsx bytes'], 'orders.xlsx')] })
    await input.trigger('change')
    mocks.post.mockResolvedValueOnce({ data: preview })
    await button(wrapper, '预览并校验').trigger('click')
    await flushPromises()
    expect(mocks.post.mock.calls[0][0]).toBe('/import/orders/preview/')
    expect(mocks.post.mock.calls[0][1].get('file').name).toBe('orders.xlsx')
    expect(wrapper.text()).toContain('1 张可导入，1 张待修正')
    expect(wrapper.text()).toContain('预览不会写入业务数据')
    expect(button(wrapper, '确认导入 1 张草稿')).toBeDefined()
  } finally {
    create.mockRestore()
    wrapper.unmount()
  }
})

it('keeps whole-order errors downloadable while confirming valid drafts once', async () => {
  const wrapper = mountPage()
  try {
    await flushPromises()
    await button(wrapper, '销售订单').trigger('click')
    const input = orderFileInput(wrapper)
    Object.defineProperty(input.element, 'files', { configurable: true, value: [new File(['workbook'], 'orders.xlsx')] })
    await input.trigger('change')
    mocks.post.mockResolvedValueOnce({ data: preview })
    await button(wrapper, '预览并校验').trigger('click')
    await flushPromises()
    expect(button(wrapper, '下载错误清单 CSV')).toBeDefined()

    const execute = {
      batch_id: '17', status: 'partial', total_rows: 3, total_orders: 2,
      created_orders: 1, failed_orders: 1,
      orders: [{ source_order_no: 'SRC-OK', order_id: 17, order_no: 'SO-2026-00017', status: 'draft', customer_code: 'C001', line_count: 2, currency: 'USD', total_amount: '25.00' }],
      errors: preview.errors,
    }
    mocks.post.mockResolvedValueOnce({ data: execute })
    await button(wrapper, '确认导入 1 张草稿').trigger('click')
    await flushPromises()
    expect(mocks.confirm).toHaveBeenCalledTimes(1)
    expect(mocks.post).toHaveBeenCalledTimes(2)
    expect(mocks.post.mock.calls[1][0]).toBe('/import/orders/execute/')
    expect(mocks.post.mock.calls[1][1].get('preview_token')).toBe(preview.preview_token)
    expect(wrapper.text()).toContain('已创建 1 张草稿，1 张未创建')
    expect(wrapper.text()).toContain('SO-2026-00017')
    expect(wrapper.text()).toContain('历史资料预检与承接')
  } finally { wrapper.unmount() }
})

it('exports the order preview and validation issues as a UTF-8 result CSV', async () => {
  const create = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:sales-order-results')
  let downloadedLink
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () { downloadedLink = this })
  const wrapper = mountPage()
  try {
    await flushPromises()
    await button(wrapper, '销售订单').trigger('click')
    const input = orderFileInput(wrapper)
    Object.defineProperty(input.element, 'files', { configurable: true, value: [new File(['workbook'], 'orders.xlsx')] })
    await input.trigger('change')
    mocks.post.mockResolvedValueOnce({ data: preview })
    await button(wrapper, '预览并校验').trigger('click')
    await flushPromises()
    await button(wrapper, '下载导入结果 CSV').trigger('click')
    const blob = create.mock.calls.at(-1)[0]
    const buffer = await new Promise(resolve => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.readAsArrayBuffer(blob)
    })
    const bytes = new Uint8Array(buffer)
    const csv = new TextDecoder('utf-8').decode(buffer)
    expect(downloadedLink.download).toBe('sales-order-import-results.csv')
    expect(Array.from(bytes.slice(0, 3))).toEqual([0xef, 0xbb, 0xbf])
    expect(csv).toContain('来源订单编号')
    expect(csv).toContain('SRC-OK')
    expect(csv).toContain('SRC-BAD')
    expect(csv).toContain('找不到 SKU。')
    expect(click).toHaveBeenCalled()
  } finally {
    click.mockRestore()
    create.mockRestore()
    wrapper.unmount()
  }
})

function deferred() { let resolve; const promise = new Promise(done => { resolve = done }); return { promise, resolve } }
async function readyPage() {
  const wrapper = mountPage(); await flushPromises(); await button(wrapper, '销售订单').trigger('click')
  const input = orderFileInput(wrapper)
  const file = new File(['workbook'], 'orders.xlsx', { lastModified: 42 })
  Object.defineProperty(input.element, 'files', { configurable: true, value: [file] }); await input.trigger('change')
  mocks.post.mockResolvedValueOnce({ data: preview }); await button(wrapper, '预览并校验').trigger('click'); await flushPromises()
  return { wrapper, file }
}
it('does not execute a stale confirmation after component unmount', async () => {
  const { wrapper } = await readyPage(), confirm = deferred()
  mocks.confirm.mockReturnValueOnce(confirm.promise)
  await button(wrapper, '确认导入 1 张草稿').trigger('click'); wrapper.unmount()
  confirm.resolve(true); await flushPromises()
  expect(mocks.post).toHaveBeenCalledTimes(1)
})
it('restores the original preview identity after a lost response and reopen', async () => {
  const { wrapper, file } = await readyPage()
  sessionStorage.setItem('sales-order-import-pending-v1:codex-test', JSON.stringify([{file:'other.xlsx:1:2',preview_token:'other-tab-token'}]))
  mocks.post.mockRejectedValueOnce(new Error('Network response lost'))
  await button(wrapper, '确认导入 1 张草稿').trigger('click'); await flushPromises()
  wrapper.unmount()
  const reopened = mountPage(); await flushPromises(); await button(reopened, '销售订单').trigger('click')
  const input = orderFileInput(reopened)
  Object.defineProperty(input.element, 'files', { configurable: true, value: [file] }); await input.trigger('change')
  expect(reopened.text()).toContain('已恢复待核对导入批次')
  mocks.post.mockResolvedValueOnce({ data: { batch_id:'17', total_rows:3, total_orders:2, created_orders:1, failed_orders:1, orders:[], errors:[] } })
  await button(reopened, '确认导入 1 张草稿').trigger('click'); await flushPromises()
  expect(mocks.post.mock.calls[2][1].get('preview_token')).toBe(preview.preview_token)
  expect(JSON.parse(sessionStorage.getItem('sales-order-import-pending-v1:codex-test'))).toEqual([{file:'other.xlsx:1:2',preview_token:'other-tab-token'}]); reopened.unmount()
})

it('keeps the latest selected file when preview responses arrive out of order', async () => {
  const wrapper = mountPage(); await flushPromises(); await button(wrapper, '销售订单').trigger('click')
  const input = orderFileInput(wrapper), requestA = deferred(), requestB = deferred()
  Object.defineProperty(input.element, 'files', { configurable: true, value: [new File(['A'], 'A.xlsx')] }); await input.trigger('change')
  mocks.post.mockReturnValueOnce(requestA.promise)
  await button(wrapper, '预览并校验').trigger('click')
  Object.defineProperty(input.element, 'files', { configurable: true, value: [new File(['B'], 'B.xlsx')] }); await input.trigger('change')
  mocks.post.mockReturnValueOnce(requestB.promise)
  await button(wrapper, '预览并校验').trigger('click')
  const responseFor = (file, token) => ({
    ...preview, total_rows: 1, total_orders: 1, valid_orders: 1, invalid_orders: 0, errors: [],
    preview_token: token, orders: [{ ...preview.orders[0], source_order_no: file }],
  })
  requestB.resolve({ data: responseFor('FILE-B', 'token-b') }); await flushPromises()
  requestA.resolve({ data: responseFor('FILE-A', 'token-a') }); await flushPromises()
  expect(wrapper.text()).toContain('FILE-B')
  expect(wrapper.text()).not.toContain('FILE-A')
  wrapper.unmount()
})

it('invalidates a late confirmation after the signed-in account changes', async () => {
  const { wrapper } = await readyPage(), confirmation = deferred()
  mocks.confirm.mockReturnValueOnce(confirmation.promise)
  await button(wrapper, '确认导入 1 张草稿').trigger('click')
  setAccessOperator({ id: 'different-account', username: 'different-account', authenticated: true, has_all_permissions: true })
  confirmation.resolve(true); await flushPromises()
  expect(mocks.post).toHaveBeenCalledTimes(1)
  wrapper.unmount()
})

it('does not execute when import permission is narrowed while confirmation is open', async () => {
  const { wrapper } = await readyPage(), confirmation = deferred()
  mocks.confirm.mockReturnValueOnce(confirmation.promise)
  await button(wrapper, '确认导入 1 张草稿').trigger('click')
  setAccessOperator({ id: 'codex-test', username: 'codex-test', authenticated: true, rbac_enforcement: true, permissions: { imports: { import: false } } })
  confirmation.resolve(true); await flushPromises()
  expect(mocks.post).toHaveBeenCalledTimes(1)
  wrapper.unmount()
})

it('blocks workspace close and refresh throughout confirmation and execution', async () => {
  const workspace = { id:'guard-test', guards:new Set(), controller:new AbortController(), closed:false, busy:0, stale:false }
  const wrapper = mount(ImportPage, { global:{ provide:{ [workspaceKey]:workspace, [workspaceManagerKey]:{identity:ref('codex-test')} }, stubs:{RouterLink:{template:'<a><slot /></a>'}} } })
  await flushPromises(); await button(wrapper, '销售订单').trigger('click')
  const input=orderFileInput(wrapper); Object.defineProperty(input.element,'files',{value:[new File(['xlsx'],'guard.xlsx')],configurable:true}); await input.trigger('change')
  mocks.post.mockResolvedValueOnce({data:preview}); await button(wrapper,'预览并校验').trigger('click'); await flushPromises()
  const confirmation=deferred(), execution=deferred(); mocks.confirm.mockReturnValueOnce(confirmation.promise); mocks.post.mockReturnValueOnce(execution.promise)
  await button(wrapper,'确认导入 1 张草稿').trigger('click')
  const guard=[...workspace.guards][0]; expect(await guard.confirmLeave()).toBe(false)
  let event=new Event('beforeunload',{cancelable:true}); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true)
  confirmation.resolve(true); await flushPromises(); expect(await guard.confirmLeave()).toBe(false)
  event=new Event('beforeunload',{cancelable:true}); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true)
  execution.resolve({data:{batch_id:'18',total_rows:3,total_orders:2,created_orders:1,failed_orders:1,orders:[],errors:[]}}); await flushPromises()
  expect(await guard.confirmLeave()).toBe(true); wrapper.unmount()
})
