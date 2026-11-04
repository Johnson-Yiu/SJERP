// @vitest-environment jsdom
import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import SKUPage from '../src/views/SKUPage.vue'
const m=vi.hoisted(()=>({api:{get:vi.fn(),post:vi.fn(),put:vi.fn(),patch:vi.fn(),delete:vi.fn()},listAll:vi.fn(),confirm:vi.fn()}))
vi.mock('../src/api',()=>({api:m.api,listAll:m.listAll,listData:r=>r.data}))
vi.mock('../src/dialogs',()=>({confirmDialog:m.confirm}))
vi.mock('../src/accessControl',()=>({useAccessControl:()=>({can:()=>true})}))
const attr={id:1,category_id:1,name:'功率',key:'power',unit:'W',include_in_sku:true,include_in_sales_model:false,required:true}
const product={id:1,name:'隔离灯具',code:'F7',category:1,sales_model_prefix:'F7',combination_rules:[]}
let wrapper,router,records
function gate(){let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no});return{promise,resolve,reject}}
beforeEach(()=>{vi.clearAllMocks();records=[];m.confirm.mockResolvedValue(false);m.listAll.mockImplementation(async url=>url==='/products/'?[product]:url==='/suppliers/'?[{id:1,name:'供应商A'}]:url==='/skus/'?records:[]);m.api.get.mockImplementation(async url=>({data:url.includes('/categories/')?[{id:1,name:'照明',effective_attributes:[attr],attributes:[attr]}]:url.includes('supplier-candidate-pool')?[{id:1,name:'供应商A',code:'GA',category_match:true}]:{}}))})
afterEach(()=>wrapper?.unmount())
async function open(){router=createRouter({history:createMemoryHistory(),routes:[{path:'/:pathMatch(.*)*',component:{template:'<main />'}}]});await router.push('/skus');wrapper=mount(SKUPage,{global:{plugins:[router],stubs:{EntityDetailModal:true,Teleport:true}}});await flushPromises()}
it.each(['success','failure'])('stale supplier sources %s cannot replace current SKU context',async outcome=>{
  await open()
  const old=gate(),current=gate(),fallback=m.listAll.getMockImplementation()
  m.listAll.mockImplementation((url,config)=>url==='/supplier-skus/'?(config.params.sku===1?old.promise:current.promise):fallback(url,config))
  const row=id=>({id,product:1,unit:'pcs',currency:'USD',active:true,parameter_values:{},product_details:[]})
  await wrapper.vm.openEdit(row(1));await wrapper.vm.closeModal();await wrapper.vm.openEdit(row(2))
  if(outcome==='success')old.resolve([{id:11,supplier_name:'旧 SKU 来源'}]);else old.reject(new Error('旧 SKU 错误'))
  await flushPromises()
  expect(wrapper.vm.editingId).toBe(2)
  expect(wrapper.vm.supplierSourcesLoading).toBe(true)
  expect(wrapper.vm.supplierSources).toEqual([])
  expect(wrapper.vm.supplierSourcesError).toBe('')
  current.resolve([{id:22,supplier_name:'当前 SKU 来源'}]);await flushPromises()
  expect(wrapper.vm.supplierSources[0].id).toBe(22)
  expect(wrapper.vm.supplierSourcesLoading).toBe(false)
})
it('newest supplier source failure remains retryable in the same SKU',async()=>{
  await open();wrapper.vm.editingId=2
  m.listAll.mockRejectedValueOnce(new Error('当前来源失败'))
  await wrapper.vm.loadSupplierSources(2)
  expect(wrapper.vm.supplierSourcesError).toContain('当前来源失败')
  m.listAll.mockResolvedValueOnce([{id:22}]);await wrapper.vm.loadSupplierSources(2)
  expect(wrapper.vm.supplierSourcesError).toBe('')
  expect(wrapper.vm.supplierSources[0].id).toBe(22)
})
