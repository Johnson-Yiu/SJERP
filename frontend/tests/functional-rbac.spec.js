// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  listAll: vi.fn(),
}))
vi.mock('../src/api', () => ({ ...mocks, listData: response => response.data?.results || response.data || [], downloadQuoteExport: vi.fn() }))
vi.mock('../src/api.js', () => ({ ...mocks, listData: response => response.data?.results || response.data || [], downloadQuoteExport: vi.fn() }))

import App from '../src/App.vue'
import router from '../src/router.js'
import ResourcePage from '../src/views/ResourcePage.vue'
import DocumentPage from '../src/views/DocumentPage.vue'
import ImportPage from '../src/views/ImportPage.vue'
import OrganizationPage from '../src/views/OrganizationPage.vue'
import RelatedCreateModal from '../src/components/RelatedCreateModal.vue'
import { resourceConfigs } from '../src/resourceConfigs.js'
import { can, firstPermittedPath, setAccessOperator } from '../src/accessControl.js'

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
  vi.restoreAllMocks()
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

it('permission administrators can enter Organization and see its sidebar link without organization.view', async () => {
  setAccessOperator({ ...operator(), can_manage_permissions: true })
  await router.push('/organization')
  expect(router.currentRoute.value.path).toBe('/organization')
  wrapper = mount(App, { global: { plugins: [router], stubs: { AppDialogHost: true } } })
  await flush()
  expect(wrapper.find('.sidebar nav a[href="/organization"]').text()).toContain('组织与权限')
})

it('ordinary users without organization.view remain denied and are not offered Organization as a return path', async () => {
  setAccessOperator(operator())
  await router.push('/organization')
  expect(router.currentRoute.value.name).toBe('access-denied')
  expect(firstPermittedPath()).toBe('')
})

it('firstPermittedPath offers Organization as the permission administrator landing path', () => {
  setAccessOperator({ ...operator(), can_manage_permissions: true })
  expect(firstPermittedPath()).toBe('/organization')
})

it('refreshes current-operator after saving the permission matrix and updates the sidebar immediately', async () => {
  const admin = { ...operator(), can_manage_permissions: true }
  const updatedOperator = operator()
  let current = admin
  const role = { id: 7, code: 'admin', name: '管理员', description: '', default_data_scope_display: '全部数据', permissions: [] }
  const overview = {
    units: [], roles: [role], summary: { departments: 0, positions: 0, roles: 1, members: 1 },
    modules: [{ code: 'customers', name: '客户' }, { code: 'organization', name: '组织与权限' }], enforcement: true,
  }
  const actualApi = await vi.importActual('../src/api.js')
  const currentOperatorFetch = vi.spyOn(actualApi.api, 'get').mockResolvedValue({ data: updatedOperator })
  setAccessOperator(admin)
  await router.push('/organization')
  mocks.api.get.mockImplementation(async url => {
    if (url === '/session/current-operator/') return { data: current }
    if (url === '/organization/overview/') return { data: overview }
    return { data: [] }
  })
  mocks.api.post.mockImplementation(async () => {
    current = updatedOperator
    return { data: role }
  })
  wrapper = mount(App, { global: { plugins: [router], stubs: { AppDialogHost: true } } })
  await flush()
  expect(wrapper.find('.sidebar nav a[href="/organization"]').exists()).toBe(true)
  await wrapper.get('.role-header-actions .btn-primary').trigger('click')
  await flush()
  expect(mocks.api.post).toHaveBeenCalled()
  expect(currentOperatorFetch).toHaveBeenCalledWith('/session/current-operator/')
  expect(wrapper.find('.sidebar nav a[href="/organization"]').exists()).toBe(false)
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
