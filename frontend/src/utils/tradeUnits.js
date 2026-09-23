export function fromTradeLine(line) {
  return { ...line, _historical_trade_unit: line.trade_unit, quantity: line.trade_quantity ?? line.quantity, unit_price: line.trade_unit_price ?? line.unit_price }
}
export function tradePayload(line, priceField = 'unit_price') {
  const result = { ...line, trade_unit: line.trade_unit || null }
  delete result.trade_snapshot
  delete result._historical_trade_unit
  if (line.trade_unit) {
    result.trade_quantity = line.quantity
    if (priceField) result.trade_unit_price = line[priceField]
  } else {
    delete result.trade_quantity
    delete result.trade_unit_price
  }
  return result
}
export function baseQuantity(line) {
  return Number(line.quantity || 0) * Number(line.trade_unit ? line.trade_snapshot?.factor || 1 : 1)
}
export function tradeLabel(line, fallback = '') {
  return line.trade_snapshot?.unit || line.unit || fallback
}
export function withDefaultTradeUnit(line, sku, supplier = null) {
  const unit = sku?.trade_units?.find(u => u.active && u.is_default && (!u.supplier || Number(u.supplier) === Number(supplier)))
  if (!unit) return line
  return { ...line, trade_unit: unit.id, trade_snapshot: { name: unit.name, unit: unit.unit, factor: unit.factor, base_unit: unit.base_unit, allow_fraction: unit.allow_fraction }, unit_price: line.unit_price === '' ? '' : Number((Number(line.unit_price || 0) * Number(unit.factor)).toFixed(4)) }
}
export function restoreTradeLines(selectedLines, previousLines) {
  return selectedLines.flatMap(line => {
    const matches = previousLines.filter(previous => String(previous.sku) === String(line.sku))
    return matches.length ? matches : [line]
  })
}
