import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { createServer } from 'node:net'
import { randomBytes, randomUUID } from 'node:crypto'
import { lstat, mkdtemp, mkdir, readFile, realpath, rm, stat, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const scriptPath = fileURLToPath(import.meta.url)
const frontendRoot = path.resolve(path.dirname(scriptPath), '..')
const repositoryRoot = path.resolve(frontendRoot, '..')
const backendRoot = path.join(repositoryRoot, 'backend')
const markerName = '.sunjack-playwright-isolation.json'
const ownedChildren = new Set()

export async function reservePort() {
  const server = createServer()
  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  const { port } = server.address()
  await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()))
  return port
}

export async function assertPortsAvailable(assignments) {
  const seen = new Set()
  for (const { name, port } of assignments) {
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
      throw new Error(`${name} port must be an integer from 1 to 65535.`)
    }
    if (seen.has(port)) throw new Error('API and Vite must use distinct ports.')
    seen.add(port)
    const server = createServer()
    try {
      await new Promise((resolve, reject) => {
        server.once('error', reject)
        server.listen(port, '127.0.0.1', resolve)
      })
    } catch (error) {
      if (error?.code === 'EADDRINUSE' || error?.code === 'EACCES') {
        throw new Error(`${name} port ${port} is already in use or unavailable; refusing to reuse another service.`)
      }
      throw error
    } finally {
      if (server.listening) await new Promise(resolve => server.close(() => resolve()))
    }
  }
}

function configuredPort(name) {
  const raw = process.env[name]
  if (raw === undefined || raw.trim() === '') return null
  const port = Number(raw)
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`${name} must be an integer from 1 to 65535.`)
  }
  return port
}

async function choosePorts() {
  const configuredApiPort = configuredPort('ISOLATED_API_PORT')
  const configuredVitePort = configuredPort('ISOLATED_VITE_PORT')
  const reservations = []
  const reserve = async port => {
    const server = createServer()
    await new Promise((resolve, reject) => {
      server.once('error', reject)
      server.listen(port ?? 0, '127.0.0.1', resolve)
    })
    reservations.push(server)
    return server.address().port
  }
  let apiPort
  let vitePort
  try {
    apiPort = await reserve(configuredApiPort)
    vitePort = configuredVitePort === null
      ? await reserve(undefined)
      : await reserve(configuredVitePort)
  } finally {
    await Promise.all(reservations.map(server => new Promise(resolve => server.close(() => resolve()))))
  }
  const assignments = [{ name: 'API', port: apiPort }, { name: 'Vite', port: vitePort }]
  await assertPortsAvailable(assignments)
  return { apiPort, vitePort }
}

export function sqliteDatabaseUrl(databasePath) {
  const normalized = path.resolve(databasePath).replaceAll('\\', '/')
  const encoded = normalized.split('/').map(segment => /^[A-Za-z]:$/.test(segment)
    ? segment
    : encodeURIComponent(segment)).join('/')
  return `sqlite:///${encoded}`
}

async function requireLocalDependencies() {
  const required = [
    path.join(frontendRoot, 'node_modules', 'vite', 'bin', 'vite.js'),
    path.join(frontendRoot, 'node_modules', '@playwright', 'test', 'cli.js'),
  ]
  for (const filePath of required) {
    try {
      await stat(filePath)
    } catch {
      throw new Error(`Missing local frontend dependency ${path.relative(repositoryRoot, filePath)}; run npm ci in frontend first.`)
    }
  }
}

function isWithin(parent, child) {
  const relative = path.relative(parent, child)
  return relative !== '' && relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative)
}

async function resolveEvidenceRoot(candidate, tempRoot) {
  if (!candidate) return path.join(tempRoot, 'evidence')
  const allowedRoot = path.resolve(repositoryRoot, 'docs', 'uat-evidence')
  const evidenceRoot = path.resolve(candidate)
  if (!isWithin(allowedRoot, evidenceRoot)) {
    throw new Error('ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT must be a child of docs/uat-evidence.')
  }
  await mkdir(evidenceRoot, { recursive: true })
  return evidenceRoot
}

async function pythonExecutable() {
  const explicit = process.env.ISOLATED_TEST_PYTHON || process.env.PYTHON
  if (explicit) return explicit
  const candidates = [
    path.join(repositoryRoot, '.venv', 'Scripts', 'python.exe'),
    path.join(backendRoot, '.venv', 'Scripts', 'python.exe'),
    path.join(repositoryRoot, '.venv', 'bin', 'python'),
    path.join(backendRoot, '.venv', 'bin', 'python'),
  ].filter(Boolean)
  for (const candidate of candidates) {
    try {
      await stat(candidate)
      return candidate
    } catch {
      // Try the next conventional local virtual environment.
    }
  }
  return 'python'
}

function createChild(command, args, { cwd, env, label, capture = false }) {
  const child = spawn(command, args, {
    cwd,
    env,
    detached: process.platform !== 'win32',
    windowsHide: true,
    stdio: capture ? ['ignore', 'pipe', 'pipe'] : 'inherit',
  })
  ownedChildren.add(child)
  child.once('close', () => ownedChildren.delete(child))
  if (!capture) return child

  let output = ''
  const append = (chunk, stream) => {
    const value = chunk.toString()
    output = `${output}${value}`.slice(-16000)
    process[stream].write(`[${label}] ${value}`)
  }
  child.stdout.on('data', chunk => append(chunk, 'stdout'))
  child.stderr.on('data', chunk => append(chunk, 'stderr'))
  child.isolationOutput = () => output
  return child
}

async function runCommand(command, args, options) {
  const child = createChild(command, args, options)
  const [code, signal] = await once(child, 'close')
  if (code !== 0) throw new Error(`${options.label || command} exited with ${signal || `code ${code}`}.`)
}

async function runStage(label, command, args, options) {
  console.log(`[isolation] ${label}`)
  await runCommand(command, args, options)
  console.log(`[isolation] ${label}: passed`)
}

function childIsRunning(child) {
  return Boolean(child && child.exitCode === null && child.signalCode === null)
}

async function taskkillOwnedTree(pid, force) {
  const args = ['/PID', String(pid), '/T']
  if (force) args.push('/F')
  const killer = spawn('taskkill.exe', args, { windowsHide: true, stdio: 'ignore' })
  return new Promise(resolve => {
    killer.once('error', () => resolve(false))
    killer.once('close', code => resolve(code === 0))
  })
}

async function signalOwnedTree(child, force) {
  if (!child?.pid) return
  if (process.platform === 'win32') {
    const stopped = await taskkillOwnedTree(child.pid, force)
    if (!stopped && childIsRunning(child)) child.kill(force ? 'SIGKILL' : 'SIGTERM')
    return
  }
  try {
    process.kill(-child.pid, force ? 'SIGKILL' : 'SIGTERM')
  } catch (error) {
    if (error?.code !== 'ESRCH' && childIsRunning(child)) child.kill(force ? 'SIGKILL' : 'SIGTERM')
  }
}

export async function stopOwnedProcessTree(child, { graceMs = 4000, forceMs = 4000 } = {}) {
  if (!child) return
  if (!childIsRunning(child)) return
  const closed = once(child, 'close').then(() => true)
  await signalOwnedTree(child, false)
  const gracefulTimer = new Promise(resolve => setTimeout(() => resolve(false), graceMs))
  if (await Promise.race([closed, gracefulTimer])) return
  await signalOwnedTree(child, true)
  const forcedTimer = new Promise(resolve => setTimeout(() => resolve(false), forceMs))
  if (!(await Promise.race([closed, forcedTimer]))) {
    throw new Error(`Owned process tree ${child.pid} did not exit after forced cleanup.`)
  }
}

function markerPath(root) {
  return path.join(root, markerName)
}

async function createOwnedTempRoot(runId, token) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'sunjack-r1-repair-06-'))
  try {
    await writeFile(markerPath(root), JSON.stringify({ runId, token, root: path.resolve(root) }, null, 2), {
      encoding: 'utf8',
      flag: 'wx',
    })
    await mkdir(path.join(root, 'media'))
    return root
  } catch (error) {
    await rm(root, { recursive: true, force: false })
    throw error
  }
}

export async function cleanupOwnedTempRoot(root, { runId, token }) {
  const tempRoot = await realpath(os.tmpdir())
  const resolvedRoot = path.resolve(root)
  const relative = path.relative(tempRoot, resolvedRoot)
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error('Refusing cleanup: target is not a child of the system temp directory.')
  }
  if (!path.basename(resolvedRoot).startsWith('sunjack-r1-repair-06-')) {
    throw new Error('Refusing cleanup: target does not have this runner\'s temp prefix.')
  }
  const realRoot = await realpath(resolvedRoot)
  const normalize = value => {
    const normalized = path.normalize(value).replace(/^\\\\\?\\/, '')
    return process.platform === 'win32' ? normalized.toLowerCase() : normalized
  }
  if (normalize(realRoot) !== normalize(resolvedRoot) || (await lstat(resolvedRoot)).isSymbolicLink()) {
    throw new Error('Refusing cleanup: temp root resolves through a link or alias.')
  }
  const marker = JSON.parse(await readFile(markerPath(resolvedRoot), 'utf8'))
  if (marker.runId !== runId || marker.token !== token || path.resolve(marker.root) !== resolvedRoot) {
    throw new Error('Refusing cleanup: ownership marker does not match this run.')
  }
  await rm(resolvedRoot, { recursive: true, force: false })
}

async function stopChild(child) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return
  child.kill('SIGTERM')
  const closed = once(child, 'close').then(() => true)
  const timeout = new Promise(resolve => setTimeout(() => resolve(false), 4000))
  if (!(await Promise.race([closed, timeout]))) child.kill('SIGKILL')
}

function requestJson(url, timeoutMs = 1200) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  return fetch(url, { signal: controller.signal })
    .then(async response => {
      let body
      try {
        body = await response.json()
      } catch {
        body = null
      }
      return { status: response.status, body }
    })
    .finally(() => clearTimeout(timeout))
}

export async function waitForIdentity(child, url, expected, label, { timeoutMs = 30000, pollIntervalMs = 200 } = {}) {
  const deadline = Date.now() + timeoutMs
  let lastError = 'server did not return an identity response'
  while (Date.now() < deadline) {
    if (child.exitCode !== null || child.signalCode !== null) {
      throw new Error(`${label} exited before identity verification.\n${child.isolationOutput?.() || ''}`)
    }
    try {
      const { status, body } = await requestJson(url)
      if (status === 200 && body?.runId === expected.runId && body?.token === expected.token) return body
      lastError = `${label} responded with HTTP ${status} or a mismatched run identity`
    } catch (error) {
      lastError = error.message
    }
    await new Promise(resolve => setTimeout(resolve, pollIntervalMs))
  }
  throw new Error(`${label} identity check failed: ${lastError}.\n${child.isolationOutput?.() || ''}`)
}

function samePath(actual, expected) {
  const resolvedActual = path.resolve(actual)
  const resolvedExpected = path.resolve(expected)
  return process.platform === 'win32'
    ? resolvedActual.toLocaleLowerCase('en-US') === resolvedExpected.toLocaleLowerCase('en-US')
    : resolvedActual === resolvedExpected
}

export function assertApiIdentity(actual, expected, label) {
  const mismatches = []
  for (const field of ['runId', 'token']) {
    if (actual?.[field] !== expected?.[field]) mismatches.push(field)
  }
  for (const field of ['database', 'mediaRoot']) {
    if (typeof actual?.[field] !== 'string' || typeof expected?.[field] !== 'string'
      || !samePath(actual[field], expected[field])) mismatches.push(field)
  }
  if (expected?.rbacEnforcement !== undefined && actual?.rbacEnforcement !== expected.rbacEnforcement) {
    mismatches.push('rbacEnforcement')
  }
  if (mismatches.length) {
    throw new Error(`${label} identity mismatch (${mismatches.join(', ')}); refusing browser tests.`)
  }
}

export async function verifyProxiedApiIdentity(viteServer, baseURL, directIdentity, expectedIdentity, options) {
  const proxyUrl = new URL(`/api/__test__/isolation/${encodeURIComponent(expectedIdentity.token)}/`, baseURL).href
  const proxiedIdentity = await waitForIdentity(
    viteServer,
    proxyUrl,
    { runId: expectedIdentity.runId, token: expectedIdentity.token },
    'Vite-proxied Django API',
    options,
  )
  assertApiIdentity(proxiedIdentity, directIdentity, 'Vite-proxied Django API')
  assertApiIdentity(proxiedIdentity, expectedIdentity, 'Vite-proxied Django API')
  return proxiedIdentity
}

export async function resolvePlaywrightSelection(userArgs) {
  const args = userArgs[0] === '--' ? userArgs.slice(1) : userArgs
  if (args.length === 0) return { businessTest: null, businessSuite: false }
  if (args[0] === '--all-business-tests') {
    if (args.length === 1) return { businessTest: '*', businessSuite: true, excludedBusinessTests: [] }
    if (args.length % 2 === 0) throw new Error('Suite exclusions must use repeated --exclude-business-test <name.spec.js> pairs.')
    const excludedBusinessTests = []
    for (let index = 1; index < args.length; index += 2) {
      if (args[index] !== '--exclude-business-test') {
        throw new Error('Only --exclude-business-test <name.spec.js> may follow --all-business-tests.')
      }
      const requested = args[index + 1]
      if (!requested || path.basename(requested) !== requested || !requested.endsWith('.spec.js')) {
        throw new Error('Excluded business test must be a single .spec.js filename inside frontend/browser-tests.')
      }
      const testPath = path.join(frontendRoot, 'browser-tests', requested)
      const fileStat = await lstat(testPath).catch(error => {
        if (error?.code === 'ENOENT') throw new Error(`Business test does not exist: ${requested}`)
        throw error
      })
      if (!fileStat.isFile() || fileStat.isSymbolicLink() || !samePath(await realpath(testPath), testPath)) {
        throw new Error('Excluded business test must be a regular file inside frontend/browser-tests; refusing selection.')
      }
      if (excludedBusinessTests.includes(requested)) throw new Error(`Duplicate excluded business test: ${requested}`)
      excludedBusinessTests.push(requested)
    }
    return { businessTest: '*', businessSuite: true, excludedBusinessTests }
  }
  if (args.length !== 2 || args[0] !== '--business-test') {
    throw new Error('Only --business-test <name.spec.js> or --all-business-tests is supported; isolation settings and Playwright options cannot be overridden.')
  }
  const requested = args[1]
  if (!requested || path.basename(requested) !== requested || !requested.endsWith('.spec.js')) {
    throw new Error('Business test must be a single .spec.js filename inside frontend/browser-tests.')
  }
  const testsRoot = path.join(frontendRoot, 'browser-tests')
  const testPath = path.join(testsRoot, requested)
  const fileStat = await lstat(testPath).catch(error => {
    if (error?.code === 'ENOENT') throw new Error(`Business test does not exist: ${requested}`)
    throw error
  })
  if (!fileStat.isFile() || fileStat.isSymbolicLink() || !samePath(await realpath(testPath), testPath)) {
    throw new Error('Business test must be a regular file inside frontend/browser-tests; refusing selection.')
  }
  return { businessTest: requested, businessSuite: false }
}

export function isolatedFixtureSeed(businessTest) {
  const allowed = {
    'iss022-moq-real.spec.js': { seedFile: 'seed_iss022_browser.py', evidenceEnv: 'ISS022_EVIDENCE_DIR' },
    'iss075-payment-terms-real.spec.js': { seedFile: 'seed_iss075_browser.py', evidenceEnv: 'ISS075_EVIDENCE_DIR' },
    'historical-orders-fix-02.spec.js': {
      seedFile: path.join('..', 'docs', 'uat-evidence', 'r1-repair-03-history-recipient-typography', 'prepare_evidence.py'),
      evidenceEnv: 'R1_REPAIR_EVIDENCE_DIR',
    },
    'historical-orders-fix-03.spec.js': {
      seedFile: path.join('..', 'docs', 'uat-evidence', 'r1-repair-03-history-recipient-typography', 'prepare_evidence.py'),
      evidenceEnv: 'R1_REPAIR_EVIDENCE_DIR',
    },
    'iss029-recipient-snapshot.spec.js': {
      seedFile: path.join('..', 'docs', 'uat-evidence', 'r1-repair-03-history-recipient-typography', 'prepare_evidence.py'),
      evidenceEnv: 'R1_REPAIR_EVIDENCE_DIR',
    },
    'quote-editor-mobile-actions.spec.js': {
      seedFile: path.join('..', 'docs', 'uat-evidence', 'r1-ux-quote-actions-20261029', 'prepare_quote_actions.py'),
      evidenceEnv: 'R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR',
    },
    'iss055-customer-404-real.spec.js': {
      seedFile: path.join('browser-run', 'iss055', 'seed.py'),
      evidenceEnv: 'ISS055_EVIDENCE_DIR',
    },
    'iss028-035-category-schema.spec.js': { seedFile: null, evidenceEnv: 'ISS028_035_EVIDENCE_DIR' },
  }
  const profile = allowed[businessTest]
  return profile ? { ...profile, scriptPath: profile.seedFile ? path.resolve(backendRoot, profile.seedFile) : null } : null
}

export function isolatedFixtureSeeds(selection) {
  if (!selection?.businessSuite) {
    const profile = isolatedFixtureSeed(selection?.businessTest)
    return profile?.scriptPath ? [profile] : []
  }
  const suiteSeedFiles = [
    'iss022-moq-real.spec.js',
    'iss075-payment-terms-real.spec.js',
    'historical-orders-fix-03.spec.js',
  ]
  return suiteSeedFiles
    .filter(testFile => !selection.excludedBusinessTests?.includes(testFile))
    .map(isolatedFixtureSeed)
    .filter(Boolean)
}

export function browserArgs() {
  return [
    path.join(frontendRoot, 'node_modules', '@playwright', 'test', 'cli.js'),
    'test',
    '--config',
    path.join(frontendRoot, 'playwright.isolated.config.js'),
  ]
}

async function main() {
  let receivedSignal = null
  const handleSignal = signal => {
    receivedSignal ??= signal
    for (const child of ownedChildren) {
      if (childIsRunning(child)) {
        void stopOwnedProcessTree(child).catch(error => console.error(error.message))
      }
    }
  }
  const onInterrupt = () => handleSignal('SIGINT')
  const onTerminate = () => handleSignal('SIGTERM')
  process.once('SIGINT', onInterrupt)
  process.once('SIGTERM', onTerminate)
  try {
    await requireLocalDependencies()
    const selection = await resolvePlaywrightSelection(process.argv.slice(2))
    const playwrightArguments = browserArgs()
    const python = await pythonExecutable()
    const { apiPort, vitePort } = await choosePorts()
    if (receivedSignal) throw new Error(`Interrupted by ${receivedSignal} before isolated resources were created.`)
    const runId = randomUUID()
    const token = randomBytes(24).toString('hex')
    const tempRoot = await createOwnedTempRoot(runId, token)
    const databasePath = path.join(tempRoot, 'db.sqlite3')
    const mediaRoot = path.join(tempRoot, 'media')
    const baseURL = `http://127.0.0.1:${vitePort}`
    const rbacTestMode = selection.businessTest === 'iss055-customer-404-real.spec.js'
    let evidenceRoot
    try {
      evidenceRoot = await resolveEvidenceRoot(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, tempRoot)
    } catch (error) {
      await cleanupOwnedTempRoot(tempRoot, { runId, token })
      throw error
    }
    const env = {
      ...process.env,
      APP_STAGE: 'development',
      DJANGO_DEBUG: '1',
      DEVELOPMENT_SUPERADMIN: rbacTestMode ? '0' : '1',
      RBAC_ENFORCEMENT: rbacTestMode ? '1' : '0',
      ISOLATED_TEST_RBAC_MODE: rbacTestMode ? 'iss055' : '',
      AUDIT_LOG_ENABLED: '0',
      MEDIA_STORAGE_BACKEND: 'django.core.files.storage.FileSystemStorage',
      DJANGO_SETTINGS_MODULE: 'test_support.isolated_settings',
      DATABASE_URL: sqliteDatabaseUrl(databasePath),
      MEDIA_ROOT: mediaRoot,
      ISOLATED_TEST_ROOT: tempRoot,
      ISOLATED_TEST_RUN_ID: runId,
      ISOLATED_TEST_TOKEN: token,
      ISOLATED_TEST_DATABASE: databasePath,
      ISOLATED_TEST_MEDIA_ROOT: mediaRoot,
      ISOLATED_API_PORT: String(apiPort),
      ISOLATED_VITE_PORT: String(vitePort),
      ISOLATED_PLAYWRIGHT_BASE_URL: baseURL,
      ISOLATED_PLAYWRIGHT_API_BASE_URL: `http://127.0.0.1:${apiPort}`,
      ISOLATED_PLAYWRIGHT_TEST_FILE: selection.businessTest || '',
      ISOLATED_PLAYWRIGHT_TEST_EXCLUDE: selection.businessSuite
        ? JSON.stringify([...new Set(['iss055-customer-404-real.spec.js', ...selection.excludedBusinessTests])])
        : '',
      ISOLATED_PLAYWRIGHT_OUTPUT_DIR: path.join(evidenceRoot, 'artifacts', runId),
      ISOLATED_TEST_PYTHON: python,
      ISS055_UI_USERNAME: rbacTestMode ? `iss055-${runId.slice(0, 8)}` : '',
      ISS055_UI_PASSWORD: rbacTestMode ? randomBytes(24).toString('base64url') : '',
      PYTHONDONTWRITEBYTECODE: '1',
      PYTHONUNBUFFERED: '1',
      PYTHONUTF8: '1',
      PYTHONIOENCODING: 'utf-8',
      PYTHONPATH: [backendRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
    }
    const evidenceEnvironmentNames = [
      'EVIDENCE_DIR',
      'ISS008_FUP_01_EVIDENCE_DIR',
      'ISS022_EVIDENCE_DIR',
      'ISS028_035_EVIDENCE_DIR',
      'ISS055_EVIDENCE_DIR',
      'ISS075_EVIDENCE_DIR',
      'R1A_EVIDENCE_DIR',
      'R1_REPAIR_EVIDENCE_DIR',
      'R1_REPAIR_04_EVIDENCE_DIR',
      'R1_REPAIR_07_EVIDENCE_DIR',
      'SUPPLIER_UX_EVIDENCE_DIR',
    ]
    for (const name of evidenceEnvironmentNames) {
      env[name] = path.join(evidenceRoot, 'browser', name.toLowerCase())
    }
    if (selection.businessTest && !selection.businessSuite) {
      const fixtureProfile = isolatedFixtureSeed(selection.businessTest)
      if (fixtureProfile) env[fixtureProfile.evidenceEnv] = path.join(evidenceRoot, 'browser', path.parse(selection.businessTest).name)
    }
    if (selection.businessSuite) {
      env.R1_REPAIR_EVIDENCE_DIR = path.join(evidenceRoot, 'browser', 'historical-orders-and-iss029')
      env.ISS022_EVIDENCE_DIR = path.join(evidenceRoot, 'browser', 'iss022-moq-real')
      env.ISS075_EVIDENCE_DIR = path.join(evidenceRoot, 'browser', 'iss075-payment-terms-real')
      env.ISS028_035_EVIDENCE_DIR = path.join(evidenceRoot, 'browser', 'iss028-035-category-schema')
    }
    env.ISS055_EVIDENCE_DIR = path.join(evidenceRoot, 'browser', 'iss055-customer-404')

    let apiServer
    let viteServer
    let cleanupError
    try {
      if (receivedSignal) throw new Error(`Interrupted by ${receivedSignal} before tests started.`)
      console.log(`Isolation run ${runId}; API 127.0.0.1:${apiPort}; Vite 127.0.0.1:${vitePort}`)
      console.log(`Isolated SQLite: ${databasePath}`)
      console.log(`Isolated MEDIA_ROOT: ${mediaRoot}`)
      console.log(`Playwright selection: ${selection.businessSuite ? `all browser tests except ${JSON.parse(env.ISOLATED_PLAYWRIGHT_TEST_EXCLUDE).join(', ')}` : selection.businessTest || 'infrastructure smoke tests'}`)
      console.log(`Isolated RBAC mode: ${rbacTestMode ? 'ISS-055 employee session' : 'development superadmin'}`)
      const verificationCode = databaseMustExist => [
        'import django',
        'django.setup()',
        'from django.conf import settings',
        'from test_support.isolated_runtime import verify_isolated_runtime',
        `print(verify_isolated_runtime(settings=settings, database_must_exist=${databaseMustExist ? 'True' : 'False'}))`,
      ].join('; ')

      await runStage('Pre-migration isolation verification', python, ['-c', verificationCode(false)], { cwd: backendRoot, env, label: 'Pre-migration isolation verification' })
      await runStage('Django system check', python, ['manage.py', 'check'], { cwd: backendRoot, env, label: 'Django system check' })
      await runStage('Isolated database migrations', python, ['manage.py', 'migrate', '--noinput'], { cwd: backendRoot, env, label: 'Isolated database migrations' })
      await runStage('Migration completeness check', python, ['manage.py', 'migrate', '--check'], { cwd: backendRoot, env, label: 'Migration completeness check' })
      await runStage('Post-migration isolation verification', python, ['-c', verificationCode(true)], { cwd: backendRoot, env, label: 'Post-migration isolation verification' })

      const fixtureSeeds = isolatedFixtureSeeds(selection)
      for (const fixtureSeed of fixtureSeeds) {
        await mkdir(env[fixtureSeed.evidenceEnv], { recursive: true })
        await runStage(`Allowlisted synthetic fixture seed (${path.basename(fixtureSeed.scriptPath)})`, python, [fixtureSeed.scriptPath], {
          cwd: backendRoot,
          env,
          label: `Synthetic fixture seed for ${path.basename(fixtureSeed.scriptPath)}`,
        })
      }
      if (rbacTestMode) {
        const fixturePath = path.join(env.ISS055_EVIDENCE_DIR, 'fixture.json')
        const fixture = JSON.parse(await readFile(fixturePath, 'utf8'))
        env.ISS055_VISIBLE_ID = String(fixture.visible_id)
        env.ISS055_HIDDEN_ID = String(fixture.hidden_id)
      }

      apiServer = createChild(python, [
        'manage.py', 'runserver', `127.0.0.1:${apiPort}`, '--noreload',
      ], { cwd: backendRoot, env, label: 'isolated Django API', capture: true })
      const apiIdentityUrl = `http://127.0.0.1:${apiPort}/api/__test__/isolation/${token}/`
      const viteIdentityUrl = `${baseURL}/__test__/isolation/`
      const expectedApiIdentity = {
        runId,
        token,
        database: databasePath,
        mediaRoot,
        rbacEnforcement: rbacTestMode,
      }
      const apiIdentity = await waitForIdentity(apiServer, apiIdentityUrl, { runId, token }, 'Django API')
      assertApiIdentity(apiIdentity, expectedApiIdentity, 'Direct Django API')
      console.log('[isolation] Direct Django API identity, SQLite path, and MEDIA_ROOT: passed')

      viteServer = createChild(process.execPath, [
        path.join(frontendRoot, 'node_modules', 'vite', 'bin', 'vite.js'),
        '--configLoader', 'runner',
        '--config', path.join(frontendRoot, 'vite.isolated.config.js'),
        '--host', '127.0.0.1', '--port', String(vitePort),
      ], { cwd: frontendRoot, env, label: 'isolated Vite', capture: true })
      await waitForIdentity(viteServer, viteIdentityUrl, { runId, token }, 'Vite')
      console.log('[isolation] Vite identity: passed')
      await verifyProxiedApiIdentity(viteServer, baseURL, apiIdentity, expectedApiIdentity)
      console.log('[isolation] Vite /api proxy identity, SQLite path, and MEDIA_ROOT: passed')

      const testOutputDir = env.ISOLATED_PLAYWRIGHT_OUTPUT_DIR
      await mkdir(testOutputDir, { recursive: true })
      await runStage('Playwright suite', process.execPath, playwrightArguments, {
        cwd: frontendRoot,
        env,
        label: 'Isolated Playwright suite',
      })
    } finally {
      const shutdown = await Promise.allSettled([
        stopOwnedProcessTree(viteServer),
        stopOwnedProcessTree(apiServer),
      ])
      const shutdownErrors = shutdown.filter(result => result.status === 'rejected').map(result => result.reason)
      try {
        if (!shutdownErrors.length) {
          await assertPortsAvailable([{ name: 'API', port: apiPort }, { name: 'Vite', port: vitePort }])
          console.log('[isolation] Owned API and Vite process trees stopped; both ports are released.')
        } else {
          throw new AggregateError(shutdownErrors, 'One or more owned server process trees did not stop.')
        }
        await cleanupOwnedTempRoot(tempRoot, { runId, token })
        console.log('Removed only this run\'s marked temporary database and MEDIA_ROOT.')
      } catch (error) {
        cleanupError = error
        console.error(`Temporary resources retained for safety; inspect this exact run directory: ${tempRoot}`)
        console.error(error.message)
      }
      if (cleanupError) throw cleanupError
    }
  } finally {
    process.removeListener('SIGINT', onInterrupt)
    process.removeListener('SIGTERM', onTerminate)
    if (receivedSignal) process.exitCode = receivedSignal === 'SIGINT' ? 130 : 143
  }
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  main().catch(error => {
    console.error(error.stack || error)
    if (![130, 143].includes(process.exitCode)) process.exitCode = 1
  })
}
