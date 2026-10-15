export const certificateFilters = [
  ['', '全部'], ['attention', '需关注'], ['expired', '已过期'], ['expiring', '90 天内到期'], ['valid', '90 天后到期'], ['no_expiry', '无有效期'],
]
export const certificateFilterLabels = { attention: '需要关注的证书', expired: '已过期证书', expiring: '90 天内到期的证书', valid: '90 天后到期的证书', no_expiry: '无有效期证书' }
export function certificateBadge(row) {
  const days = row.days_to_expiry
  if (row.expiry_status === 'expired') return `已过期 · ${Math.abs(days)} 天`
  if (['expiring_30', 'expiring_90'].includes(row.expiry_status)) return days === 0 ? '今日到期' : `${days} 天后到期`
  return row.expiry_status === 'no_expiry' ? '无有效期' : row.expiry_status_display || '有效'
}
export function certificateFilterQuery(query, expiry) {
  const next = { ...query }
  if (expiry) next.expiry = expiry
  else delete next.expiry
  return next
}
