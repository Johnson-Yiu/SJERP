// Sum API decimals as scaled integers rather than floating point numbers.
export function scaled(value, places = 2) {
  const raw = String(value ?? '0')
  if (!/^-?\d+(\.\d+)?$/.test(raw)) throw new Error('数值格式不正确')
  const negative = raw.startsWith('-')
  const [whole, fraction = ''] = raw.replace(/^-/, '').split('.')
  if (fraction.slice(places).replace(/0/g, '')) throw new Error(`最多填写 ${places} 位小数`)
  return (negative ? -1n : 1n) * BigInt(whole + fraction.slice(0, places).padEnd(places, '0'))
}
export function decimal(value, places = 2) {
  const sign = value < 0n ? '-' : ''
  const digits = (value < 0n ? -value : value).toString().padStart(places + 1, '0')
  const fraction = digits.slice(-places).replace(/0+$/, '')
  return sign + digits.slice(0, -places) + (fraction ? `.${fraction}` : '')
}
export function shippedSkus(shipment) {
  const rows = new Map()
  for (const item of shipment.items || []) {
    const key = String(item.sku)
    const row = rows.get(key) || { sku: item.sku, sku_code: item.sku_code, display_name: item.display_name, base_unit: item.base_unit || 'pcs', quantity: 0n }
    row.quantity += scaled(item.quantity)
    rows.set(key, row)
  }
  return [...rows.values()]
}
export function packingSummary(shipment, packages) {
  const sum = (field, places) => decimal(packages.reduce((total, row) => total + scaled(row[field], places), 0n), places)
  const rows = shippedSkus(shipment).map(row => {
    const packed = packages.flatMap(p => p.items || []).filter(item => String(item.sku) === String(row.sku)).reduce((total, item) => total + scaled(item.quantity), 0n)
    return { ...row, shipped: decimal(row.quantity), packed: decimal(packed), remaining: decimal(row.quantity - packed), complete: packed === row.quantity }
  })
  return { count: packages.length, net: sum('actual_net_weight', 3), gross: sum('actual_gross_weight', 3), cbm: sum('actual_cbm', 6), rows, complete: rows.length > 0 && rows.every(row => row.complete) }
}
