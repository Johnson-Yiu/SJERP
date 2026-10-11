import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import ResourcePage from './views/ResourcePage.vue'
import DocumentPage from './views/DocumentPage.vue'
import ImportPage from './views/ImportPage.vue'
import OrganizationPage from './views/OrganizationPage.vue'
import CategoryPage from './views/CategoryPage.vue'
import ProductPage from './views/ProductPage.vue'
import SKUPage from './views/SKUPage.vue'
import InventoryPage from './views/InventoryPage.vue'
import PurchaseOrderPage from './views/PurchaseOrderPage.vue'
import FinanceDashboardPage from './views/FinanceDashboardPage.vue'
import PaymentPlanPage from './views/PaymentPlanPage.vue'
import TransactionPage from './views/TransactionPage.vue'
import PackagingPage from './views/PackagingPage.vue'
import HSCodePage from './views/HSCodePage.vue'
import { resourceConfigs } from './resourceConfigs'
import { installModalNavigationGuard } from './utils/modalNavigation'
import AccessDeniedPage from './views/AccessDeniedPage.vue'
import { can, loadAccessControl } from './accessControl'

const resourceModules = {
  suppliers: 'suppliers', customers: 'customers', contacts: 'contacts', 'follow-ups': 'followups',
  'inventory-movements': 'inventory', 'product-parameters': 'parameters', 'product-certificates': 'certificates',
}

export const routes = [
  { path: '/sku-trade-units', component: () => import('./views/TradeUnitsPage.vue'), meta: { title: 'SKU 交易单位', eyebrow: 'Transaction units', module: 'trade_units' } },
  { path: '/reports', component: () => import('./views/ReportsPage.vue'), meta: { title: '报表中心', eyebrow: 'Reports & analytics', module: 'reports' } },
  { path: '/', component: Dashboard, meta: { title: '经营概览', eyebrow: 'Business overview', module: 'dashboard' } },
  ...Object.entries(resourceConfigs).filter(([path]) => !['categories', 'products', 'skus', 'transactions'].includes(path)).map(([path, config]) => ({
    path: `/${path}`,
    component: ResourcePage,
    props: { config },
    meta: { title: config.title, eyebrow: config.eyebrow, module: resourceModules[path] || path },
  })),
  { path: '/categories', component: CategoryPage, meta: { title: '产品分类', eyebrow: 'Catalog structure', module: 'categories' } },
  { path: '/products', component: ProductPage, meta: { title: '产品管理', eyebrow: 'Product catalog', module: 'products' } },
  { path: '/skus', component: SKUPage, meta: { title: 'SKU 管理', eyebrow: 'Sellable variants', module: 'skus' } },
  { path: '/sku-packaging', component: PackagingPage, meta: { title: '包装管理', eyebrow: 'Packaging maintenance', module: 'packaging' } },
  { path: '/hs-codes', component: HSCodePage, meta: { title: 'HS 编码维护', eyebrow: 'Customs classification', module: 'hs_codes' } },
  { path: '/quotes', component: DocumentPage, props: { type: 'quotes' }, meta: { title: '报价管理', eyebrow: 'Quotation desk', module: 'quotes' } },
  { path: '/orders', component: DocumentPage, props: { type: 'orders' }, meta: { title: '订单管理', eyebrow: 'Sales orders', module: 'orders' } },
  { path: '/import', component: ImportPage, meta: { title: '数据导入', eyebrow: 'Data onboarding', module: 'imports' } },
  { path: '/organization', component: OrganizationPage, meta: { title: '组织与权限', eyebrow: 'Organization & access', module: 'organization' } },
  { path: '/inventory', component: InventoryPage, meta: { title: '库存', eyebrow: 'Current inventory', module: 'inventory' } },
  { path: '/purchase-orders', component: PurchaseOrderPage, meta: { title: '采购管理', eyebrow: 'Procurement desk', module: 'purchases' } },
  { path: '/finance', component: FinanceDashboardPage, meta: { title: '财务概览', eyebrow: 'Operating finance', module: 'finance' } },
  { path: '/receivables', component: PaymentPlanPage, props: { direction: 'receivable' }, meta: { title: '应收计划', eyebrow: 'Accounts receivable', module: 'finance' } },
  { path: '/payables', component: PaymentPlanPage, props: { direction: 'payable' }, meta: { title: '应付计划', eyebrow: 'Accounts payable', module: 'finance' } },
  { path: '/transactions', component: TransactionPage, meta: { title: '财务流水', eyebrow: 'Cash ledger', module: 'transactions' } },
  { path: '/access-denied', name: 'access-denied', component: AccessDeniedPage, meta: { accessStatus: true, title: '访问受限', eyebrow: 'Access denied' } },
  { path: '/access-status-error', name: 'access-status-error', component: AccessDeniedPage, meta: { accessStatus: true, title: '权限状态', eyebrow: 'Access status' } },
]

const router = createRouter({ history: createWebHistory(), routes })
installModalNavigationGuard(router)

router.beforeEach(async to => {
  if (to.meta.accessStatus) return true
  try { await loadAccessControl() }
  catch { return { name: 'access-status-error', replace: true } }
  const module = to.meta.module
  if (module && !can(module, 'view')) return { name: 'access-denied', query: { from: to.fullPath }, replace: true }
  return true
})

export default router
