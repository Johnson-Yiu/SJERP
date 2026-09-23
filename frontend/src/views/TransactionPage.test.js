import { readFile } from 'node:fs/promises'
import test from 'node:test'
import assert from 'node:assert/strict'

const componentUrl = new URL('./TransactionPage.vue', import.meta.url)

test('direct customer receipts validate and serialize a positive amount before saving', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /const amount = Number\(form\.amount\)/)
  assert.match(source, /请输入大于 0 的有效金额/)
  assert.match(source, /amount: String\(amount\)/)
  assert.match(source, /v-model\.number="form\.amount"/)
})
