import assert from 'node:assert/strict'
import test from 'node:test'
import { api, apiErrorMessage, formatApiError, listAll } from './api.js'

test('formatApiError preserves field and nested item context', () => {
  assert.equal(formatApiError({ items: [{}, { quantity: ['必须大于0'] }] }), '第 2 条商品 · 数量：必须大于0')
  assert.equal(formatApiError({ customer: { detail: ['客户已停用'] } }), '客户：客户已停用')
  assert.equal(formatApiError({ items: [{}, { non_field_errors: ['商品组合无效'] }] }), '第 2 条商品：商品组合无效')
  assert.equal(formatApiError({ metadata: { unknown_field: ['值无效'] } }), 'metadata · unknown_field：值无效')
  assert.equal(formatApiError({ detail: '请求无效' }), '请求无效')
  assert.equal(formatApiError({ non_field_errors: ['两个字段不能同时填写'] }), '两个字段不能同时填写')
})

test('apiErrorMessage uses understandable network and server fallbacks', () => {
  assert.equal(apiErrorMessage({ isApiError: true, code: 'ERR_NETWORK' }), '网络连接失败，请检查网络后重试。')
  assert.equal(apiErrorMessage({ isApiError: true, status: 503, data: { detail: 'traceback' } }), '服务器暂时不可用，请稍后重试。')
})

test('API errors retain status, parsed data and the original response', async () => {
  const response = { status: 400, data: { items: [{}, { quantity: ['必须大于0'] }] } }
  const adapter = config => Promise.reject({ config, response, code: 'ERR_BAD_REQUEST' })
  await assert.rejects(api.post('/test/', {}, { adapter }), error => {
    assert.equal(error.message, '第 2 条商品 · 数量：必须大于0')
    assert.equal(error.status, 400)
    assert.equal(error.data, response.data)
    assert.equal(error.response, response)
    return true
  })
})

test('API parses Blob JSON errors before formatting', async () => {
  const blob = new Blob([JSON.stringify({ detail: '文件内容无效' })], { type: 'application/json' })
  const response = { status: 400, data: blob }
  const adapter = config => Promise.reject({ config, response, code: 'ERR_BAD_REQUEST' })
  await assert.rejects(api.post('/test/', {}, { adapter, responseType: 'blob' }), error => {
    assert.equal(error.message, '文件内容无效')
    assert.deepEqual(error.data, { detail: '文件内容无效' })
    assert.equal(error.rawData, blob)
    return true
  })
})

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
