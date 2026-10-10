// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import QuoteEditorModal from '../src/components/QuoteEditorModal.vue'
import OrderDraftModal from '../src/components/OrderDraftModal.vue'
import DocumentPage from '../src/views/DocumentPage.vue'
import { changeDocumentCurrency } from '../src/utils/documentCurrency'
import { installModalNavigationGuard } from '../src/utils/modalNavigation'

const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, listAll: vi.fn(), confirmDialog: vi.fn() }))
vi.mock('../src/api', () => ({ api: mocks.api, listAll: mocks.listAll, downloadQuoteExport: vi.fn() }))
vi.mock('../src/dialogs', () => ({ confirmDialog: mocks.confirmDialog }))
const customers = [{ id: 13, name: 'R0A Buyer' }]
const skus = [{ id: 1, sku: 'USD-SKU', currency: 'USD', default_price: '10', unit: 'pcs', trade_units: [] }, { id: 2, sku: 'EUR-SKU', currency: 'EUR', default_price: '20', unit: 'pcs', trade_units: [] }]
const draft = { customer: 13, quote: 7, order_date: '2026-10-10', expected_ship_date: '2026-10-20', currency: 'USD', exchange_rate: '6.9', shipping_fee: '5', discount: '2', notes: 'Saved terms', items: [{ sku: 1, quantity: '4', unit_price: '31', trade_unit: 9, trade_quantity: '2', trade_unit_price: '62', trade_snapshot: { factor: '2', unit: 'box' } }] }
let wrapper
const global = { directives: { 'money-input': {} }, stubs: { SkuPickerPanel: true, QuoteDetailModal: true, OrderDetailModal: true, TradeUnitPicker: true } }
beforeEach(() => {
  vi.clearAllMocks()
  mocks.confirmDialog.mockResolvedValue(true)
  mocks.listAll.mockImplementation(async url => url === '/customers/' ? customers : url === '/skus/' ? skus : url === '/quotes/' ? [{ id: 7, quote_no: 'QT-7', status: 'draft', items: [] }, { id: 8, quote_no: 'QT-8', status: 'expired', items: [] }] : [])
  mocks.api.get.mockImplementation(async url => ({ data: url.endsWith('/order-draft/') ? structuredClone(draft) : {} }))
  mocks.api.post.mockImplementation(async url => ({ data: url.includes('sales-rules') ? [] : { id: 91, quote_no: 'QT-91', order_no: 'SO-91' } }))
})
afterEach(() => wrapper?.unmount())
function select(ids) { wrapper.findComponent({ name: 'SkuPickerPanel' }).vm.$emit('update:modelValue', ids) }
async function page(type, query = '') {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { template: '<main />' } }] })
  installModalNavigationGuard(router)
  await router.push(`/${type}${query}`)
  wrapper = mount(DocumentPage, { props: { type }, global: { ...global, plugins: [router] } })
  await flushPromises()
  await wrapper.findAll('button').find(b => b.text() === (type === 'orders' ? '新建订单' : '新建报价')).trigger('click')
  await flushPromises()
  return router
}
function quote(quote = null, mode = 'create') {
  wrapper = mount(QuoteEditorModal, { props: { quote, mode, customers, skus }, global })
}

it('Quote adds matching defaults and leaves foreign SKU price blank with a clear hint', async () => {
  quote(); select(['1', '2']); await flushPromises()
  expect(wrapper.findAll('[aria-label="单价"]').map(e => e.element.value)).toEqual(['10', ''])
  expect(wrapper.text()).toContain('默认售价为 EUR 20.00')
})
it('Quote currency cancellation preserves price/rate and confirmation clears old prices', async () => {
  quote(); select(['1', '2']); await flushPromises()
  await wrapper.findAll('[aria-label="单价"]')[0].setValue('39')
  mocks.confirmDialog.mockResolvedValueOnce(false)
  await wrapper.get('[aria-label="单据币种"]').setValue('EUR'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledWith(expect.objectContaining({ confirmText: '继续切换' }))
  expect(wrapper.get('[aria-label="单据币种"]').element.value).toBe('USD')
  expect(wrapper.get('[aria-label="对人民币汇率"]').element.value).toBe('7.2')
  expect(wrapper.findAll('[aria-label="单价"]')[0].element.value).toBe('39')
  await wrapper.get('[aria-label="单据币种"]').setValue('EUR'); await flushPromises()
  expect(wrapper.findAll('[aria-label="单价"]').map(e => e.element.value)).toEqual(['', '20'])
  expect(wrapper.get('[aria-label="对人民币汇率"]').element.value).toBe('')
})
it.each(['CNY', 'EUR', 'GBP'])('empty Quote changes to %s without confirmation and uses only its own rate', async currency => {
  quote(); await wrapper.get('[aria-label="单据币种"]').setValue(currency); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  expect(wrapper.get('[aria-label="对人民币汇率"]').element.value).toBe(currency === 'CNY' ? '1' : '')
})
it('new Quote defaults to 30%, historical Quote retains 100% and saved rate', () => {
  quote()
  const percent = () => wrapper.findAll('.field').find(f => f.find('label').text() === '定金比例（%）').get('input').element.value
  expect(percent()).toBe('30'); wrapper.unmount()
  quote({ id: 7, deposit_ratio: '1', currency: 'USD', exchange_rate: '6.9' }, 'revise')
  expect(percent()).toBe('100')
  expect(wrapper.get('[aria-label="对人民币汇率"]').element.value).toBe('6.9')
})
it('OrderDraft keeps inherited quote trade price and safely adds new SKU defaults', async () => {
  wrapper = mount(OrderDraftModal, { props: { draft, customers, skus }, global })
  expect(wrapper.findAll('.line-row input')[1].element.value).toBe('62')
  select(['1', '2']); await flushPromises()
  expect(wrapper.findAll('.line-row')[0].findAll('input')[1].element.value).toBe('62')
  expect(wrapper.findAll('.line-row')[1].findAll('input')[1].element.value).toBe('')
  expect(wrapper.text()).toContain('默认售价为 EUR 20.00')
})
it('Direct Order matching/mismatched defaults and cancellation protect its existing draft', async () => {
  await page('orders'); select(['1', '2']); await flushPromises()
  const prices = () => wrapper.findAll('.line-row').map(r => r.findAll('input')[1].element.value)
  expect(prices()).toEqual(['10', ''])
  expect(wrapper.text()).toContain('默认售价为 EUR 20.00')
  mocks.confirmDialog.mockResolvedValueOnce(false)
  await wrapper.get('[aria-label="单据币种"]').setValue('CNY'); await flushPromises()
  expect(prices()).toEqual(['10', ''])
  expect(wrapper.get('[aria-label="对人民币汇率"]').element.value).toBe('7.2')
  await wrapper.get('[aria-label="单据币种"]').setValue('CNY'); await flushPromises()
  expect(prices()).toEqual(['', ''])
  expect(wrapper.get('[aria-label="对人民币汇率"]').element.value).toBe('1')
})
it('Direct Order loads full API draft, keeps snapshots, locks customer and clear does not roll back', async () => {
  await page('orders')
  const source = wrapper.get('[aria-label="从报价载入（可选）"]')
  expect(source.text()).not.toContain('QT-8')
  await source.setValue('7'); await flushPromises()
  expect(mocks.api.get).toHaveBeenCalledWith('/quotes/7/order-draft/')
  const form = wrapper.vm.form
  expect(form).toMatchObject({ customer: 13, quote: 7, currency: 'USD', exchange_rate: '6.9', shipping_fee: '5', discount: '2', notes: 'Saved terms', expected_ship_date: '2026-10-20' })
  expect(form.items[0]).toMatchObject({ quantity: '2', unit_price: '62', trade_unit: 9, trade_snapshot: { factor: '2' } })
  expect(wrapper.findAll('.field').find(f => f.get('label').text() === '客户 *').get('select').element.disabled).toBe(true)
  await source.setValue(''); await flushPromises()
  expect(form.quote).toBe(''); expect(form.items[0].unit_price).toBe('62'); expect(form.notes).toBe('Saved terms')
})
it('Direct Order source overwrite cancel makes no API request or draft mutation', async () => {
  await page('orders'); select(['1']); await flushPromises()
  const before = JSON.stringify(wrapper.vm.form)
  mocks.confirmDialog.mockResolvedValueOnce(false)
  await wrapper.get('[aria-label="从报价载入（可选）"]').setValue('7'); await flushPromises()
  expect(mocks.api.get).not.toHaveBeenCalledWith('/quotes/7/order-draft/')
  expect(JSON.stringify(wrapper.vm.form)).toBe(before)
})
it('Direct Order save opens new Workbench while retaining list context', async () => {
  const router = await page('orders', '?search=UAT&status=draft&todo=delivery&customer=13&sku=1&ordering=-id&extra=keep')
  select(['1']); await flushPromises(); expect(wrapper.vm.form.customer).toBe(13)
  await wrapper.get('form.modal').trigger('submit'); await flushPromises()
  expect(router.currentRoute.value.query).toMatchObject({ detail: '91', tab: 'overview', search: 'UAT', status: 'draft', todo: 'delivery', customer: '13', sku: '1', ordering: '-id', extra: 'keep' })
})
it('Quote saved/revised event opens returned revision Workbench with filters', async () => {
  const router = await page('quotes', '?search=UAT&customer=13&status=draft')
  wrapper.findComponent(QuoteEditorModal).vm.$emit('saved', { id: 92, quote_no: 'QT-R1' }); await flushPromises()
  expect(router.currentRoute.value.query).toEqual({ search: 'UAT', customer: '13', status: 'draft', detail: '92', tab: 'overview' })
})
it('new Quote actual API save enters the returned Workbench', async () => {
  const router = await page('quotes', '?customer=13&extra=keep')
  const editor = wrapper.findComponent(QuoteEditorModal)
  editor.findComponent({ name: 'SkuPickerPanel' }).vm.$emit('update:modelValue', ['1'])
  await flushPromises()
  await editor.findAll('button').find(b => b.text() === '保存报价').trigger('click')
  await flushPromises()
  expect(mocks.api.post).toHaveBeenCalledWith('/quotes/', expect.objectContaining({ deposit_ratio: 0.3 }))
  expect(router.currentRoute.value.query).toMatchObject({ detail: '91', tab: 'overview', customer: '13', extra: 'keep' })
})
it('returnTo create context keeps its original destination after Quote save', async () => {
  const router = await page('quotes', '?create=1&customer=13&returnTo=%2Fcustomers%3Fdetail%3D13')
  wrapper.findComponent(QuoteEditorModal).vm.$emit('saved', { id: 93, quote_no: 'QT-93' }); await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe('/customers?detail=13')
})
it('currency reseeding respects trade unit factor and does not auto convert', async () => {
  const document = { currency: 'EUR', exchange_rate: '8', items: [{ sku: 1, unit_price: '999', trade_unit: 9, trade_snapshot: { factor: '2' } }] }
  await changeDocumentCurrency(document, 'USD', skus, async () => true)
  expect(document.items[0].unit_price).toBe(20)
  expect(document.exchange_rate).toBe('7.2')
})

it.each([0, null, undefined])('Quote revision preserves zero lead time and defaults only nullish values (%s)', async lead => {
  quote({ id: 7, customer: 13, lead_time_days: lead, items: [{ sku: 1, quantity: 1, unit_price: 10 }] }, 'revise')
  const days = wrapper.findAll('.field').find(f => f.find('label').text() === '交期（天）').get('input')
  expect(days.element.value).toBe(lead === 0 ? '0' : '10')
  expect(days.attributes('min')).toBe('0')
  await wrapper.get('[placeholder="例如：调整数量、价格、交期或付款条款"]').setValue('Focused zero day revision')
  await wrapper.findAll('button').find(b => b.text() === '保存报价').trigger('click'); await flushPromises()
  expect(mocks.api.post).toHaveBeenCalledWith('/quotes/7/revise/', expect.objectContaining({ lead_time_days: lead === 0 ? 0 : 10 }))
})
it('fresh Direct Order loads a quote without unnecessary confirmation', async () => {
  await page('orders')
  await wrapper.get('[aria-label="从报价载入（可选）"]').setValue('7'); await flushPromises()
  expect(mocks.confirmDialog).not.toHaveBeenCalled()
  expect(mocks.api.get).toHaveBeenCalledWith('/quotes/7/order-draft/')
})
it.each([{ order_date: '2026-09-01' }, { expected_ship_date: '2026-12-01' }, { currency: 'EUR' }, { exchange_rate: '8.25' }, { currency: 'GBP', exchange_rate: '9', expected_ship_date: '2026-11-01' }])('manual order defaults require confirmation and cancellation preserves all inputs (%j)', async changes => {
  await page('orders'); Object.assign(wrapper.vm.form, changes); await flushPromises()
  const before = JSON.stringify(wrapper.vm.form)
  mocks.confirmDialog.mockResolvedValueOnce(false)
  await wrapper.get('[aria-label="从报价载入（可选）"]').setValue('7'); await flushPromises()
  expect(mocks.confirmDialog).toHaveBeenCalledWith(expect.objectContaining({ confirmText: '载入报价' }))
  expect(mocks.api.get).not.toHaveBeenCalledWith('/quotes/7/order-draft/')
  expect(JSON.stringify(wrapper.vm.form)).toBe(before)
  await wrapper.get('[aria-label="从报价载入（可选）"]').setValue('7'); await flushPromises()
  expect(mocks.api.get).toHaveBeenCalledWith('/quotes/7/order-draft/')
  expect(wrapper.vm.form).toMatchObject({ order_date: draft.order_date, expected_ship_date: draft.expected_ship_date, currency: draft.currency, exchange_rate: draft.exchange_rate })
})
