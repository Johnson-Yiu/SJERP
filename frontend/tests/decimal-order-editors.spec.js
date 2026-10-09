// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import DocumentPage from '../src/views/DocumentPage.vue'
import OrderDraftModal from '../src/components/OrderDraftModal.vue'
const mocks=vi.hoisted(()=>({api:{get:vi.fn(),post:vi.fn(),put:vi.fn()},listAll:vi.fn()}))
vi.mock('../src/api',()=>({...mocks,downloadQuoteExport:vi.fn()}))
const source={id:5,order_no:'SO-5',status:'draft',customer:12,order_date:'2026-10-09',currency:'USD',exchange_rate:'7.200000',items:[{sku:3,quantity:'2',unit_price:'3',cost_price:'1',sales_model_snapshot:'HIST'}]}
let wrapper
beforeEach(()=>{
 vi.clearAllMocks()
 mocks.listAll.mockImplementation(async url=>url==='/orders/'?[source]:url==='/customers/'?[{id:12,name:'UAT Buyer'}]:url==='/skus/'?[{id:3,unit:'pcs',trade_units:[]}]:[])
 mocks.api.put.mockResolvedValue({data:{}});mocks.api.post.mockResolvedValue({data:{id:6}})
})
afterEach(()=>wrapper?.unmount())
it('order edit compacts loaded rate without changing source or numeric PUT payload',async()=>{
 const raw=JSON.stringify(source)
 const router=createRouter({history:createMemoryHistory(),routes:[{path:'/orders',component:DocumentPage,props:{type:'orders'}}]})
 await router.push('/orders')
 wrapper=mount(DocumentPage,{props:{type:'orders'},global:{plugins:[router],directives:{'money-input':{}},stubs:{SkuPickerPanel:true}}})
 await flushPromises();await wrapper.get('[aria-label="编辑 SO-5"]').trigger('click');await flushPromises()
 const field=wrapper.findAll('.field').find(f=>f.get('label').text()==='对人民币汇率')
 expect(field.get('input').element.value).toBe('7.2')
 await wrapper.get('form.modal').trigger('submit');await flushPromises()
 const payload=mocks.api.put.mock.calls.find(([url])=>url==='/orders/5/')[1]
 expect(Number(payload.exchange_rate)).toBe(Number(source.exchange_rate))
 expect(payload.expected_ship_date).toBeNull()
 expect(JSON.stringify(source)).toBe(raw)
})
it('quote-generated OrderDraft compacts rate and retains source / numeric POST payload',async()=>{
 const draft={...source,quote:39,source_quote_no:'QT-39'}
 const raw=JSON.stringify(draft)
 wrapper=mount(OrderDraftModal,{props:{draft,customers:[{id:12,name:'UAT Buyer'}],skus:[{id:3,unit:'pcs',trade_units:[]}]},global:{directives:{'money-input':{}},stubs:{SkuPickerPanel:true}}})
 const field=wrapper.findAll('.field').find(f=>f.get('label').text()==='对人民币汇率')
 expect(field.get('input').element.value).toBe('7.2')
 await wrapper.get('form').trigger('submit');await flushPromises()
 expect(mocks.api.post).toHaveBeenCalledWith('/orders/',expect.objectContaining({quote:39,exchange_rate:'7.2'}))
 expect(Number(mocks.api.post.mock.calls[0][1].exchange_rate)).toBe(Number(draft.exchange_rate))
 expect(mocks.api.post.mock.calls[0][1].expected_ship_date).toBeNull()
 expect(JSON.stringify(draft)).toBe(raw)
})
