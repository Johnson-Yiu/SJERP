export function inventoryPage(value, count, size = 25) {
  const requested = typeof value === 'string' && /^[1-9]\d*$/.test(value) ? Number(value) : 1
  return Math.min(requested, Math.max(1, Math.ceil(count / size)))
}
