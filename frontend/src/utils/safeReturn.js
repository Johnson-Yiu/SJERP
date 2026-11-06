export function safeReturn(value, origin) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || /[\\\x00-\x1f]/.test(value)) return '/'
  try { return new URL(value, origin).origin === origin ? value : '/' } catch { return '/' }
}
