import { beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ReportBlock from '../src/components/reports/ReportBlock.vue'

const api = vi.hoisted(() => ({ get: vi.fn() }))
vi.mock('../src/api', () => ({ api }))
const response = () => ({ data: { date_field: 'order_date', date_label: '订单日期', filters: {}, period: { date_from: '2026-09-01', date_to: '2026-09-30' }, comparison_period: { date_from: '2026-08-02', date_to: '2026-08-31' }, comparison: 'previous', totals: { amount: '189', count: 1, quantities: { pcs: 2, box: 1 } }, changes: { amount: null, count: null }, rows: [{ key: '1', label: '甲客户', amount: '189', count: 1, quantities: { pcs: 2, box: 1 } }], note: '统计口径' } })
beforeEach(() => { vi.clearAllMocks(); api.get.mockResolvedValue(response()) })

it('independently queries an embedded preset with scoped filters and emits drill context', async () => {
  const wrapper = mount(ReportBlock, { props: { blockId: 'sales-customer', filters: { date_from: '2026-09-01', filter_country: 'CN' } } })
  await flushPromises()
  expect(api.get.mock.calls[0][1].params).toMatchObject({ source: 'sales', group_by: 'customer', filter_country: 'CN' })
  expect(wrapper.text()).toContain('189')
  await wrapper.find('.report-link').trigger('click')
  expect(wrapper.emitted('drill')[0][0]).toMatchObject({ dimension: 'customer', value: '1', source: 'sales', date_field: 'order_date' })
  wrapper.unmount()
})

it('a slower superseded request cannot overwrite the latest filter results', async () => {
  let resolveOld
  api.get.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
  const wrapper = mount(ReportBlock)
  await wrapper.setProps({ filters: { date_from: '2026-09-02' } })
  await flushPromises()
  resolveOld({ data: { ...response().data, totals: { amount: 999, count: 7, quantities: {} } } })
  await flushPromises()
  expect(wrapper.find('.block-kpis').text()).toContain('189')
  expect(wrapper.find('.block-kpis').text()).not.toContain('999')
  wrapper.unmount()
})

it('negative values never produce misleading donut proportions', async () => {
  const data = response(); data.data.rows[0].amount = '-189'
  api.get.mockResolvedValue(data)
  const wrapper = mount(ReportBlock, { props: { config: { source: 'cash', view: 'donut' } } })
  await flushPromises()
  expect(wrapper.find('.report-donut').exists()).toBe(false)
  expect(wrapper.find('.negative').exists()).toBe(true)
  wrapper.unmount()
})

it('switches quantity chart units without summing incompatible units', async () => {
  const wrapper = mount(ReportBlock, { props: { blockId: 'inventory-warehouse' } })
  await flushPromises()
  expect(wrapper.find('.report-bar-row').text()).toContain('2')
  await wrapper.find('.chart-caption select').setValue('box')
  expect(wrapper.find('.report-bar-row').text()).toContain('1')
  expect(wrapper.text()).not.toContain('金额合计')
  wrapper.unmount()
})

it('failed requests show retry and suppress export of stale data', async () => {
  api.get.mockRejectedValueOnce(new Error('请求失败'))
  const wrapper = mount(ReportBlock)
  await flushPromises()
  expect(wrapper.find('[role="alert"]').text()).toContain('请求失败')
  expect(wrapper.find('.block-actions button').attributes('disabled')).toBeDefined()
  await wrapper.find('[role="alert"] button').trigger('click')
  await flushPromises()
  expect(wrapper.find('.block-kpis').exists()).toBe(true)
  wrapper.unmount()
})
