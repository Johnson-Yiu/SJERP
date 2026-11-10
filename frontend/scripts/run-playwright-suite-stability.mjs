import { spawn } from 'node:child_process'
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
  { name: 'workspace-tabs-isolated', file: 'workspace-tabs-real.spec.js' },
  { name: 'workspace-integration-isolated', file: 'workspace-integration-real.spec.js', codex: true },
  { name: 'first-release-consolidation-isolated', file: 'first-release-consolidation-02.spec.js' },
  { name: 'sales-order-import-isolated', file: 'sales-order-import-real.spec.js', codex: true },
  { name: 'historical-orders-02-isolated', file: 'historical-orders-fix-02.spec.js' },
  { name: 'historical-orders-03-isolated', file: 'historical-orders-fix-03.spec.js' },
  { name: 'recipient-snapshot-isolated', file: 'iss029-recipient-snapshot.spec.js' },
  { name: 'party-order-purchase-isolated', file: 'party-order-purchase-real.spec.js' },
  { name: 'party-replacement-acceptance-isolated', file: 'party-replacement-acceptance-20261106.spec.js' },
  { name: 'party-replacement-po-isolated', file: 'party-replacement-po-real.spec.js' },
  { name: 'party-replacement-quote-isolated', file: 'party-replacement-quote-real.spec.js' },
  { name: 'party-replacement-order-isolated', file: 'party-replacement-real.spec.js' },
]

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
      ...dedicatedRuns.flatMap(run => ['--exclude-business-test', run.file]),
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
  runEnv.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT = reportRoot
  runEnv.ISOLATED_CODEX_TEST_SUPERADMIN = run.codex ? '1' : '0'
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
    command: [process.execPath, runnerPath, ...run.args],
    exitCode: code,
    signal,
    stdout: path.relative(repositoryRoot, stdoutPath).replaceAll('\\', '/'),
    stderr: path.relative(repositoryRoot, stderrPath).replaceAll('\\', '/'),
  })
}

const allPassed = summary.every(run => run.exitCode === 0 && !run.signal)
const summaryPath = path.join(reportRoot, 'suite-run-summary.json')
await writeFile(summaryPath, `${JSON.stringify({ allPassed, runs: summary }, null, 2)}\n`, 'utf8')
console.log(`Playwright suite stability: ${allPassed ? 'passed' : 'failed'}; summary ${summaryPath}`)
if (!allPassed) process.exitCode = 1
