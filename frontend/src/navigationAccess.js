import { can, canAccessHistoricalOrders, canAccessOrganization, loadAccessControl } from './accessControl'
export async function navigationAccess(to) {
  if (to.meta.accessStatus) return true
  try { await loadAccessControl() } catch { return { name: 'access-status-error', replace: true } }
  const permitted = to.path === '/organization' ? canAccessOrganization() : to.path === '/historical-orders' ? canAccessHistoricalOrders() : can(to.meta.module, 'view')
  return to.meta.module && !permitted ? { name: 'access-denied', query: { from: to.fullPath }, replace: true } : true
}
