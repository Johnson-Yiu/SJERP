import { expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ProductWorkspace from '../src/components/ProductWorkspace.vue'
const sales = [
  { id: 1, order_no: 'SO1', order_date: '2026-09-10', customer_name: '甲', quantity: 2, amount: 20, currency: 'USD', unit: 'm' },
  { id: 1, order_no: 'SO1', order_date: '2026-09-10', customer_name: '甲', quantity: 3, amount: 30, currency: 'USD', unit: 'm' },
  { id: 2, order_no: 'SO2', order_date: '2026-09-11', customer_name: '乙', quantity: 100, amount: 1000, currency: 'CNY', unit: 'm' },
  { id: 3, order_no: 'SO3', order_date: '2026-09-12', customer_name: '丙', quantity: 9, amount: 900, currency: 'USD', unit: 'pcs' },
]
const data = { info: [], sections: [{ key: 'sales', title: '订单记录', rows: sales }, { key: 'skus', title: 'SKU', rows: [] }] }
it('separates currency and units and counts distinct orders', async () => {
  const w = mount(ProductWorkspace, { props: { data, activeTab: 'sales-summary' } })
  const metrics = () => w.findAll('.sales-metrics strong').map(x => x.text())
  expect(metrics()).toEqual(['1', '5', '50'])
  await w.findAll('select')[0].setValue('CNY')
  expect(metrics()).toEqual(['1', '100', '1,000'])
  await w.find('input[type=date]').setValue('2026-09-12')
  expect(metrics()).toEqual(['0', '0', '0'])
  w.unmount()
})
it('navigates from overview and emits the selected order', async () => {
  const w = mount(ProductWorkspace, { props: { data, activeTab: '__overview' } })
  await w.findAll('.preview-grid section')[1].find('button').trigger('click')
  expect(w.emitted('update:activeTab')[0]).toEqual(['skus'])
  await w.setProps({ activeTab: 'sales' })
  await w.find('.sales-table tbody button').trigger('click')
  expect(w.emitted('drill')[0][0].order_no).toBe('SO1')
  w.unmount()
})
