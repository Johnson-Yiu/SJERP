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
  if (args.length === 0) return { businessTest: null }
  if (args.length !== 2 || args[0] !== '--business-test') {
    throw new Error('Only --business-test <name.spec.js> is supported; isolation settings and Playwright options cannot be overridden.')
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
  return { businessTest: requested }
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
      if (child.exitCode === null && child.signalCode === null) child.kill('SIGTERM')
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
    const { apiPort, vitePort } = await choosePorts()
    if (receivedSignal) throw new Error(`Interrupted by ${receivedSignal} before isolated resources were created.`)
    const runId = randomUUID()
    const token = randomBytes(24).toString('hex')
    const tempRoot = await createOwnedTempRoot(runId, token)
    const databasePath = path.join(tempRoot, 'db.sqlite3')
    const mediaRoot = path.join(tempRoot, 'media')
    const baseURL = `http://127.0.0.1:${vitePort}`
    const env = {
      ...process.env,
      APP_STAGE: 'development',
      DJANGO_DEBUG: '1',
      DEVELOPMENT_SUPERADMIN: '1',
      RBAC_ENFORCEMENT: '0',
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
      ISOLATED_PLAYWRIGHT_TEST_FILE: selection.businessTest || '',
      PYTHONDONTWRITEBYTECODE: '1',
      PYTHONUNBUFFERED: '1',
    }

    let apiServer
    let viteServer
    let cleanupError
    try {
      if (receivedSignal) throw new Error(`Interrupted by ${receivedSignal} before tests started.`)
      console.log(`Isolation run ${runId}; API 127.0.0.1:${apiPort}; Vite 127.0.0.1:${vitePort}`)
      console.log(`Isolated SQLite: ${databasePath}`)
      console.log(`Isolated MEDIA_ROOT: ${mediaRoot}`)
      console.log(`Playwright selection: ${selection.businessTest || 'infrastructure smoke tests'}`)
      const python = await pythonExecutable()
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

      await runStage('Playwright suite', process.execPath, playwrightArguments, {
        cwd: frontendRoot,
        env,
        label: 'Isolated Playwright suite',
      })
    } finally {
      await stopChild(viteServer)
      await stopChild(apiServer)
      try {
        await cleanupOwnedTempRoot(tempRoot, { runId, token })
        console.log('Removed only this run\'s marked temporary database and MEDIA_ROOT.')
      } catch (error) {
        cleanupError = error
        console.error(`Temporary cleanup refused or failed; inspect this exact run directory: ${tempRoot}`)
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
