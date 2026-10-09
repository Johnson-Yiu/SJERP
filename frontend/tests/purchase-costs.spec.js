import { beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PurchaseCostAllocationModal from '../src/components/PurchaseCostAllocationModal.vue'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('../src/api', () => ({ api }))
const initial = { version: 0, expenses: [], allocations: [{ purchase_item: 7, target_type: 'inventory', order: null, quantity: '1000', sku_code: 'WIRE', base_amount: '10000', additional_amount: '0', total_amount: '10000' }], base_amount: '10000', additional_amount: '0', total_amount: '10000' }
const props = { purchase: { id: 2, purchase_no: 'PO-2', status: 'ordered', currency: 'CNY', items: [{ id: 7, sku_code: 'WIRE', quantity: '1000', unit_price: '10' }] }, orders: [{ id: 3, order_no: 'SO-A', customer_name: 'A' }] }
beforeEach(() => { vi.clearAllMocks(); api.get.mockResolvedValue({ data: initial }) })

it('edits allocation, saves the revision and renders authoritative calculated totals', async () => {
  const wrapper = mount(PurchaseCostAllocationModal, { props })
  await flushPromises()
  expect(wrapper.find('.item-title').text()).toContain('CNY 10.00')
  expect(wrapper.find('.cost-footer .btn-secondary').text()).toBe('取消')
  await wrapper.find('.cost-row select').setValue('order')
  await wrapper.findAll('.cost-row select')[1].setValue(3)
  await wrapper.find('input[type="number"]').setValue('200')
  expect(wrapper.text()).toContain('剩余 800.00')
  expect(wrapper.find('.cost-result').exists()).toBe(true)
  expect(wrapper.find('.cost-result').text()).toContain('计算中…')
  api.post.mockResolvedValue({ data: { ...initial, version: 1 } })
  await wrapper.find('form').trigger('submit')
  await flushPromises()
  expect(api.post).toHaveBeenCalledWith('/purchase-orders/2/cost-allocation/', { version: 0, allocations: [{ purchase_item: 7, target_type: 'order', order: 3, quantity: 200 }], expenses: [] })
  expect(wrapper.text()).toContain('已保存的成本分摊结果')
  expect(wrapper.emitted('saved')).toHaveLength(1)
  wrapper.unmount()
})

it('keeps edits and shows server conflict without claiming success', async () => {
  const wrapper = mount(PurchaseCostAllocationModal, { props })
  await flushPromises()
  api.post.mockRejectedValue({ response: { data: ['成本分配已被其他人修改'] } })
  await wrapper.find('form').trigger('submit')
  await flushPromises()
  expect(wrapper.find('[role="alert"]').text()).toContain('已被其他人修改')
  expect(wrapper.emitted('saved')).toBeUndefined()
  expect(wrapper.find('input').element.value).toBe('1000')
  wrapper.unmount()
})

it('keeps results on outside clicks and submits a custom target name', async () => {
  const wrapper = mount(PurchaseCostAllocationModal, { props })
  await flushPromises()
  await wrapper.find('.cost-backdrop').trigger('mousedown')
  expect(wrapper.emitted('close')).toBeUndefined()
  await wrapper.find('.cost-row select').setValue('other')
  const custom = wrapper.find('input[placeholder="请输入成本归属名称"]')
  expect(custom.exists()).toBe(true)
  expect(custom.attributes('required')).toBeDefined()
  await custom.setValue('项目备用物料')
  expect(wrapper.find('.cost-result').exists()).toBe(true)
  api.post.mockResolvedValue({ data: { ...initial, version: 1, allocations: [{ ...initial.allocations[0], target_type: 'other', target_name: '项目备用物料', display_name: '白色电线' }] } })
  await wrapper.find('form').trigger('submit'); await flushPromises()
  expect(api.post.mock.calls[0][1].allocations[0]).toMatchObject({ target_type: 'other', target_name: '项目备用物料' })
  expect(wrapper.find('.cost-result').text()).toContain('项目备用物料')
  expect(wrapper.find('.cost-result').text()).toContain('白色电线')
  expect(wrapper.find('.pending-badge').exists()).toBe(false)
  wrapper.unmount()
})

it('automatically previews fees without saving and ignores stale responses', async () => {
  vi.useFakeTimers()
  const wrapper = mount(PurchaseCostAllocationModal, { props })
  try {
    await flushPromises()
    await wrapper.findAll('button').find(b => b.text() === '添加附加费用').trigger('click')
    await wrapper.findAll('input[type="number"]').at(-1).setValue('50')
    let resolveFirst
    api.post.mockImplementationOnce(() => new Promise(resolve => { resolveFirst = resolve }))
    await vi.advanceTimersByTimeAsync(250)
    expect(api.post.mock.calls[0][0]).toBe('/purchase-orders/2/cost-allocation-preview/')
    await wrapper.findAll('input[type="number"]').at(-1).setValue('60')
    api.post.mockResolvedValueOnce({ data: { ...initial, additional_amount: '60', total_amount: '10060' } })
    await vi.advanceTimersByTimeAsync(250); await flushPromises()
    expect(wrapper.find('.cost-result').text()).toContain('10,060.00')
    resolveFirst({ data: { ...initial, additional_amount: '50', total_amount: '10050' } })
    await flushPromises()
    expect(wrapper.find('.cost-result').text()).toContain('10,060.00')
    expect(wrapper.find('.cost-result').text()).toContain('未保存')
    expect(wrapper.emitted('saved')).toBeUndefined()
    api.post.mockRejectedValueOnce({ response: { data: { expenses: ['金额无效'] } } })
    await wrapper.findAll('input[type="number"]').at(-1).setValue('')
    await vi.advanceTimersByTimeAsync(250); await flushPromises()
    expect(wrapper.find('.cost-result').text()).toContain('金额无效')
    expect(wrapper.find('.cost-result').text()).toContain('10,060.00')
  } finally { wrapper.unmount(); vi.useRealTimers() }
})
