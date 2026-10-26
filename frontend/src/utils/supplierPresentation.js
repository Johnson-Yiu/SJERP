export function supplierStoreUrl(value) {
  const text = String(value || '').trim()
  if (!text || text === '—') return ''
  try { const url = new URL(/^[a-z][a-z\d+.-]*:/i.test(text) ? text : `https://${text}`); return ['http:', 'https:'].includes(url.protocol) ? url.href : '' } catch { return '' }
}
export function supplierFilters(query = {}) {
  return { category: typeof query.supplyCategory === 'string' && /^[1-9]\d*$/.test(query.supplyCategory) ? query.supplyCategory : '' }
}
export function supplierRows(rows, query, categories = []) {
  const { category } = supplierFilters(query)
  const parents = new Map(categories.map(row => [Number(row.id), Number(row.parent || 0)]))
  function ancestor(id, target) { const seen = new Set(); while (id && !seen.has(id)) { if (id === target) return true; seen.add(id); id = parents.get(id) } return false }
  return rows.filter(row => !category || (row.supply_categories || []).some(id => ancestor(Number(id), Number(category)) || ancestor(Number(category), Number(id))))
}
