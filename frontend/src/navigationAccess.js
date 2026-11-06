import { can, canAccessHistoricalOrders, canAccessOrganization, loadAccessControl } from './accessControl'
export async function navigationAccess(to) {
  if (to.name === 'login' || to.meta.accessStatus) return true
  let operator
  try { operator = await loadAccessControl() } catch { return { name: 'access-status-error', replace: true } }
  if (!operator?.authenticated && !operator?.development_superadmin) return { name: 'login', query: { next: to.fullPath }, state: { __workspace: null }, replace: true }
  const permitted = to.path === '/organization' ? canAccessOrganization() : to.path === '/historical-orders' ? canAccessHistoricalOrders() : can(to.meta.module, 'view')
  return to.meta.module && !permitted ? { name: 'access-denied', query: { from: to.fullPath }, replace: true } : true
}
