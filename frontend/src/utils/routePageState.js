const transientRouteQueryKeys = new Set(['create', 'detail', 'edit', 'returnTo'])
const transientModalQueryKeys = new Set(['create', 'edit', 'returnTo'])

export function pageIdentityKey(route) {
  return route?.path || '/'
}

export function routeDataQuery(query = {}) {
  return Object.fromEntries(
    Object.entries(query).filter(([key]) => !transientRouteQueryKeys.has(key)),
  )
}

export function routeDataQuerySignature(query = {}) {
  return JSON.stringify(Object.entries(routeDataQuery(query)).sort(([left], [right]) => left.localeCompare(right)))
}

export function withoutModalActionQuery(query = {}) {
  return Object.fromEntries(
    Object.entries(query).filter(([key]) => !transientModalQueryKeys.has(key)),
  )
}
