import assert from 'node:assert/strict'
import test from 'node:test'
import { api, listAll } from './api.js'

test('aggregated lists include subsequent pages and keep filters', async () => {
  const original = api.get
  const calls = []
  api.get = async (url, config) => {
    calls.push([url, config.params])
    const results = config.params.page === 1
      ? Array.from({ length: 50 }, (_, index) => ({ id: index + 1 }))
      : Array.from({ length: 15 }, (_, index) => ({ id: index + 51 }))
    return { data: { results, next: config.params.page === 1 ? '/next' : null } }
  }
  try {
    for (const url of ['/customers/', '/quotes/', '/orders/', '/skus/']) {
      const rows = await listAll(url, { params: url === '/customers/' ? { search: 'buyer' } : {} })
      assert.equal(rows.length, 65, `${url} should include both pages`)
      assert.equal(rows[50].id, 51)
      assert.equal(rows[64].id, 65)
    }
    assert.deepEqual(calls.slice(0, 2), [['/customers/', { search: 'buyer', page: 1 }], ['/customers/', { search: 'buyer', page: 2 }]])
    assert.equal(calls.length, 8)
    assert.deepEqual(calls.filter(([url]) => url === '/orders/'), [['/orders/', { page: 1 }], ['/orders/', { page: 2 }]])
  } finally { api.get = original }
})

test('listAll handles non-paginated array actions in one request', async () => {
  const original = api.get
  let callCount = 0
  api.get = async () => { callCount += 1; return { data: [{ id: 1 }, { id: 2 }] } }
  try {
    assert.deepEqual(await listAll('/categories/tree/'), [{ id: 1 }, { id: 2 }])
    assert.equal(callCount, 1)
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
