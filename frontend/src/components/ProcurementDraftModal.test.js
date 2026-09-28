import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./ProcurementDraftModal.vue', import.meta.url)

test('procurement preview groups by supplier and currency and validates user inputs', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /supplier_name.*currency/)
  assert.match(source, /draftable_quantity/)
  assert.match(source, /CNY 固定为 1/)
  assert.match(source, /非 CNY 必填且必须大于 0/)
  assert.match(source, /Number\(item\.quantity\) > Number\(item\.draftable_quantity\)/)
  assert.match(source, /generate-purchase-drafts/)
  assert.match(source, /emit\('created', response\.data\)/)
})
