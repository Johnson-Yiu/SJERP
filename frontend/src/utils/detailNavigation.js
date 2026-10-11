import { internalPagePath } from './modalNavigation.js'
import { withoutDocumentDetailQuery } from './documentDetailRoute.js'

function detailLocation(path, id, tab, returnTo) {
  const query = { detail: String(id) }
  if (tab) query.tab = tab
  const origin = internalPagePath(returnTo)
  if (origin) query.returnTo = origin
  return { path, query }
}

export function quoteDetailLocation(id, tab, returnTo) {
  return detailLocation('/quotes', id, tab, returnTo)
}
export function orderDetailLocation(id, tab, returnTo) {
  return detailLocation('/orders', id, tab, returnTo)
}
export function purchaseDetailLocation(id, tab, returnTo) {
  return detailLocation('/purchase-orders', id, tab, returnTo)
}
export function workbenchCloseLocation(route) {
  const origin = internalPagePath(route.query?.returnTo)
  if (origin) return origin
  const location = withoutDocumentDetailQuery(route)
  delete location.query.returnTo
  return location
}

export function relationWorkbenchLocation(entity, id, sourceEntity, sectionKey, returnTo) {
  const helpers = { quotes: quoteDetailLocation, orders: orderDetailLocation, 'purchase-orders': purchaseDetailLocation }
  const details = { customers: ['quotes', 'orders', 'purchases'], suppliers: ['purchases'], products: ['sales'], skus: ['orders'], 'supplier-skus': ['orders', 'purchases'] }
  const tab = details[sourceEntity]?.includes(sectionKey) ? 'items' : 'overview'
  return helpers[entity]?.(id, tab, returnTo)
}

const relatedCreateRoles = {
  customers: { contacts: 'contacts', followups: 'follow-ups', quotes: 'quotes', orders: 'orders' },
  suppliers: { purchases: 'purchase-orders' },
  products: { skus: 'skus', parameters: 'product-parameters', certificates: 'product-certificates' },
}
export function canCreateRelated(entity, section) {
  return Boolean(section && relatedCreateRoles[entity]?.[section.key] === section.entity)
}
