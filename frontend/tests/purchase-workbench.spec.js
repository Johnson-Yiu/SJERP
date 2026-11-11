// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PurchaseDetailModal from '../src/components/PurchaseDetailModal.vue'
import { purchaseArrival, purchaseTasks, receiptProgress } from '../src/utils/purchaseOverview.js'
const item = { id: 71, sku: 3, sku_code: 'SKU-3', display_name: '测试灯', quantity: '10', received_quantity: '4', remaining_quantity: '6', unit_price: '2', supplier_name: '历史供应商', supplier_model: 'MODEL-A', supplier_sku_code: 'SOURCE-A', supplier_characteristics_snapshot: { 色温: '3000K' }, trade_snapshot: { base_unit: 'pcs' }, receipts: [{ id: 91, receipt_date: '2026-10-01', quantity: '4', unit_cost: '2', overage_summary: '赠品 1 件' }, { id: 92, receipt_date: '2026-10-02', quantity: '1', unit_cost: '2', reversed_at: '2026-10-03' }] }
const purchase = { id: 41, purchase_no: 'PO-41', supplier_name: '供应商甲', supplier_name_snapshot: '供应商甲', order_date: '2026-10-01', expected_arrival_date: '2026-10-08', status: 'partial', status_display: '部分到货', currency: 'USD', total_amount: '20', paid_amount: '4', unpaid_amount: '16', items: [item], related_orders: [{ id: 22, order_no: 'SO-22', customer_name: '客户乙' }] }
const mountDetail = overrides => mount(PurchaseDetailModal, { props: { purchase: { ...purchase, ...overrides } }, global: { stubs: { ContractAmountAdjustments: true, RouterLink: { props: ['to'], template: '<a :href="`/orders?detail=${to.query.detail}`"><slot /></a>' } } } })
const click = async (wrapper, label) => wrapper.findAll('button').find(button => button.text() === label).trigger('click')

describe('purchase workbench Phase A', () => {
  it('formats receipt cost without changing raw precision, quantity or reversal targets', async () => {
    const receipt = { ...item.receipts[0], unit_cost: '6.500000000000' }
    const receiptItem = { ...item, receipts: [receipt, item.receipts[1]] }
    const original = { ...purchase, items: [receiptItem] }
    const wrapper = mountDetail(original)
    await click(wrapper, '收货')
    const history = wrapper.findAll('.receipt-history-row')[0].text()
    expect(history).toContain('到货 4 · USD 6.50')
    expect(history).not.toContain('6.500000000000')
    expect(history).toContain('赠品 1 件')
    expect(wrapper.text()).toContain('已冲销')
    await click(wrapper, '验货入库')
    const trigger = wrapper.findAll('button').find(button => button.text() === '验货入库').element
    expect(wrapper.emitted('receive')[0]).toEqual([original, receiptItem, trigger])
    await click(wrapper, '冲销')
    expect(wrapper.emitted('reverse-receipt')[0]).toEqual([original, receiptItem, receipt])
    expect(receipt.unit_cost).toBe('6.500000000000')
    expect(receipt.quantity).toBe('4')
    wrapper.unmount()
  })
  it('renders header identity, exactly one close and five tabs with overview cards', () => {
    const wrapper = mountDetail()
    const header = wrapper.get('header').text()
    for (const text of ['PO-41','供应商甲','2026-10-01','2026-10-08','部分到货']) expect(header).toContain(text)
    expect(wrapper.findAll('[aria-label="关闭采购详情"]')).toHaveLength(1)
    expect(wrapper.findAll('.workbench-tabs button').map(button => button.text())).toEqual(['概览','采购明细','收货','供应商应付','关联销售订单'])
    for (const text of ['采购摘要','当前待办','到货进度','付款进度','采购成本分配','待到货','待付款']) expect(wrapper.text()).toContain(text)
    expect(wrapper.getComponent({ name: 'ContractAmountAdjustments' }).props('contract')).toEqual(purchase)
    wrapper.unmount()
  })
  it('preserves lifecycle actions and emits exact purchase objects', async () => {
    const wrapper = mountDetail({ status: 'draft' })
    for (const [label,event] of [['确认采购下单','confirm'],['编辑草稿','edit'],['删除草稿','delete'],['取消采购单','cancel']]) {
      await wrapper.findAll('header button').find(button => button.text() === label).trigger('click')
      expect(wrapper.emitted(event)[0][0].id).toBe(41)
    }
    expect(wrapper.text()).toContain('采购单待确认')
    expect(wrapper.findComponent({ name: 'ContractAmountAdjustments' }).exists()).toBe(false)
    for (const status of ['partial','completed','cancelled']) {
      await wrapper.setProps({ purchase: { ...purchase, status } })
      expect(wrapper.findAll('header button')).toHaveLength(1)
    }
    await wrapper.setProps({ purchase: { ...purchase, status: 'ordered' } })
    expect(wrapper.findAll('header button').map(button => button.text())).toEqual(['关闭','取消采购单'])
    wrapper.unmount()
  })
  it('switches todo to receipt and preserves exact receipt and reversal targets', async () => {
    const wrapper = mountDetail()
    await click(wrapper, '查看收货')
    await click(wrapper, '验货入库')
    const trigger = wrapper.findAll('button').find(button => button.text() === '验货入库').element
    expect(wrapper.emitted('receive')[0]).toEqual([purchase,item, trigger])
    expect(wrapper.text()).toContain('赠品 1 件')
    expect(wrapper.text()).toContain('已冲销')
    expect(wrapper.findAll('.receipt-history-row button')).toHaveLength(1)
    await click(wrapper, '冲销')
    expect(wrapper.emitted('reverse-receipt')[0]).toEqual([purchase,item,item.receipts[0]])
    wrapper.unmount()
  })
  it('switches payment todo and reuses payment and cost events', async () => {
    const wrapper = mountDetail()
    await click(wrapper, '分配采购成本 / 公共费用')
    expect(wrapper.emitted('allocate-cost')[0]).toEqual([purchase])
    await click(wrapper, '查看 / 登记付款')
    await click(wrapper, '登记付款')
    expect(wrapper.emitted('pay')[0]).toEqual([purchase])
    await wrapper.setProps({ purchase: { ...purchase, unpaid_amount: '0' } })
    expect(wrapper.text()).toContain('本采购单已无待付余额')
    expect(wrapper.findAll('button').some(button => button.text() === '登记付款')).toBe(false)
    wrapper.unmount()
  })
  it('keeps supplier snapshots in items and exact related order links', async () => {
    const wrapper = mountDetail()
    await click(wrapper, '采购明细')
    for (const text of ['历史供应商','MODEL-A','3000K','SKU-3','采购单价']) expect(wrapper.text()).toContain(text)
    await click(wrapper, '关联销售订单')
    expect(wrapper.get('a').attributes('href')).toBe('/orders?detail=22')
    expect(wrapper.text()).toContain('客户乙')
    wrapper.unmount()
  })
  it('keeps completed unpaid work visible and suppresses receipt tasks for terminal states', () => {
    expect(purchaseTasks({ ...purchase, status: 'completed', unpaid_amount: '0' }).map(task => task.title)).toEqual(['采购已完成'])
    expect(purchaseTasks({ ...purchase, status: 'completed' }).map(task => task.title)).toEqual(['待付款'])
    expect(purchaseTasks({ ...purchase, status: 'cancelled' }).map(task => task.title)).toEqual(['采购已取消'])
    expect(purchaseTasks({ ...purchase, items: [item,{...item,id:72}] })[0].description).toBe('还有 2 条明细未全部到货。')
  })
  it('uses calendar dates for arrival and excludes inactive statuses', () => {
    const now = new Date(2026,9,7,23,50)
    expect(purchaseArrival(purchase,now)).toEqual({kind:'future',label:'还剩 1 天'})
    expect(purchaseArrival({...purchase,expected_arrival_date:'2026-10-07'},now)).toEqual({kind:'today',label:'今日到货'})
    expect(purchaseArrival({...purchase,expected_arrival_date:'2026-10-05'},now)).toEqual({kind:'overdue',label:'逾期 2 天'})
    for (const status of ['draft','completed','cancelled']) expect(purchaseArrival({...purchase,status},now)).toBeNull()
    expect(purchaseArrival({...purchase,expected_arrival_date:null},now)).toBeNull()
  })
  it('uses base quantities for a single SKU and line counts for incompatible SKUs', () => {
    expect(receiptProgress([item])).toMatchObject({lines:false,ordered:10,received:4,remaining:6,percent:40,unit:'pcs'})
    expect(receiptProgress([item,{...item,sku:4,remaining_quantity:'0'}])).toMatchObject({lines:true,ordered:2,received:1,remaining:1,percent:50})
    expect(receiptProgress([])).toMatchObject({lines:true,ordered:0,percent:0})
  })
})


describe('purchase financial fields from scoped API responses', () => {
  it('keeps procurement visible while omitting unavailable payment information', () => {
    const wrapper = mountDetail({ paid_amount: undefined, unpaid_amount: undefined, related_orders: [] })
    expect(wrapper.text()).toContain('采购金额')
    expect(wrapper.text()).toContain('20.00')
    expect(wrapper.text()).not.toContain('已付金额')
    expect(wrapper.text()).not.toContain('未付金额')
    expect(wrapper.text()).not.toContain('付款进度')
    expect(wrapper.findAll('button').map(button => button.text())).not.toContain('付款')
    wrapper.unmount()
  })
  it('retains legitimate zero payment values and the normal payment tab', async () => {
    const wrapper = mountDetail({ paid_amount: '0', unpaid_amount: '20' })
    expect(wrapper.text()).toContain('已付金额')
    expect(wrapper.text()).toContain('付款进度')
    await click(wrapper, '供应商应付')
    expect(wrapper.text()).toContain('供应商付款')
    wrapper.unmount()
  })
})
