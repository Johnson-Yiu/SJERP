export function skuContextId(rawSkuId) {
  if (Array.isArray(rawSkuId)) return rawSkuId.length === 1 ? String(rawSkuId[0] ?? '').trim() : ''
  return String(rawSkuId ?? '').trim()
}

export function skuContextLabel(rows, rawSkuId) {
  const skuId = skuContextId(rawSkuId)
  if (!skuId) return ''

  for (const row of rows || []) {
    if (String(row.sku ?? '') === skuId) {
      const code = row.sku_code || row.sku_code_snapshot
      if (code) return code
    }
    for (const item of row.items || []) {
      if (String(item.sku ?? '') === skuId) {
        const code = item.sku_code || item.sku_code_snapshot
        if (code) return code
      }
    }
  }

  return `SKU #${skuId}`
}

export function withoutSkuContext(route) {
  const { sku: _sku, ...query } = route?.query || {}
  return { path: route?.path || '/', query, hash: route?.hash || '' }
}
