import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { access, copyFile, mkdir, mkdtemp, readFile, readdir, rm, symlink, writeFile } from 'node:fs/promises'
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
  isolatedCashAccountEnvironment,
  isolatedFixtureSeed,
  isolatedFixtureSeeds,
  reservePort,
  resolvePlaywrightSelection,
  sqliteDatabaseUrl,
  stopOwnedProcessTree,
  verifyProxiedApiIdentity,
  waitForIdentity,
} from '../scripts/run-isolated-browser-tests.mjs'

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = path.resolve(frontendRoot, '..')

test('bank-fee selection receives fixed synthetic accounts without external configuration', async () => {
  const selection = await resolvePlaywrightSelection(['--business-test', 'independent-bank-fee-real.spec.js'])
  assert.deepEqual(isolatedCashAccountEnvironment(selection), { RMB_CASH_ACCOUNT_IDS: 'SYNTH_FX,SYNTH_CNY' })
  assert.equal(({ RMB_CASH_ACCOUNT_IDS: 'OUTER_ALIAS', ...isolatedCashAccountEnvironment(selection) }).RMB_CASH_ACCOUNT_IDS, 'SYNTH_FX,SYNTH_CNY')
})

test('full business suite receives bank-fee synthetic accounts at the standard CI entry', async () => {
  const selection = await resolvePlaywrightSelection(['--all-business-tests'])
  assert.deepEqual(isolatedCashAccountEnvironment(selection), { RMB_CASH_ACCOUNT_IDS: 'SYNTH_FX,SYNTH_CNY' })
})

test('other business selections and infrastructure smoke preserve existing account configuration', async () => {
  for (const selection of [await resolvePlaywrightSelection([]), await resolvePlaywrightSelection(['--business-test', 'cash-events-p2b.spec.js']), undefined]) {
    const delta = isolatedCashAccountEnvironment(selection)
    assert.deepEqual(delta, {})
    assert.equal(({ RMB_CASH_ACCOUNT_IDS: 'EXISTING_ALIAS', ...delta }).RMB_CASH_ACCOUNT_IDS, 'EXISTING_ALIAS')
    assert.equal(Object.hasOwn({ ...delta }, 'RMB_CASH_ACCOUNT_IDS'), false)
  }
})

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
  assert.deepEqual(await resolvePlaywrightSelection(['--all-business-tests']), {
    businessTest: '*', businessSuite: true, excludedBusinessTests: [],
  })
  assert.deepEqual(await resolvePlaywrightSelection([
    '--all-business-tests', '--exclude-business-test', 'iss022-moq-real.spec.js',
  ]), {
    businessTest: '*', businessSuite: true, excludedBusinessTests: ['iss022-moq-real.spec.js'],
  })
  assert.equal((await resolvePlaywrightSelection(['--business-test', 'import-ux.spec.js'])).businessTest, 'import-ux.spec.js')
  for (const args of [
    ['--config', '../playwright.config.js'],
    ['--config=../playwright.config.js'],
    ['--test-dir=./browser-tests'],
    ['--grep', 'synthetic-only'],
    ['--business-test', '../playwright.config.js'],
    ['--business-test', 'missing.spec.js'],
    ['--all-business-tests', '--exclude-business-test', '../playwright.config.js'],
    ['--all-business-tests', '--exclude-business-test', 'missing.spec.js'],
  ]) {
    await assert.rejects(resolvePlaywrightSelection(args))
  }
  assert.ok(browserArgs().includes(path.join(frontendRoot, 'playwright.isolated.config.js')))
})

test('only allowlisted real API suites receive fixed synthetic fixture seeds', () => {
  assert.equal(path.basename(isolatedFixtureSeed('iss006-frontend-storage-chrome.spec.js').scriptPath), 'seed_iss006_frontend_storage_browser.py')
  assert.equal(isolatedFixtureSeed('iss006-frontend-storage-chrome.spec.js').evidenceEnv, 'ISS006_STORAGE_EVIDENCE_DIR')
  assert.equal(path.basename(isolatedFixtureSeed('iss007-attachment-real.spec.js').scriptPath), 'seed_isolated.py')
  assert.equal(isolatedFixtureSeed('iss007-attachment-real.spec.js').evidenceEnv, 'ISS007_EVIDENCE_DIR')
  assert.equal(path.basename(isolatedFixtureSeed('iss007-image-snapshot-real.spec.js').scriptPath), 'seed_iss007_image_browser.py')
  assert.equal(isolatedFixtureSeed('iss007-image-snapshot-real.spec.js').evidenceEnv, 'ISS007_EVIDENCE_DIR')
  assert.equal(path.basename(isolatedFixtureSeed('iss022-moq-real.spec.js').scriptPath), 'seed_iss022_browser.py')
  assert.equal(isolatedFixtureSeed('iss022-moq-real.spec.js').evidenceEnv, 'ISS022_EVIDENCE_DIR')
  assert.equal(path.basename(isolatedFixtureSeed('iss075-payment-terms-real.spec.js').scriptPath), 'seed_iss075_browser.py')
  assert.equal(isolatedFixtureSeed('iss075-payment-terms-real.spec.js').evidenceEnv, 'ISS075_EVIDENCE_DIR')
  assert.equal(path.basename(isolatedFixtureSeed('iss055-customer-404-real.spec.js').scriptPath), 'seed.py')
  assert.equal(isolatedFixtureSeed('iss055-customer-404-real.spec.js').evidenceEnv, 'ISS055_EVIDENCE_DIR')
  assert.equal(isolatedFixtureSeed('iss028-035-category-schema.spec.js').scriptPath, null)
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
  assert.equal(path.basename(isolatedFixtureSeeds({ businessTest: 'quote-editor-mobile-actions.spec.js' })[0].scriptPath), 'prepare_quote_actions.py')
  for (const businessTest of [null, '', 'import-ux.spec.js', '../seed.py']) {
    assert.equal(isolatedFixtureSeed(businessTest), null)
  }
  assert.equal(isolatedFixtureSeeds({ businessSuite: true }).length, 3)
  assert.equal(isolatedFixtureSeeds({ businessSuite: true, excludedBusinessTests: ['iss022-moq-real.spec.js'] }).length, 2)
})

test('API identity comparison checks run ID, token, SQLite path, and MEDIA_ROOT', () => {
  const identity = { runId: 'run', token: 'secret', database: path.join(os.tmpdir(), 'a.sqlite3'), mediaRoot: path.join(os.tmpdir(), 'media') }
  assert.doesNotThrow(() => assertApiIdentity({ ...identity }, identity, 'API'))
  for (const field of ['runId', 'token', 'database', 'mediaRoot']) {
    assert.throws(() => assertApiIdentity({ ...identity, [field]: `wrong-${identity[field]}` }, identity, 'API'), new RegExp(field))
  }
  assert.throws(
    () => assertApiIdentity({ ...identity, rbacEnforcement: true }, { ...identity, rbacEnforcement: false }, 'API'),
    /rbacEnforcement/,
  )
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
    ], { cwd: frontendRoot, env, detached: process.platform !== 'win32', windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] })
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
    await stopOwnedProcessTree(vite)
    if (api.listening) {
      api.close()
      await once(api, 'close')
    }
    await rm(tempRoot, { recursive: true, force: false })
  }
})

test('browser CI invokes the isolated suite and keeps run evidence under an isolated root', async () => {
  const [config, packageText, workflow, suiteRunner] = await Promise.all([
    readFile(path.join(frontendRoot, 'playwright.config.js'), 'utf8'),
    readFile(path.join(frontendRoot, 'package.json'), 'utf8'),
    readFile(path.join(frontendRoot, '..', '.github', 'workflows', 'ci.yml'), 'utf8'),
    readFile(path.join(frontendRoot, 'scripts', 'run-playwright-suite-stability.mjs'), 'utf8'),
  ])
  const packageJson = JSON.parse(packageText)
  assert.match(config, /process\.env\.CI/)
  assert.match(config, /const webServer = usePlaywrightWebServer/)
  assert.match(config, /\.\.\.\(webServer \? \{ webServer \} : \{\}\)/)
  assert.match(packageJson.scripts['test:browser'], /run-playwright-suite-stability\.mjs/)
  assert.ok(workflow.includes('sudo apt-get install --yes xvfb xauth'))
  assert.ok(workflow.includes('command -v xvfb-run'))
  assert.ok(workflow.includes('command -v xauth'))
  assert.ok(workflow.includes('xvfb-run --auto-servernum --server-args="-screen 0 1440x1000x24 -nolisten tcp" npm run test:browser'))
  assert.ok(workflow.includes('R1_PLAYWRIGHT_EVIDENCE_ROOT: ${{ github.workspace }}/docs/uat-evidence/ci-${{ github.run_id }}-${{ github.run_attempt }}'))
  const jobsText = workflow.slice(workflow.indexOf('\njobs:'))
  const jobHeaders = [...jobsText.matchAll(/^  ([\w-]+):\r?\n/gm)]
  const jobs = Object.fromEntries(jobHeaders.map((header, index) => [
    header[1], jobsText.slice(header.index, jobHeaders[index + 1]?.index),
  ]))
  assert.deepEqual(Object.keys(jobs), ['backend', 'backend-postgres', 'frontend'])
  assert.equal((workflow.match(/pip install -r backend\/requirements\.lock/g) || []).length, 3)
  for (const [name, job] of Object.entries(jobs)) {
    assert.match(job, /uses: actions\/setup-python@v5\s+with:\s+python-version: '3\.12'/, `${name} requires Python 3.12`)
    assert.equal((job.match(/run: pip install -r backend\/requirements\.lock/g) || []).length, 1, `${name} installs all locked Python dependencies`)
    assert.ok(job.indexOf('actions/setup-python@v5') < job.indexOf('run: pip install -r backend/requirements.lock'))
    const validationSteps = job.replace(/      - name: Retain isolated browser and print evidence\r?\n        if: always\(\)\r?\n        uses: actions\/upload-artifact@v4[\s\S]*$/, '')
    assert.doesNotMatch(validationSteps, /^\s+(?:if|continue-on-error):/m, `${name} must not skip or ignore required validation`)
  }
  const postgres = jobs['backend-postgres']
  assert.match(postgres, /image: postgres:17/)
  assert.match(postgres, /APP_STAGE: staging/)
  assert.match(postgres, /DEVELOPMENT_SUPERADMIN: 'false'/)
  assert.match(postgres, /RBAC_ENFORCEMENT: 'true'/)
  assert.doesNotMatch(postgres.slice(0, postgres.indexOf('    steps:')), /\$\{\{ runner\./, 'runner context belongs in a step, not job-level env')
  assert.match(postgres, /MEDIA_ROOT: \$\{\{ runner\.temp \}\}\/sunjack-postgres-media/)
  const mediaPreparation = postgres.slice(postgres.indexOf('- name: Create isolated private media directory'), postgres.indexOf('- name: Django system check'))
  assert.match(mediaPreparation, /env:\s+MEDIA_ROOT: \$\{\{ runner\.temp \}\}\/sunjack-postgres-media/)
  assert.ok(mediaPreparation.includes('install -d -m 700 "$MEDIA_ROOT"'))
  assert.ok(mediaPreparation.includes('echo "MEDIA_ROOT=$MEDIA_ROOT" >> "$GITHUB_ENV"'))
  assert.ok(postgres.indexOf('install -d -m 700 "$MEDIA_ROOT"') < postgres.indexOf('run: python manage.py check'))
  for (const name of ['backend', 'backend-postgres']) {
    const testCommand = name === 'backend-postgres' ? 'python manage.py test --verbosity 2' : 'python manage.py test'
    assert.ok(jobs[name].split(/\r?\n/).some(line => line.trim() === `run: ${testCommand}`), `${name} runs the unfiltered full test suite`)
    assert.ok(jobs[name].indexOf('run: pip install -r backend/requirements.lock') < jobs[name].indexOf('run: python manage.py check'))
  }
  const frontend = jobs.frontend
  const chromiumInstall = frontend.indexOf('run: npx playwright install --with-deps chromium')
  assert.ok(chromiumInstall >= 0)
  assert.ok(frontend.indexOf('run: npm ci') < chromiumInstall)
  for (const command of [
    'npm run test:unit',
    'node --test tests/detail-drawer-typography.spec.js',
    'npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js',
    'npm run test:browser',
    'npm run build',
  ]) {
    const position = frontend.indexOf(command === 'npm run test:browser'
      ? 'xvfb-run --auto-servernum --server-args="-screen 0 1440x1000x24 -nolisten tcp" npm run test:browser'
      : `run: ${command}`)
    assert.ok(position > chromiumInstall, `${command} must execute after Chromium installation`)
    assert.ok(position > frontend.indexOf('run: pip install -r backend/requirements.lock'))
  }
  assert.doesNotMatch(workflow, /pip install -r backend\/requirements\.txt/)
  assert.doesNotMatch(workflow, /run:\s*npx playwright test/)
  assert.match(suiteRunner, /process\.env\.R1_PLAYWRIGHT_EVIDENCE_ROOT/)
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
      assert.match(result.output, /Owned API and Vite process trees stopped; both ports are released\./)
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
    for (const identity of identities) {
      await assert.rejects(access(path.dirname(identity.database)), { code: 'ENOENT' })
      await assert.rejects(access(identity.media), { code: 'ENOENT' })
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
