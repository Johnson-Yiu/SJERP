// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }, listAll: vi.fn() }))
vi.mock('../src/api', () => ({ api: mocks.api, listAll: mocks.listAll, listData: value => value?.results || value || [] }))
import ResourcePage from '../src/views/ResourcePage.vue'
import OrderDraftModal from '../src/components/OrderDraftModal.vue'
import { resourceConfigs } from '../src/resourceConfigs'
let wrapper
const customer = { id: 12, name: 'UAT Customer', code: 'C12', country: 'Singapore', region: 'APAC', owner: 'Johnson', source: 'Website', website: 'https://example.invalid', address: 'UAT', notes: 'original' }
const followup = { id: 8, customer: 12, contact: 9, followed_at: '2026-10-09T10:30:00+08:00', type: 'Email', subject: 'UAT followup', content: '<p>content</p>', result: 'reply', next_action: 'quote', next_follow_up_mode: 'set', next_follow_up: '2026-10-11', owner: 'Johnson', attachments: [] }
beforeEach(() => {
 vi.clearAllMocks()
 mocks.listAll.mockImplementation(async url => url === '/customers/' ? [customer] : url === '/contacts/' ? [{ id: 9, customer: 12, name: 'UAT Contact' }, { id: 10, customer: 99, name: 'Other Contact' }] : url === '/follow-ups/' ? [followup] : [])
 mocks.api.get.mockImplementation(async url => ({ data: url === '/customers/next-code/' ? { code: 'C13' } : { name: 'Johnson' } }))
 mocks.api.post.mockResolvedValue({ data: { id: 13 } })
 mocks.api.put.mockResolvedValue({ data: { id: 8 } })
})
afterEach(() => wrapper?.unmount())
async function resource(entity, query = '') {
 const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:entity', component: { template: '<div />' } }] })
 await router.push('/' + entity + query)
 wrapper = mount(ResourcePage, { props: { config: resourceConfigs[entity] }, global: { plugins: [router], stubs: { EntityDetailModal: true } } })
 await flushPromises()
}
async function button(text) { await wrapper.findAll('button').find(b => b.text() === text).trigger('click'); await flushPromises() }
function field(label) { return wrapper.findAll('.modal .field').find(f => f.get('label').text().replace(/\s*\*$/, '') === label) }
it('Customer create prioritizes name and required contacts, preserves exact payload and blocks duplicate submit', async () => {
 await resource('customers'); await button('新建客户')
 expect(wrapper.get('.modal h3').text()).toBe('新建客户')
 expect(wrapper.findAll('.modal-body > .form-grid').at(0).findAll('.field label').map(l => l.text())).toEqual(['客户名称 *','客户编号 *','国家/地区','业务区域','负责人','客户来源'])
 expect(wrapper.get('.contact-create-section').element.compareDocumentPosition(wrapper.get('.optional-heading').element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
 expect(field('客户名称').get('input').attributes('required')).toBeDefined()
 expect(wrapper.get('.contact-fields input').attributes('required')).toBeDefined()
 await field('客户名称').get('input').setValue('Created Customer')
 await wrapper.get('.contact-fields input').setValue('Created Contact')
 let resolveSave
 mocks.api.post.mockImplementationOnce(() => new Promise(resolve => { resolveSave = resolve }))
 await wrapper.get('form.modal').trigger('submit'); await wrapper.get('form.modal').trigger('submit')
 expect(mocks.api.post).toHaveBeenCalledTimes(1)
 expect(wrapper.get('.modal-foot .btn-primary').text()).toBe('保存中…')
 expect(mocks.api.post).toHaveBeenCalledWith('/customers/', { name: 'Created Customer', code: 'C13', country: '', region: '', owner: 'Johnson', source: '', website: '', address: '', notes: '', contacts: [{name:'Created Contact',title:'',email:'',phone:'',whatsapp:'',notes:'',is_primary:true}] })
 resolveSave({ data: { id: 13 } }); await flushPromises()
})
it('Customer edit has a dedicated identity and preserves all fields without create contacts', async () => {
 await resource('customers'); await wrapper.get('tbody [title="编辑"]').trigger('click'); await flushPromises()
 expect(wrapper.get('.modal h3').text()).toBe('编辑客户')
 expect(wrapper.find('.contact-create-section').exists()).toBe(false)
 await wrapper.get('form.modal').trigger('submit'); await flushPromises()
 const {id, ...payload} = customer
 expect(mocks.api.put).toHaveBeenCalledWith('/customers/12/', payload)
})
it('Followup edit keeps customer contact filtering, rich text, dates, attachment input and exact payload', async () => {
 await resource('follow-ups'); await wrapper.get('tbody [title="编辑"]').trigger('click'); await flushPromises()
 expect(wrapper.get('.modal h3').text()).toBe('编辑跟进记录')
 expect(field('联系人').findAll('option').map(o => o.text())).toEqual(['请选择','UAT Contact'])
 expect(wrapper.get('.follow-up-attachment-picker input').attributes('multiple')).toBeDefined()
 expect(field('跟进方式').text()).toContain('*')
 await wrapper.get('form.modal').trigger('submit'); await flushPromises()
 expect(mocks.api.put).toHaveBeenCalledWith('/follow-ups/8/', { customer:12,contact:9,followed_at:'2026-10-09T10:30:00+08:00',type:'Email',subject:'UAT followup',content:'<p>content</p>',result:'reply',next_action:'quote',next_follow_up_mode:'set',next_follow_up:'2026-10-11',owner:'Johnson' })
})
it('Quote-generated Order draft retains source, snapshots, totals and trade-unit save payload', async () => {
 const draft = { quote:39, source_quote_no:'QT-39', customer:12, order_date:'2026-10-09', currency:'USD', exchange_rate:'7.2', shipping_fee:'2', discount:'1', status:'draft', items:[{sku:3,quantity:'10',unit_price:'2',trade_unit:7,trade_quantity:'2',trade_unit_price:'10',trade_snapshot:{base_unit:'pcs',factor:'5',trade_unit:'box'},sales_model_snapshot:'Historical Model'}] }
 wrapper=mount(OrderDraftModal,{props:{draft,customers:[customer],skus:[{id:3,unit:'pcs',trade_units:[]}]},global:{directives:{'money-input':{}},stubs:{SkuPickerPanel:true}}})
 expect(wrapper.get('h3').text()).toBe('新建订单')
 expect(wrapper.get('.modal-head').text()).toContain('来源报价：QT-39')
 expect(wrapper.get('.totals').text()).toContain('商品小计 USD 20.00')
 expect(wrapper.get('.totals strong').text()).toBe('USD 21.00')
 await wrapper.get('form').trigger('submit'); await flushPromises()
 const payload=mocks.api.post.mock.calls.find(([url])=>url==='/orders/')[1]
 expect(payload).toMatchObject({quote:39,customer:12,shipping_fee:'2',discount:'1',items:[{sku:3,trade_unit:7,trade_quantity:2,trade_unit_price:10,sales_model_snapshot:'Historical Model'}]})
 expect(payload).not.toHaveProperty('status'); expect(payload).not.toHaveProperty('order_no')
 expect(draft.items[0].trade_snapshot.base_unit).toBe('pcs')
})
