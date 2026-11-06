// @vitest-environment jsdom
import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
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
  vi.resetAllMocks()
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
