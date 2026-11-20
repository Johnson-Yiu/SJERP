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

it('shows actual line-point currency data, including zero and missing amounts', async () => {
  const fixture = response()
  fixture.data.rows = [
    { key: 'sep', label: '2026-09', amount: '-12345678.5' },
    { key: 'oct', label: '2026-10', amount: 0 },
    { key: 'nov', label: '2026-11', amount: null },
  ]
  api.get.mockResolvedValue(fixture)
  const wrapper = mount(ReportBlock, { props: { config: { view: 'line' } } })
  await flushPromises()
  const targets = wrapper.findAll('.line-hit')
  await targets[0].trigger('pointerenter')
  expect(wrapper.get('[role=tooltip]').text()).toContain('2026-09')
  expect(wrapper.get('[role=tooltip]').text()).toContain('¥ -12,345,678.5')
  await targets[0].trigger('pointerleave')
  expect(wrapper.find('[role=tooltip]').exists()).toBe(false)
  await targets[1].trigger('focus')
  expect(wrapper.get('[role=tooltip]').text()).toContain('¥ 0')
  await targets[2].trigger('focus')
  expect(wrapper.get('[role=tooltip]').text()).toContain('金额待核实')
  await targets[2].trigger('keydown', { key: 'Escape' })
  expect(wrapper.find('[role=tooltip]').exists()).toBe(false)
  wrapper.unmount()
})

it('shows the selected quantity unit on bars while preserving drill and chart switching', async () => {
  const wrapper = mount(ReportBlock, { props: { blockId: 'inventory-warehouse' } })
  await flushPromises()
  await wrapper.get('.bar-track').trigger('pointerenter')
  expect(wrapper.get('[role=tooltip]').text()).toContain('2 pcs')
  await wrapper.get('.chart-caption select').setValue('box')
  expect(wrapper.find('[role=tooltip]').exists()).toBe(false)
  await wrapper.get('.bar-track').trigger('click')
  expect(wrapper.get('[role=tooltip]').text()).toContain('1 box')
  await wrapper.get('button.bar-label').trigger('click')
  expect(wrapper.emitted('drill')).toHaveLength(1)
  await wrapper.get('[aria-label="图表显示方式"]').setValue('table')
  expect(wrapper.find('[role=tooltip]').exists()).toBe(false)
  wrapper.unmount()
})

it('shows counts and percentage through donut sector focus and legend clicks', async () => {
  const fixture = response()
  fixture.data.rows = [{ key: 'a', label: '甲客户', count: 12500 }, { key: 'b', label: '乙客户', count: 0 }]
  api.get.mockResolvedValue(fixture)
  const wrapper = mount(ReportBlock, { props: { config: { view: 'donut', metric: 'count' } } })
  await flushPromises()
  const sector = wrapper.get('.report-donut circle[tabindex]')
  await sector.trigger('focus')
  expect(wrapper.get('[role=tooltip]').text()).toContain('12,500')
  expect(wrapper.get('[role=tooltip]').text()).toContain('100%')
  await sector.trigger('blur')
  expect(wrapper.find('[role=tooltip]').exists()).toBe(false)
  await wrapper.findAll('.report-donut p')[1].trigger('click')
  expect(wrapper.get('[role=tooltip]').text()).toContain('乙客户')
  expect(wrapper.get('[role=tooltip]').text()).toContain('占比 0%')
  wrapper.unmount()
})
