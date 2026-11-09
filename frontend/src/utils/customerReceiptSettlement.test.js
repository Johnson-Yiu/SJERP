import assert from 'node:assert/strict'
import test from 'node:test'
import { saveOrVerifyCustomerReceipt } from './customerReceiptSettlement.js'

test('ambiguous receipt save is looked up before any retry', async () => {
  let saveCalls = 0
  const receipt = { id: 21, transaction_no: 'FIN-ORIGINAL', kind: 'customer_receipt' }
  const recovered = await saveOrVerifyCustomerReceipt({
    outcome: 'unknown',
    lookup: async () => receipt,
    save: async () => { saveCalls += 1; return { id: 22 } },
  })
  assert.equal(recovered.status, 'found')
  assert.equal(recovered.receipt.id, 21)
  assert.equal(saveCalls, 0)
})

test('missing ambiguous receipt remains a verify result and is not resent', async () => {
  let saveCalls = 0
  const result = await saveOrVerifyCustomerReceipt({
    outcome: 'unknown', lookup: async () => null,
    save: async () => { saveCalls += 1; return { id: 23 } },
  })
  assert.equal(result.status, 'missing')
  assert.equal(saveCalls, 0)
})

test('confirmed missing receipt can be retried with the same form identity', async () => {
  let lookupCalls = 0
  let savedIdentity = ''
  const result = await saveOrVerifyCustomerReceipt({
    outcome: 'rejected',
    lookup: async () => { lookupCalls += 1; return null },
    save: async () => { savedIdentity = 'FIN-ORIGINAL'; return { id: 24, transaction_no: savedIdentity } },
  })
  assert.equal(result.status, 'saved')
  assert.equal(result.receipt.transaction_no, 'FIN-ORIGINAL')
  assert.equal(lookupCalls, 0)
})

test('transport failure is ambiguous and requires a later lookup', async () => {
  const result = await saveOrVerifyCustomerReceipt({
    outcome: 'not-submitted', lookup: async () => null,
    save: async () => { throw new Error('connection lost') },
  })
  assert.equal(result.status, 'unknown')
})

test('a server-protected retry sends the same receipt instead of assuming a number match', async () => {
  const original = { transaction_no: 'FIN-ORIGINAL', amount: '50', currency: 'USD' }
  let sent
  const result = await saveOrVerifyCustomerReceipt({
    outcome: 'unknown', safeReplay: true,
    lookup: async () => { throw new Error('lookup must not be used') },
    save: async () => { sent = { ...original }; return { id: 24, ...original } },
  })
  assert.equal(result.status, 'saved')
  assert.deepEqual(sent, original)
})
