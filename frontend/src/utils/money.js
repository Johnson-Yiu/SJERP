/** Display currency uniformly without changing the submitted/stored value. */
export function formatMoney(value) {
  return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/**
 * Keep a money input compact by default while retaining an intentionally entered
 * precision greater than two decimal places.
 */
export function normalizeMoneyInput(value) {
  if (value === null || value === undefined || value === '') return ''
  const raw = String(value).trim()
  if (!/^-?\d+(?:\.\d+)?$/.test(raw)) return raw
  const [integer, decimal = ''] = raw.split('.')
  if (decimal.replace(/0+$/, '').length > 2) return raw
  return `${integer}.${decimal.slice(0, 2).padEnd(2, '0')}`
}
