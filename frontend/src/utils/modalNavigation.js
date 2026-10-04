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

export function installModalNavigationGuard(router) {
  return router.beforeEach((to, from) => {
    const sourceWasModal = isModalRoute(from)
    const targetIsModal = isModalRoute(to)
    const origin = modalOrigin(from)

    // Closing removes the action query on the same route. Do not intercept
    // deliberate navigation to another page, such as a sidebar click.
    if (sourceWasModal && !targetIsModal && to.path === from.path && origin) {
      if (internalPagePath(to.fullPath) === origin) return true
      return origin
    }
    if (!targetIsModal || modalOrigin(to)) return true
    // A create/edit modal on the current page can close by clearing its action
    // query. Adding returnTo here would redirect that close back to itself.
    if (to.path === from.path) return true

    // Nested modal routes keep the original page. Directly opened modal URLs
    // have no predecessor and therefore close back to their own list page.
    const inheritedOrigin = origin || (from.matched?.length ? internalPagePath(from.fullPath) : '')
    if (!inheritedOrigin) return true
    return { path: to.path, query: { ...to.query, returnTo: inheritedOrigin }, hash: to.hash }
  })
}

export function clearModalRoute(router, route) {
  if (!isModalRoute(route)) return Promise.resolve()
  const query = withoutModalActionQuery(route.query)
  return router.replace({ path: route.path, query, hash: route.hash })
}
