function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function safeImageUrl(value) {
  const url = String(value || '')
  if (/^data:image\/(?:png|jpe?g|gif|webp);base64,[a-z\d+/]+={0,2}$/i.test(url)) return url

  if (url.startsWith('/media/')) {
    try {
      const parsed = new URL(url, 'https://local.invalid')
      if (parsed.origin === 'https://local.invalid' && parsed.pathname.startsWith('/media/')) return url
    } catch { /* Invalid URLs remain plain text. */ }
    return ''
  }

  try {
    const parsed = new URL(url)
    if (parsed.protocol === 'https:' && !parsed.username && !parsed.password) return url
  } catch { /* Invalid URLs remain plain text. */ }
  return ''
}

export function renderRichText(value) {
  const images = []
  const source = String(value ?? '').replace(/!\[([^\]]*)\]\(((?:data:image\/|\/media\/|https?:\/\/)[^\s)]+)\)/g, (markdown, alt, rawUrl) => {
    const url = safeImageUrl(rawUrl)
    if (!url) return markdown
    const token = `\u0000RICHIMAGE${images.length}\u0000`
    images.push(`<img src="${escapeHtml(url)}" alt="${escapeHtml(alt)}" loading="lazy" />`)
    return token
  })

  const escaped = escapeHtml(source)
  const inline = text => text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/_(.+?)_/g, '<em>$1</em>')
    .replace(/\u0000RICHIMAGE(\d+)\u0000/g, (_, index) => images[Number(index)] || '')

  const lines = escaped.split('\n')
  let html = '', listType = ''
  const closeList = () => {
    if (!listType) return
    html += `</${listType}>`
    listType = ''
  }

  lines.forEach(line => {
    const unordered = line.match(/^\s*-\s+(.+)$/)
    const ordered = line.match(/^\s*\d+\.\s+(.+)$/)
    const nextType = unordered ? 'ul' : ordered ? 'ol' : ''
    if (nextType) {
      if (listType !== nextType) {
        closeList()
        listType = nextType
        html += `<${listType}>`
      }
      html += `<li>${inline((unordered || ordered)[1])}</li>`
      return
    }
    closeList()
    html += `<p>${inline(line) || '&nbsp;'}</p>`
  })
  closeList()
  return html
}
