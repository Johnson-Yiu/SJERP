import { reactive } from 'vue'
import { api } from './api.js'

export const accessState = reactive({ operator: null, loading: true, loaded: false, error: '' })

let requestPromise = null

export async function loadAccessControl({ force = false } = {}) {
  if (accessState.loaded && !force) return accessState.operator
  if (requestPromise && !force) return requestPromise
  accessState.loading = true
  accessState.error = ''
  requestPromise = api.get('/session/current-operator/').then(response => {
    accessState.operator = response.data || null
    accessState.loaded = true
    return accessState.operator
  }).catch(error => {
    accessState.operator = null
    accessState.loaded = false
    accessState.error = error?.response?.data?.detail || error?.message || '无法读取当前账号的权限状态。'
    throw error
  }).finally(() => {
    accessState.loading = false
    requestPromise = null
  })
  return requestPromise
}

export function setAccessOperator(operator) {
  accessState.operator = operator || null
  accessState.loaded = true
  accessState.loading = false
  accessState.error = ''
}

export function can(module, action = 'view') {
  if (!accessState.loaded || accessState.error || !accessState.operator) return false
  if (accessState.operator.has_all_permissions === true || accessState.operator.development_superadmin === true) return true
  if (accessState.operator.rbac_enforcement !== true) return false
  return accessState.operator.permissions?.[module]?.[action] === true
}

export function canAccessOrganization() {
  return can('organization', 'view') || (
    accessState.loaded && !accessState.error && accessState.operator?.can_manage_permissions === true
  )
}

export function canAccessHistoricalOrders() {
  return can('orders', 'view') || can('purchases', 'view')
}

export const PERMITTED_PAGE_MODULES = [
  ['/', 'dashboard'], ['/reports', 'reports'], ['/customers', 'customers'], ['/contacts', 'contacts'],
  ['/follow-ups', 'followups'], ['/quotes', 'quotes'], ['/orders', 'orders'], ['/suppliers', 'suppliers'],
  ['/purchase-orders', 'purchases'], ['/inventory', 'inventory'], ['/inventory-movements', 'inventory'],
  ['/products', 'products'], ['/skus', 'skus'], ['/categories', 'categories'],
  ['/product-parameters', 'parameters'], ['/sku-packaging', 'packaging'], ['/sku-trade-units', 'trade_units'],
  ['/product-certificates', 'certificates'], ['/hs-codes', 'hs_codes'], ['/finance', 'finance'],
  ['/receivables', 'finance'], ['/payables', 'finance'], ['/transactions', 'transactions'], ['/rmb-cash-events', 'transactions'],
  ['/import', 'imports'], ['/organization', 'organization'], ['/historical-orders', 'historical-orders'],
]

export function firstPermittedPath() {
  return PERMITTED_PAGE_MODULES.find(([path, module]) => (
    path === '/organization' ? canAccessOrganization() : path === '/historical-orders' ? canAccessHistoricalOrders() : can(module, 'view')
  ))?.[0] || ''
}

export function useAccessControl() {
  return { can, accessState, loadAccessControl }
}
