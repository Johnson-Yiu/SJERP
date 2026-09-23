import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import vm from 'node:vm'
import { baseQuantity } from '../utils/tradeUnits.js'

async function editor(post) {
  const source = await readFile(new URL('./QuoteEditorModal.vue', import.meta.url), 'utf8')
  const check = source.slice(source.indexOf('const salesChecks ='), source.indexOf('watch(() => JSON.stringify([draft.quote_date'))
  const save = source.slice(source.indexOf('async function save('), source.indexOf('async function retryExport'))
  const context = vm.createContext({ baseQuantity, ref: value => ({ value }), api: { post }, draft: { quote_date: '2026-09-16', items: [{ sku: 7, quantity: 50 }] }, validate: () => '', payload: () => ({}), saving: { value: false }, errorMessage: { value: '' }, exportError: { value: '' }, savedQuote: { value: null }, props: { mode: 'create' }, emit: () => {}, clearTimeout })
  vm.runInContext(`${check}\n${save}\nglobalThis.state = { salesChecks, salesCheckError };`, context)
  return context
}

test('quote save stops on MOQ violation or unavailable validation service', async () => {
  for (const fail of [false, true]) {
    const calls = []
    const context = await editor(async path => {
      calls.push(path)
      if (fail) throw new Error('服务不可用')
      return { data: [{ line: 1, rules: [{ minimum_quantity: '100' }], errors: ['最低 100 pcs'] }] }
    })
    await context.save()
    assert.deepEqual(calls, ['/sales-rules/check-quote/'])
    assert.ok(context.errorMessage.value)
    assert.equal(context.saving.value, false)
  }
})

test('valid MOQ check allows quote creation and ignores stale check responses', async () => {
  const calls = []
  const context = await editor(async path => {
    calls.push(path)
    return { data: path.includes('check-quote') ? [{ rules: [], errors: [] }] : { id: 42 } }
  })
  await context.save()
  assert.deepEqual(calls, ['/sales-rules/check-quote/', '/quotes/'])
  assert.equal(context.savedQuote.value.id, 42)
  const pending = []
  context.api.post = () => new Promise(resolve => pending.push(resolve))
  const old = context.checkSalesRules(), current = context.checkSalesRules()
  pending[1]({ data: [{ rules: [], errors: ['current'] }] })
  await current
  pending[0]({ data: [{ rules: [], errors: [] }] })
  await old
  assert.equal(context.state.salesChecks.value[0].errors[0], 'current')
})
