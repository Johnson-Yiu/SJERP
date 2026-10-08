import { purchaseArrivalState } from './orderFulfillment.js'
export function purchaseArrival(purchase, now = new Date()) {
  if (!['ordered', 'partial'].includes(purchase.status)) return null
  const state = purchaseArrivalState(purchase, now)
  if (!state) return null
  return { ...state, label: state.label.replace('预计 ', '还剩 ').replace(' 天后到货', ' 天').replace('预计今日到货', '今日到货').replace('到货逾期', '逾期') }
}
export function purchaseTasks(purchase) {
  const tasks = []
  if (purchase.status === 'draft') tasks.push({ title: '采购单待确认', description: '确认后进入正式采购流程。', action: '确认下单', target: 'confirm' })
  const remaining = (purchase.items || []).filter(item => Number(item.remaining_quantity) > 0).length
  if (['ordered', 'partial'].includes(purchase.status) && remaining) tasks.push({ title: '待到货', description: `还有 ${remaining} 条明细未全部到货。`, action: '查看收货', target: 'receipt' })
  if (!['draft', 'cancelled'].includes(purchase.status) && Number(purchase.unpaid_amount) > 0) tasks.push({ title: '待付款', description: `待付 ${purchase.currency} ${Number(purchase.unpaid_amount).toFixed(2)}`, action: '查看 / 登记付款', target: 'payment' })
  if (purchase.status === 'completed' && !tasks.length) tasks.push({ title: '采购已完成', description: '当前没有待处理事项。' })
  if (purchase.status === 'cancelled') tasks.push({ title: '采购已取消', description: '采购单已取消。' })
  return tasks
}
export function receiptProgress(items = []) {
  const identities = new Set(items.map(item => `${item.sku ?? item.sku_code}:${item.trade_snapshot?.base_unit || ''}`))
  const pending = items.filter(item => Number(item.remaining_quantity) > 0).length
  if (identities.size !== 1) return { lines: true, ordered: items.length, received: items.length - pending, remaining: pending, percent: items.length ? Math.round((items.length - pending) / items.length * 100) : 0 }
  const sum = key => items.reduce((total, item) => total + Number(item[key] || 0), 0)
  const ordered = sum('quantity'), remaining = sum('remaining_quantity'), received = sum('received_quantity')
  return { lines: false, ordered, received, remaining, unit: items[0]?.trade_snapshot?.base_unit, percent: ordered ? Math.min(100, Math.round(received / ordered * 100)) : 0 }
}
