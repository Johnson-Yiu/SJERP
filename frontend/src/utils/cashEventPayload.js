// Empty selections (including restored drafts) must not become 0 or NaN.
export function optionalSettlementId(value) {
  if (value === null || value === undefined || !['string', 'number'].includes(typeof value)) return null
  if (typeof value === 'string' && !value.trim()) return null
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}
