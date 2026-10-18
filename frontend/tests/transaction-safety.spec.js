// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import TransactionPage from '../src/views/TransactionPage.vue'
import { dialogState, resolveDialog } from '../src/dialogs'

const mocks = vi.hoisted(() => ({ post: vi.fn(), listAll: vi.fn() }))
vi.mock('../src/api', () => ({ api: { post: mocks.post }, listAll: mocks.listAll }))
let wrapper, router
const button = name => wrapper.findAll('button').find(b => b.text() === name)
const dialog = () => wrapper.get('form.dialog')
async function open() { await button('新增记账').trigger('click'); await flushPromises() }
async function submit() { await dialog().trigger('submit'); await flushPromises() }
async function fill() {
  await dialog().find('select').setValue('customer_receipt')
  await dialog().get('input[placeholder="客户或订单号"]').setValue('SO-FUP')
  await flushPromises()
  await dialog().get('button.order').trigger('click')
  await dialog().find('input[type="number"]').setValue('12.34')
  await dialog().findAll('input[type="number"]')[1].setValue('7.123456')
  await dialog().findAll('fieldset').at(-1).findAll('input').at(-1).setValue('保留备注')
}
beforeEach(async () => {
  vi.clearAllMocks()
  mocks.post.mockResolvedValue({ data: {} })
  mocks.listAll.mockImplementation(async url => url === '/orders/' ? [{ id: 7, order_no: 'SO-FUP', customer_name: '合成客户', currency: 'USD', exchange_rate: '7.1', status: 'confirmed', total_amount: '500' }] : [])
  router = createRouter({ history: createMemoryHistory(), routes: ['/transactions', '/orders'].map(path => ({ path, component: { template: '<div />' } })) })
  await router.push('/transactions')
  wrapper = mount(TransactionPage, { global: { plugins: [router], directives: { 'money-input': {} } } })
  await flushPromises()
})
afterEach(async () => { if (dialogState.current) { resolveDialog(false); await flushPromises() }; wrapper?.unmount() })

describe('FUP-01 transaction editor protection', () => {
  it('A: blank initialized form cancels without confirmation', async () => {
    await open(); await dialog().find('footer button').trigger('click'); await flushPromises()
    expect(wrapper.find('form.dialog').exists()).toBe(false)
    expect(dialogState.current).toBeNull()
  })
  it.each(['cancel', 'close', 'mask', 'route'])('B: dirty %s requires confirmation, cancellation preserves all fields', async entry => {
    await open(); await fill()
    let navigation
    if (entry === 'route') navigation = router.push('/orders')
    else if (entry === 'mask') await wrapper.get('.mask').trigger('click')
    else await dialog().get(entry === 'close' ? 'button[aria-label="关闭"]' : 'footer button').trigger('click')
    await flushPromises()
    expect(dialogState.current.title).toBe('未保存修改')
    resolveDialog(false); await flushPromises(); await navigation
    expect(router.currentRoute.value.path).toBe('/transactions')
    expect(dialog().find('input[type="number"]').element.value).toBe('12.34')
    expect(dialog().text()).toContain('SO-FUP')
    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true)
  })
  it('C: submitting blocks close, mask, new form, route and browser unload', async () => {
    await open(); await fill()
    let reject
    mocks.post.mockImplementationOnce(() => new Promise((_, no) => { reject = no }))
    await dialog().trigger('submit'); await dialog().trigger('submit')
    await wrapper.get('.mask').trigger('click'); await button('新增记账').trigger('click')
    await router.push('/orders')
    expect(mocks.post).toHaveBeenCalledTimes(1)
    expect(dialog().get('button[aria-label="关闭"]').attributes('disabled')).toBeDefined()
    expect(dialog().get('footer button').attributes('disabled')).toBeDefined()
    expect(dialog().get('fieldset').attributes('disabled')).toBeDefined()
    expect(dialogState.current).toBeNull()
    expect(router.currentRoute.value.path).toBe('/transactions')
    const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true)
    reject({ response: { status: 400, data: { detail: '未写入，金额无效' } } }); await flushPromises()
  })
  it('D/I: definite rejection keeps identity, relations and error; corrected retry succeeds and next form gets new identity', async () => {
    await open(); await fill()
    mocks.post.mockRejectedValueOnce({ response: { status: 400, data: { detail: '未写入，金额无效' } } })
    await submit()
    const payload = mocks.post.mock.calls[0][1]
    expect(payload).toMatchObject({ order: 7, currency: 'USD', amount: 12.34, exchange_rate: 7.123456, notes: '保留备注' })
    expect(dialog().text()).toContain('未写入，金额无效')
    expect(dialog().text()).not.toContain('记账结果尚未确认')
    await dialog().get('button[aria-label="关闭"]').trigger('click'); await flushPromises(); resolveDialog(false); await flushPromises()
    expect(dialog().text()).toContain('未写入，金额无效')
    await dialog().find('input[type="number"]').setValue('20'); await submit()
    expect(mocks.post.mock.calls[1][1]).toMatchObject({ ...payload, amount: 20 })
    expect(wrapper.find('form.dialog').exists()).toBe(false)
    const unload = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(unload); expect(unload.defaultPrevented).toBe(false)
    await open(); await dialog().find('input[type="number"]').setValue('20'); await submit()
    expect(mocks.post.mock.calls[2][1].transaction_no).not.toBe(payload.transaction_no)
  })
  it.each(['close', 'route'])('E/F/G/H: lost response and duplicate rejection remain unknown; %s warns with original number', async entry => {
    await open(); await fill()
    mocks.post.mockRejectedValueOnce(new Error('connection dropped after commit'))
    await submit()
    const payload = mocks.post.mock.calls[0][1]
    expect(dialog().text()).toContain('记账结果尚未确认')
    mocks.post.mockRejectedValueOnce({ response: { status: 400, data: { transaction_no: ['already exists'] } } })
    await submit()
    expect(mocks.post.mock.calls[1][1]).toEqual(payload)
    expect(dialog().text()).toContain('编号重复不代表本次保存成功')
    let navigation
    if (entry === 'route') navigation = router.push('/orders')
    else await dialog().get('button[aria-label="关闭"]').trigger('click')
    await flushPromises()
    expect(dialogState.current.title).toBe('记账结果尚未确认')
    expect(dialogState.current.message).toContain(payload.transaction_no)
    expect(dialogState.current.message).toContain('重新新建可能重复记账')
    resolveDialog(false); await flushPromises(); await navigation
    expect(dialog().get('input[readonly]').element.value).toBe(payload.transaction_no)
    expect(dialog().find('input[type="number"]').element.value).toBe('12.34')
    expect(dialog().text()).toContain('编号重复不代表本次保存成功')
    await button('新增记账').trigger('click')
    expect(dialog().get('input[readonly]').element.value).toBe(payload.transaction_no)
  })
  it('explicit abandonment of an ambiguous request needs the risk acknowledgement', async () => {
    await open(); await fill(); mocks.post.mockRejectedValueOnce({ response: { status: 503, data: { detail: '连接中断' } } }); await submit()
    await dialog().get('footer button').trigger('click'); await flushPromises()
    expect(dialogState.current.confirmText).toBe('已记录编号，放弃表单')
    resolveDialog(true); await flushPromises()
    expect(wrapper.find('form.dialog').exists()).toBe(false)
    expect(mocks.post).toHaveBeenCalledTimes(1)
  })
})
