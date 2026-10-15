// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ProductPage from '../src/views/ProductPage.vue'
import CategoryPage from '../src/views/CategoryPage.vue'

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
for(const [component,path] of [[ProductPage,'/products'],[CategoryPage,'/categories']])it(`${path} blocks saving close/navigation and retains rejected fields`,async()=>{
  await open(component,path)
  const category=path==='/categories'
  if(category)wrapper.vm.openCategory();else await wrapper.vm.openCreate()
  await flushPromises()
  if(category)wrapper.vm.categoryForm.name='输入保留';else {wrapper.vm.form.name='输入保留';wrapper.vm.form.sales_model_prefix='TEST'}
  const pending=gate();mocks.api.post.mockReturnValue(pending.promise)
  const operation=category?wrapper.vm.saveCategory():wrapper.vm.save()
  await flushPromises()
  await wrapper.get('.modal-backdrop').trigger('mousedown')
  await router.push('/other')
  expect(router.currentRoute.value.path).toBe(path)
  expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
  expect(mocks.confirm).not.toHaveBeenCalled()
  if(category)void wrapper.vm.saveCategory();else void wrapper.vm.save()
  expect(mocks.api.post).toHaveBeenCalledTimes(1)
  pending.reject(new Error('可重试错误'));await operation;await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('可重试错误')
  expect(category?wrapper.vm.categoryForm.name:wrapper.vm.form.name).toBe('输入保留')
  expect(wrapper.vm.saving).toBe(false)
})
it('category depth remains based on full tree after collapse/search',async()=>{await open(CategoryPage,'/categories');expect(wrapper.vm.maxDepth).toBe(2);wrapper.vm.expandAll(false);expect(wrapper.vm.flatTree).toHaveLength(1);expect(wrapper.vm.maxDepth).toBe(2);wrapper.vm.search='子';expect(wrapper.vm.flatTree).toHaveLength(1);expect(wrapper.vm.maxDepth).toBe(2)})
it('first category load failure is not described as a successful prior load',async()=>{mocks.api.get.mockRejectedValue(new Error('首次失败'));await open(CategoryPage,'/categories');expect(wrapper.vm.hasLoaded).toBe(false);expect(wrapper.get('[role="alert"]').text()).toContain('数据加载失败');expect(wrapper.get('[role="alert"]').text()).not.toContain('上一次')})
it('opening and cancelling a category form does not clear an attribute draft baseline',async()=>{
  await open(CategoryPage,'/categories');await wrapper.vm.startAttribute();wrapper.vm.newAttribute.name='保留属性草稿'
  wrapper.vm.openCategory();await flushPromises();await wrapper.vm.closeCategory();await flushPromises()
  expect(wrapper.vm.categoryModal).toBe(false);expect(wrapper.vm.addingAttribute).toBe(true)
  await wrapper.vm.selectCategory(2);expect(wrapper.vm.selectedId).toBe(1);expect(mocks.confirm).toHaveBeenCalledTimes(1)
  expect(wrapper.vm.newAttribute.name).toBe('保留属性草稿')
})
