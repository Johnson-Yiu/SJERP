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
import { resourceConfigs } from './resourceConfigs'

const routes = [
  { path: '/', component: Dashboard, meta: { title: '经营概览', eyebrow: 'Business overview' } },
  ...Object.entries(resourceConfigs).filter(([path]) => !['categories', 'products', 'skus'].includes(path)).map(([path, config]) => ({
    path: `/${path}`,
    component: ResourcePage,
    props: { config },
    meta: { title: config.title, eyebrow: config.eyebrow },
  })),
  { path: '/categories', component: CategoryPage, meta: { title: '产品分类', eyebrow: 'Catalog structure' } },
  { path: '/products', component: ProductPage, meta: { title: '产品管理', eyebrow: 'Product catalog' } },
  { path: '/skus', component: SKUPage, meta: { title: 'SKU 管理', eyebrow: 'Sellable variants' } },
  { path: '/quotes', component: DocumentPage, props: { type: 'quotes' }, meta: { title: '报价管理', eyebrow: 'Quotation desk' } },
  { path: '/orders', component: DocumentPage, props: { type: 'orders' }, meta: { title: '订单管理', eyebrow: 'Sales orders' } },
  { path: '/import', component: ImportPage, meta: { title: '数据导入', eyebrow: 'Data onboarding' } },
  { path: '/organization', component: OrganizationPage, meta: { title: '组织与权限', eyebrow: 'Organization & access' } },
  { path: '/inventory', component: InventoryPage, meta: { title: '库存', eyebrow: 'Current inventory' } },
  { path: '/purchase-orders', component: PurchaseOrderPage, meta: { title: '采购管理', eyebrow: 'Procurement desk' } },
]

export default createRouter({ history: createWebHistory(), routes })
