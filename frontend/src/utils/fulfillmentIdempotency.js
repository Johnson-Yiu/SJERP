import { workspaceAccountScope } from '../workspaceSession.js'
const STORAGE_PREFIX = 'sunjack:fulfillment-idempotency:'
const pendingRequestIds = new Map()

export class FulfillmentIdempotencyStorageError extends Error {
  constructor(message, options = {}) {
    super(message, options)
    this.name = 'FulfillmentIdempotencyStorageError'
    this.code = 'FULFILLMENT_IDEMPOTENCY_STORAGE_UNAVAILABLE'
    this.operationCompleted = Boolean(options.operationCompleted)
  }
}

function storageFailure(cause, operationCompleted = false) {
  const message = operationCompleted
    ? '服务器已确认收货/发货成功，但浏览器无法清理重试标识。请先核对业务记录，再开始新的收货或发货。'
    : '无法安全保存本次收货/发货请求标识，已阻止提交。请检查浏览器会话存储权限后重试。'
  return new FulfillmentIdempotencyStorageError(message, { cause, operationCompleted })
}

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

function requestStorage(operation, targetId, operationCompleted = false) {
  try {
    if (typeof window === 'undefined') throw new Error('Window storage is unavailable.')
    const storage = window.sessionStorage
    if (!storage) throw new Error('Session storage is unavailable.')
    return {
      storage,
      key: `${STORAGE_PREFIX}${workspaceAccountScope() === 'standalone' ? '' : `${workspaceAccountScope()}:`}${operation}:${targetId}`,
    }
  } catch (error) {
    throw storageFailure(error, operationCompleted)
  }
}

function newRequestId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  return `erp-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}

function readSavedRequest(storage, key) {
  let raw
  try {
    raw = storage.getItem(key)
  } catch (error) {
    throw storageFailure(error)
  }
  if (raw == null) return null

  try {
    const saved = JSON.parse(raw)
    if (typeof saved?.requestId !== 'string' || !saved.requestId || typeof saved.fingerprint !== 'string') {
      throw new Error('Stored fulfillment request identity is invalid.')
    }
    return saved
  } catch (error) {
    throw storageFailure(error)
  }
}

// Keep only a fingerprint in sessionStorage. The request body stays in the
// form state, while a refresh can still retry the exact pending operation.
// Never return a key until its identity has been read and saved successfully.
export function fulfillmentRequestId(operation, targetId, payload) {
  const fingerprint = shortFingerprint(stableSerialize(payload))
  const handle = requestStorage(operation, targetId)
  const saved = readSavedRequest(handle.storage, handle.key)
  if (saved?.fingerprint === fingerprint) {
    pendingRequestIds.set(handle.key, { requestId: saved.requestId, fingerprint })
    return saved.requestId
  }

  const pending = pendingRequestIds.get(handle.key)
  const requestId = pending?.fingerprint === fingerprint ? pending.requestId : newRequestId()
  pendingRequestIds.set(handle.key, { requestId, fingerprint })
  try {
    handle.storage.setItem(handle.key, JSON.stringify({ requestId, fingerprint }))
  } catch (error) {
    // Keep this candidate in memory. If storage recovers in the same page, the
    // exact same pending request can persist and use this ID; until then no
    // network request is allowed to leave the page.
    throw storageFailure(error)
  }
  return requestId
}

export function clearFulfillmentRequest(operation, targetId) {
  const handle = requestStorage(operation, targetId, true)
  try {
    handle.storage.removeItem(handle.key)
  } catch (error) {
    throw storageFailure(error, true)
  }
  pendingRequestIds.delete(handle.key)
}
