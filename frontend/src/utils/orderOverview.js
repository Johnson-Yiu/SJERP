import { daysBetween } from './orderDate.js'

export function deliveryState(order, now = new Date()) {
  if (!['confirmed', 'production'].includes(order.status)) return null
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  const days = daysBetween(today, order.expected_ship_date)
  if (days === '') return null
  return days > 0 ? { kind: 'future', label: `还剩 ${days} 天` } : days === 0 ? { kind: 'today', label: '今日到期' } : { kind: 'overdue', label: `逾期 ${-days} 天` }
}

export function receivableNeedsReview(order, payment) {
  const amount = Number(order?.total_amount)
  return !!order && !['draft', 'cancelled'].includes(order.status) && Number.isFinite(amount) && amount !== 0 && ['no_plans', 'review'].includes(payment?.settlement?.state ?? order.receivable_state)
}

export function orderTasks(order, fulfillment, payment, { canViewPayments = true } = {}) {
  if (!order || order.status === 'cancelled') return []
  if (order.status === 'draft') return [{ key: 'confirm', title: '订单待确认', description: '确认后生成库存预留和应收计划。', action: '确认订单' }]
  const tasks = []
  const count = field => new Set((fulfillment?.items || []).filter(item => Number(item[field]) > 0).map(item => item.sku ?? item.sku_code ?? item.id)).size
  const shortage = count('draftable_quantity')
  if (shortage && order.status !== 'completed') tasks.push({ key: 'procurement', title: '待采购', description: `还有 ${shortage} 个 SKU 需要采购。`, action: '查看采购与发货', warning: true })
  const unshipped = count('unshipped_quantity')
  if (unshipped && ['confirmed', 'production'].includes(order.status)) tasks.push({ key: 'shipment', title: '待发货', description: `还有 ${unshipped} 个 SKU 未完成发货。`, action: '查看采购与发货' })
  const balance = payment ? payment.balance_amount : order.balance_amount
  if (canViewPayments && receivableNeedsReview(order, payment)) tasks.push({ key: 'receivable_review', title: '应收计划待核对', description: '待收金额尚未确认，请核对应收计划。', action: '查看本单应收', warning: true })
  else if (canViewPayments && balance != null && Number(balance) > 0) tasks.push({ key: 'receivable', title: '待收款', amount: balance, action: '查看 / 登记本单应收', warning: true })
  if (order.status === 'shipped') tasks.push({ key: 'complete', title: '货物已全部发出', description: '全部发货后可完成履约，未收款项继续追踪。', action: '完成履约' })
  return tasks
}
