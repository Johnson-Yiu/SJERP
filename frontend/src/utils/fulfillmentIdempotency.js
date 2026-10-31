const STORAGE_PREFIX = 'sunjack:fulfillment-idempotency:'

function stableSerialize(value) {
  if (Array.isArray(value)) return `[${value.map(stableSerialize).join(',')}]`
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stableSerialize(value[key])}`).join(',')}}`
  }
  return JSON.stringify(value)
}

function shortFingerprint(value) {
  let hash = 2166136261
  for (const char of value) {
    hash ^= char.charCodeAt(0)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(16)
}

function requestStorage(operation, targetId) {
  if (typeof window === 'undefined' || !window.sessionStorage) return null
  try {
    return {
      storage: window.sessionStorage,
      key: `${STORAGE_PREFIX}${operation}:${targetId}`,
    }
  } catch {
    return null
  }
}

function newRequestId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  return `erp-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}

// Keep only a fingerprint in sessionStorage. The request body stays in the
// form state, while a refresh can still retry the exact pending operation.
export function fulfillmentRequestId(operation, targetId, payload) {
  const handle = requestStorage(operation, targetId)
  const fingerprint = shortFingerprint(stableSerialize(payload))
  if (handle) {
    try {
      const saved = JSON.parse(handle.storage.getItem(handle.key) || 'null')
      if (saved?.requestId && saved.fingerprint === fingerprint) return saved.requestId
      const requestId = newRequestId()
      handle.storage.setItem(handle.key, JSON.stringify({ requestId, fingerprint }))
      return requestId
    } catch {
      // Private browsing or a blocked storage implementation should not stop
      // a normal request; the server still verifies the header it receives.
    }
  }
  return newRequestId()
}

export function clearFulfillmentRequest(operation, targetId) {
  const handle = requestStorage(operation, targetId)
  if (!handle) return
  try { handle.storage.removeItem(handle.key) } catch { /* best effort */ }
}
