// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { readFileSync } from 'node:fs'
import App from '../src/App.vue'
import ResourcePage from '../src/views/ResourcePage.vue'
import DocumentPage from '../src/views/DocumentPage.vue'
import PurchaseOrderPage from '../src/views/PurchaseOrderPage.vue'
import InventoryPage from '../src/views/InventoryPage.vue'
import { resourceConfigs } from '../src/resourceConfigs'
import { customerListStatus } from '../src/utils/customerListStatus'
import { movementSummary, movementSource } from '../src/utils/inventoryLedger'

const mocks = vi.hoisted(() => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }, listAll: vi.fn() }))
vi.mock('../src/api.js', () => ({ ...mocks, downloadQuoteExport: vi.fn(), listData: r => r.data?.results || r.data || [] }))
const statuses = ['lead', 'contact', 'opportunity', 'customer', 'company']
const customers = statuses.map((status, id) => ({ id: id + 1, name: `Customer ${id}`, status, code: `C${id}`, status_display: status === 'company' ? '已有2张及以上正式订单' : `原说明 ${id}` }))
const order = { id: 1, order_no: 'SO-001', customer_name: 'Customer', status: 'cancelled', status_display: '已取消', items: [], currency: 'USD', total_amount: 100, paid_amount: 0, balance_amount: 100, order_date: '2026-10-08', expected_ship_date: '2026-10-10' }
const quote = { ...order, quote_no: 'QT-001', status: 'sent', parent_quote: null }
const purchase = { id: 1, purchase_no: 'PO-001', status: 'ordered', status_display: '已下单', supplier_name: 'Supplier', items: [{ remaining_quantity: 2 }], total_amount: 100, unpaid_amount: 100, currency: 'USD' }
const skus = [
  { id: 1, sku: 'SKU-PCS', display_name_cn: 'Lamp', unit: 'pcs', actual_quantity: 10, available_quantity: 8, reserved_quantity: 2, in_transit_quantity: 3, to_procure_quantity: 1 },
  { id: 2, sku: 'SKU-M', display_name_cn: 'Cable', unit: 'm', actual_quantity: 20, available_quantity: 20, reserved_quantity: 0, in_transit_quantity: 0, to_procure_quantity: 0 },
]
const core = [
  ['/customers', '客户管理', ResourcePage, { config: resourceConfigs.customers }, '新建客户'],
  ['/quotes', '报价管理', DocumentPage, { type: 'quotes' }, '新建报价'],
  ['/orders', '订单管理', DocumentPage, { type: 'orders' }, '新建订单'],
  ['/purchase-orders', '采购管理', PurchaseOrderPage, {}, '新建采购单'],
  ['/inventory', '库存', InventoryPage, {}, null],
  ['/inventory-movements', '库存流水', ResourcePage, { config: resourceConfigs['inventory-movements'] }, '新建库存调整'],
]
let wrapper
async function setup(url) {
  const router = createRouter({ history: createMemoryHistory(), routes: core.map(([path, title, component, props]) => ({ path, component, props, meta: { title, eyebrow: 'Business' } })) })
  await router.push(url)
  wrapper = mount(App, { global: { plugins: [router], stubs: { AppDialogHost: true }, directives: { 'money-input': {} } } })
  await flushPromises()
  return router
}
beforeEach(() => {
  mocks.listAll.mockImplementation(async url => ({ '/customers/': customers, '/orders/': [order], '/quotes/': [quote, { ...quote, id: 2, quote_no: 'QT-001-R1', parent_quote: 1, parent_quote_no: 'QT-001' }], '/purchase-orders/': [purchase], '/skus/inventory-list/': skus, '/inventory-movements/': [{ id: 1, type: 'adjust_in', movement_no: 'IM-001', signed_quantity: 2, source_type: 'manual' }] }[url] || []))
  mocks.api.get.mockImplementation(async url => ({ data: url === '/session/current-operator/' ? { name: 'Dev', development_superadmin: true, can_manage_hs_codes: true } : [] }))
})
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks() })

it.each(core)('%s keeps topbar identity, one title and a specific action', async (path, title, component, props, action) => {
  await setup(path)
  expect(wrapper.get('.topbar h1').text()).toBe(title)
  expect(wrapper.find('.page-head h2').exists()).toBe(false)
  expect(wrapper.get('.page-head').classes()).toContain('list-intro')
  if (action) expect(wrapper.get('.page-head .btn-primary').text()).toBe(action)
  else expect(wrapper.find('.page-head .btn-primary').exists()).toBe(false)
})
it('Customer list shortens real lifecycle keys and keeps full explanations and data', async () => {
  await setup('/customers')
  const badges = wrapper.findAll('.customer-list-table .status')
  expect(badges.map(b => b.text())).toEqual(['线索', '已联系', '商机', '正式客户', '返单客户'])
  expect(badges.map(b => statuses.find(s => b.classes().includes(s)))).toEqual(statuses)
  expect(badges[4].attributes('title')).toBe('已有2张及以上正式订单')
  expect(customers.map(c => c.status)).toEqual(statuses)
  expect(customerListStatus('future', '原状态')).toBe('原状态')
})
it('Quote tree expands and collapses revisions without changing metrics', async () => {
  await setup('/quotes')
  expect(wrapper.findAll('.quote-tree-row')).toHaveLength(1)
  expect(wrapper.findAll('.quote-metrics strong').map(v => v.text())).toEqual(['1', '2', '2', '0'])
  await wrapper.get('.quote-expand').trigger('click')
  expect(wrapper.findAll('.quote-tree-row')).toHaveLength(2)
  await wrapper.get('.quote-expand').trigger('click')
  expect(wrapper.findAll('.quote-tree-row')).toHaveLength(1)
})
it('Order filters keep status/todo and other query context', async () => {
  const router = await setup('/orders?search=SO&customer=1')
  await wrapper.get('[aria-label="按订单状态筛选"]').setValue('cancelled'); await flushPromises()
  await wrapper.get('[aria-label="按订单待办筛选"]').setValue('due'); await flushPromises()
  expect(router.currentRoute.value.query).toMatchObject({ search: 'SO', customer: '1', status: 'cancelled', todo: 'due' })
})
it('Purchase filters keep their values and API parameters', async () => {
  const router = await setup('/purchase-orders?sku=2')
  await wrapper.get('[aria-label="按状态筛选"]').setValue('ordered'); await flushPromises()
  await wrapper.get('.purchase-pending-filter input').setValue(true); await flushPromises()
  expect(router.currentRoute.value.query).toMatchObject({ sku: '2', status: 'ordered', pending_receipt: '1' })
  expect(mocks.listAll).toHaveBeenCalledWith('/purchase-orders/', { params: { sku: '2', status: 'ordered', pending_receipt: '1' } })
})
it('Inventory keeps per-unit calculations with one accessible attention toggle', async () => {
  const router = await setup('/inventory?search=SKU&sort=available_quantity')
  expect(wrapper.findAll('.inventory-summary > *')).toHaveLength(5)
  expect(wrapper.get('.inventory-summary').text()).toContain('10 pcs / 20 m')
  expect(wrapper.get('.inventory-summary').text()).toContain('8 pcs / 20 m')
  expect(wrapper.findAll('.attention-card')).toHaveLength(1)
  expect(wrapper.find('.attention-toggle').exists()).toBe(false)
  await wrapper.get('.attention-card').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query).toMatchObject({ attention: '1', search: 'SKU', sort: 'available_quantity' })
  expect(wrapper.get('.attention-card').attributes('aria-pressed')).toBe('true')
  expect(wrapper.findAll('.inventory-row')).toHaveLength(1)
  await wrapper.get('.attention-card').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query.attention).toBeUndefined()
})
it('Movement type/direction/source filters preserve their original query keys', async () => {
  const router = await setup('/inventory-movements?sku=2')
  for (const [label, value] of [['按流水类型筛选', 'adjust_in'], ['按库存方向筛选', 'in'], ['按流水来源筛选', 'manual']]) {
    await wrapper.get(`[aria-label="${label}"]`).setValue(value); await flushPromises()
  }
  expect(router.currentRoute.value.query).toEqual({ sku: '2', type: 'adjust_in', direction: 'in', source: 'manual' })
})
it('Sidebar preserves every route, module and Finance order in the requested groups', async () => {
  await setup('/customers')
  const expected = {
    '经营': ['/', '/reports', '/historical-orders'], '客户': ['/customers', '/contacts', '/follow-ups'], '销售': ['/quotes', '/orders'],
    '采购与库存': ['/suppliers', '/purchase-orders', '/inventory', '/inventory-movements'],
    '产品资料': ['/products', '/skus', '/categories', '/product-parameters', '/sku-packaging', '/sku-trade-units', '/product-certificates', '/hs-codes'],
    '财务与工具': ['/finance', '/receivables', '/payables', '/transactions', '/rmb-cash-events', '/import', '/history-takeover'], '组织与系统': ['/organization'],
  }
  const actual = {}; let group
  for (const node of wrapper.findAll('.sidebar nav > *')) {
    if (node.classes().includes('nav-section')) { group = node.text(); actual[group] = [] }
    else actual[group].push(node.attributes('href'))
  }
  expect(actual).toEqual(expected)
  expect(wrapper.get('.nav-item.router-link-active').attributes('href')).toBe('/customers')
})
it('List-only CSS defines nowrap, minimum widths, desktop five cards and readable navigation', () => {
  const css = readFileSync('src/styles.css', 'utf8')
  expect(css).toMatch(/\.order-list-table th:nth-child\(1\)\s*\{ min-width: 125px/)
  expect(css).toMatch(/\.order-list-table th:nth-child\(3\), \.order-list-table th:nth-child\(4\)\s*\{ min-width: 100px/)
  expect(css).toMatch(/\.order-list-table td:not\(:nth-child\(2\)\)[^{]+\{ white-space: nowrap/)
  expect(css).toMatch(/\.customer-list-table td:not\(:first-child\)\s*\{ white-space: nowrap/)
  expect(css).toMatch(/\.core-list-page[^}]+\.status,[^{]+\{ white-space: nowrap/)
  expect(css).toMatch(/\.customer-name[^}]+-webkit-line-clamp: 2/)
  expect(css).toMatch(/\.inventory-summary[^}]+repeat\(5, minmax\(0, 1fr\)\)/)
  expect(css).toMatch(/@media \(max-width: 1200px\)[^}]+repeat\(3, minmax\(0, 1fr\)\)/)
  expect(css).toMatch(/\.nav-item[^}]+min-height: 40px/)
})
it('Focused repair separates original inventory name/unit values into two styled blocks', async () => {
  await setup('/inventory')
  const cells = wrapper.findAll('.inventory-name-cell')
  expect(cells.map(cell => cell.get('span').text())).toEqual(['Cable', 'Lamp'])
  expect(cells.map(cell => cell.get('small').text())).toEqual(['基础单位：m', '基础单位：pcs'])
  expect(wrapper.findAll('.inventory-row .primary-cell').map(cell => cell.text())).toEqual(['SKU-M', 'SKU-PCS'])
  const source = readFileSync('src/views/InventoryPage.vue', 'utf8')
  expect(source).toMatch(/\.inventory-name-cell > span\{display:block;color:inherit;line-height:1.45\}/)
  expect(source).toMatch(/\.inventory-name-cell > small\{display:block;margin-top:3px;font-size:var\(--text-caption\);color:#81908a\}/)
})
it('Focused repair styles only sidebar navigation scrollbars and preserves visible scrolling', () => {
  const css = readFileSync('src/styles.css', 'utf8')
  expect(css).toMatch(/\.sidebar nav \{ scrollbar-width: thin; scrollbar-color: rgba\(198, 222, 213, \.38\) transparent;/)
  expect(css).toMatch(/\.sidebar nav::-webkit-scrollbar \{ width: 6px;/)
  expect(css).toMatch(/\.sidebar nav::-webkit-scrollbar-track \{ background: transparent;/)
  expect(css).toMatch(/\.sidebar nav::-webkit-scrollbar-thumb \{[^}]+border-radius: 999px/)
  expect(css).toMatch(/\.sidebar nav::-webkit-scrollbar-thumb:hover \{ background: rgba\(198, 222, 213, \.58\)/)
  const scrollbarRules = [...css.matchAll(/([^{}]+)\{[^{}]*(?:scrollbar-|::-webkit-scrollbar)[^{}]*\}/g)]
  expect(scrollbarRules.length).toBeGreaterThan(0)
  expect(scrollbarRules.every(rule => rule[1].trim().startsWith('.sidebar nav'))).toBe(true)
  expect(css.replace(/\/\*[\s\S]*?\*\//g, '')).not.toMatch(/(?:^|})\s*(?:body|html|\*)[^{}]*::-webkit-scrollbar/)
})
it('Focused repair keeps movement labels/counts and uses exactly four distinct hints', () => {
  const rows = [
    { type: 'purchase_in', is_automatic: true }, { type: 'sale_out', is_automatic: true },
    { type: 'adjust_in', source_type: 'manual' }, { type: 'adjust_out', source_type: 'manual', is_reversed: true },
    { type: 'return_in', source_type: 'reversal' }, { type: 'unknown', source_type: 'manual' },
  ]
  const summary = movementSummary(rows)
  expect(summary.map(item => item.label)).toEqual(['流水记录', '入库记录', '出库记录', '冲销记录'])
  expect(summary.map(item => item.value)).toEqual([6, 3, 2, 1])
  expect(summary.map(item => item.hint)).toEqual(['当前筛选结果', '库存增加', '库存减少', '冲销生成'])
  const filtered = rows.filter(row => movementSource(row) === 'manual')
  expect(movementSummary(filtered).map(item => item.value)).toEqual([3, 1, 1, 0])
  expect(movementSummary([]).map(item => item.value)).toEqual([0, 0, 0, 0])
})
it.each(core.filter(c => c[0] !== '/inventory'))('%s has concise initial and filtered empty states', async (path, title, component, props, action) => {
  mocks.listAll.mockResolvedValue([])
  const router = await setup(path)
  expect(wrapper.get('.list-empty-state h3').text()).toMatch(/^暂无/)
  expect(wrapper.get('.list-empty-state').text()).toContain(path === '/customers' ? '添加客户资料' : action)
  const endpoint = path === '/inventory-movements' ? '/inventory-movements/' : `${path}/`
  const existing = path === '/customers' ? { id: 1, name: 'Existing Customer', code: 'C1', status: 'customer' }
    : path === '/quotes' ? { id: 1, quote_no: 'QT-1', status: 'sent', items: [] }
      : path === '/orders' ? { id: 1, order_no: 'SO-1', status: 'completed', items: [] }
        : path === '/purchase-orders' ? { id: 1, purchase_no: 'PO-1', supplier_name: 'Supplier', status: 'completed', items: [] }
          : { id: 1, movement_no: 'IM-1', type: 'adjust_in', quantity: 1, sku_code: 'SKU-1' }
  mocks.listAll.mockImplementation(async (url, config = {}) => url === endpoint && config.params?.search === 'missing' ? [] : url === endpoint ? [existing] : [])
  await router.push({ path, query: { search: 'missing' } }); await flushPromises()
  expect(wrapper.get('.list-empty-state h3').text()).toBe('没有符合当前条件的记录')
  expect(wrapper.get('.list-empty-state p').text()).toBe('请调整搜索或筛选条件。')
  expect(wrapper.get('.list-empty-clear').text()).toBe('清除筛选')
})
