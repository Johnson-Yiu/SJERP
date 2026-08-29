import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const launcher = new URL('../start-main-worktree.ps1', import.meta.url)

test('main launcher owns the consolidated service ports and opens the root page', async () => {
  const source = await readFile(launcher, 'utf8')

  assert.match(source, /\$BackendPort = 8100/)
  assert.match(source, /\$FrontendPort = 5191/)
  assert.match(source, /& \$VenvPython \$ManagePy migrate --noinput/)
  assert.match(source, /VITE_API_PROXY_PORT/)
  assert.match(source, /127\.0\.0\.1:\$FrontendPort/)
})

test('batch launcher uses Windows CRLF line endings for cmd.exe', async () => {
  const source = await readFile(new URL('../启动主工作树.bat', import.meta.url))

  const text = source.toString('utf8')
  assert.ok(text.includes('\r\n'))
  assert.equal(text.replaceAll('\r\n', '').includes('\n'), false)
  assert.match(text, /start-main-worktree\.ps1/)
})

test('launcher uses TCP probes for both fixed ports before starting either service', async () => {
  const source = await readFile(launcher, 'utf8')

  assert.match(source, /System\.Net\.Sockets\.TcpClient/)
  assert.match(source, /if \(-not \(Test-PortOpen \$BackendPort\)\)/)
  assert.match(source, /if \(-not \(Test-PortOpen \$FrontendPort\)\)/)
})

test('launcher opens the root page when both services already run', async () => {
  const source = await readFile(launcher, 'utf8')

  assert.match(source, /if \(-not \(Wait-ForPort \$BackendPort 30\)\)/)
  assert.match(source, /if \(-not \(Wait-ForPort \$FrontendPort 30\)\)/)
  assert.match(source, /Start-Process \$url/)
})
