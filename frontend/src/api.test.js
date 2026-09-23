import assert from 'node:assert/strict'
import test from 'node:test'
import { api, listAll } from './api.js'

test('aggregated lists include subsequent pages and keep filters', async () => {
  const original = api.get
  const calls = []
  api.get = async (url, config) => {
    calls.push([url, config.params])
    return { data: { results: [config.params.page], next: config.params.page === 1 ? '/next' : null } }
  }
  try {
    assert.deepEqual(await listAll('/payment-plans/', { params: { status: 'open' } }), [1, 2])
    assert.deepEqual(calls, [['/payment-plans/', { status: 'open', page: 1 }], ['/payment-plans/', { status: 'open', page: 2 }]])
  } finally { api.get = original }
})

test('failed later pages never return a misleading partial total', async () => {
  const original = api.get
  api.get = async (url, config) => {
    if (config.params.page === 2) throw new Error('second page unavailable')
    return { data: { results: [{ amount: 100 }], next: '/next' } }
  }
  try { await assert.rejects(listAll('/transactions/'), /second page unavailable/) }
  finally { api.get = original }
})
