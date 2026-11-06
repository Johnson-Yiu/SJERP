// @vitest-environment jsdom
import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const mock = vi.hoisted(() => ({ post: vi.fn(), list: vi.fn() }))
vi.mock('../src/api', () => ({ api: { post: mock.post }, listAll: mock.list }))
import PartyReplacementForm from '../src/components/PartyReplacementForm.vue'

const label = (wrapper, text) => wrapper.findAll('label').find(item => item.text().startsWith(text))
const button = (wrapper, text) => wrapper.findAll('button').find(item => item.text() === text)
beforeEach(() => { mock.post.mockReset().mockResolvedValue({ data: { result_quote_id: 9 } }); mock.list.mockReset() })

it('uses scoped customer results and requires explicit proposed values', async () => {
  mock.list.mockResolvedValue([{ id: 1, name: '原客户', code: 'OLD' }, { id: 2, name: '合成目标', code: 'SYN' }])
  const wrapper = mount(PartyReplacementForm, { props: { kind: 'quote', mode: 'propose', sourceId: 7, sourcePartyId: 1, baseline: { fingerprint: 'base' } } })
  await flushPromises()
  expect(mock.list).toHaveBeenCalledWith('/customers/', {})
  expect(wrapper.text()).not.toContain('原客户 · OLD')
  await label(wrapper, '目标客户').get('select').setValue('2')
  await button(wrapper, '提交替换申请').trigger('click')
  expect(mock.post).not.toHaveBeenCalled()
  for (const item of wrapper.findAll('button').filter(item => item.text() === '确认留空')) await item.trigger('click')
  await label(wrapper, '原因').get('textarea').setValue('合成原因')
  await label(wrapper, '依据').get('textarea').setValue('合成依据')
  await button(wrapper, '提交替换申请').trigger('click'); await flushPromises()
  expect(mock.post).toHaveBeenCalledWith('/quotes/7/party-change/', expect.objectContaining({ replacement_target_id: 2, change_type: 'replacement', proposed_snapshot: expect.objectContaining({ name: '合成目标', tax_id: '' }) }))
})

it('submits only explicit new quote facts and approved party', async () => {
  mock.list.mockResolvedValue([{ id: 3, sku: 'SYN-SKU', active: true }])
  const request = { id: 5, replacement_target: { customer_id: 2, name: '合成目标' }, proposed_snapshot: { contact: '', address: '', phone: '', email: '', tax_id: '0001' } }
  const wrapper = mount(PartyReplacementForm, { props: { kind: 'quote', mode: 'create', sourceId: 7, request } })
  await flushPromises()
  await button(wrapper, '创建关联草稿').trigger('click')
  expect(mock.post).not.toHaveBeenCalled()
  for (const [name, value] of [['单据日期','2026-11-05'], ['币种','USD'], ['汇率','7.2'], ['运费','0'], ['折扣','0'], ['定金比例','0.3'], ['数量','2'], ['单价','4']]) await label(wrapper, name).get('input').setValue(value)
  await label(wrapper, 'SKU').get('select').setValue('3')
  await wrapper.get('input[type="checkbox"]').setValue(true)
  await button(wrapper, '创建关联草稿').trigger('click'); await flushPromises()
  expect(mock.post).toHaveBeenCalledWith('/quotes/7/party-change/5/create-replacement/', expect.objectContaining({ customer: 2, buyer_tax_id: '0001', items: [{ sku: 3, quantity: '2', unit_price: '4' }] }))
  expect(mock.post.mock.calls[0][1]).not.toHaveProperty('parent_quote')
})

it('starts replacement structured facts as unknown rather than copying the source', async () => {
  mock.list.mockResolvedValue([{ id: 2, name: '合成目标', code: 'SYN' }])
  const keys = ['name', 'country', 'address', 'tax_id', 'contact', 'phone', 'email', 'billing_address', 'shipping_address', 'recipient']
  const side = Object.fromEntries(keys.map(key => [key, null]))
  const baseline = { fingerprint: 'base', snapshot: { party_details: { schema: 'party-document-details-v1', buyer: { ...side, name: '旧主体', address: '不能复制的旧地址' }, seller: { ...side } } } }
  const wrapper = mount(PartyReplacementForm, { props: { kind: 'order', mode: 'propose', sourceId: 7, baseline } })
  await flushPromises()
  await label(wrapper, '目标客户').get('select').setValue('2')
  for (const item of wrapper.findAll('label').filter(item => item.text().startsWith('拟议')).flatMap(item => item.findAll('button')).filter(item => item.text() === '确认留空')) await item.trigger('click')
  await label(wrapper, '原因').get('textarea').setValue('合成原因')
  await label(wrapper, '依据').get('textarea').setValue('合成依据')
  await button(wrapper, '提交替换申请').trigger('click')
  expect(mock.post).not.toHaveBeenCalled()
  await wrapper.get('input[type="checkbox"]').setValue(true)
  await button(wrapper, '提交替换申请').trigger('click'); await flushPromises()
  expect(mock.post.mock.calls[0][1].proposed_snapshot.party_details.buyer).toMatchObject({ name: '合成目标', address: null })
  expect(JSON.stringify(mock.post.mock.calls[0][1])).not.toContain('不能复制的旧地址')
})
