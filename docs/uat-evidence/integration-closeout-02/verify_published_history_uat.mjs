import { spawn } from 'node:child_process'
import { createHash, randomBytes, randomUUID } from 'node:crypto'
import { access, cp, copyFile, lstat, mkdir, mkdtemp, readFile, stat, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { once } from 'node:events'
import { fileURLToPath, pathToFileURL } from 'node:url'

const reportRoot = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(reportRoot, '../../..')
const frozenRoot = path.join(repoRoot, '.tmp', 'final-integrated-447d')
const backendRoot = path.join(frozenRoot, 'backend')
const python = path.join(repoRoot, '.tmp', 'closeout-python312', 'Scripts', 'python.exe')
const verifyScript = path.join(reportRoot, 'verify_integrated_history_uat.py')
const sourceEvidence = path.join(reportRoot, 'final-447d-history-chrome-r03')
const sourceDatabase = path.join(sourceEvidence, 'artifacts', 'isolated-sanitized.sqlite3')
const sourceMedia = path.join(sourceEvidence, 'artifacts', 'media')
const output = path.join(sourceEvidence, 'business-row-summary-corrected-final.json')
const logOutput = path.join(sourceEvidence, 'logs', 'read-only-business-verification-corrected-final.log')
const helperPath = path.join(frozenRoot, 'frontend', 'scripts', 'run-isolated-browser-tests.mjs')
const { cleanupOwnedTempRoot, sqliteDatabaseUrl } = await import(pathToFileURL(helperPath).href)

const runId = randomUUID()
const token = randomBytes(24).toString('hex')
const root = await mkdtemp(path.join(os.tmpdir(), 'sunjack-r1-repair-06-'))
const databasePath = path.join(root, 'db.sqlite3')
const mediaRoot = path.join(root, 'media')
const rawLogPath = path.join(root, 'verification.raw.log')
const markerPath = path.join(root, '.sunjack-playwright-isolation.json')
let child
let exitCode = null
let log = ''
const hash = value => createHash('sha256').update(value).digest('hex')

try {
  await writeFile(markerPath, `${JSON.stringify({ runId, token, root: path.resolve(root) }, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' })
  const sourceStat = await lstat(sourceDatabase)
  if (!sourceStat.isFile() || sourceStat.isSymbolicLink()) throw new Error('Published SQLite source must be a regular file.')
  await access(sourceMedia)
  await copyFile(sourceDatabase, databasePath)
  await cp(sourceMedia, mediaRoot, { recursive: true, errorOnExist: true, force: false })

  const env = { ...process.env }
  for (const key of Object.keys(env)) if (key.startsWith('PG')) delete env[key]
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
    ISOLATED_TEST_ROOT: root,
    ISOLATED_TEST_RUN_ID: runId,
    ISOLATED_TEST_TOKEN: token,
    ISOLATED_TEST_DATABASE: databasePath,
    ISOLATED_TEST_MEDIA_ROOT: mediaRoot,
    ISOLATED_TEST_PYTHON: python,
    PYTHONDONTWRITEBYTECODE: '1',
    PYTHONUNBUFFERED: '1',
    PYTHONUTF8: '1',
    PYTHONIOENCODING: 'utf-8',
    PYTHONPATH: [backendRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
  })

  child = spawn(python, [verifyScript, '--summary', '--output', output], {
    cwd: backendRoot, env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
  })
  const chunks = []
  child.stdout.on('data', chunk => chunks.push(Buffer.from(chunk)))
  child.stderr.on('data', chunk => chunks.push(Buffer.from(chunk)))
  const [code, signal] = await once(child, 'close')
  exitCode = code
  log = Buffer.concat(chunks).toString('utf8')
  await writeFile(rawLogPath, log, 'utf8')
  const publishedLog = log.split(token).join('[ISOLATION_TOKEN_REDACTED]')
  await writeFile(logOutput, publishedLog, 'utf8')
  const report = {
    result: code === 0 ? 'PASS' : 'FAIL',
    scope: 'Read-only verification against the sanitized r03 database/media copy; original Chrome services were already stopped.',
    source_product_sha: '447d7816ead2e971e249cb2e762b1a6f7009b9c0',
    source_database_sha256: hash(await readFile(sourceDatabase)),
    verification_database_copy: path.basename(root),
    exit_code: code,
    signal,
    summary: code === 0 ? JSON.parse(log) : null,
    output_json: path.relative(repoRoot, output).replaceAll(path.sep, '/'),
    log: path.relative(repoRoot, logOutput).replaceAll(path.sep, '/'),
    log_sha256_raw: hash(Buffer.from(log, 'utf8')),
    log_sha256_published: hash(Buffer.from(publishedLog, 'utf8')),
    token_redactions: log.split(token).length - 1,
    original_application_database_unchanged: true,
  }
  const resultPath = path.join(sourceEvidence, 'corrected-verification-final.json')
  await writeFile(resultPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8')
  console.log(JSON.stringify({ result: report.result, exit_code: code, output_json: report.output_json, log: report.log }, null, 2))
  if (code !== 0) process.exitCode = 1
} catch (error) {
  log = `${error?.stack || error}\n`
  await writeFile(rawLogPath, log, 'utf8').catch(() => {})
  const publishedLog = log.split(token).join('[ISOLATION_TOKEN_REDACTED]')
  await writeFile(logOutput, publishedLog, 'utf8').catch(() => {})
  const resultPath = path.join(sourceEvidence, 'corrected-verification-final.json')
  await writeFile(resultPath, `${JSON.stringify({ result: 'FAIL', exit_code: exitCode, error: publishedLog }, null, 2)}\n`, 'utf8').catch(() => {})
  console.error(publishedLog)
  process.exitCode = 1
} finally {
  try {
    await cleanupOwnedTempRoot(root, { runId, token })
  } catch (error) {
    console.error(`Marked verification root retained: ${root}; cleanup guard: ${error.message}`)
    process.exitCode = 1
  }
}
