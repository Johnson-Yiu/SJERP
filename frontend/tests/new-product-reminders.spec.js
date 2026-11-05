import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { beforeEach, describe, it, expect, vi } from 'vitest'
import Reminders from '../src/components/NewProductReminders.vue'
import { api } from '../src/api'
vi.mock('../src/api', () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }))
const record = { id: 7, customer: 2, customer_name: '合成客户', requirement: '壁灯', specification: 'IP65', other_requirements: '', version: 1, created_by: '开发超级管理员（非实名员工）', created_at: '2026-11-05', voided_at: null }
async function render(query = '') {
  const router = createRouter({history:createMemoryHistory(),routes:[{path:'/:pathMatch(.*)*',component:Reminders}]})
  await router.push('/new-product-reminders'+query)
  const wrapper = mount(Reminders,{global:{plugins:[router]}})
  await flushPromises()
  return {wrapper,router}
}
beforeEach(() => {
  vi.clearAllMocks()
  api.get.mockImplementation(async (url) => ({data:url.endsWith('history/') ? [] : url === '/customers/' ? {results:[{id:2,name:'合成客户'}]} : url === '/new-product-reminders/7/' ? {...record} : {results:[{...record}],count:51}}))
})
describe('new product requirements', () => {
  it('submits free text without optional links and reuses its request key after failure', async () => {
    const {wrapper} = await render()
    await wrapper.findAll('button').find(b=>b.text()==='记录新品需求').trigger('click'); await flushPromises()
    const editor = wrapper.find('.editor')
    await editor.find('select').setValue('2')
    await editor.find('textarea').setValue('未建档产品')
    api.post.mockRejectedValueOnce(new Error('暂时失败')).mockResolvedValueOnce({data:{...record,requirement:'未建档产品'}})
    await editor.find('form').trigger('submit'); await flushPromises()
    const key=api.post.mock.calls[0][1].request_key
    await editor.find('form').trigger('submit'); await flushPromises()
    expect(api.post.mock.calls[1][1]).toMatchObject({customer:2,requirement:'未建档产品',contact:null,product:null,request_key:key})
    expect(wrapper.text()).toContain('已保存')
    wrapper.unmount()
  })
  it('sends keyword state and page through the existing query API', async () => {
    const {wrapper,router} = await render('?search=IP65&state=all&page=2')
    expect(api.get).toHaveBeenCalledWith('/new-product-reminders/',{params:expect.objectContaining({tag:'新品提醒',search:'IP65',state:'all',page:2})})
    await wrapper.find('.filters input').setValue('IP67')
    await wrapper.find('.filters').trigger('submit'); await flushPromises()
    expect(router.currentRoute.value.query.page).toBe('1')
    wrapper.unmount()
  })
  it('cancels void without a write then requires a reason and sends the loaded version', async () => {
    const {wrapper} = await render('?detail=7')
    await wrapper.findAll('button').find(b=>b.text()==='作废').trigger('click')
    await wrapper.findAll('button').find(b=>b.text()==='取消作废').trigger('click')
    expect(api.post).not.toHaveBeenCalled()
    await wrapper.findAll('button').find(b=>b.text()==='作废').trigger('click')
    const form=wrapper.find('.editor form')
    expect(form.find('button').attributes('disabled')).toBeDefined()
    await form.find('textarea').setValue('用途调整')
    api.post.mockResolvedValue({data:{...record,version:2,voided_at:'2026-11-05',void_reason:'用途调整'}})
    await form.trigger('submit'); await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/new-product-reminders/7/void/',{reason:'用途调整',version:1})
    expect(wrapper.find('.editor .voided').text()).toContain('已作废')
    expect(wrapper.findAll('button').some(b=>b.text()==='修改需求')).toBe(false)
    wrapper.unmount()
  })
  it('clears the previous detail when a new query removes record positioning', async () => {
    const {wrapper} = await render('?detail=7&state=all')
    expect(wrapper.find('.editor').exists()).toBe(true)
    await wrapper.find('.filters input').setValue('new query')
    await wrapper.find('.filters').trigger('submit'); await flushPromises()
    expect(wrapper.find('.editor').exists()).toBe(false)
    wrapper.unmount()
  })
  it('keeps a failed edit visible and sends the version for conflict checking', async () => {
    const {wrapper} = await render('?detail=7')
    await wrapper.findAll('button').find(b=>b.text()==='修改需求').trigger('click')
    await wrapper.find('.editor textarea').setValue('新要求')
    api.patch.mockRejectedValue(new Error('记录已变更，请重新打开后再操作。'))
    await wrapper.find('.editor form').trigger('submit'); await flushPromises()
    expect(api.patch).toHaveBeenCalledWith('/new-product-reminders/7/',expect.objectContaining({version:1,requirement:'新要求'}))
    expect(wrapper.find('[role=alert]').text()).toContain('记录已变更')
    expect(wrapper.find('.editor textarea').element.value).toBe('新要求')
    wrapper.unmount()
  })
})
