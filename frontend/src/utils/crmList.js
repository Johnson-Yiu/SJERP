const normalized = value => String(value || '').normalize('NFKC').trim().toLocaleLowerCase()

function compact(value) {
  return normalized(value).replace(/[\s\p{P}\p{S}]+/gu, '')
}

export function normalizeContactPhone(value) {
  const raw = normalized(value).replace(/(?:ext\.?|x|分机)\s*\d+.*$/i, '')
  const digits = raw.replace(/\D/g, '')
  if (!digits) return ''
  // Keep the country code.  0086... and +86... are equivalent, while a
  // local number is not silently treated as the same number in another country.
  return raw.trim().startsWith('+') ? `+${digits}` : raw.trim().startsWith('00') ? `+${digits.slice(2)}` : digits
}

function editDistance(left, right) {
  const previous = Array.from({ length: right.length + 1 }, (_, index) => index)
  for (let row = 1; row <= left.length; row += 1) {
    const current = [row]
    for (let column = 1; column <= right.length; column += 1) {
      current[column] = Math.min(
        current[column - 1] + 1,
        previous[column] + 1,
        previous[column - 1] + (left[row - 1] === right[column - 1] ? 0 : 1),
      )
    }
    for (let column = 0; column <= right.length; column += 1) previous[column] = current[column]
  }
  return previous[right.length]
}

function similarContactName(left, right) {
  const first = compact(left)
  const second = compact(right)
  if (!first || !second) return false
  if (first === second) return true
  const longest = Math.max(first.length, second.length)
  if (longest < 4) return false
  const distance = editDistance(first, second)
  return distance <= (longest >= 8 ? 2 : 1) && distance / longest <= 0.25
}

export function contactRows(rows = [], filters = {}) {
  const customerId = String(filters.customer || '')
  const primary = String(filters.primary || '')
  const search = normalized(filters.search)
  return rows.filter(row => {
    if (customerId && String(row.customer ?? '') !== customerId) return false
    if (primary === 'primary' && !row.is_primary) return false
    if (primary === 'other' && row.is_primary) return false
    if (search && ![row.name, row.title, row.email, row.phone, row.whatsapp, row.customer_name].some(value => normalized(value).includes(search))) return false
    return true
  })
}

export function followUpRows(rows = [], filters = {}) {
  const customerId = String(filters.customer || '')
  const owner = normalized(filters.owner)
  const type = String(filters.type || '')
  const from = String(filters.from || '')
  const to = String(filters.to || '')
  const search = normalized(filters.search)
  const direction = filters.sort === 'oldest' ? 1 : -1
  return rows.filter(row => {
    if (customerId && String(row.customer ?? '') !== customerId) return false
    if (owner && normalized(row.owner) !== owner) return false
    if (type && String(row.type ?? '') !== type) return false
    const date = String(row.followed_at || '').slice(0, 10)
    if (from && date < from) return false
    if (to && date > to) return false
    if (search && ![row.subject, row.content, row.result, row.customer_name, row.contact_name, row.owner, row.next_action, row.type_display].some(value => normalized(value).includes(search))) return false
    return true
  }).sort((left, right) => {
    const leftDate = String(left.followed_at || '')
    const rightDate = String(right.followed_at || '')
    const dateCompare = leftDate.localeCompare(rightDate) * direction
    return dateCompare || (Number(right.id) - Number(left.id)) * direction
  })
}

export function duplicateContactMatches(rows = [], form = {}, editingId = null) {
  const customer = String(form.customer || '')
  const name = normalized(form.name)
  const email = normalized(form.email)
  const phone = normalizeContactPhone(form.phone)
  if (!customer || (!name && !email && !phone)) return []
  return rows.filter(row => {
    if (String(row.id) === String(editingId) || String(row.customer ?? '') !== customer) return false
    const rowEmail = normalized(row.email)
    const rowPhone = normalizeContactPhone(row.phone)
    const reasons = []
    if (name && similarContactName(name, row.name)) reasons.push('姓名')
    if (email && rowEmail && email === rowEmail) reasons.push('邮箱')
    if (phone && rowPhone && phone === rowPhone) reasons.push('电话')
    return reasons.length > 0
  }).map(row => {
    const reasons = []
    if (name && similarContactName(name, row.name)) reasons.push('姓名')
    if (email && normalized(row.email) && email === normalized(row.email)) reasons.push('邮箱')
    if (phone && normalizeContactPhone(row.phone) && phone === normalizeContactPhone(row.phone)) reasons.push('电话')
    return { ...row, matchReasons: reasons }
  })
}

export function duplicateContactHint(rows = [], form = {}, editingId = null) {
  const match = duplicateContactMatches(rows, form, editingId)[0]
  return match ? `该客户已有相同姓名或联系方式的疑似重复联系人：${match.name}。请确认是否继续。` : ''
}

export function richTextExcerpt(value, maxLength = 120) {
  const text = String(value || '')
    .replace(/<\/(p|div|li|h[1-6]|blockquote)>/gi, ' ')
    .replace(/<br\s*\/?\s*>/gi, ' ')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;|&#160;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/\s+/g, ' ')
    .trim()
  return text.length > maxLength ? `${text.slice(0, maxLength)}…` : text
}
