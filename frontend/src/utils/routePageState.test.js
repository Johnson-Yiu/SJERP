import assert from 'node:assert/strict'
import test from 'node:test'
import { clearModalRoute } from './modalNavigation.js'
import { pageIdentityKey, routeDataQuery, routeDataQuerySignature, withoutModalActionQuery } from './routePageState.js'

test('page identity stays on the same path across transient query changes', () => {
  assert.equal(pageIdentityKey({ path: '/orders', fullPath: '/orders?detail=4' }), '/orders')
  assert.equal(pageIdentityKey({ path: '/orders', fullPath: '/orders?detail=5' }), '/orders')
  assert.notEqual(pageIdentityKey({ path: '/orders' }), pageIdentityKey({ path: '/quotes' }))
})

test('list query data excludes modal and detail actions while retaining business context', () => {
  const query = { detail: '4', create: '1', edit: '10', returnTo: '/orders?status=draft', customer: '5', supplier: '9', status: 'confirmed', sku: '12', date: '2026-10-05' }
  assert.deepEqual(routeDataQuery(query), { customer: '5', supplier: '9', status: 'confirmed', sku: '12', date: '2026-10-05' })
  assert.equal(routeDataQuerySignature({ ...query, detail: '5' }), routeDataQuerySignature(query))
  assert.notEqual(routeDataQuerySignature(query), routeDataQuerySignature({ ...query, status: 'draft' }))
})

test('closing a route modal removes action keys and preserves all context query values', async () => {
  const query = { create: '1', edit: '10', returnTo: '/orders?detail=4', customer: '5', supplier: '9', status: 'confirmed', order: '8' }
  assert.deepEqual(withoutModalActionQuery(query), { customer: '5', supplier: '9', status: 'confirmed', order: '8' })

  let replaced
  await clearModalRoute({ replace: async value => { replaced = value } }, { path: '/purchase-orders', query, hash: '#create' })
  assert.deepEqual(replaced, { path: '/purchase-orders', query: { customer: '5', supplier: '9', status: 'confirmed', order: '8' }, hash: '#create' })
})
