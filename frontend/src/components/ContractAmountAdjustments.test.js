import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

test('contract adjustment history renders the backend status display', async () => {
  const source = await readFile(new URL('./ContractAmountAdjustments.vue', import.meta.url), 'utf8')
  assert.match(source, /row\.status_display/)
  assert.match(source, /确认/)
  assert.match(source, /拒绝/)
})
