import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { copyFile, mkdir, mkdtemp, readFile, readdir, rm, symlink, writeFile } from 'node:fs/promises'
import http from 'node:http'
import { fileURLToPath } from 'node:url'
import net from 'node:net'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'

import {
  assertPortsAvailable,
  assertApiIdentity,
  browserArgs,
  cleanupOwnedTempRoot,
  isolatedFixtureSeed,
  reservePort,
  resolvePlaywrightSelection,
  sqliteDatabaseUrl,
  verifyProxiedApiIdentity,
  waitForIdentity,
} from '../scripts/run-isolated-browser-tests.mjs'

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = path.resolve(frontendRoot, '..')

function runProcess(command, args, options) {
  const child = spawn(command, args, {
    ...options,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  let output = ''
  child.stdout.on('data', chunk => { output += chunk.toString() })
  child.stderr.on('data', chunk => { output += chunk.toString() })
  return new Promise((resolve, reject) => {
    child.once('error', reject)
    child.once('close', (code, signal) => resolve({ code, signal, output }))
  })
}

async function createShadowWorktree(parent, label) {
  const root = path.join(parent, label)
  const shadowFrontend = path.join(root, 'frontend')
  const files = [
    'scripts/run-isolated-browser-tests.mjs',
    'playwright.isolated.config.js',
    'vite.isolated.config.js',
    'infrastructure-tests/isolated-runtime.spec.js',
    'package.json',
  ]
  for (const relative of files) {
    const destination = path.join(shadowFrontend, relative)
    await mkdir(path.dirname(destination), { recursive: true })
    await copyFile(path.join(frontendRoot, relative), destination)
  }
  const linkType = process.platform === 'win32' ? 'junction' : 'dir'
  const realModules = path.join(frontendRoot, 'node_modules')
  const shadowModules = path.join(shadowFrontend, 'node_modules')
  await mkdir(shadowModules)
  for (const entry of await readdir(realModules, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name === '.bin' || entry.name === '.vite' || entry.name === '.vite-temp') continue
    const source = path.join(realModules, entry.name)
    const destination = path.join(shadowModules, entry.name)
    if (entry.name.startsWith('@')) {
      await mkdir(destination)
      for (const scopedPackage of await readdir(source, { withFileTypes: true })) {
        if (scopedPackage.isDirectory()) {
          await symlink(path.join(source, scopedPackage.name), path.join(destination, scopedPackage.name), linkType)
        }
      }
    } else {
      await symlink(source, destination, linkType)
    }
  }
  await symlink(path.join(repositoryRoot, 'backend'), path.join(root, 'backend'), linkType)
  return { root, frontend: shadowFrontend }
}

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

test('actual runner fails before creating isolated resources when its API port is occupied', async () => {
  const server = net.createServer()
  server.listen(0, '127.0.0.1')
  await once(server, 'listening')
  const apiPort = server.address().port
  const vitePort = await reservePort()
  const env = { ...process.env, ISOLATED_API_PORT: String(apiPort), ISOLATED_VITE_PORT: String(vitePort) }
  const result = await runProcess(process.execPath, [path.join(frontendRoot, 'scripts/run-isolated-browser-tests.mjs')], {
    cwd: frontendRoot,
    env,
  })
  try {
    assert.notEqual(result.code, 0)
    assert.match(result.output, /EADDRINUSE|already in use|unavailable/)
    assert.doesNotMatch(result.output, /Isolation run /)
    assert.equal(server.listening, true, 'the pre-existing listener must remain untouched')
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

test('API identity mismatch is rejected before browser tests can proceed', async () => {
  const server = http.createServer((_request, response) => {
    response.writeHead(200, { 'content-type': 'application/json' })
    response.end(JSON.stringify({ runId: 'another-worktree', token: 'wrong-token' }))
  })
  server.listen(0, '127.0.0.1')
  await once(server, 'listening')
  const { port } = server.address()
  try {
    await assert.rejects(
      waitForIdentity(
        { exitCode: null, signalCode: null, isolationOutput: () => '' },
        `http://127.0.0.1:${port}/api/__test__/isolation/`,
        { runId: 'expected-run', token: 'expected-token' },
        'Django API',
        { timeoutMs: 30, pollIntervalMs: 2 },
      ),
      /Django API identity check failed: Django API responded with HTTP 200 or a mismatched run identity/,
    )
  } finally {
    server.close()
    await once(server, 'close')
  }
})

test('only an existing browser test file can be selected; Playwright service and config overrides are rejected', async () => {
  assert.equal((await resolvePlaywrightSelection([])).businessTest, null)
  assert.equal((await resolvePlaywrightSelection(['--business-test', 'import-ux.spec.js'])).businessTest, 'import-ux.spec.js')
  for (const args of [
    ['--config', '../playwright.config.js'],
    ['--config=../playwright.config.js'],
    ['--test-dir=./browser-tests'],
    ['--grep', 'synthetic-only'],
    ['--business-test', '../playwright.config.js'],
    ['--business-test', 'missing.spec.js'],
  ]) {
    await assert.rejects(resolvePlaywrightSelection(args))
  }
  assert.ok(browserArgs().includes(path.join(frontendRoot, 'playwright.isolated.config.js')))
})

test('only allowlisted real API suites receive fixed synthetic fixture seeds', () => {
  assert.equal(path.basename(isolatedFixtureSeed('iss022-moq-real.spec.js').scriptPath), 'seed_iss022_browser.py')
  assert.equal(isolatedFixtureSeed('iss022-moq-real.spec.js').evidenceEnv, 'ISS022_EVIDENCE_DIR')
  assert.equal(path.basename(isolatedFixtureSeed('iss075-payment-terms-real.spec.js').scriptPath), 'seed_iss075_browser.py')
  assert.equal(isolatedFixtureSeed('iss075-payment-terms-real.spec.js').evidenceEnv, 'ISS075_EVIDENCE_DIR')
  for (const businessTest of [
    'historical-orders-fix-02.spec.js',
    'historical-orders-fix-03.spec.js',
    'iss029-recipient-snapshot.spec.js',
  ]) {
    assert.equal(path.basename(isolatedFixtureSeed(businessTest).scriptPath), 'prepare_evidence.py')
    assert.equal(isolatedFixtureSeed(businessTest).evidenceEnv, 'R1_REPAIR_EVIDENCE_DIR')
  }
  assert.equal(path.basename(isolatedFixtureSeed('quote-editor-mobile-actions.spec.js').scriptPath), 'prepare_quote_actions.py')
  assert.equal(isolatedFixtureSeed('quote-editor-mobile-actions.spec.js').evidenceEnv, 'R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR')
  for (const businessTest of [null, '', 'import-ux.spec.js', '../seed.py', 'iss055-customer-404-real.spec.js']) {
    assert.equal(isolatedFixtureSeed(businessTest), null)
  }
})

test('API identity comparison checks run ID, token, SQLite path, and MEDIA_ROOT', () => {
  const identity = { runId: 'run', token: 'secret', database: path.join(os.tmpdir(), 'a.sqlite3'), mediaRoot: path.join(os.tmpdir(), 'media') }
  assert.doesNotThrow(() => assertApiIdentity({ ...identity }, identity, 'API'))
  for (const field of ['runId', 'token', 'database', 'mediaRoot']) {
    assert.throws(() => assertApiIdentity({ ...identity, [field]: `wrong-${identity[field]}` }, identity, 'API'), new RegExp(field))
  }
})

test('a real Vite /api proxy to the wrong database and MEDIA_ROOT is rejected before Playwright', { timeout: 30000 }, async () => {
  const tempRoot = await mkdtemp(path.join(os.tmpdir(), 'sunjack-proxy-target-rejection-'))
  const runId = 'proxy-validation-run'
  const token = 'proxy-validation-token'
  const database = path.join(tempRoot, 'db.sqlite3')
  const mediaRoot = path.join(tempRoot, 'media')
  const wrongIdentity = {
    runId,
    token,
    database: path.join(tempRoot, 'other-worktree.sqlite3'),
    mediaRoot: path.join(tempRoot, 'other-media'),
  }
  let proxiedPath = null
  const api = http.createServer((request, response) => {
    proxiedPath = request.url
    response.writeHead(200, { 'content-type': 'application/json' })
    response.end(JSON.stringify(wrongIdentity))
  })
  let vite
  try {
    api.listen(0, '127.0.0.1')
    await once(api, 'listening')
    const apiPort = api.address().port
    const vitePort = await reservePort()
    const baseURL = `http://127.0.0.1:${vitePort}`
    const env = {
      ...process.env,
      ISOLATED_TEST_ROOT: tempRoot,
      ISOLATED_TEST_RUN_ID: runId,
      ISOLATED_TEST_TOKEN: token,
      ISOLATED_API_PORT: String(apiPort),
      ISOLATED_VITE_PORT: String(vitePort),
    }
    vite = spawn(process.execPath, [
      path.join(frontendRoot, 'node_modules', 'vite', 'bin', 'vite.js'),
      '--configLoader', 'runner', '--config', path.join(frontendRoot, 'vite.isolated.config.js'),
      '--host', '127.0.0.1', '--port', String(vitePort),
    ], { cwd: frontendRoot, env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] })
    let output = ''
    vite.stdout.on('data', chunk => { output += chunk.toString() })
    vite.stderr.on('data', chunk => { output += chunk.toString() })
    vite.isolationOutput = () => output

    await waitForIdentity(vite, `${baseURL}/__test__/isolation/`, { runId, token }, 'Vite', { timeoutMs: 15000 })
    await assert.rejects(
      verifyProxiedApiIdentity(vite, baseURL, { runId, token, database, mediaRoot }, { runId, token, database, mediaRoot }, { timeoutMs: 5000 }),
      /database, mediaRoot.*refusing browser tests/,
    )
    assert.equal(proxiedPath, `/api/__test__/isolation/${token}/`, 'identity must traverse the Vite /api proxy')
  } finally {
    if (vite && vite.exitCode === null && vite.signalCode === null) {
      vite.kill('SIGTERM')
      await Promise.race([once(vite, 'exit'), new Promise(resolve => setTimeout(resolve, 5000))])
    }
    if (api.listening) {
      api.close()
      await once(api, 'close')
    }
    await rm(tempRoot, { recursive: true, force: false })
  }
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

test('two independent worktree runtimes can start concurrently without sharing ports or data', { timeout: 120000 }, async t => {
  const parent = await mkdtemp(path.join(os.tmpdir(), 'sunjack-parallel-worktrees-'))
  try {
    const worktrees = await Promise.all([
      createShadowWorktree(parent, 'worktree-a'),
      createShadowWorktree(parent, 'worktree-b'),
    ])
    const env = { ...process.env }
    delete env.ISOLATED_API_PORT
    delete env.ISOLATED_VITE_PORT
    const results = await Promise.all(worktrees.map(worktree => runProcess(
      process.execPath,
      [path.join(worktree.frontend, 'scripts/run-isolated-browser-tests.mjs')],
      { cwd: worktree.frontend, env },
    )))
    for (const result of results) {
      assert.equal(result.code, 0, result.output)
      assert.match(result.output, /Migration completeness check: passed/)
      assert.match(result.output, /Playwright suite: passed/)
      assert.match(result.output, /Removed only this run's marked temporary database and MEDIA_ROOT/)
    }
    const identities = results.map(({ output }) => {
      const match = output.match(/Isolation run ([\w-]+); API 127\.0\.0\.1:(\d+); Vite 127\.0\.0\.1:(\d+)/)
      assert.ok(match, output)
      const database = output.match(/Isolated SQLite: (.+)/)?.[1]
      const media = output.match(/Isolated MEDIA_ROOT: (.+)/)?.[1]
      assert.ok(database, output)
      assert.ok(media, output)
      return { runId: match[1], apiPort: match[2], vitePort: match[3], database, media }
    })
    for (const field of ['runId', 'apiPort', 'vitePort', 'database', 'media']) {
      assert.notEqual(identities[0][field], identities[1][field], `${field} must be unique per worktree run`)
    }
    assert.equal(
      new Set(identities.flatMap(({ apiPort, vitePort }) => [apiPort, vitePort])).size,
      4,
      'all concurrent API and Vite listeners must have distinct ports',
    )
    t.diagnostic(`parallel isolated runs: ${JSON.stringify(identities)}`)
  } finally {
    await rm(parent, { recursive: true, force: false })
  }
})
