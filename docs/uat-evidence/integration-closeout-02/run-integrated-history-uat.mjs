import { spawn } from 'node:child_process'
import { execFileSync } from 'node:child_process'
import { createHash, randomBytes, randomUUID } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { once } from 'node:events'
import { access, cp, lstat, mkdir, mkdtemp, readFile, realpath, rm, stat, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const reportRoot = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(reportRoot, '../../..')
const frozenRoot = path.join(repoRoot, '.tmp', 'final-integrated-447d')
const frontendRoot = path.join(frozenRoot, 'frontend')
const backendRoot = path.join(frozenRoot, 'backend')
const python = path.join(repoRoot, '.tmp', 'closeout-python312', 'Scripts', 'python.exe')
const seedScript = path.join(reportRoot, 'seed_integrated_history_uat.py')
const verifyScript = path.join(reportRoot, 'verify_integrated_history_uat.py')
const inventoryCopy = path.join(reportRoot, 'history-inventory-location-chrome-uat-447d-r03.mjs')
const evidenceRoot = path.join(reportRoot, 'final-447d-history-chrome-r03')
const expectedSha = '447d7816ead2e971e249cb2e762b1a6f7009b9c0'
const apiPort = 53621
const vitePort = 53622
const baseURL = `http://127.0.0.1:${vitePort}`
const apiBaseURL = `http://127.0.0.1:${apiPort}`
const chromeChannel = 'chrome'
const sourceNames = [
  'history-operational-chrome-uat.mjs',
  'history-operational-workflow-uat.mjs',
  'history-operational-fulfillment-uat.mjs',
  'history-inventory-location-chrome-uat.mjs',
  'history-template-chrome-uat.mjs',
]

const helperPath = path.join(frontendRoot, 'scripts', 'run-isolated-browser-tests.mjs')
const {
  assertApiIdentity,
  assertPortsAvailable,
  cleanupOwnedTempRoot,
  sqliteDatabaseUrl,
  stopOwnedProcessTree,
  verifyProxiedApiIdentity,
  waitForIdentity,
} = await import(pathToFileURL(helperPath).href)

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex')
}

function countOccurrences(value, needle) {
  return value.split(needle).length - 1
}

function redacted(value, token) {
  return value.split(token).join('[ISOLATION_TOKEN_REDACTED]')
}

function startCaptured(command, args, { cwd, env, label }) {
  const child = spawn(command, args, { cwd, env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] })
  const chunks = []
  let bytes = 0
  const append = chunk => {
    chunks.push(Buffer.from(chunk))
    bytes += chunk.length
    while (bytes > 32 * 1024 * 1024 && chunks.length > 1) bytes -= chunks.shift().length
  }
  child.stdout.on('data', append)
  child.stderr.on('data', append)
  child.isolationOutput = () => Buffer.concat(chunks).toString('utf8')
  child.isolationLabel = label
  return child
}

async function executeStage(label, command, args, { cwd, env, logRoot }) {
  const started = Date.now()
  const child = startCaptured(command, args, { cwd, env, label })
  let close
  try {
    close = await once(child, 'close')
  } catch (error) {
    const output = child.isolationOutput()
    const logPath = path.join(logRoot, `${label}.raw.log`)
    await writeFile(logPath, output, 'utf8')
    throw Object.assign(error, { stageLogPath: logPath, stageOutput: output })
  }
  const output = child.isolationOutput()
  const logPath = path.join(logRoot, `${label}.raw.log`)
  await writeFile(logPath, output, 'utf8')
  return {
    label,
    exit_code: close[0],
    signal: close[1],
    duration_ms: Date.now() - started,
    raw_log_path: logPath,
    output,
  }
}

async function captureOutput(label, child, logRoot) {
  const output = child?.isolationOutput?.() || ''
  const logPath = path.join(logRoot, `${label}.raw.log`)
  await writeFile(logPath, output, 'utf8')
  return logPath
}

async function copyDirectoryContents(source, destination) {
  const sourceReal = await realpath(source)
  const sourceInfo = await lstat(source)
  if (!sourceInfo.isDirectory() || sourceInfo.isSymbolicLink()) throw new Error('Refusing to copy a linked MEDIA_ROOT.')
  await mkdir(destination, { recursive: false })
  const entries = await (await import('node:fs/promises')).readdir(sourceReal, { withFileTypes: true })
  for (const entry of entries) {
    const from = path.join(sourceReal, entry.name)
    const to = path.join(destination, entry.name)
    if (entry.isSymbolicLink()) throw new Error(`Refusing to copy linked media entry: ${entry.name}`)
    if (entry.isDirectory()) await copyDirectoryContents(from, to)
    else if (entry.isFile()) await cp(from, to, { errorOnExist: true, force: false })
    else throw new Error(`Refusing to copy non-regular media entry: ${entry.name}`)
  }
}

async function pngInfo(filename) {
  const bytes = await readFile(filename)
  if (bytes.length < 24 || bytes.toString('ascii', 1, 4) !== 'PNG') throw new Error(`Invalid PNG evidence: ${filename}`)
  return {
    path: path.relative(evidenceRoot, filename).replaceAll(path.sep, '/'),
    width: bytes.readUInt32BE(16),
    height: bytes.readUInt32BE(20),
    size: bytes.length,
    sha256: sha256(bytes),
  }
}

async function listPngs(directory) {
  const result = []
  for (const entry of await (await import('node:fs/promises')).readdir(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name)
    if (entry.isDirectory()) result.push(...await listPngs(filename))
    else if (entry.isFile() && entry.name.toLowerCase().endsWith('.png')) result.push(await pngInfo(filename))
  }
  return result
}

async function publishLog(label, rawPath, token, publishedLogRoot) {
  const raw = await readFile(rawPath)
  const published = redacted(raw.toString('utf8'), token)
  const publishedPath = path.join(publishedLogRoot, `${label}.log`)
  await writeFile(publishedPath, published, 'utf8')
  return {
    name: `${label}.log`,
    raw_sha256: sha256(raw),
    published_sha256: sha256(Buffer.from(published, 'utf8')),
    raw_bytes: raw.length,
    published_bytes: Buffer.byteLength(published, 'utf8'),
    token_redactions: countOccurrences(raw.toString('utf8'), token),
  }
}

async function createInventoryAcceptanceCopy(actualSku) {
  const source = path.join(frontendRoot, 'scripts', 'history-inventory-location-chrome-uat.mjs')
  const original = await readFile(source, 'utf8')
  const oldSku = 'UAT-HT-S1'
  const importLine = "from '@playwright/test'"
  if (countOccurrences(original, oldSku) < 1 || countOccurrences(original, importLine) !== 1) {
    throw new Error('The delivered inventory-location script no longer has the expected single import and SKU fixture marker.')
  }
  if (!original.includes("chromium.launch({ channel: 'chrome', headless: true })")) {
    throw new Error('The delivered inventory-location script does not explicitly launch Chrome.')
  }
  const packageEntry = path.join(frontendRoot, 'node_modules', '@playwright', 'test', 'index.mjs')
  const rewrittenImport = `from '${pathToFileURL(packageEntry).href}'`
  let transformed = original.replace(importLine, rewrittenImport).replaceAll(oldSku, actualSku)
  const restored = transformed.replace(rewrittenImport, importLine).replaceAll(actualSku, oldSku)
  if (restored !== original) throw new Error('Inventory acceptance copy contains edits beyond the generated SKU and frozen Playwright import substitutions.')
  await writeFile(inventoryCopy, transformed, { encoding: 'utf8', flag: 'wx' })
  return {
    source: path.relative(repoRoot, source).replaceAll(path.sep, '/'),
    acceptance_copy: path.relative(repoRoot, inventoryCopy).replaceAll(path.sep, '/'),
    fixture_replacements: countOccurrences(original, oldSku),
    only_changes: ['UAT-HT-S1 -> generated API SKU', '@playwright/test -> frozen checkout node_modules entry'],
  }
}

function requiredStage(name, result) {
  if (result.exit_code !== 0) throw new Error(`${name} exited ${result.signal || `code ${result.exit_code}`}.`)
  return result
}

const initialHead = execFileSync('git', ['-C', frozenRoot, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
if (initialHead !== expectedSha) throw new Error(`Frozen product checkout moved: expected ${expectedSha}, actual ${initialHead}.`)
for (const filename of [python, path.join(frontendRoot, 'node_modules', 'vite', 'bin', 'vite.js'), path.join(frontendRoot, 'node_modules', '@playwright', 'test', 'index.mjs'), ...sourceNames.map(name => path.join(frontendRoot, 'scripts', name))]) {
  await access(filename)
}
if (await stat(evidenceRoot).then(() => true, () => false)) throw new Error(`Evidence directory already exists; refusing to overwrite: ${evidenceRoot}`)
if (await stat(inventoryCopy).then(() => true, () => false)) throw new Error(`Inventory acceptance copy already exists; refusing to overwrite: ${inventoryCopy}`)

await assertPortsAvailable([{ name: 'API', port: apiPort }, { name: 'Vite', port: vitePort }])
const runId = randomUUID()
const token = randomBytes(24).toString('hex')
const tempRoot = await mkdtemp(path.join(os.tmpdir(), 'sunjack-r1-repair-06-'))
const databasePath = path.join(tempRoot, 'db.sqlite3')
const mediaRoot = path.join(tempRoot, 'media')
const sessionDir = path.join(tempRoot, `sunjack-history-operational-closeout-447d-${runId}`)
const rawLogRoot = path.join(tempRoot, 'logs')
const publishedLogRoot = path.join(evidenceRoot, 'logs')
const artifactRoot = path.join(evidenceRoot, 'artifacts')
const marker = { runId, token, root: path.resolve(tempRoot) }
await writeFile(path.join(tempRoot, '.sunjack-playwright-isolation.json'), `${JSON.stringify(marker, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' })
await mkdir(mediaRoot)
await mkdir(rawLogRoot)
await mkdir(evidenceRoot, { recursive: false })
await mkdir(publishedLogRoot)
await mkdir(artifactRoot)

const password = randomBytes(24).toString('base64url')
const env = { ...process.env }
for (const key of Object.keys(env)) {
  if (key.startsWith('PG')) delete env[key]
}
Object.assign(env, {
  APP_STAGE: 'development',
  DJANGO_DEBUG: '1',
  DEVELOPMENT_SUPERADMIN: '1',
  RBAC_ENFORCEMENT: '0',
  ISOLATED_TEST_RBAC_MODE: '',
  AUDIT_LOG_ENABLED: '1',
  MEDIA_STORAGE_BACKEND: 'django.core.files.storage.FileSystemStorage',
  DJANGO_SETTINGS_MODULE: 'test_support.isolated_settings',
  DJANGO_SECRET_KEY: randomBytes(48).toString('base64url'),
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
  ISOLATED_PLAYWRIGHT_API_BASE_URL: apiBaseURL,
  CSRF_TRUSTED_ORIGINS: baseURL,
  ISOLATED_TEST_PYTHON: python,
  PYTHONDONTWRITEBYTECODE: '1',
  PYTHONUNBUFFERED: '1',
  PYTHONUTF8: '1',
  PYTHONIOENCODING: 'utf-8',
  PYTHONPATH: [backendRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
  SYNTHETIC_TEST_PASSWORD: password,
  DEBUG: 'pw:browser',
  DEBUG_COLORS: '0',
})

const result = {
  schema_version: 1,
  product_sha: expectedSha,
  frozen_checkout: path.relative(repoRoot, frozenRoot).replaceAll(path.sep, '/'),
  run_id: runId,
  chrome_channel_explicit_in_source_scripts: chromeChannel,
  runtime: { node: process.version, python: null, chrome_version: null },
  isolation: {
    root_basename: path.basename(tempRoot),
    api_port: apiPort,
    vite_port: vitePort,
    database: databasePath,
    media_root: mediaRoot,
    session_dir_basename: path.basename(sessionDir),
    development_superadmin: true,
    rbac_enforcement: false,
    audit_log_enabled: true,
    filesystem_media: true,
    pg_environment_variables_removed: true,
  },
  identities: {},
  seed: null,
  inventory_acceptance_copy: null,
  stages: [],
  screenshots: [],
  logs: [],
  database_copy: null,
  media_copy: null,
  teardown: { api_stopped: false, vite_stopped: false, ports_released: false, owned_temp_cleanup: false },
  errors: [],
  blocked_stages: [],
}

let apiServer
let viteServer
let cleanupSafe = false
let seedData = null

async function stage(label, command, args, options) {
  console.log(`[UAT] starting ${label}`)
  const value = await executeStage(label, command, args, options)
  const { output, ...publicValue } = value
  result.stages.push(publicValue)
  if (value.exit_code !== 0) {
    result.errors.push(`${label}: exited ${value.signal || `code ${value.exit_code}`}`)
  }
  console.log(`[UAT] ${label}: ${value.exit_code === 0 ? 'PASS' : 'FAIL'} (${value.duration_ms} ms)`)
  return value
}

try {
  const pythonVersion = await stage('python-version', python, ['--version'], { cwd: backendRoot, env, logRoot: rawLogRoot })
  result.runtime.python = pythonVersion.output.trim()
  requiredStage('Python version', pythonVersion)

  const migrate = await stage('isolated-migration', python, [seedScript, '--migrate-only'], { cwd: backendRoot, env, logRoot: rawLogRoot })
  requiredStage('Isolated migration', migrate)

  apiServer = startCaptured(python, ['manage.py', 'runserver', `127.0.0.1:${apiPort}`, '--noreload'], {
    cwd: backendRoot, env, label: 'isolated Django API',
  })
  const identityURL = `${apiBaseURL}/api/__test__/isolation/${token}/`
  const expectedIdentity = { runId, token, database: databasePath, mediaRoot, rbacEnforcement: false }
  const apiIdentity = await waitForIdentity(apiServer, identityURL, { runId, token }, 'Django API')
  assertApiIdentity(apiIdentity, expectedIdentity, 'Direct isolated API')
  result.identities.direct_api = { verified: true, database_path_matches: true, media_root_matches: true, rbac_enforcement: false }

  viteServer = startCaptured(process.execPath, [
    path.join(frontendRoot, 'node_modules', 'vite', 'bin', 'vite.js'),
    '--configLoader', 'runner', '--config', path.join(frontendRoot, 'vite.isolated.config.js'),
    '--host', '127.0.0.1', '--port', String(vitePort), '--strictPort',
  ], { cwd: frontendRoot, env, label: 'isolated Vite' })
  const viteIdentity = await waitForIdentity(viteServer, `${baseURL}/__test__/isolation/`, { runId, token }, 'Vite')
  result.identities.vite = { verified: true }
  await verifyProxiedApiIdentity(viteServer, baseURL, apiIdentity, expectedIdentity)
  result.identities.vite_api_proxy = { verified: true, database_path_matches: true, media_root_matches: true }

  const seed = await stage('synthetic-api-seed', python, [seedScript], { cwd: backendRoot, env, logRoot: rawLogRoot })
  requiredStage('Synthetic API seed', seed)
  seedData = JSON.parse(seed.output.trim())
  result.seed = seedData
  if (seedData.database_engine !== 'django.db.backends.sqlite3' || seedData.generated_sku == null) {
    throw new Error('Seed result did not confirm isolated SQLite and an API-generated SKU.')
  }
  result.inventory_acceptance_copy = await createInventoryAcceptanceCopy(seedData.generated_sku)

  const browserEnv = { ...env, HISTORY_UAT_ORIGIN: baseURL, HISTORY_UAT_SESSION_DIR: sessionDir }
  const runBrowserScript = async (label, scriptPath, subdir, overrides = {}) => {
    const folder = path.join(evidenceRoot, subdir)
    await mkdir(folder, { recursive: true })
    const scriptEnv = {
      ...browserEnv,
      HISTORY_UAT_EVIDENCE_DIR: folder,
      ...overrides,
    }
    const test = await stage(label, process.execPath, [scriptPath], { cwd: frontendRoot, env: scriptEnv, logRoot: rawLogRoot })
    if (test.exit_code !== 0) result.errors.push(`${label}: browser assertions failed; inspect logs/${label}.log.`)
    return test
  }

  const operational = await runBrowserScript(
    'history-operational-chrome',
    path.join(frontendRoot, 'scripts', 'history-operational-chrome-uat.mjs'),
    'operational',
    { HISTORY_UAT_SESSION_FILE: path.join(sessionDir, 'reviewer-session.json') },
  )

  let workflow = null
  if (operational.exit_code === 0) {
    workflow = await runBrowserScript(
      'history-operational-workflow',
      path.join(frontendRoot, 'scripts', 'history-operational-workflow-uat.mjs'),
      'workflow',
    )
  } else {
    result.blocked_stages.push({ stage: 'history-operational-workflow', reason: 'Initial history review/execution browser scenario failed; dependent mutations were not attempted.' })
  }

  if (workflow?.exit_code === 0) {
    await runBrowserScript(
      'history-operational-fulfillment',
      path.join(frontendRoot, 'scripts', 'history-operational-fulfillment-uat.mjs'),
      'fulfillment',
    )
  } else {
    result.blocked_stages.push({ stage: 'history-operational-fulfillment', reason: 'Continuation contract scenario did not pass; dependent receipt/shipment requests were not attempted.' })
  }

  await runBrowserScript('history-inventory-location', inventoryCopy, 'inventory-location')
  await runBrowserScript(
    'history-template',
    path.join(frontendRoot, 'scripts', 'history-template-chrome-uat.mjs'),
    'template',
  )

  const verification = await stage('read-only-business-verification', python, [
    verifyScript, '--summary', '--output', path.join(evidenceRoot, 'business-row-summary.json'),
  ], { cwd: backendRoot, env, logRoot: rawLogRoot })
  if (verification.exit_code === 0) {
    result.business_verification = JSON.parse(verification.output)
  } else {
    result.errors.push('Read-only business verification did not complete.')
  }

  const templatePath = path.join(evidenceRoot, 'template', 'history-takeover-template.xlsx')
  const templateBytes = await readFile(templatePath).catch(() => null)
  if (templateBytes) result.template_download = { path: 'template/history-takeover-template.xlsx', size: templateBytes.length, sha256: sha256(templateBytes) }

  result.screenshots = await listPngs(evidenceRoot)
  const browserJsonFiles = [
    'operational/chrome-run.json',
    'workflow/chrome-workflow.json',
    'fulfillment/chrome-fulfillment.json',
    'fulfillment/chrome-run.json',
    'inventory-location/inventory-location-chrome.json',
    'template/chrome-run.json',
  ]
  const versions = []
  for (const relative of browserJsonFiles) {
    try {
      const parsed = JSON.parse(await readFile(path.join(evidenceRoot, relative), 'utf8'))
      if (parsed.chrome) versions.push({ file: relative, chrome: parsed.chrome })
    } catch {}
  }
  const versionFromLogs = result.stages.flatMap(item => {
    try {
      const text = readFileSync(item.raw_log_path, 'utf8')
      return [...text.matchAll(/Chrome(?:\s+version)?\s+([0-9.]+)/g)].map(match => ({ file: path.basename(item.raw_log_path), chrome: match[1] }))
    } catch { return [] }
  })
  result.runtime.chrome_versions = [...versions, ...versionFromLogs]
  if (versions.length) result.runtime.chrome_version = versions[0].chrome
  result.runtime.chrome_launch_evidence = result.stages.flatMap(item => {
    try {
      const text = readFileSync(item.raw_log_path, 'utf8')
      return text.split(/\r?\n/).filter(line => /launching|chrome\.exe/i.test(line)).slice(0, 20)
    } catch { return [] }
  }).map(line => redacted(line, token))

  // Stop only the two process trees started by this run before database/media export.
} catch (error) {
  result.errors.push(redacted(error?.stack || String(error), token))
  console.error(`[UAT] fatal: ${redacted(error?.message || String(error), token)}`)
} finally {
  const shutdowns = await Promise.allSettled([
    stopOwnedProcessTree(viteServer),
    stopOwnedProcessTree(apiServer),
  ])
  result.teardown.vite_stopped = shutdowns[0].status === 'fulfilled'
  result.teardown.api_stopped = shutdowns[1].status === 'fulfilled'
  for (const entry of shutdowns) if (entry.status === 'rejected') result.errors.push(`Owned process shutdown failed: ${entry.reason?.message || entry.reason}`)

  if (viteServer) await captureOutput('vite-server', viteServer, rawLogRoot).catch(error => result.errors.push(`Vite log capture failed: ${error.message}`))
  if (apiServer) await captureOutput('api-server', apiServer, rawLogRoot).catch(error => result.errors.push(`API log capture failed: ${error.message}`))

  try {
    await assertPortsAvailable([{ name: 'API', port: apiPort }, { name: 'Vite', port: vitePort }])
    result.teardown.ports_released = true
  } catch (error) {
    result.errors.push(`Port release verification failed: ${error.message}`)
  }

  try {
    if (await stat(databasePath).then(() => true, () => false)) {
      const dbCopy = path.join(artifactRoot, 'isolated-sanitized.sqlite3')
      const sanitize = await executeStage('sanitized-database-copy', python, [verifyScript, '--sanitize-db', dbCopy], {
        cwd: backendRoot, env, label: 'sanitized-database-copy', logRoot: rawLogRoot,
      })
      const { output, ...publicValue } = sanitize
      result.stages.push(publicValue)
      if (sanitize.exit_code === 0) result.database_copy = JSON.parse(output)
      else result.errors.push(`Sanitized database copy failed (code ${sanitize.exit_code}).`)

      const mediaCopy = path.join(artifactRoot, 'media')
      await copyDirectoryContents(mediaRoot, mediaCopy)
      const mediaFiles = []
      async function walkMedia(directory) {
        for (const entry of await (await import('node:fs/promises')).readdir(directory, { withFileTypes: true })) {
          const file = path.join(directory, entry.name)
          if (entry.isDirectory()) await walkMedia(file)
          else if (entry.isFile()) {
            const bytes = await readFile(file)
            mediaFiles.push({ path: path.relative(mediaCopy, file).replaceAll(path.sep, '/'), size: bytes.length, sha256: sha256(bytes) })
          }
        }
      }
      await walkMedia(mediaCopy)
      result.media_copy = { path: 'artifacts/media', file_count: mediaFiles.length, files: mediaFiles }
    }
  } catch (error) {
    result.errors.push(`Artifact preservation failed: ${error?.stack || error}`)
  }

  for (const item of result.stages) {
    try {
      result.logs.push(await publishLog(path.basename(item.raw_log_path).replace(/\.raw\.log$/, ''), item.raw_log_path, token, publishedLogRoot))
    } catch (error) {
      result.errors.push(`Could not publish ${item.raw_log_path}: ${error.message}`)
    }
  }
  for (const label of ['api-server', 'vite-server']) {
    const rawPath = path.join(rawLogRoot, `${label}.raw.log`)
    if (await stat(rawPath).then(() => true, () => false)) {
      try { result.logs.push(await publishLog(label, rawPath, token, publishedLogRoot)) }
      catch (error) { result.errors.push(`Could not publish ${label} log: ${error.message}`) }
    }
  }

  if (result.teardown.api_stopped && result.teardown.vite_stopped && result.teardown.ports_released) {
    try {
      await cleanupOwnedTempRoot(tempRoot, { runId, token })
      result.teardown.owned_temp_cleanup = true
      result.teardown.temp_root_removed = path.basename(tempRoot)
    } catch (error) {
      result.errors.push(`Owned temporary root cleanup refused: ${error.message}`)
      result.teardown.temp_root_retained = tempRoot
    }
  } else {
    result.teardown.temp_root_retained = tempRoot
    result.errors.push('Temporary root retained because owned services or ports could not be proven stopped.')
  }

  result.final_status = result.errors.length === 0 && result.blocked_stages.length === 0 ? 'PASS' : 'INCOMPLETE_OR_FAILED'
  const resultPath = path.join(evidenceRoot, 'result.json')
  await writeFile(resultPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8').catch(error => console.error(`Could not write final result JSON: ${error.message}`))
  console.log(`[UAT] final status ${result.final_status}; result ${resultPath}`)
}

if (result.final_status !== 'PASS') process.exitCode = 1
