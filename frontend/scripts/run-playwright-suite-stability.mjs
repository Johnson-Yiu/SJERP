import { execFileSync, spawn } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptsRoot = path.dirname(fileURLToPath(import.meta.url))
const frontendRoot = path.resolve(scriptsRoot, '..')
const repositoryRoot = path.resolve(frontendRoot, '..')
const defaultReportRoot = path.join(repositoryRoot, 'docs', 'uat-evidence', 'r1-integration-iss006-052-ux-pw-auth')
const reportRoot = process.env.R1_PLAYWRIGHT_EVIDENCE_ROOT
  ? path.resolve(process.env.R1_PLAYWRIGHT_EVIDENCE_ROOT)
  : defaultReportRoot
const logsRoot = path.join(reportRoot, 'logs')
const runnerPath = path.join(scriptsRoot, 'run-isolated-browser-tests.mjs')

const dedicatedRuns = [
  { name: 'history-product-linking-h2-isolated', file: 'history-product-linking-h2-real.spec.js', codex: true },
  { name: 'sales-evidence-01-isolated', file: 'ui-sales-state-evidence-01.spec.js', codex: true },
  { name: 'sales-evidence-01-party-isolated', file: 'ui-sales-state-evidence-01-party.spec.js', codex: true },
  { name: 'product-operations-evidence-01-isolated', file: 'ui-product-operations-state-evidence-01.spec.js', codex: true },
  { name: 'sales-completion-02-isolated', file: 'ui-sales-completion-02.spec.js', codex: true },
  { name: 'product-operations-completion-02-isolated', file: 'ui-product-operations-completion-02.spec.js', codex: true },
  { name: 'product-operations-prefix-02-isolated', file: 'ui-product-operations-prefix-02.spec.js', codex: true },
  { name: 'product-operations-parameter-02-isolated', file: 'ui-product-operations-parameter-02.spec.js', codex: true },
  { name: 'product-operations-carton-02-isolated', file: 'ui-product-operations-carton-02.spec.js', codex: true },
  { name: 'product-operations-category-02-isolated', file: 'ui-product-operations-category-02.spec.js', codex: true },
  { name: 'product-operations-sku-lifecycle-02-isolated', file: 'ui-product-operations-sku-lifecycle-02.spec.js', codex: true },
  { name: 'product-operations-supplier-02-isolated', file: 'ui-product-operations-supplier-02.spec.js', codex: true },
  { name: 'product-operations-lots-02-isolated', file: 'ui-product-operations-lots-02.spec.js', codex: true },
  ...Array.from({ length: 10 }, (_, index) => ({
    name: `sales-completion-extra-${index + 1}`,
    file: 'ui-sales-completion-02.spec.js',
    codex: true,
    env: { E1_R2_EXTRA: String(index + 1) },
  })),
  ...['JOURNEYS', 'SUPPLEMENTAL', 'FOCUSED'].map(mode => ({
    name: `sales-state-${mode.toLowerCase()}`,
    file: 'ui-sales-state-evidence-01.spec.js',
    codex: true,
    env: { [`SALES_STATE_${mode}`]: '1' },
  })),
  {
    name: 'sales-state-apply-quantity',
    file: 'ui-sales-state-evidence-01.spec.js',
    codex: true,
    env: {
      SALES_STATE_JOURNEYS: '1',
      SALES_STATE_APPLY_QUANTITY: '1',
      SALES_STATE_SCENARIOS: 'O04-confirm,O06-quantity',
    },
  },
  ...['1', 'refresh', 'lifecycle', 'verify', 'priority', 'candidate', 'priority-standard'].map(mode => ({
    name: `product-operations-state-${mode}`,
    file: 'ui-product-operations-state-evidence-01.spec.js',
    codex: true,
    env: mode === 'priority-standard'
      ? { PRODUCT_OPS_FOLLOWUP: 'priority', PRODUCT_OPS_PRIORITY_ZOOM: '100' }
      : { PRODUCT_OPS_FOLLOWUP: mode },
  })),
  { name: 'product-operations-inventory-actions-02', file: 'ui-product-operations-inventory-actions-02.spec.js', codex: true },
  { name: 'product-operations-receipts-02', file: 'ui-product-operations-receipts-02.spec.js', codex: true },
  { name: 'workspace-tabs-isolated', file: 'workspace-tabs-real.spec.js' },
  { name: 'workspace-integration-isolated', file: 'workspace-integration-real.spec.js', codex: true },
  { name: 'first-release-consolidation-isolated', file: 'first-release-consolidation-02.spec.js', codex: true },
  { name: 'sales-order-import-isolated', file: 'sales-order-import-real.spec.js', codex: true },
  { name: 'historical-orders-02-isolated', file: 'historical-orders-fix-02.spec.js' },
  { name: 'historical-orders-03-isolated', file: 'historical-orders-fix-03.spec.js' },
  { name: 'recipient-snapshot-isolated', file: 'iss029-recipient-snapshot.spec.js' },
  { name: 'party-order-purchase-isolated', file: 'party-order-purchase-real.spec.js' },
  { name: 'party-replacement-acceptance-isolated', file: 'party-replacement-acceptance-20261106.spec.js' },
  { name: 'party-replacement-po-isolated', file: 'party-replacement-po-real.spec.js' },
  { name: 'party-replacement-quote-isolated', file: 'party-replacement-quote-real.spec.js' },
  { name: 'party-lifecycle-isolated', file: 'party-lifecycle-real.spec.js' },
  ...['party-lifecycle-real.spec.js', 'party-replacement-quote-real.spec.js'].map(file => ({
    name: file.replace('.spec.js', '-native-125'),
    file,
    env: { SALES_PARTY_NATIVE_ZOOM: '1.25' },
  })),
  { name: 'party-replacement-order-isolated', file: 'party-replacement-real.spec.js' },
]

const source = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repositoryRoot, encoding: 'utf8' }).trim()

const runs = [
  {
    name: 'business-suite',
    args: [
      '--all-business-tests',
      '--exclude-business-test', 'iss022-moq-real.spec.js',
      '--exclude-business-test', 'iss028-035-category-schema.spec.js',
      '--exclude-business-test', 'iss055-customer-404-real.spec.js',
      '--exclude-business-test', 'iss006-frontend-storage-chrome.spec.js',
      '--exclude-business-test', 'iss007-attachment-real.spec.js',
      '--exclude-business-test', 'iss007-image-snapshot-real.spec.js',
      '--exclude-business-test', 'shared-report-templates.spec.js',
      '--exclude-business-test', 'quote-editor-mobile-actions.spec.js',
      ...[...new Set(dedicatedRuns.map(run => run.file))].flatMap(file => ['--exclude-business-test', file]),
    ],
  },
  { name: 'shared-report-templates-isolated', args: ['--business-test', 'shared-report-templates.spec.js'] },
  { name: 'quote-editor-isolated', args: ['--business-test', 'quote-editor-mobile-actions.spec.js'] },
  { name: 'iss006-storage-isolated', args: ['--business-test', 'iss006-frontend-storage-chrome.spec.js'] },
  { name: 'iss007-attachment-isolated', args: ['--business-test', 'iss007-attachment-real.spec.js'] },
  { name: 'iss007-image-snapshot-isolated', args: ['--business-test', 'iss007-image-snapshot-real.spec.js'] },
  { name: 'iss022-isolated', args: ['--business-test', 'iss022-moq-real.spec.js'] },
  { name: 'iss028-035-isolated', args: ['--business-test', 'iss028-035-category-schema.spec.js'] },
  { name: 'iss055-rbac', args: ['--business-test', 'iss055-customer-404-real.spec.js'] },
  ...dedicatedRuns.map(run => ({ ...run, args: ['--business-test', run.file] })),
]

await mkdir(logsRoot, { recursive: true })
const summary = []

for (const run of runs) {
  const stdoutChunks = []
  const stderrChunks = []
  const runEnv = { ...process.env }
  for (const key of [
    'E1_R2_EXTRA', 'E1_R2_WIDTH', 'SALES_PARTY_NATIVE_ZOOM',
    'SALES_STATE_JOURNEYS', 'SALES_STATE_SUPPLEMENTAL', 'SALES_STATE_FOCUSED',
    'SALES_STATE_CASES', 'SALES_STATE_SCENARIOS', 'SALES_STATE_SHOTS',
    'SALES_STATE_WIDTH', 'SALES_STATE_ZOOM', 'SALES_STATE_APPLY_QUANTITY',
    'PRODUCT_OPS_FOLLOWUP', 'PRODUCT_OPS_PRIORITY_ZOOM',
  ]) delete runEnv[key]
  Object.assign(runEnv, run.env)
  runEnv.PRODUCT_OPS_CANDIDATE_SHA = source
  runEnv.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT = path.join(reportRoot, run.name)
  runEnv.ISOLATED_PLAYWRIGHT_JSON = '1'
  runEnv.A3_STRICT_BROWSER_EVIDENCE = '1'
  runEnv.ISOLATED_CODEX_TEST_SUPERADMIN = run.codex ? '1' : '0'
  if (run.codex && process.env.GITHUB_ACTIONS === 'true') {
    runEnv.ERP_TEST_USERNAME = 'codex'
    runEnv.ERP_TEST_PASSWORD = randomBytes(24).toString('base64url')
  }
  const child = spawn(process.execPath, [runnerPath, ...run.args], {
    cwd: frontendRoot,
    env: runEnv,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  child.stdout.on('data', chunk => {
    stdoutChunks.push(chunk)
    process.stdout.write(`[${run.name}] ${chunk}`)
  })
  child.stderr.on('data', chunk => {
    stderrChunks.push(chunk)
    process.stderr.write(`[${run.name}] ${chunk}`)
  })

  const [code, signal] = await new Promise((resolve, reject) => {
    child.once('error', reject)
    child.once('close', (exitCode, exitSignal) => resolve([exitCode, exitSignal]))
  })
  const stdoutPath = path.join(logsRoot, `${run.name}.stdout.log`)
  const stderrPath = path.join(logsRoot, `${run.name}.stderr.log`)
  await Promise.all([
    writeFile(stdoutPath, Buffer.concat(stdoutChunks)),
    writeFile(stderrPath, Buffer.concat(stderrChunks)),
  ])
  summary.push({
    name: run.name,
    mode: run.env ?? {},
    command: [process.execPath, runnerPath, ...run.args],
    exitCode: code,
    signal,
    stdout: path.relative(repositoryRoot, stdoutPath).replaceAll('\\', '/'),
    stderr: path.relative(repositoryRoot, stderrPath).replaceAll('\\', '/'),
  })
}

const allPassed = summary.every(run => run.exitCode === 0 && !run.signal)
const summaryPath = path.join(reportRoot, 'suite-run-summary.json')
await writeFile(summaryPath, `${JSON.stringify({ source, allPassed, runs: summary }, null, 2)}\n`, 'utf8')
console.log(`Playwright suite stability: ${allPassed ? 'passed' : 'failed'}; summary ${summaryPath}`)
if (!allPassed) process.exitCode = 1
