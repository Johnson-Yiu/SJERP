const normalized = value => String(value || '').trim().toLocaleLowerCase()

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
  const type = String(filters.type || '')
  const from = String(filters.from || '')
  const to = String(filters.to || '')
  const search = normalized(filters.search)
  const direction = filters.sort === 'oldest' ? 1 : -1
  return rows.filter(row => {
    if (customerId && String(row.customer ?? '') !== customerId) return false
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

export function duplicateContactHint(rows = [], form = {}, editingId = null) {
  const customer = String(form.customer || '')
  const name = normalized(form.name)
  const email = normalized(form.email)
  const phone = normalized(form.phone)
  if (!customer || (!name && !email && !phone)) return ''
  const match = rows.find(row => {
    if (String(row.id) === String(editingId) || String(row.customer ?? '') !== customer) return false
    return (name && normalized(row.name) === name)
      || (email && normalized(row.email) === email)
      || (phone && normalized(row.phone) === phone)
  })
  return match ? `该客户已有相同姓名或联系方式的联系人：${match.name}。请确认是否继续。` : ''
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
