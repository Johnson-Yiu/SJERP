import { spawn } from 'node:child_process'
import { execFileSync } from 'node:child_process'
import { createHash, randomBytes, randomUUID } from 'node:crypto'
import { constants, createWriteStream, readFileSync } from 'node:fs'
import { once } from 'node:events'
import { access, cp, copyFile, lstat, mkdir, mkdtemp, readFile, realpath, stat, writeFile } from 'node:fs/promises'
import { finished } from 'node:stream/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const reportRoot = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(reportRoot, '../../..')
function parseArgs(argv) {
  const values = {}
  for (let index = 0; index < argv.length; index += 1) {
    const name = argv[index]
    if (name === '--help' || name === '-h') return { help: true }
    if (!['--checkout', '--sha', '--evidence-dir'].includes(name)) throw new Error(`Unknown argument: ${name}`)
    const value = argv[index + 1]
    if (!value || value.startsWith('--')) throw new Error(`Missing value for ${name}`)
    values[name] = value
    index += 1
  }
  for (const name of ['--checkout', '--sha', '--evidence-dir']) {
    if (!values[name]) throw new Error(`Required argument: ${name}`)
  }
  return { checkout: values['--checkout'], sha: values['--sha'], evidenceDir: values['--evidence-dir'] }
}

const options = parseArgs(process.argv.slice(2))
if (options.help) {
  console.log('Usage: node run-final-history-chrome.mjs --checkout <absolute-worktree> --sha <full-40-char-sha> --evidence-dir <new-direct-child-of-this-report-directory>')
  process.exit(0)
}
const expectedSha = options.sha.toLowerCase()
if (!/^[0-9a-f]{40}$/.test(expectedSha)) throw new Error('--sha must be a complete 40-character Git SHA.')
const frozenRoot = await realpath(path.resolve(options.checkout))
const evidenceRoot = path.resolve(options.evidenceDir)
if (path.dirname(evidenceRoot) !== reportRoot || path.basename(evidenceRoot) === '.') {
  throw new Error('--evidence-dir must name a new direct child of this report directory.')
}
const frontendRoot = path.join(frozenRoot, 'frontend')
const backendRoot = path.join(frozenRoot, 'backend')
const python = process.env.ISOLATED_TEST_PYTHON || path.join(repoRoot, '.tmp', 'closeout-python312', 'Scripts', 'python.exe')
const seedScript = path.join(reportRoot, 'seed_integrated_history_uat.py')
const verifyScript = path.join(reportRoot, 'verify_integrated_history_uat.py')
const inventoryCopy = path.join(evidenceRoot, 'harness', 'history-inventory-location-chrome-uat.mjs')
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
const sourceScriptBaselineSha256 = {
  'history-operational-chrome-uat.mjs': '17c527958a0876938b0aae3cd735c8c50224f3d8a62d221dd23ef0b4f05c4951',
  'history-operational-workflow-uat.mjs': '67612e51626ebe4597701dee91178e36753cc22960284796b19b7b584b9f4cb1',
  'history-operational-fulfillment-uat.mjs': '8c01503132273e80af3a0a26d87341da89104cecda7a57f19778cd282a9aa651',
  'history-inventory-location-chrome-uat.mjs': 'fa36c1fe2edee2b02c237e62b5d5a6d323d0f6b2e52b5589d0e1e72afc34710a',
  'history-template-chrome-uat.mjs': '45faa88db307660438ad432b7251933464c0538c60ce6d714c37ea304cb365a9',
}

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

function redacted(value, tokens) {
  let output = value
  for (const token of Array.isArray(tokens) ? tokens : [tokens]) {
    if (token) output = output.split(token).join('[ISOLATION_TOKEN_REDACTED]')
  }
  return output
}

function startCaptured(command, args, { cwd, env, label, logPath }) {
  const child = spawn(command, args, { cwd, env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] })
  const logStream = createWriteStream(logPath, { flags: 'wx' })
  logStream.on('error', error => { child.isolationLogError = error })
  const chunks = []
  let bytes = 0
  let totalBytes = 0
  const append = chunk => {
    const buffer = Buffer.from(chunk)
    logStream.write(buffer)
    chunks.push(buffer)
    bytes += buffer.length
    totalBytes += buffer.length
    while (bytes > 32 * 1024 * 1024 && chunks.length > 1) bytes -= chunks.shift().length
  }
  child.stdout.on('data', append)
  child.stderr.on('data', append)
  child.once('close', () => logStream.end())
  child.isolationOutput = () => Buffer.concat(chunks).toString('utf8')
  child.isolationLabel = label
  child.isolationLogPath = logPath
  child.isolationLogTruncated = () => totalBytes > bytes
  child.isolationFlush = async () => {
    if (!logStream.writableEnded) logStream.end()
    await finished(logStream)
    if (child.isolationLogError) throw child.isolationLogError
  }
  return child
}

async function executeStage(label, command, args, { cwd, env, logRoot }) {
  const started = Date.now()
  const logPath = path.join(logRoot, `${label}.raw.log`)
  const child = startCaptured(command, args, { cwd, env, label, logPath })
  let close
  try {
    close = await once(child, 'close')
  } catch (error) {
    await child.isolationFlush().catch(() => {})
    const output = child.isolationOutput()
    throw Object.assign(error, { stageLogPath: logPath, stageOutput: output })
  }
  await child.isolationFlush()
  const output = child.isolationOutput()
  return {
    label,
    exit_code: close[0],
    signal: close[1],
    duration_ms: Date.now() - started,
    raw_log_path: logPath,
    raw_log_truncated: child.isolationLogTruncated(),
    output,
  }
}

async function captureOutput(label, child, logRoot) {
  if (!child) return null
  await child.isolationFlush()
  return child.isolationLogPath || path.join(logRoot, `${label}.raw.log`)
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

async function runCorrectedCopyVerification({ sourceDatabase, sourceMedia, outputJson, python, backendRoot, baseEnv, rawLogRoot, secretTokens }) {
  const runId = randomUUID()
  const token = randomBytes(24).toString('hex')
  secretTokens.push(token)
  const root = await mkdtemp(path.join(os.tmpdir(), 'sunjack-r1-repair-06-'))
  const databasePath = path.join(root, 'db.sqlite3')
  const mediaRoot = path.join(root, 'media')
  const markerPath = path.join(root, '.sunjack-playwright-isolation.json')
  const report = {
    result: 'FAIL',
    exit_code: null,
    source_database: path.relative(evidenceRoot, sourceDatabase).replaceAll(path.sep, '/'),
    verification_database_copy: path.basename(root),
    database_sha256_before: null,
    database_sha256_after: null,
    database_unchanged: false,
    isolated_identity: false,
    log: null,
    temp_root_cleanup: false,
    stage: null,
  }
  try {
    await writeFile(markerPath, `${JSON.stringify({ runId, token, root: path.resolve(root) }, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' })
    const sourceStat = await lstat(sourceDatabase)
    if (!sourceStat.isFile() || sourceStat.isSymbolicLink()) throw new Error('Sanitized published database must be a regular file.')
    await copyFile(sourceDatabase, databasePath, constants.COPYFILE_EXCL)
    await copyDirectoryContents(sourceMedia, mediaRoot)
    report.database_sha256_before = sha256(await readFile(databasePath))

    const verifyEnv = { ...baseEnv }
    Object.assign(verifyEnv, {
      DATABASE_URL: sqliteDatabaseUrl(databasePath),
      MEDIA_ROOT: mediaRoot,
      ISOLATED_TEST_ROOT: root,
      ISOLATED_TEST_RUN_ID: runId,
      ISOLATED_TEST_TOKEN: token,
      ISOLATED_TEST_DATABASE: databasePath,
      ISOLATED_TEST_MEDIA_ROOT: mediaRoot,
      ISOLATED_TEST_PYTHON: python,
      PYTHONPATH: [backendRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
    })
    const verification = await executeStage('corrected-copy-business-verification', python, [
      verifyScript, '--summary', '--output', outputJson,
    ], { cwd: backendRoot, env: verifyEnv, logRoot: rawLogRoot })
    report.stage = {
      label: 'corrected-copy-business-verification',
      exit_code: verification.exit_code,
      signal: verification.signal,
      duration_ms: verification.duration_ms,
      raw_log_path: verification.raw_log_path,
    }
    report.exit_code = verification.exit_code
    report.log = path.basename(verification.raw_log_path)
    if (verification.exit_code === 0) {
      report.result = 'PASS'
      report.summary = JSON.parse(verification.output)
      report.isolated_identity = true
    } else {
      report.error_output = redacted(verification.output, secretTokens)
    }
    report.database_sha256_after = sha256(await readFile(databasePath))
    report.database_unchanged = report.database_sha256_before === report.database_sha256_after
    if (!report.database_unchanged) {
      report.result = 'FAIL'
      report.error = 'Read-only verification changed its isolated published database copy.'
    }
  } catch (error) {
    report.error = redacted(error?.stack || String(error), secretTokens)
  } finally {
    try {
      await cleanupOwnedTempRoot(root, { runId, token })
      report.temp_root_cleanup = true
    } catch (error) {
      report.temp_root_retained = root
      report.cleanup_error = error.message
      report.result = 'FAIL'
    }
  }
  return report
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

async function assertNoSessionFiles(directory) {
  for (const entry of await (await import('node:fs/promises')).readdir(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name)
    if (/^(session\.json|reviewer-session\.json)$/i.test(entry.name)) throw new Error(`Private session file entered published evidence: ${filename}`)
    if (entry.isSymbolicLink()) throw new Error(`Unexpected linked evidence path: ${filename}`)
    if (entry.isDirectory()) await assertNoSessionFiles(filename)
  }
}

async function publishLog(label, rawPath, tokens, publishedLogRoot) {
  const raw = await readFile(rawPath)
  const rawText = raw.toString('utf8')
  const published = redacted(rawText, tokens)
  const publishedPath = path.join(publishedLogRoot, `${label}.log`)
  await writeFile(publishedPath, published, { encoding: 'utf8', flag: 'wx' })
  return {
    name: `${label}.log`,
    raw_sha256: sha256(raw),
    published_sha256: sha256(Buffer.from(published, 'utf8')),
    raw_bytes: raw.length,
    published_bytes: Buffer.byteLength(published, 'utf8'),
    token_redactions: (Array.isArray(tokens) ? tokens : [tokens]).reduce((count, token) => count + countOccurrences(rawText, token), 0),
  }
}

async function captureSourceScripts() {
  const sourceRoot = path.join(frontendRoot, 'scripts')
  const snapshotRoot = path.join(evidenceRoot, 'harness', 'source-scripts')
  const provenance = []
  for (const name of sourceNames) {
    const source = path.join(sourceRoot, name)
    const bytes = await readFile(source)
    const text = bytes.toString('utf8')
    const sourceHash = sha256(bytes)
    if (sourceHash !== sourceScriptBaselineSha256[name]) {
      throw new Error(`${name} differs from the reviewed 447d source script; refusing an unreviewed acceptance-script change.`)
    }
    if (!text.includes("channel: 'chrome'")) throw new Error(`${name} does not explicitly launch Chrome.`)
    const snapshot = path.join(snapshotRoot, name)
    await writeFile(snapshot, bytes, { flag: 'wx' })
    provenance.push({
      name,
      source: path.relative(frozenRoot, source).replaceAll(path.sep, '/'),
      source_sha256: sourceHash,
      reviewed_447d_sha256: sourceScriptBaselineSha256[name],
      source_bytes: bytes.length,
      evidence_copy: path.relative(evidenceRoot, snapshot).replaceAll(path.sep, '/'),
      evidence_copy_sha256: sha256(await readFile(snapshot)),
      explicitly_launches_chrome: true,
    })
  }
  return provenance
}

async function verifySourceScriptsUnchanged(provenance) {
  const after = []
  for (const entry of provenance) {
    const source = path.join(frozenRoot, entry.source)
    const bytes = await readFile(source)
    const current = sha256(bytes)
    if (current !== entry.source_sha256) throw new Error(`Source browser script changed during run: ${entry.name}`)
    const snapshot = path.join(evidenceRoot, entry.evidence_copy)
    if (sha256(await readFile(snapshot)) !== entry.evidence_copy_sha256) throw new Error(`Evidence source copy changed during run: ${entry.name}`)
    after.push({ name: entry.name, source_sha256_before: entry.source_sha256, source_sha256_after: current, unchanged: true })
  }
  return after
}

async function createInventoryAcceptanceCopy(actualSku) {
  const source = path.join(frontendRoot, 'scripts', 'history-inventory-location-chrome-uat.mjs')
  const sourceBytes = await readFile(source)
  const original = sourceBytes.toString('utf8')
  const oldSku = 'UAT-HT-S1'
  const importLine = "from '@playwright/test'"
  const skuOccurrences = countOccurrences(original, oldSku)
  if (skuOccurrences < 1 || countOccurrences(original, importLine) !== 1 || !actualSku || original.includes(actualSku)) {
    throw new Error('The delivered inventory-location script does not have a unique import and replaceable SKU fixture.')
  }
  if (!original.includes("chromium.launch({ channel: 'chrome', headless: true })")) {
    throw new Error('The delivered inventory-location script does not explicitly launch Chrome.')
  }
  const packageEntry = path.join(frontendRoot, 'node_modules', '@playwright', 'test', 'index.mjs')
  const rewrittenImport = `from '${pathToFileURL(packageEntry).href}'`
  const afterImport = original.replace(importLine, rewrittenImport)
  const importBytes = Buffer.from(afterImport, 'utf8')
  const transformed = afterImport.replaceAll(oldSku, actualSku)
  const transformedBytes = Buffer.from(transformed, 'utf8')
  const restored = transformed.replaceAll(actualSku, oldSku).replace(rewrittenImport, importLine)
  if (restored !== original) throw new Error('Inventory acceptance copy contains edits beyond the generated SKU and frozen Playwright import substitutions.')
  await writeFile(inventoryCopy, transformedBytes, { flag: 'wx' })
  return {
    source: path.relative(frozenRoot, source).replaceAll(path.sep, '/'),
    source_sha256: sha256(sourceBytes),
    transformations: [
      {
        kind: 'playwright-import',
        from: importLine,
        to: rewrittenImport,
        occurrences: 1,
        input_sha256: sha256(sourceBytes),
        output_sha256: sha256(importBytes),
      },
      {
        kind: 'api-generated-sku-fixture',
        from: oldSku,
        to: actualSku,
        occurrences: skuOccurrences,
        input_sha256: sha256(importBytes),
        output_sha256: sha256(transformedBytes),
      },
    ],
    acceptance_copy: path.relative(evidenceRoot, inventoryCopy).replaceAll(path.sep, '/'),
    acceptance_copy_sha256: sha256(transformedBytes),
    acceptance_copy_bytes: transformedBytes.length,
    round_trip_matches_original: restored === original,
  }
}

function requiredStage(name, result) {
  if (result.exit_code !== 0) throw new Error(`${name} exited ${result.signal || `code ${result.exit_code}`}.`)
  return result
}

function gitOutput(args) {
  return execFileSync('git', ['-C', frozenRoot, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()
}

function samePath(left, right) {
  const a = path.resolve(left).replace(/[\\/]+$/, '')
  const b = path.resolve(right).replace(/[\\/]+$/, '')
  return process.platform === 'win32' ? a.toLowerCase() === b.toLowerCase() : a === b
}

async function assertStableCheckout(phase) {
  const actualHead = gitOutput(['rev-parse', 'HEAD'])
  if (actualHead !== expectedSha) throw new Error(`${phase}: expected HEAD ${expectedSha}, found ${actualHead}.`)
  const actualRoot = await realpath(gitOutput(['rev-parse', '--show-toplevel']))
  if (!samePath(actualRoot, frozenRoot)) throw new Error(`${phase}: Git top-level does not match supplied checkout path.`)
  const dirty = gitOutput(['status', '--porcelain=v1', '--untracked-files=all', '--', 'backend', 'frontend'])
  if (dirty) throw new Error(`${phase}: backend/frontend are not clean:\n${dirty}`)
  return { head: actualHead, application_dirs_clean: true, git_root: actualRoot }
}

async function assertPathAbsent(target, label) {
  try {
    await lstat(target)
    throw new Error(`${label} already exists; refusing to overwrite: ${target}`)
  } catch (error) {
    if (error?.code !== 'ENOENT') throw error
  }
}

const preflightGit = await assertStableCheckout('Preflight')
for (const filename of [python, path.join(frontendRoot, 'node_modules', 'vite', 'bin', 'vite.js'), path.join(frontendRoot, 'node_modules', '@playwright', 'test', 'index.mjs'), ...sourceNames.map(name => path.join(frontendRoot, 'scripts', name))]) {
  await access(filename)
}
await assertPathAbsent(evidenceRoot, 'Evidence directory')
const pythonVersionProbe = execFileSync(python, ['--version'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()
if (!/^Python 3\.12\./.test(pythonVersionProbe)) throw new Error(`Expected Python 3.12 environment; found ${pythonVersionProbe}.`)

await assertPortsAvailable([{ name: 'API', port: apiPort }, { name: 'Vite', port: vitePort }])
const runId = randomUUID()
const token = randomBytes(24).toString('hex')
const secretTokens = [token]
const tempRoot = await mkdtemp(path.join(os.tmpdir(), 'sunjack-r1-repair-06-'))
const databasePath = path.join(tempRoot, 'db.sqlite3')
const mediaRoot = path.join(tempRoot, 'media')
const sessionDir = path.join(tempRoot, `sunjack-history-operational-closeout-final-${runId}`)
const rawLogRoot = path.join(tempRoot, 'logs')
const publishedLogRoot = path.join(evidenceRoot, 'logs')
const artifactRoot = path.join(evidenceRoot, 'artifacts')
const marker = { runId, token, root: path.resolve(tempRoot) }

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
  ISOLATED_HISTORY_SESSION_DIR: sessionDir,
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
  schema_version: 2,
  run_kind: 'FINAL_DOCS_ONLY_HISTORY_CHROME_UAT',
  product_sha: expectedSha,
  frozen_checkout: frozenRoot,
  evidence_directory: evidenceRoot,
  run_id: runId,
  chrome_channel_explicit_in_source_scripts: chromeChannel,
  runtime: { node: process.version, python: pythonVersionProbe, chrome_version: null },
  preflight: { git_before: preflightGit, git_after: null, python_312: true, node_dependencies_present: true },
  source_scripts: [],
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
    session_files_kept_out_of_evidence: true,
  },
  identities: {},
  seed: null,
  inventory_acceptance_copy: null,
  stages: [],
  screenshots: [],
  logs: [],
  database_copy: null,
  media_copy: null,
  teardown: { api_stopped: false, vite_stopped: false, ports_released: false, owned_temp_cleanup: false, sanitized_copy_verification_cleanup: false },
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
  await writeFile(path.join(tempRoot, '.sunjack-playwright-isolation.json'), `${JSON.stringify(marker, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' })
  await mkdir(mediaRoot)
  await mkdir(rawLogRoot)
  await mkdir(evidenceRoot, { recursive: false })
  await mkdir(publishedLogRoot)
  await mkdir(artifactRoot)
  await mkdir(path.join(evidenceRoot, 'harness'))
  await mkdir(path.join(evidenceRoot, 'harness', 'source-scripts'))
  result.source_scripts = await captureSourceScripts()
  const pythonVersion = await stage('python-version', python, ['--version'], { cwd: backendRoot, env, logRoot: rawLogRoot })
  result.runtime.python = pythonVersion.output.trim()
  requiredStage('Python version', pythonVersion)

  const migrate = await stage('isolated-migration', python, [seedScript, '--migrate-only'], { cwd: backendRoot, env, logRoot: rawLogRoot })
  requiredStage('Isolated migration', migrate)

  apiServer = startCaptured(python, ['manage.py', 'runserver', `127.0.0.1:${apiPort}`, '--noreload'], {
    cwd: backendRoot, env, label: 'isolated Django API', logPath: path.join(rawLogRoot, 'api-server.raw.log'),
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
  ], { cwd: frontendRoot, env, label: 'isolated Vite', logPath: path.join(rawLogRoot, 'vite-server.raw.log') })
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

  const workflowStagesPassed = result.stages.some(item => item.label === 'history-operational-chrome' && item.exit_code === 0)
    && result.stages.some(item => item.label === 'history-operational-workflow' && item.exit_code === 0)
    && result.stages.some(item => item.label === 'history-operational-fulfillment' && item.exit_code === 0)
  if (workflowStagesPassed) {
    const verification = await stage('read-only-business-verification-live', python, [
      verifyScript, '--summary', '--output', path.join(evidenceRoot, 'business-row-summary-live.json'),
    ], { cwd: backendRoot, env, logRoot: rawLogRoot })
    if (verification.exit_code === 0) {
      result.business_verification_live = JSON.parse(verification.output)
    } else {
      result.errors.push('Live read-only business verification did not complete.')
    }
  } else {
    result.blocked_stages.push({ stage: 'read-only-business-verification-live', reason: 'The operational, workflow, and fulfillment Chrome prerequisites did not all pass; read-only business assertions were not evaluated as if missing downstream records were product failures.' })
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
  }).map(line => redacted(line, secretTokens))

  result.source_scripts_unchanged = await verifySourceScriptsUnchanged(result.source_scripts)
  if (result.inventory_acceptance_copy && sha256(await readFile(inventoryCopy)) !== result.inventory_acceptance_copy.acceptance_copy_sha256) {
    throw new Error('Inventory acceptance copy changed after its recorded mechanical substitutions.')
  }
  result.preflight.git_after = await assertStableCheckout('Post-browser run')

  // Stop only the two process trees started by this run before database/media export.
} catch (error) {
  result.errors.push(redacted(error?.stack || String(error), secretTokens))
  console.error(`[UAT] fatal: ${redacted(error?.message || String(error), secretTokens)}`)
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

  const isolatedServicesStopped = result.teardown.api_stopped && result.teardown.vite_stopped && result.teardown.ports_released
  if (isolatedServicesStopped) {
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
            const info = await lstat(file)
            if (info.isSymbolicLink()) throw new Error(`Refusing linked media artifact: ${file}`)
            if (info.isDirectory()) await walkMedia(file)
            else if (info.isFile()) {
              const bytes = await readFile(file)
              mediaFiles.push({ path: path.relative(mediaCopy, file).replaceAll(path.sep, '/'), size: bytes.length, sha256: sha256(bytes) })
            } else throw new Error(`Refusing non-regular media artifact: ${file}`)
          }
        }
        await walkMedia(mediaCopy)
        result.media_copy = { path: 'artifacts/media', file_count: mediaFiles.length, files: mediaFiles }

        const corePassed = ['history-operational-chrome', 'history-operational-workflow', 'history-operational-fulfillment']
          .every(label => result.stages.some(item => item.label === label && item.exit_code === 0))
        if (sanitize.exit_code === 0 && corePassed) {
          const corrected = await runCorrectedCopyVerification({
            sourceDatabase: dbCopy,
            sourceMedia: mediaCopy,
            outputJson: path.join(evidenceRoot, 'business-row-summary-corrected.json'),
            python,
            backendRoot,
            baseEnv: env,
            rawLogRoot,
            secretTokens,
          })
          result.corrected_copy_verification = corrected
          if (corrected.stage) result.stages.push(corrected.stage)
          result.teardown.sanitized_copy_verification_cleanup = corrected.temp_root_cleanup
          if (corrected.result !== 'PASS') result.errors.push('Corrected read-only verification of the published database/media copy failed.')
        } else {
          result.corrected_copy_verification = {
            result: 'BLOCKED',
            reason: 'Sanitized database copy or operational/workflow/fulfillment Chrome prerequisite did not pass.',
          }
          result.blocked_stages.push({ stage: 'corrected-copy-business-verification', reason: result.corrected_copy_verification.reason })
        }
      } else {
        result.errors.push('Isolated database was not present for artifact preservation.')
      }
    } catch (error) {
      result.errors.push(`Artifact preservation or corrected verification failed: ${redacted(error?.stack || String(error), secretTokens)}`)
    }
  } else {
    result.errors.push('Database/media export withheld because owned services or ports were not proven stopped.')
  }

  for (const item of result.stages) {
    try {
      const rawPath = item.raw_log_path
      const label = path.basename(rawPath).replace(/\.raw\.log$/, '')
      result.logs.push(await publishLog(label, rawPath, secretTokens, publishedLogRoot))
      item.evidence_log = `logs/${label}.log`
      delete item.raw_log_path
    } catch (error) {
      result.errors.push(`Could not publish ${item.raw_log_path}: ${error.message}`)
    }
  }
  for (const label of ['api-server', 'vite-server']) {
    const rawPath = path.join(rawLogRoot, `${label}.raw.log`)
    if (await stat(rawPath).then(() => true, () => false)) {
      try {
        result.logs.push(await publishLog(label, rawPath, secretTokens, publishedLogRoot))
        if (label === 'api-server') {
          const text = await readFile(rawPath, 'utf8')
          const requests = [...text.matchAll(/"([A-Z]+) ([^ "\r\n]+) HTTP\/1\.1" (\d{3})/g)].map(match => ({ method: match[1], path: match[2], status: Number(match[3]) }))
          result.http_evidence = {
            api_log: 'logs/api-server.log',
            vite_log: 'logs/vite-server.log',
            local_api_requests: requests.length,
            status_counts: Object.fromEntries([...new Set(requests.map(row => row.status))].sort().map(status => [String(status), requests.filter(row => row.status === status).length])),
            requests,
          }
        }
      }
      catch (error) { result.errors.push(`Could not publish ${label} log: ${error.message}`) }
    }
  }

  if (!result.preflight.git_after) {
    try { result.preflight.git_after = await assertStableCheckout('Finalization') }
    catch (error) { result.errors.push(`Final checkout verification failed: ${error.message}`) }
  }
  if (!result.source_scripts_unchanged && result.source_scripts.length) {
    try { result.source_scripts_unchanged = await verifySourceScriptsUnchanged(result.source_scripts) }
    catch (error) { result.errors.push(`Source browser script stability check failed: ${error.message}`) }
  }
  try { await assertNoSessionFiles(evidenceRoot) }
  catch (error) { result.errors.push(`Published evidence privacy check failed: ${error.message}`) }

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

  const requiredChromeStages = [
    'history-operational-chrome',
    'history-operational-workflow',
    'history-operational-fulfillment',
    'history-inventory-location',
    'history-template',
  ]
  const chromeStageResults = Object.fromEntries(requiredChromeStages.map(label => [
    label,
    result.stages.find(item => item.label === label)?.exit_code ?? null,
  ]))
  const chromePassed = Object.values(chromeStageResults).every(code => code === 0)
  const correctedVerifyPassed = result.corrected_copy_verification?.result === 'PASS'
    && result.corrected_copy_verification?.exit_code === 0
  const liveVerifyPassed = result.stages.some(item => item.label === 'read-only-business-verification-live' && item.exit_code === 0)
  const artifactEvidencePassed = result.screenshots.length === 8
    && Boolean(result.template_download)
    && Boolean(result.database_copy)
    && Boolean(result.media_copy)
  result.acceptance = {
    chrome_stage_results: chromeStageResults,
    chrome_pass_count: Object.values(chromeStageResults).filter(code => code === 0).length,
    chrome_fail_or_missing_count: Object.values(chromeStageResults).filter(code => code !== 0).length,
    live_read_only_verification_exit_code: result.stages.find(item => item.label === 'read-only-business-verification-live')?.exit_code ?? null,
    corrected_copy_verification_exit_code: result.corrected_copy_verification?.exit_code ?? null,
    screenshots_count: result.screenshots.length,
    downloaded_workbook_present: Boolean(result.template_download),
    required_artifacts_present: artifactEvidencePassed,
  }
  result.final_status = chromePassed && correctedVerifyPassed && liveVerifyPassed && artifactEvidencePassed
    && result.errors.length === 0 && result.blocked_stages.length === 0
    && result.teardown.api_stopped && result.teardown.vite_stopped && result.teardown.ports_released
    && result.teardown.owned_temp_cleanup && result.teardown.sanitized_copy_verification_cleanup
    && Array.isArray(result.source_scripts_unchanged) && result.source_scripts_unchanged.length === sourceNames.length
    && result.source_scripts_unchanged.every(item => item.unchanged)
    && result.preflight.git_after?.application_dirs_clean
    ? 'PASS'
    : 'INCOMPLETE_OR_FAILED'
  const resultPath = path.join(evidenceRoot, 'result.json')
  const resultText = `${redacted(JSON.stringify(result, null, 2), secretTokens)}\n`
  await writeFile(resultPath, resultText, { encoding: 'utf8', flag: 'wx' }).catch(error => console.error(`Could not write final result JSON: ${error.message}`))
  console.log(`[UAT] final status ${result.final_status}; result ${resultPath}`)
}

if (result.final_status !== 'PASS') process.exitCode = 1
