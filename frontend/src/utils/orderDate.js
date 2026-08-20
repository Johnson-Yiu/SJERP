function parseIsoDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return null
  const date = new Date(`${value}T00:00:00Z`)
  return Number.isNaN(date.valueOf()) || date.toISOString().slice(0, 10) !== value ? null : date
}

function formatIsoDate(date) {
  return date.toISOString().slice(0, 10)
}

export function addDays(startDate, days) {
  const date = parseIsoDate(startDate)
  const numberOfDays = Number(days)
  if (!date || !Number.isFinite(numberOfDays)) return ''
  date.setUTCDate(date.getUTCDate() + numberOfDays)
  return formatIsoDate(date)
}

export function daysBetween(startDate, endDate) {
  const start = parseIsoDate(startDate)
  const end = parseIsoDate(endDate)
  if (!start || !end) return ''
  return Math.round((end - start) / 86400000)
}
