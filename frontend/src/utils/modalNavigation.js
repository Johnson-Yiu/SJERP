import { withoutModalActionQuery } from './routePageState.js'

export function isModalRoute(route) {
  return route?.query?.create === '1' || Boolean(route?.query?.edit)
}

export function internalPagePath(value) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//')) return ''
  try {
    const url = new URL(value, window.location.origin)
    return url.origin === window.location.origin ? `${url.pathname}${url.search}${url.hash}` : ''
  } catch {
    return ''
  }
}

export function modalOrigin(route) {
  return internalPagePath(route?.query?.returnTo)
}

export function clearModalRoute(router, route) {
  if (!isModalRoute(route)) return Promise.resolve()
  const query = withoutModalActionQuery(route.query)
  return router.replace({ path: route.path, query, hash: route.hash })
}
