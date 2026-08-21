import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const launcher = new URL('../启动库存履约分支.ps1', import.meta.url)

test('inventory fulfillment launcher owns fixed branch ports and opens the inventory page', async () => {
  const source = await readFile(launcher, 'utf8')

  assert.match(source, /\$BackendPort = 8138/)
  assert.match(source, /\$FrontendPort = 5228/)
  assert.match(source, /Join-Path \$BackendDir "manage\.py"\) migrate --noinput/)
  assert.match(source, /VITE_API_PROXY_PORT/)
  assert.match(source, /127\.0\.0\.1:\$FrontendPort\/inventory/)
})
