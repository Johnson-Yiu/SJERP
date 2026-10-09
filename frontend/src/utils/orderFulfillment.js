import { daysBetween } from './orderDate.js'

export const fulfillmentStateLabels = {
  completed: '已完成', needs_supplier: '待选供应商', needs_procurement: '待采购',
  purchasing: '采购中', ready_to_ship: '可发货', waiting_stock: '待备货',
}

export function fulfillmentItemState(item) {
  if (Number(item.unshipped_quantity) <= 0) return 'completed'
  if (Number(item.draftable_quantity) > 0) return item.supplier_name ? 'needs_procurement' : 'needs_supplier'
  if (Number(item.purchased_quantity) > Number(item.arrived_quantity) || Number(item.in_transit_quantity) > 0) return 'purchasing'
  if (Number(item.unshipped_quantity) > 0 && Number(item.allocated_quantity) > 0 && Number(item.draftable_quantity) <= 0) return 'ready_to_ship'
  return 'waiting_stock'
}

export function fulfillmentMetrics(items = []) {
  const uniqueSkus = predicate => new Set(items.filter(predicate).map(item => item.sku ?? item.sku_code ?? item.id)).size
  return [
    { label: '待采购 SKU', value: uniqueSkus(item => Number(item.draftable_quantity) > 0) },
    { label: '采购中 SKU', value: uniqueSkus(item => Number(item.purchased_quantity) > Number(item.arrived_quantity) || Number(item.in_transit_quantity) > 0) },
    { label: '待发货明细', value: items.filter(item => Number(item.unshipped_quantity) > 0).length },
    { label: '已完成明细', value: items.filter(item => Number(item.unshipped_quantity) <= 0).length },
  ]
}

export function purchaseArrivalState(purchase, now = new Date()) {
  // The existing API uses ordered for the placed lifecycle state.
  if (!['ordered', 'placed', 'partial'].includes(purchase.status)) return null
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  const days = daysBetween(today, purchase.expected_arrival_date)
  if (days === '') return null
  return days > 0 ? { kind: 'future', label: `预计 ${days} 天后到货` } : days === 0 ? { kind: 'today', label: '预计今日到货' } : { kind: 'overdue', label: `到货逾期 ${-days} 天` }
}
