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

test('batch launcher uses Windows CRLF line endings for cmd.exe', async () => {
  const source = await readFile(new URL('../启动库存履约分支.bat', import.meta.url))

  const text = source.toString('utf8')
  assert.ok(text.includes('\r\n'))
  assert.equal(text.replaceAll('\r\n', '').includes('\n'), false)
})

test('launcher uses TCP probes for both fixed ports before starting either service', async () => {
  const source = await readFile(launcher, 'utf8')

  assert.match(source, /System\.Net\.Sockets\.TcpClient/)
  assert.match(source, /\$backendAlreadyRunning = Test-PortOpen \$BackendPort/)
  assert.match(source, /\$frontendAlreadyRunning = Test-PortOpen \$FrontendPort/)
})

test('launcher opens the inventory page when both branch services already run', async () => {
  const source = await readFile(launcher, 'utf8')

  assert.match(source, /\$backendAlreadyRunning = Test-PortOpen \$BackendPort/)
  assert.match(source, /\$frontendAlreadyRunning = Test-PortOpen \$FrontendPort/)
  assert.match(source, /if \(\$backendAlreadyRunning -and \$frontendAlreadyRunning\)/)
})
