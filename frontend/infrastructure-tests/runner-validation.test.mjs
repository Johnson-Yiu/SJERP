import assert from 'node:assert/strict'
import { once } from 'node:events'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import net from 'node:net'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'

import { assertPortsAvailable, cleanupOwnedTempRoot, reservePort, sqliteDatabaseUrl } from '../scripts/run-isolated-browser-tests.mjs'

test('port allocator returns a free explicit loopback port', async () => {
  const port = await reservePort()
  assert.ok(port > 0 && port <= 65535)
  await assertPortsAvailable([{ name: 'test', port }])
})

test('port preflight rejects an occupied port instead of reusing another server', async () => {
  const server = net.createServer()
  server.listen(0, '127.0.0.1')
  await once(server, 'listening')
  const port = server.address().port
  try {
    await assert.rejects(
      assertPortsAvailable([{ name: 'occupied API', port }]),
      /occupied API port .* is already in use/,
    )
  } finally {
    server.close()
    await once(server, 'close')
  }
})

test('port preflight rejects duplicate API and Vite assignments', async () => {
  const port = await reservePort()
  await assert.rejects(
    assertPortsAvailable([{ name: 'API', port }, { name: 'Vite', port }]),
    /must use distinct ports/,
  )
})

test('SQLite URL preserves an absolute platform path for Django parsing', () => {
  const databasePath = path.resolve(os.tmpdir(), 'isolated-run', 'db.sqlite3')
  const url = sqliteDatabaseUrl(databasePath)
  if (process.platform === 'win32') {
    assert.match(url, /^sqlite:\/\/\/[A-Za-z]:\//)
    assert.doesNotMatch(url, /^sqlite:\/\/\/\/[A-Za-z]:\//)
  } else {
    assert.match(url, /^sqlite:\/\/\/\//)
  }
})

test('cleanup removes only a marked run directory under system temp', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'sunjack-r1-repair-06-'))
  const identity = { runId: 'cleanup-test', token: 'owned-token' }
  const marker = path.join(root, '.sunjack-playwright-isolation.json')
  await writeFile(marker, JSON.stringify({ ...identity, root: path.resolve(root) }), { flag: 'wx' })
  await writeFile(path.join(root, 'db.sqlite3'), 'synthetic isolated database')
  await cleanupOwnedTempRoot(root, identity)
  await assert.rejects(readFile(root), { code: 'ENOENT' })
})

test('cleanup refuses an ownership marker belonging to another run', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'sunjack-r1-repair-06-'))
  const marker = path.join(root, '.sunjack-playwright-isolation.json')
  await writeFile(marker, JSON.stringify({ runId: 'someone-else', token: 'other-token', root: path.resolve(root) }), { flag: 'wx' })
  try {
    await assert.rejects(
      cleanupOwnedTempRoot(root, { runId: 'not-owner', token: 'not-owner' }),
      /ownership marker does not match/,
    )
    await readFile(marker, 'utf8')
  } finally {
    await rm(root, { recursive: true, force: false })
  }
})
