import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./SupplierAllocationModal.vue', import.meta.url)

test('supplier allocation metrics follow the selected SupplierSKU rather than the first source', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /function sourceForCandidate\(candidate\)/)
  assert.match(source, /selectedSupplierSku\.value/)
  assert.doesNotMatch(source, /candidate\.supplier_skus\[0\]/)
  assert.match(source, /sourceForCandidate\(candidate\)\?\.lead_time_days/)
  assert.match(source, /sourceForCandidate\(candidate\)\?\.moq/)
  assert.match(source, /选择当前采购来源/)
  assert.match(source, /已经生成的采购单保留原采购来源，不会被改写/)
})
