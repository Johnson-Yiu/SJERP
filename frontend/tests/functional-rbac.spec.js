// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  listAll: vi.fn(),
}))
vi.mock('../src/api.js', () => ({ ...mocks, listData: response => response.data?.results || response.data || [], downloadQuoteExport: vi.fn() }))

import App from '../src/App.vue'
import router from '../src/router.js'
import ResourcePage from '../src/views/ResourcePage.vue'
import DocumentPage from '../src/views/DocumentPage.vue'
import ImportPage from '../src/views/ImportPage.vue'
import RelatedCreateModal from '../src/components/RelatedCreateModal.vue'
import { resourceConfigs } from '../src/resourceConfigs.js'
import { can, setAccessOperator } from '../src/accessControl.js'

const modules = ['dashboard', 'reports', 'customers', 'contacts', 'followups', 'quotes', 'orders', 'suppliers', 'purchases', 'inventory', 'products', 'skus', 'categories', 'parameters', 'packaging', 'trade_units', 'certificates', 'hs_codes', 'finance', 'transactions', 'imports', 'organization', 'employees', 'permissions']
function operator(grants = {}) {
  const permissions = Object.fromEntries(modules.map(module => [module, { view: false, create: false, update: false, delete: false, export: false, import: false, ...(grants[module] || {}) }]))
  return { name: '只读 UAT', role: '受限员工', authenticated: true, development_superadmin: false, rbac_enforcement: true, has_all_permissions: false, can_manage_permissions: false, permissions }
}
let wrapper
const flush = () => flushPromises()

beforeEach(() => {
  setAccessOperator(operator())
  mocks.api.get.mockImplementation(async url => ({ data: url === '/session/current-operator/' ? operator() : [] }))
  mocks.listAll.mockImplementation(async url => {
    if (url === '/customers/') return [{ id: 1, name: '测试客户', code: 'C-001', status: 'customer', country: '中国', owner: 'UAT' }]
    if (url === '/quotes/') return [{ id: 1, quote_no: 'QT-001', customer_name: '测试客户', status: 'sent', status_display: '已发送', items: [], total_amount: '9.90' }]
    return []
  })
})
afterEach(async () => {
  wrapper?.unmount()
  wrapper = null
  vi.clearAllMocks()
  setAccessOperator(operator())
  await router.replace('/')
})

it('O: hides sidebar modules without view permission', async () => {
  setAccessOperator(operator({ customers: { view: true }, dashboard: { view: true } }))
  await router.replace('/customers')
  wrapper = mount(App, { global: { plugins: [router], stubs: { AppDialogHost: true } } })
  await flush()
  const links = wrapper.findAll('.sidebar nav a').map(link => link.attributes('href'))
  expect(links).toContain('/customers')
  expect(links).not.toContain('/orders')
  expect(wrapper.find('.sidebar nav').text()).not.toContain('订单管理')
})

it('P: redirects a manually opened forbidden route to the access denied page', async () => {
  setAccessOperator(operator({ customers: { view: true } }))
  await router.push('/orders')
  expect(router.currentRoute.value.name).toBe('access-denied')
  wrapper = mount(App, { global: { plugins: [router], stubs: { AppDialogHost: true } } })
  await flush()
  expect(wrapper.text()).toContain('无权访问此功能')
})

it('denies access when the current-operator permission contract is incomplete', () => {
  setAccessOperator({ name: '未识别的权限状态', permissions: { customers: { view: true } } })
  expect(can('customers', 'view')).toBe(false)
  expect(can('orders', 'view')).toBe(false)
})

it('Q: customer view-only access has no create, edit, or delete actions', async () => {
  setAccessOperator(operator({ customers: { view: true } }))
  await router.replace('/customers')
  wrapper = mount(ResourcePage, { props: { config: resourceConfigs.customers }, global: { plugins: [router], directives: { 'money-input': {} } } })
  await flush()
  expect(wrapper.find('.page-head .btn-primary').exists()).toBe(false)
  expect(wrapper.findAll('.table-actions button[title="编辑"]').length).toBe(0)
  expect(wrapper.findAll('.table-actions button[title="删除"]').length).toBe(0)
})

it('R: quote without export permission has no export action', async () => {
  setAccessOperator(operator({ quotes: { view: true } }))
  wrapper = mount(DocumentPage, { props: { type: 'quotes' }, global: { plugins: [router], stubs: { SummaryCards: true, QuoteDetailModal: true, QuoteEditorModal: true } } })
  await flush()
  expect(wrapper.find('[aria-label="导出 QT-001"]').exists()).toBe(false)
})

it('S: import viewer cannot preview or execute data imports', async () => {
  setAccessOperator(operator({ imports: { view: true } }))
  wrapper = mount(ImportPage)
  await flush()
  expect(wrapper.text()).toContain('不能预览或执行导入')
  expect(wrapper.get('.upload-btn').element.disabled).toBe(true)
  expect(wrapper.find('.execute-btn').exists()).toBe(false)
  expect(mocks.api.post).not.toHaveBeenCalled()
})

it('T: related create modal refuses a target entity without create permission', async () => {
  setAccessOperator(operator({ customers: { view: true }, quotes: { view: true } }))
  wrapper = mount(RelatedCreateModal, { props: { entity: 'quotes', query: { customer: 1 } }, global: { stubs: { Teleport: true } } })
  await flush()
  expect(wrapper.text()).toContain('无权新建此类记录')
  expect(wrapper.find('form').exists()).toBe(false)
  expect(mocks.api.post).not.toHaveBeenCalled()
})
