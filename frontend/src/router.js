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
import { internalPagePath, isModalRoute, modalOrigin } from './utils/modalNavigation'

const routes = [
  { path: '/sku-trade-units', component: () => import('./views/TradeUnitsPage.vue'), meta: { title: 'SKU 交易单位', eyebrow: 'Transaction units' } },
  { path: '/reports', component: () => import('./views/ReportsPage.vue'), meta: { title: '报表中心', eyebrow: 'Reports & analytics' } },
  { path: '/', component: Dashboard, meta: { title: '经营概览', eyebrow: 'Business overview' } },
  ...Object.entries(resourceConfigs).filter(([path]) => !['categories', 'products', 'skus', 'transactions'].includes(path)).map(([path, config]) => ({
    path: `/${path}`,
    component: ResourcePage,
    props: { config },
    meta: { title: config.title, eyebrow: config.eyebrow },
  })),
  { path: '/categories', component: CategoryPage, meta: { title: '产品分类', eyebrow: 'Catalog structure' } },
  { path: '/products', component: ProductPage, meta: { title: '产品管理', eyebrow: 'Product catalog' } },
  { path: '/skus', component: SKUPage, meta: { title: 'SKU 管理', eyebrow: 'Sellable variants' } },
  { path: '/sku-packaging', component: PackagingPage, meta: { title: '包装管理', eyebrow: 'Packaging maintenance' } },
  { path: '/hs-codes', component: HSCodePage, meta: { title: 'HS 编码维护', eyebrow: 'Customs classification' } },
  { path: '/quotes', component: DocumentPage, props: { type: 'quotes' }, meta: { title: '报价管理', eyebrow: 'Quotation desk' } },
  { path: '/orders', component: DocumentPage, props: { type: 'orders' }, meta: { title: '订单管理', eyebrow: 'Sales orders' } },
  { path: '/import', component: ImportPage, meta: { title: '数据导入', eyebrow: 'Data onboarding' } },
  { path: '/organization', component: OrganizationPage, meta: { title: '组织与权限', eyebrow: 'Organization & access' } },
  { path: '/inventory', component: InventoryPage, meta: { title: '库存', eyebrow: 'Current inventory' } },
  { path: '/purchase-orders', component: PurchaseOrderPage, meta: { title: '采购管理', eyebrow: 'Procurement desk' } },
  { path: '/finance', component: FinanceDashboardPage, meta: { title: '财务概览', eyebrow: 'Operating finance' } },
  { path: '/receivables', component: PaymentPlanPage, props: { direction: 'receivable' }, meta: { title: '应收计划', eyebrow: 'Accounts receivable' } },
  { path: '/payables', component: PaymentPlanPage, props: { direction: 'payable' }, meta: { title: '应付计划', eyebrow: 'Accounts payable' } },
  { path: '/transactions', component: TransactionPage, meta: { title: '财务流水', eyebrow: 'Cash ledger' } },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to, from) => {
  const sourceWasModal = isModalRoute(from)
  const targetIsModal = isModalRoute(to)
  const origin = modalOrigin(from)

  // Closing removes the action query on the same route. Do not intercept
  // deliberate navigation to another page, such as a sidebar click.
  if (sourceWasModal && !targetIsModal && to.path === from.path && origin) return origin
  if (!targetIsModal || modalOrigin(to)) return true

  // Nested modal routes keep the original page. Directly opened modal URLs
  // have no predecessor and therefore close back to their own list page.
  const inheritedOrigin = origin || (from.matched?.length ? internalPagePath(from.fullPath) : '')
  if (!inheritedOrigin) return true
  return { path: to.path, query: { ...to.query, returnTo: inheritedOrigin }, hash: to.hash, replace: true }
})

export default router
