// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  clearFulfillmentRequest,
  fulfillmentRequestId,
  FulfillmentIdempotencyStorageError,
} from '../src/utils/fulfillmentIdempotency.js'

const operation = 'ship'
const targetId = 823
const payload = { shipment_date: '2026-10-30', items: [{ order_item: 12, quantity: 2 }] }
const storageKey = `sunjack:fulfillment-idempotency:${operation}:${targetId}`
let sessionStorageDescriptor

beforeEach(() => {
  sessionStorageDescriptor = Object.getOwnPropertyDescriptor(window, 'sessionStorage')
  window.sessionStorage.clear()
})

afterEach(() => {
  vi.restoreAllMocks()
  if (sessionStorageDescriptor) Object.defineProperty(window, 'sessionStorage', sessionStorageDescriptor)
})

describe('fulfillment request identity storage', () => {
  it('fails closed when reading the window.sessionStorage property throws', () => {
    Object.defineProperty(window, 'sessionStorage', {
      configurable: true,
      get() { throw new DOMException('Storage access is denied', 'SecurityError') },
    })

    expect(() => fulfillmentRequestId(operation, targetId, payload)).toThrow(FulfillmentIdempotencyStorageError)
    expect(() => fulfillmentRequestId(operation, targetId, payload)).toThrow('已阻止提交')
  })

  it('fails closed when getItem throws instead of returning a new key', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('Storage read is denied', 'SecurityError')
    })

    expect(() => fulfillmentRequestId(operation, targetId, payload)).toThrow('已阻止提交')
    expect(() => fulfillmentRequestId(operation, targetId, payload)).toThrow('已阻止提交')
  })

  it('retains one pending candidate through repeated setItem failures and uses it when storage recovers', () => {
    const attemptedValues = []
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation((_key, value) => {
      attemptedValues.push(value)
      throw new DOMException('Storage write is denied', 'QuotaExceededError')
    })

    expect(() => fulfillmentRequestId(operation, targetId, payload)).toThrow('已阻止提交')
    expect(() => fulfillmentRequestId(operation, targetId, payload)).toThrow('已阻止提交')
    expect(attemptedValues).toHaveLength(2)
    expect(JSON.parse(attemptedValues[0]).requestId).toBe(JSON.parse(attemptedValues[1]).requestId)

    vi.restoreAllMocks()
    const recoveredId = fulfillmentRequestId(operation, targetId, payload)
    expect(recoveredId).toBe(JSON.parse(attemptedValues[0]).requestId)
    expect(JSON.parse(window.sessionStorage.getItem(storageKey)).requestId).toBe(recoveredId)
  })

  it('reuses the persisted key when an identical request is retried after a network error', async () => {
    const attemptedIds = []
    let failFirstAttempt = true
    const submit = async () => {
      const requestId = fulfillmentRequestId(operation, targetId, payload)
      attemptedIds.push(requestId)
      if (failFirstAttempt) {
        failFirstAttempt = false
        throw new Error('network response lost')
      }
      return requestId
    }

    await expect(submit()).rejects.toThrow('network response lost')
    const retryId = await submit()
    expect(retryId).toBe(attemptedIds[0])
    expect(attemptedIds).toHaveLength(2)
  })

  it('creates a different key when request content changes and then reuses the changed request key', () => {
    const firstId = fulfillmentRequestId(operation, targetId, payload)
    const changedPayload = { ...payload, items: [{ order_item: 12, quantity: 3 }] }
    const changedId = fulfillmentRequestId(operation, targetId, changedPayload)

    expect(changedId).not.toBe(firstId)
    expect(fulfillmentRequestId(operation, targetId, changedPayload)).toBe(changedId)
  })

  it('clears a successful request identity so a new operation receives a fresh key', () => {
    const firstId = fulfillmentRequestId(operation, targetId, payload)
    clearFulfillmentRequest(operation, targetId)

    expect(window.sessionStorage.getItem(storageKey)).toBeNull()
    expect(fulfillmentRequestId(operation, targetId, payload)).not.toBe(firstId)
  })

  it('reports when cleanup fails after the server has confirmed success', () => {
    fulfillmentRequestId(operation, targetId, payload)
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new DOMException('Storage removal is denied', 'SecurityError')
    })

    try {
      clearFulfillmentRequest(operation, targetId)
      throw new Error('expected cleanup to fail')
    } catch (error) {
      expect(error).toBeInstanceOf(FulfillmentIdempotencyStorageError)
      expect(error.operationCompleted).toBe(true)
      expect(error.message).toContain('服务器已确认')
    }
  })
})
