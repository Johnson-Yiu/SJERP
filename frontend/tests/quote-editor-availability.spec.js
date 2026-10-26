// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'

const mocks = vi.hoisted(() => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  listAll: vi.fn(),
  availability: vi.fn(),
  salesRules: vi.fn(),
  createQuote: vi.fn(),
  reviseQuote: vi.fn(),
}))

vi.mock('../src/api.js', () => ({
  api: mocks.api,
  listAll: mocks.listAll,
  downloadQuoteExport: vi.fn(),
}))

import QuoteEditorModal from '../src/components/QuoteEditorModal.vue'

const SkuPickerStub = defineComponent({
  name: 'SkuPickerPanel',
  props: {
    skus: { type: Array, default: () => [] },
    modelValue: { type: Array, default: () => [] },
    activeId: { type: [String, Number], default: '' },
  },
  emits: ['update:modelValue', 'update:activeId'],
  setup(props, { emit }) {
    function toggle(sku) {
      const ids = new Set(props.modelValue.map(String))
      const key = String(sku.id)
      if (ids.has(key)) ids.delete(key)
      else ids.add(key)
      emit('update:modelValue', [...ids])
      emit('update:activeId', key)
    }
    return () => h('div', { 'data-testid': 'sku-picker' }, props.skus.map(sku => h('button', {
      type: 'button',
      'data-testid': `select-sku-${sku.id}`,
      onClick: () => toggle(sku),
    }, sku.sku)))
  },
})

const DateInputStub = defineComponent({
  name: 'SegmentedDateInput',
  props: { modelValue: String },
  emits: ['update:modelValue'],
  template: '<input :value="modelValue" />',
})
const QuotePreviewStub = defineComponent({ name: 'QuotePreviewModal', template: '<div data-testid="quote-preview" />' })

const customer = { id: 31, name: 'UAT Inventory Buyer', address: 'UAT Address' }
const skuA = {
  id: 11,
  sku: 'UAT-STOCK-A',
  product_name: 'UAT Stock Product A',
  display_name_cn: 'UAT Stock A',
  unit: 'pcs',
  default_price: '2.50',
  currency: 'USD',
  trade_units: [],
}
const skuB = {
  id: 12,
  sku: 'UAT-STOCK-B',
  product_name: 'UAT Stock Product B',
  display_name_cn: 'UAT Stock B',
  unit: 'm',
  default_price: '3.00',
  currency: 'USD',
  trade_units: [],
}

function metrics(sku, { actual = '100.00', reserved = '20.00', available = '80.00', inTransit = '50.00' } = {}) {
  return {
    sku,
    actual_quantity: actual,
    reserved_quantity: reserved,
    available_quantity: available,
    in_transit_quantity: inTransit,
  }
}

async function settle() {
  await flushPromises()
  await nextTick()
  await flushPromises()
}

function availabilityCalls() {
  return mocks.api.post.mock.calls.filter(([url]) => url === '/quotes/availability-preview/')
}

async function mountEditor({ mode = 'create', quote = null, skus = [skuA, skuB], customers = [customer] } = {}) {
  const wrapper = mount(QuoteEditorModal, {
    props: { mode, quote, skus, customers },
    global: {
      stubs: {
        SkuPickerPanel: SkuPickerStub,
        SegmentedDateInput: DateInputStub,
        QuotePreviewModal: QuotePreviewStub,
      },
    },
  })
  await settle()
  return wrapper
}

async function selectSku(wrapper, id) {
  await wrapper.get(`[data-testid="select-sku-${id}"]`).trigger('click')
  await settle()
}

function deferred() {
  let resolve, reject
  const promise = new Promise((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}

describe('QuoteEditorModal inventory reference', () => {
  let wrappers

  beforeEach(() => {
    wrappers = []
    vi.clearAllMocks()
    mocks.listAll.mockResolvedValue([])
    mocks.availability.mockImplementation(async ({ sku_ids }) => ({
      items: sku_ids.map(id => metrics(id)),
    }))
    mocks.salesRules.mockResolvedValue([])
    mocks.createQuote.mockResolvedValue({ id: 901, quote_no: 'QT-UAT-0901', status: 'draft' })
    mocks.reviseQuote.mockResolvedValue({ id: 902, quote_no: 'QT-UAT-0902', status: 'draft' })
    mocks.api.get.mockResolvedValue({ data: [] })
    mocks.api.post.mockImplementation(async (url, payload) => {
      if (url === '/quotes/availability-preview/') return { data: await mocks.availability(payload) }
      if (url === '/sales-rules/check-quote/') return { data: await mocks.salesRules(payload) }
      if (url === '/quotes/') return { data: await mocks.createQuote(payload) }
      if (/^\/quotes\/\d+\/revise\/$/.test(url)) return { data: await mocks.reviseQuote(payload) }
      return { data: {} }
    })
  })

  afterEach(() => wrappers.forEach(wrapper => wrapper.unmount()))

  it('prefills a new customer contact without changing the customer master', async () => {
    mocks.listAll.mockImplementation(async url => url === '/contacts/' ? [{ name: 'Primary', email: 'primary@example.com', phone: '123', is_primary: true }] : [])
    const wrapper = await mountEditor({ quote: { customer: customer.id } })
    wrappers.push(wrapper)
    expect(wrapper.get('#quote-recipient').element.value).toBe('Primary')
    expect(wrapper.get('#quote-buyer-email').element.value).toBe('primary@example.com')
    expect(wrapper.get('#quote-buyer-address').element.value).toBe(customer.address)
    await wrapper.get('#quote-buyer-email').setValue('manual@example.com')
    expect(mocks.api.put).not.toHaveBeenCalled()
    expect(mocks.api.patch).not.toHaveBeenCalled()
  })

  it('keeps explicit create-prefill values including an intentionally empty email', async () => {
    mocks.listAll.mockImplementation(async url => url === '/contacts/' ? [{ name: 'Primary', email: 'primary@example.com', phone: '123' }] : [])
    const wrapper = await mountEditor({ quote: { customer: customer.id, recipient_name: 'Manual', buyer_email: '', buyer_phone: '456', buyer_address: 'Manual Address' } })
    wrappers.push(wrapper)
    expect(wrapper.get('#quote-recipient').element.value).toBe('Manual')
    expect(wrapper.get('#quote-buyer-email').element.value).toBe('')
    expect(wrapper.get('#quote-buyer-phone').element.value).toBe('456')
    expect(wrapper.get('#quote-buyer-address').element.value).toBe('Manual Address')
  })

  it('does not let late contact lookup overwrite manual input or explicit clearing', async () => {
    const pending = deferred()
    mocks.listAll.mockImplementation(url => url === '/contacts/' ? pending.promise : Promise.resolve([]))
    const wrapper = await mountEditor()
    wrappers.push(wrapper)
    await wrapper.find('select').setValue(String(customer.id))
    await wrapper.get('#quote-recipient').setValue('Manual')
    await wrapper.get('#quote-buyer-email').setValue('temporary@example.com')
    await wrapper.get('#quote-buyer-email').setValue('')
    await wrapper.get('#quote-buyer-phone').setValue('Manual Phone')
    pending.resolve([{ name: 'Late Primary', email: 'late@example.com', phone: '999' }])
    await settle()
    expect(wrapper.get('#quote-recipient').element.value).toBe('Manual')
    expect(wrapper.get('#quote-buyer-email').element.value).toBe('')
    expect(wrapper.get('#quote-buyer-phone').element.value).toBe('Manual Phone')
  })

  it('ignores an older customer lookup after switching customer', async () => {
    const old = deferred(), latest = deferred()
    mocks.listAll.mockImplementation((url, options) => url !== '/contacts/' ? Promise.resolve([]) : options.params.customer === customer.id ? old.promise : latest.promise)
    const other = { id: 32, name: 'Other Buyer', address: 'Other Address' }
    const wrapper = await mountEditor({ customers: [customer, other] })
    wrappers.push(wrapper)
    await wrapper.find('select').setValue(String(customer.id))
    await wrapper.find('select').setValue(String(other.id))
    latest.resolve([{ name: 'Current Primary', email: 'current@example.com' }])
    await settle()
    old.resolve([{ name: 'Stale Primary', email: 'stale@example.com' }])
    await settle()
    expect(wrapper.get('#quote-recipient').element.value).toBe('Current Primary')
    expect(wrapper.get('#quote-buyer-email').element.value).toBe('current@example.com')
    expect(wrapper.get('#quote-buyer-address').element.value).toBe(other.address)
  })

  it('does not fetch stock before any SKU is selected', async () => {
    const wrapper = await mountEditor()
    wrappers.push(wrapper)

    expect(availabilityCalls()).toHaveLength(0)
    expect(wrapper.find('[aria-label="库存参考"]').exists()).toBe(false)
  })

  it('loads selected SKU inventory and shows separate actual, reserved, available, demand, and in-transit values', async () => {
    const wrapper = await mountEditor()
    wrappers.push(wrapper)
    await selectSku(wrapper, skuA.id)

    expect(availabilityCalls()).toHaveLength(1)
    expect(availabilityCalls()[0][1]).toEqual({ sku_ids: [skuA.id] })
    expect(wrapper.text()).toContain('100 pcs')
    expect(wrapper.text()).toContain('20 pcs')
    expect(wrapper.text()).toContain('80 pcs')
    expect(wrapper.text()).toContain('50 pcs')
    expect(wrapper.text()).toContain('本报价需求')
    expect(wrapper.text()).toContain('库存可覆盖')
    expect(wrapper.text()).toContain('报价不会锁定库存')
    expect(wrapper.text()).toContain('在途数量不计入当前可用量')
  })

  it('recalculates shortage locally when quantity changes without reloading inventory', async () => {
    mocks.availability.mockResolvedValue({ items: [metrics(skuA.id, { available: '80.00' })] })
    const wrapper = await mountEditor()
    wrappers.push(wrapper)
    await selectSku(wrapper, skuA.id)
    const callCount = availabilityCalls().length

    await wrapper.get('input[aria-label="数量"]').setValue('120')

    expect(wrapper.text()).toContain('本报价需求')
    expect(wrapper.text()).toContain('120 pcs')
    expect(wrapper.text()).toContain('库存不足')
    expect(wrapper.text()).toContain('缺口：40 pcs')
    expect(availabilityCalls()).toHaveLength(callCount)
  })

  it('aggregates duplicate SKU lines and detects a combined shortage', async () => {
    mocks.availability.mockResolvedValue({ items: [metrics(skuA.id, { available: '100.00' })] })
    const wrapper = await mountEditor()
    wrappers.push(wrapper)
    await selectSku(wrapper, skuA.id)
    const callCount = availabilityCalls().length

    await wrapper.get('input[aria-label="数量"]').setValue('60')
    await wrapper.get('.text-btn').trigger('click')
    const quantities = wrapper.findAll('input[aria-label="数量"]')
    await quantities[1].setValue('50')

    expect(wrapper.text()).toContain('本报价需求')
    expect(wrapper.text()).toContain('110 pcs')
    expect(wrapper.text()).toContain('缺口：10 pcs')
    expect(availabilityCalls()).toHaveLength(callCount)
  })

  it('uses baseQuantity for mixed trade-unit lines of the same SKU', async () => {
    const rollSku = {
      ...skuB,
      id: 18,
      sku: 'UAT-ROLL-METER',
      unit: 'm',
      trade_units: [{ id: 81, name: '整卷', unit: 'roll', factor: '20', base_unit: 'm', active: true, is_default: true, allow_fraction: true }],
    }
    mocks.availability.mockResolvedValue({ items: [metrics(rollSku.id, { actual: '500.00', reserved: '0.00', available: '300.00', inTransit: '0.00' })] })
    const wrapper = await mountEditor({ skus: [rollSku] })
    wrappers.push(wrapper)
    await selectSku(wrapper, rollSku.id)
    await wrapper.get('input[aria-label="数量"]').setValue('10')
    await wrapper.get('.text-btn').trigger('click')
    const units = wrapper.findAll('select[aria-label="交易单位与包装规格"]')
    await units[1].setValue('')
    const quantities = wrapper.findAll('input[aria-label="数量"]')
    await quantities[1].setValue('50')

    expect(wrapper.text()).toContain('250 m')
    expect(wrapper.text()).toContain('库存可覆盖')
    expect(availabilityCalls()).toHaveLength(1)
  })

  it('loads preselected revision SKUs once as a unique bulk request, including duplicate quote lines', async () => {
    const wrapper = await mountEditor({
      mode: 'revise',
      quote: {
        id: 44,
        customer: customer.id,
        quote_date: '2026-10-06',
        lead_time_days: 14,
        items: [
          { sku: skuA.id, quantity: '2', unit_price: '3', description: 'line one' },
          { sku: skuA.id, quantity: '3', unit_price: '3', description: 'line two' },
          { sku: skuB.id, quantity: '4', unit_price: '3', description: 'line three' },
        ],
      },
    })
    wrappers.push(wrapper)

    expect(availabilityCalls()).toHaveLength(1)
    expect(availabilityCalls()[0][1]).toEqual({ sku_ids: [skuA.id, skuB.id] })
    expect(wrapper.findAll('.quote-inventory-row')).toHaveLength(2)
    expect(wrapper.text()).toContain('当前报价交期')
  })

  it('updates the preview when a selected SKU is removed', async () => {
    const wrapper = await mountEditor()
    wrappers.push(wrapper)
    await selectSku(wrapper, skuA.id)
    await selectSku(wrapper, skuB.id)

    expect(availabilityCalls().at(-1)[1]).toEqual({ sku_ids: [skuA.id, skuB.id] })
    await selectSku(wrapper, skuA.id)

    expect(availabilityCalls().at(-1)[1]).toEqual({ sku_ids: [skuB.id] })
    expect(wrapper.findAll('.quote-inventory-row')).toHaveLength(1)
    expect(wrapper.findAll('.quote-inventory-row-head strong').map(node => node.text())).toEqual([`${skuB.sku} · ${skuB.display_name_cn}`])
  })

  it('ignores a late availability response from an older selection', async () => {
    const firstRequest = deferred()
    const secondRequest = deferred()
    mocks.availability.mockImplementation(({ sku_ids }) => sku_ids.length === 1 ? firstRequest.promise : secondRequest.promise)
    const wrapper = await mountEditor()
    wrappers.push(wrapper)

    await selectSku(wrapper, skuA.id)
    await selectSku(wrapper, skuB.id)
    secondRequest.resolve({ items: [metrics(skuA.id, { available: '70.00' }), metrics(skuB.id, { available: '20.00' })] })
    await settle()
    firstRequest.resolve({ items: [metrics(skuA.id, { available: '999.00' })] })
    await settle()

    expect(wrapper.text()).toContain('70 pcs')
    expect(wrapper.text()).toContain('20 pcs')
    expect(wrapper.text()).not.toContain('999 pcs')
  })

  it('manual refresh reloads inventory and preserves quote quantities', async () => {
    const wrapper = await mountEditor()
    wrappers.push(wrapper)
    await selectSku(wrapper, skuA.id)
    await wrapper.get('input[aria-label="数量"]').setValue('7')
    const callCount = availabilityCalls().length

    await wrapper.get('.quote-inventory-head button').trigger('click')
    await settle()

    expect(availabilityCalls()).toHaveLength(callCount + 1)
    expect(wrapper.get('input[aria-label="数量"]').element.value).toBe('7')
    expect(wrapper.text()).toContain('最近刷新')
  })

  it('renders negative availability and computes shortage without clamping stock to zero', async () => {
    mocks.availability.mockResolvedValue({ items: [metrics(skuA.id, { actual: '0.00', reserved: '2.00', available: '-2.00', inTransit: '50.00' })] })
    const wrapper = await mountEditor()
    wrappers.push(wrapper)
    await selectSku(wrapper, skuA.id)

    expect(wrapper.text()).toContain('-2 pcs')
    expect(wrapper.text()).toContain('缺口：3 pcs')
    expect(wrapper.text()).toContain('库存不足')
  })

  it('keeps inventory advisory errors non-blocking for quote save', async () => {
    mocks.availability.mockRejectedValue(new Error('inventory unavailable'))
    const wrapper = await mountEditor({ quote: { customer: customer.id } })
    wrappers.push(wrapper)
    await selectSku(wrapper, skuA.id)

    expect(wrapper.text()).toContain('库存参考暂时无法读取，可继续报价')
    expect(wrapper.get('button.btn-primary').attributes('disabled')).toBeUndefined()
    await wrapper.get('button.btn-primary').trigger('click')
    await settle()

    expect(mocks.api.post).toHaveBeenCalledWith('/quotes/', expect.objectContaining({ customer: customer.id }))
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('uses the shared inventory preview in inherited Customer quote creation', async () => {
    const wrapper = await mountEditor({ quote: { customer: customer.id } })
    wrappers.push(wrapper)

    await selectSku(wrapper, skuA.id)

    expect(wrapper.find('select').element.disabled).toBe(true)
    expect(availabilityCalls()).toHaveLength(1)
    expect(wrapper.text()).toContain('UAT-STOCK-A')
    expect(wrapper.text()).toContain('库存参考')
  })
  it('Phase 2C distinguishes revision, prioritizes items before buyer fields and preserves source and amounts', async () => {
    const source = { id:44,quote_no:'QT-44',customer:customer.id,quote_date:'2026-10-06',currency:'USD',shipping_fee:'2',discount:'1',revision_summary:'adjust price',items:[{sku:skuA.id,quantity:'2',unit_price:'3',description:'historical',sales_model_snapshot:'HIST-A'}] }
    const wrapper = await mountEditor({mode:'revise',quote:source}); wrappers.push(wrapper)
    expect(wrapper.get('h3').text()).toBe('创建报价修订版')
    expect(wrapper.get('.modal-head').text()).toContain('基于 QT-44')
    expect(wrapper.get('.modal-head').text()).toContain('原报价保留')
    const buyer=wrapper.findAll('.field').find(f=>f.text()==='收件人')
    expect(wrapper.get('.quote-line-items').element.compareDocumentPosition(buyer.element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(wrapper.get('.totals').text()).toContain('商品小计 USD 6.00')
    expect(wrapper.get('.totals strong').text()).toBe('USD 7.00')
    expect(wrapper.get('select').attributes('disabled')).toBeDefined()
    await wrapper.get('.revision-summary textarea').setValue('adjust price')
    await wrapper.get('button.btn-primary').trigger('click'); await settle()
    expect(mocks.api.post).toHaveBeenCalledWith('/quotes/44/revise/',expect.objectContaining({customer:customer.id,shipping_fee:'2',discount:'1',revision_summary:'adjust price',items:[expect.objectContaining({sku:skuA.id,quantity:'2',unit_price:'3',sales_model_snapshot:'HIST-A'})]}))
    expect(source.quote_no).toBe('QT-44'); expect(source.items[0].quantity).toBe('2')
  })

  it.each(['create','revise'])('compacts %s exchange rate without mutating source or payload meaning',async mode=>{
    const source={id:44,customer:customer.id,quote_no:'QT-44',exchange_rate:'7.200000',items:[{sku:skuA.id,quantity:'2',unit_price:'3',sales_model_snapshot:'HIST-A'}]}
    const raw=JSON.stringify(source)
    const wrapper=await mountEditor({mode,quote:source});wrappers.push(wrapper)
    const field=wrapper.findAll('.field').find(f=>f.find('label').text()==='对人民币汇率')
    expect(field.get('input').element.value).toBe('7.2')
    if(mode==='revise')await wrapper.get('.revision-summary textarea').setValue('UAT precision')
    await wrapper.findAll('button').find(b=>b.text()==='保存报价').trigger('click');await settle()
    const payload=mocks.api.post.mock.calls.find(([url])=>url===(mode==='revise'?'/quotes/44/revise/':'/quotes/'))[1]
    expect(Number(payload.exchange_rate)).toBe(Number(source.exchange_rate))
    expect(JSON.stringify(source)).toBe(raw)
  })
  it('new quote default exchange rate is compact',async()=>{
    const wrapper=await mountEditor();wrappers.push(wrapper)
    expect(wrapper.findAll('.field').find(f=>f.find('label').text()==='对人民币汇率').get('input').element.value).toBe('7.2')
  })
})
