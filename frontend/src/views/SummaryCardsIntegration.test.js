import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const pages = [
  'ResourcePage.vue',
  'ProductPage.vue',
  'SKUPage.vue',
  'PackagingPage.vue',
  'PurchaseOrderPage.vue',
  'PaymentPlanPage.vue',
  'TransactionPage.vue',
]

test('main list pages reuse the shared summary cards', async () => {
  await Promise.all(pages.map(async name => {
    const source = await readFile(new URL(`./${name}`, import.meta.url), 'utf8')
    assert.match(source, /import SummaryCards from '\.\.\/components\/SummaryCards\.vue'/)
    assert.match(source, /<SummaryCards :items=/)
  }))
})
