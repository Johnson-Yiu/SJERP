export function parseDocumentDetailId(value) {
  if (Array.isArray(value)) {
    if (value.length !== 1) return null
    value = value[0]
  }
  if (value === null || value === undefined) return null
  const text = String(value).trim()
  if (!/^\d+$/.test(text)) return null
  const id = Number(text)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}

export function documentDetailState(type, rawId) {
  const id = parseDocumentDetailId(rawId)
  return {
    quoteDetailId: id && type !== 'orders' ? id : null,
    orderDetailId: id && type === 'orders' ? id : null,
  }
}

export function withDocumentDetailQuery(route, id) {
  return {
    path: route.path,
    query: { ...route.query, detail: String(id), tab: 'overview' },
    hash: route.hash,
  }
}

export function withoutDocumentDetailQuery(route) {
  const { detail: _detail, tab: _tab, ...query } = route.query || {}
  return { path: route.path, query, hash: route.hash }
}
