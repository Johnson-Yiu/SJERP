// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ProductPage from '../src/views/ProductPage.vue'

const mocks=vi.hoisted(()=>({api:{get:vi.fn(),post:vi.fn(),put:vi.fn(),patch:vi.fn()},listAll:vi.fn(),confirm:vi.fn()}))
vi.mock('../src/api',()=>({api:mocks.api,listAll:mocks.listAll,listData:r=>r.data}))
vi.mock('../src/dialogs',()=>({confirmDialog:mocks.confirm}))
vi.mock('../src/accessControl',()=>({useAccessControl:()=>({can:()=>true})}))
let wrapper,router
const categories=[{id:1,name:'根分类',parent:null,sort_order:0,child_count:1,attributes:[],effective_attributes:[]},{id:2,name:'子分类',parent:1,sort_order:0,child_count:0,attributes:[],effective_attributes:[]}]
beforeEach(()=>{vi.clearAllMocks();mocks.confirm.mockResolvedValue(false);mocks.listAll.mockResolvedValue([]);mocks.api.get.mockImplementation(async url=>({data:url.includes('next-code')?{code:'AUTO'}:categories}));vi.stubGlobal('requestAnimationFrame',fn=>fn())})
afterEach(()=>{wrapper?.unmount();vi.unstubAllGlobals()})
async function open(component,path){router=createRouter({history:createMemoryHistory(),routes:[{path:'/:pathMatch(.*)*',component:{template:'<main />'}}]});await router.push(path);wrapper=mount(component,{global:{plugins:[router],stubs:{EntityDetailModal:true}}});await flushPromises()}
function gate(){let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no});return{promise,resolve,reject}}
it.each(['success','failure'])('stale product existence probe %s cannot finish a newer load',async outcome=>{
  await open(ProductPage,'/products')
  const probe=gate(),newest=gate()
  mocks.listAll.mockImplementation((url,config)=>url==='/products/' ? (config?.params?.search==='old'?Promise.resolve([]):config?.params?.search==='new'?newest.promise:probe.promise) : Promise.resolve([]))
  wrapper.vm.query='old'; const old=wrapper.vm.load(); await flushPromises()
  wrapper.vm.query='new'; const current=wrapper.vm.load(); await flushPromises()
  if(outcome==='success')probe.resolve([{id:99}]);else probe.reject(new Error('stale failure'))
  await old;await flushPromises()
  expect(wrapper.vm.loading).toBe(true)
  expect(wrapper.vm.allProductsExist).toBe(false)
  newest.resolve([{id:2,name:'新产品',code:'NEW',status:'active'}]);await current
  expect(wrapper.vm.products[0].id).toBe(2)
  expect(wrapper.vm.allProductsExist).toBe(true)
  expect(wrapper.vm.loading).toBe(false)
})
