import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./OrderDetailModal.vue', import.meta.url)

test('order workbench exposes shipment history and reversal flow', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /发货记录/)
  assert.match(source, /shipments\/\$\{shipmentReversalTarget\.value\.id\}\/reverse/)
  assert.match(source, /shipment\.has_overage/)
  assert.match(source, /包含超发\/增补，暂不能直接冲销/)
  assert.match(source, /已冲销/)
  assert.match(source, /shipmentReversalReason/)
})
