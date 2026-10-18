// @vitest-environment jsdom
import { beforeEach, afterEach, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import OrderDetailModal from '../src/components/OrderDetailModal.vue'
import { setAccessOperator } from '../src/accessControl.js'
const mocks=vi.hoisted(()=>({get:vi.fn(),post:vi.fn()}))
vi.mock('../src/api',()=>({api:mocks}))
let w,summary,order
beforeEach(()=>{
 order={id:7,order_no:'FUP02-500',status:'completed',status_display:'已完成',currency:'USD',total_amount:'500',balance_amount:'160'}
 summary={planned_amount:'500',paid_amount:'340',balance_amount:'160',settlement:{state:'partial',label:'部分收款',overdue_amount:'160'}}
 mocks.get.mockImplementation(async url=>({data:url.includes('/workbench/')?{order:{...order},payment_summary:structuredClone(summary),items:[],payments:[],inventory:[],fulfillment_summary:{},profit_summary:null}:url.includes('/fulfillment/')?{items:[{sku:1,draftable_quantity:1,unshipped_quantity:1}],shipments:[]}:[]}))
 mocks.post.mockResolvedValue({data:{}})
})
afterEach(()=>{w?.unmount();vi.clearAllMocks()})
async function view(){
 const router=createRouter({history:createMemoryHistory(),routes:['/orders','/receivables'].map(path=>({path,component:{template:'<div />'}}))})
 await router.push('/orders?detail=7');w=mount(OrderDetailModal,{props:{id:7},global:{plugins:[router],stubs:{ContractAmountAdjustments:true,OperationLogPanel:true,ShipmentActualPacking:true}}});await flushPromises();return router
}
it('completed debt shows amounts, overdue and order-specific receivable navigation without fulfillment operations',async()=>{
 await view();expect(w.get('.current-todo-card').text()).toContain('待收 USD 160.00')
 expect(w.get('.current-todo-card a').attributes('href')).toBe('/receivables?order=7')
 expect(w.get('.payment-card').text()).toContain('部分收款');expect(w.get('.payment-card').text()).toContain('应收已逾期：USD 160.00')
 expect(w.get('.current-todo-card').text()).not.toContain('待采购');expect(w.get('.current-todo-card').text()).not.toContain('待发货')
})
it('payment refresh clears task; refund refresh restores it, fulfillment unchanged',async()=>{
 await view();summary={...summary,paid_amount:'500',balance_amount:'0',settlement:{state:'settled',label:'款项已结清',overdue_amount:'0'}}
 await w.setProps({refreshKey:1});await flushPromises();expect(w.get('.payment-card').text()).toContain('款项已结清');expect(w.get('.current-todo-card').text()).not.toContain('待收款')
 summary={...summary,paid_amount:'460',balance_amount:'40',settlement:{state:'partial',label:'部分收款',overdue_amount:'40'}}
 await w.setProps({refreshKey:2});await flushPromises();expect(w.get('.current-todo-card').text()).toContain('待收 USD 40.00');expect(w.get('.detail-badge').text()).toContain('已完成')
})
it('no financial permission hides card and receipt task even with malicious unmasked fixture',async()=>{
 setAccessOperator({rbac_enforcement:true,permissions:{orders:{view:true,update:true}}});await view()
 expect(w.find('.payment-card').exists()).toBe(false);expect(w.get('.current-todo-card').text()).not.toContain('160');expect(w.find('a[href="/receivables?order=7"]').exists()).toBe(false)
})
it('historical completed no plan is not claimed financially settled',async()=>{
 summary={paid_amount:'0',balance_amount:'0',planned_amount:'0',settlement:{state:'no_plans',label:'无有效应收计划',overdue_amount:'0'}}
 await view();expect(w.get('.payment-card').text()).toContain('应收计划待核对');expect(w.get('.payment-card').text()).not.toContain('款项已结清')
})
it('failed reload does not display stale success or financial conclusion',async()=>{
 await view();mocks.get.mockRejectedValue(new Error('读取失败'));await w.setProps({refreshKey:1});await flushPromises()
 expect(w.text()).toContain('读取失败');expect(w.find('.payment-card').exists()).toBe(false)
})

it('completion success feedback clears when the reused detail switches orders',async()=>{
 order.status='shipped';await view();order.status='completed'
 await w.findAll('button').find(b=>b.text()==='完成履约').trigger('click');await flushPromises()
 expect(w.text()).toContain('履约已完成，未收款项继续保留。')
 order.id=8;order.order_no='FUP02-NEXT';order.status='draft';await w.setProps({id:8});await flushPromises()
 expect(w.text()).toContain('FUP02-NEXT');expect(w.text()).not.toContain('履约已完成，未收款项继续保留。')
})

it.each(['no_plans','review'])('unknown %s debt requires verification without confirmed zero',async state=>{
 summary={paid_amount:'0',balance_amount:'0',planned_amount:'0',settlement:{state,label:'无有效应收计划',overdue_amount:'0'}}
 await view();expect(w.get('.current-todo-card').text()).toContain('应收计划待核对')
 expect(w.get('.current-todo-card').text()).not.toContain('当前没有待处理事项')
 expect(w.get('.payment-card').findAll('dd').at(-1).text()).toBe('待核对')
 expect(w.find('.payment-card .progress-track').exists()).toBe(false)
 expect(w.get('.current-todo-card a').attributes('href')).toBe('/receivables?order=7')
 expect(w.get('.current-todo-card').findAll('button')).toHaveLength(0)
})
