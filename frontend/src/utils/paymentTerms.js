export const defaultPaymentTerms = () => [
  { label: '预付款', ratio: '0.30', due_basis: 'order_date', offset_days: 0 },
  { label: '尾款', ratio: '0.70', due_basis: 'expected_arrival_date', offset_days: 0 },
]
export const copyPaymentTerms = value => structuredClone(value?.length ? JSON.parse(JSON.stringify(value)) : defaultPaymentTerms())
export function paymentTermsError(rows) {
  if (!Array.isArray(rows) || !rows.length || rows.length > 5) return '请填写 1 至 5 个付款阶段。'
  let sum = 0n
  const scale = Math.max(...rows.map(row => String(row.ratio).split('.')[1]?.length || 0))
  for (const row of rows) {
    if (!row.label?.trim()) return '请填写付款阶段名称。'
    const ratio = String(row.ratio)
    if (!/^\d+(\.\d+)?$/.test(ratio) || Number(ratio) <= 0 || Number(ratio) > 1) return '每个付款阶段的比例必须大于 0 且不超过 100%。'
    const [whole, fraction = ''] = ratio.split('.')
    sum += BigInt(whole + fraction.padEnd(scale, '0'))
    if (!['order_date', 'expected_arrival_date', 'no_date'].includes(row.due_basis)) return '请选择有效的到期依据。'
    if (!Number.isInteger(row.offset_days) || row.offset_days < 0) return '延后天数必须是非负整数。'
  }
  return sum === 10n ** BigInt(scale) ? '' : '付款比例合计必须为 100%。'
}
export function percentToRatio(value) {
  if (!/^\d+(\.\d+)?$/.test(String(value))) return ''
  const [whole, fraction = ''] = String(value).split('.')
  const digits = whole.padStart(3, '0')
  return `${Number(digits.slice(0, -2))}.${digits.slice(-2)}${fraction}`
}
