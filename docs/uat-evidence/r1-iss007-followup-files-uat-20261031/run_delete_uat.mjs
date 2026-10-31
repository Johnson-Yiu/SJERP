import { spawnSync } from 'node:child_process'
import { fileURLToPath, pathToFileURL } from 'node:url'
import path from 'node:path'
import { resolve } from 'node:path'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(scriptDir, '../../..')
const backendRoot = resolve(repoRoot, 'backend')
const python = process.env.ISS007_UAT_PYTHON
const evidenceDir = process.env.ISS007_UAT_EVIDENCE_DIR
const username = process.env.ISS007_UAT_USERNAME
const noPermissionUser = process.env.ISS007_UAT_NO_PERMISSION_USERNAME
const password = process.env.ISS007_UAT_PASSWORD

if (!python || !evidenceDir || !username || !noPermissionUser || !password) {
  throw new Error('Missing task-scoped ISS007 UAT runtime configuration.')
}

globalThis.ISS007_UAT_CONFIG = {
  frontendBase: 'http://127.0.0.1:5279',
  apiBase: 'http://127.0.0.1:8177',
  evidenceDir: path.join(evidenceDir, 'screenshots'),
  downloadDir: process.env.ISS007_UAT_DOWNLOAD_DIR,
  operator: username,
  noPermissionUser,
  password,
}

const browserScript = resolve(repoRoot, 'frontend/browser-tests/iss007-followup-attachment-uat.mjs')
const uat = await import(pathToFileURL(browserScript).href)

function verifyDatabase(mode) {
  const verifier = path.join(scriptDir, 'verify_delete_uat.py')
  const result = spawnSync(python, [verifier, mode], {
    cwd: backendRoot,
    env: process.env,
    encoding: 'utf8',
  })
  if (result.stdout) process.stdout.write(result.stdout)
  if (result.stderr) process.stderr.write(result.stderr)
  if (result.status !== 0) throw new Error(`Database verification '${mode}' failed (exit ${result.status}).`)
}

try {
  const before = await uat.runBeforeDelete()
  verifyDatabase('snapshot')
  const deletion = await uat.runDeletePhase()
  verifyDatabase('verify')
  console.log(JSON.stringify({ before, deletion, databaseVerification: 'PASS' }, null, 2))
} finally {
  await uat.browser.close().catch(() => {})
}
