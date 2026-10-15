// @vitest-environment jsdom
import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import PackagingPage from '../src/views/PackagingPage.vue'
import TradeUnitsPage from '../src/views/TradeUnitsPage.vue'
const m=vi.hoisted(()=>({api:{post:vi.fn(),put:vi.fn(),patch:vi.fn()},listAll:vi.fn(),confirm:vi.fn()}))
vi.mock('../src/api',()=>({api:m.api,listAll:m.listAll}))
vi.mock('../src/dialogs',()=>({confirmDialog:m.confirm}))
vi.mock('../src/accessControl',()=>({useAccessControl:()=>({can:()=>true})}))
const template={id:1,name:'共享纸箱',active:true,linked_sku_count:2,carton_length:'50.0',carton_width:'40',carton_height:'30',carton_tare_weight:'1.5',partial_carton_policy:'SAME_CARTON'}
const skus=[{id:1,sku:'M-1',unit:'m'},{id:2,sku:'PCS-2',unit:'pcs'}]
const unit={id:1,sku:1,sku_code:'M-1',name:'10米卷',unit:'卷',factor:'10.00',base_unit:'m',supplier:null,allow_fraction:false,active:true,is_default:true,notes:'原备注'}
let wrapper,router,units
function gate(){let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no});return{promise,resolve,reject}}
beforeEach(()=>{vi.resetAllMocks();units=[unit];m.confirm.mockResolvedValue(false);m.listAll.mockImplementation(async url=>url==='/packaging-templates/'?[template]:url==='/skus/'?skus:url==='/sku-trade-units/'?units:[]);m.api.post.mockResolvedValue({data:{id:2}});m.api.put.mockResolvedValue({data:{}});m.api.patch.mockResolvedValue({data:{}})})
afterEach(()=>wrapper?.unmount())
async function open(component,path){router=createRouter({history:createMemoryHistory(),routes:[{path:'/:pathMatch(.*)*',component:{template:'<main />'}}]});await router.push(path);wrapper=mount(component,{global:{plugins:[router]}});await flushPromises()}
it('template pending POST blocks backdrop close/navigation and duplicate save; failure retains inputs for retry',async()=>{
 await open(PackagingPage,'/sku-packaging');await wrapper.vm.create();Object.assign(wrapper.vm.form,{name:'保留模板',carton_length:50,carton_width:40,carton_height:30,carton_tare_weight:1});const pending=gate();m.api.post.mockReturnValueOnce(pending.promise)
 const save=wrapper.vm.save();await flushPromises();await wrapper.find('.modal-backdrop').trigger('mousedown');await wrapper.vm.closeForm();await router.push('/products');await wrapper.vm.save();expect(router.currentRoute.value.path).toBe('/sku-packaging');expect(wrapper.vm.formOpen).toBe(true);expect(m.api.post).toHaveBeenCalledTimes(1)
 pending.reject(new Error('尺寸拒绝'));await save;expect(wrapper.vm.form.name).toBe('保留模板');expect(wrapper.find('[role=alert]').text()).toContain('尺寸拒绝');await wrapper.vm.save();expect(wrapper.vm.formOpen).toBe(false);expect(m.api.post).toHaveBeenCalledTimes(2)
})
it('linked template only confirms physical changes; cancelled confirmation sends no PUT',async()=>{
 await open(PackagingPage,'/sku-packaging');await wrapper.vm.edit(template);wrapper.vm.form.carton_length=50;wrapper.vm.form.description='只改备注';await wrapper.vm.save();expect(m.confirm).not.toHaveBeenCalled();expect(m.api.put).toHaveBeenCalledTimes(1)
 await wrapper.vm.edit(template);wrapper.vm.form.carton_length=60;await wrapper.vm.save();expect(m.confirm).toHaveBeenCalledWith(expect.objectContaining({title:'确认修改包装模板'}));expect(m.api.put).toHaveBeenCalledTimes(1);expect(wrapper.vm.formOpen).toBe(true)
 m.confirm.mockResolvedValueOnce(true);await wrapper.vm.save();expect(m.api.put).toHaveBeenCalledTimes(2)
})
it('copy is an editable unsaved draft and does not write before confirmation',async()=>{
 await open(PackagingPage,'/sku-packaging');await wrapper.vm.duplicate(template);expect(wrapper.vm.form.name).toBe('共享纸箱（副本）');expect(wrapper.vm.editingId).toBe(null);expect(m.api.post).not.toHaveBeenCalled();wrapper.vm.form.name='改名';await wrapper.vm.closeForm();expect(wrapper.vm.formOpen).toBe(true);m.confirm.mockResolvedValueOnce(true);await wrapper.vm.closeForm();expect(wrapper.vm.formOpen).toBe(false)
})
it('template initial error stays visible and retry restores URL detail and all-page linked SKU records',async()=>{
 m.listAll.mockRejectedValueOnce(new Error('加载失败'));await open(PackagingPage,'/sku-packaging?template=1&panel=linked&search=共享&state=active');expect(wrapper.vm.hasLoaded).toBe(false);expect(wrapper.vm.loadError).toContain('加载失败');await wrapper.vm.load();expect(wrapper.vm.loadError).toBe('');expect(wrapper.vm.linkedOpen).toBe(true);expect(wrapper.vm.query).toBe('共享');expect(m.listAll).toHaveBeenCalledWith('/skus/',{params:{include_inactive:1}})
})
it('unit pending create locks SKU switch/route and only posts once; failure keeps factor/notes',async()=>{
 await open(TradeUnitsPage,'/sku-trade-units?sku=1');Object.assign(wrapper.vm.form,{name:'50米卷',factor:'50',notes:'保留备注'});const pending=gate();m.api.post.mockReturnValueOnce(pending.promise);const save=wrapper.vm.create();await flushPromises();await wrapper.vm.selectSku('2');await router.push('/skus');await wrapper.vm.create();expect(wrapper.vm.selected).toBe('1');expect(router.currentRoute.value.path).toBe('/sku-trade-units');expect(m.api.post).toHaveBeenCalledTimes(1);pending.reject(new Error('保存失败'));await save;expect(wrapper.vm.form.factor).toBe('50');expect(wrapper.vm.form.notes).toBe('保留备注');await wrapper.vm.create();expect(wrapper.vm.notice).toBe('交易规格已添加');expect(wrapper.vm.form.factor).toBe('')
})
it('unit edit exposes only backend-mutable fields and PATCH omits the immutable definition',async()=>{
 await open(TradeUnitsPage,'/sku-trade-units?sku=1');await wrapper.vm.edit(unit);expect(wrapper.find('input[placeholder="例如：10 米/卷"]').attributes('disabled')).toBeDefined();wrapper.vm.form.notes='新备注';wrapper.vm.form.is_default=false;await wrapper.vm.create();expect(m.api.patch).toHaveBeenCalledWith('/sku-trade-units/1/',{notes:'新备注',is_default:false,active:true});expect(m.api.post).not.toHaveBeenCalled()
})
it('unit switching keeps dirty input when cancelled and clears it only after discarding',async()=>{
 await open(TradeUnitsPage,'/sku-trade-units?sku=1');wrapper.vm.form.name='未保存';await wrapper.vm.selectSku('2');expect(wrapper.vm.selected).toBe('1');expect(wrapper.vm.form.name).toBe('未保存');m.confirm.mockResolvedValueOnce(true);await wrapper.vm.selectSku('2');await flushPromises();expect(wrapper.vm.selected).toBe('2');expect(router.currentRoute.value.query.sku).toBe('2');expect(wrapper.vm.form.name).toBe('')
})
it('duplicate definition is advisory, and default changes stay serialized while PATCH is pending',async()=>{
 await open(TradeUnitsPage,'/sku-trade-units?sku=1');Object.assign(wrapper.vm.form,{name:unit.name,factor:unit.factor});await flushPromises();expect(wrapper.vm.duplicateDefinition).toBe(true);expect(wrapper.text()).toContain('需要时仍可继续添加');m.confirm.mockResolvedValue(true);const pending=gate();m.api.patch.mockReturnValueOnce(pending.promise);const change=wrapper.vm.change(unit,{is_default:false});await flushPromises();await wrapper.vm.change(unit,{is_default:false});expect(m.api.patch).toHaveBeenCalledTimes(1);pending.resolve({data:{}});await change;expect(wrapper.vm.saving).toBe(false)
})
