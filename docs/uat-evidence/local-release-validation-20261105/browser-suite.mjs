import { spawn } from 'node:child_process'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..')
if (!process.env.RELEASE_EVIDENCE_ROOT || !/^[0-9a-f]{40}$/.test(process.env.RELEASE_CANDIDATE_SHA || '')) throw new Error('RELEASE_EVIDENCE_ROOT and RELEASE_CANDIDATE_SHA required')
const reportRoot = path.resolve(process.env.RELEASE_EVIDENCE_ROOT)
const frontendRoot = path.join(repositoryRoot, 'frontend')
const runnerPath = path.join(frontendRoot, 'scripts', 'run-isolated-browser-tests.mjs')
const logsRoot = path.join(reportRoot, 'logs', 'playwright-profiles')

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
      '--exclude-business-test', 'iss037-print-output-acceptance.spec.js',
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
]

await mkdir(logsRoot, { recursive: true })
const summary = []

for (const run of runs) {
  console.log(`Starting ${run.name}`)
  const stdoutChunks = []
  const stderrChunks = []
  const runEnv = { ...process.env, ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT: reportRoot }
  const child = spawn(process.execPath, [runnerPath, ...run.args], {
    cwd: frontendRoot,
    env: runEnv,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  child.stdout.on('data', chunk => stdoutChunks.push(chunk))
  child.stderr.on('data', chunk => stderrChunks.push(chunk))
  const [exitCode, signal] = await new Promise((resolve, reject) => {
    child.once('error', reject)
    child.once('close', (code, childSignal) => resolve([code, childSignal]))
  })
  const stdoutPath = path.join(logsRoot, `${run.name}.stdout.log`)
  const stderrPath = path.join(logsRoot, `${run.name}.stderr.log`)
  await Promise.all([
    writeFile(stdoutPath, Buffer.concat(stdoutChunks)),
    writeFile(stderrPath, Buffer.concat(stderrChunks)),
  ])
  summary.push({
    name: run.name,
    args: run.args,
    exitCode,
    signal,
    stdout: path.relative(reportRoot, stdoutPath).replaceAll('\\', '/'),
    stderr: path.relative(reportRoot, stderrPath).replaceAll('\\', '/'),
  })
  console.log(`Finished ${run.name}: exit=${exitCode}; signal=${signal || 'none'}`)
}

const allPassed = summary.every(run => run.exitCode === 0 && !run.signal)
const result = {
  candidateSha: process.env.RELEASE_CANDIDATE_SHA,
  allPassed,
  originalProfileCount: 9,
  originalBusinessSuiteExclusions: [
    'iss022-moq-real.spec.js',
    'iss028-035-category-schema.spec.js',
    'iss055-customer-404-real.spec.js',
    'iss006-frontend-storage-chrome.spec.js',
    'iss007-attachment-real.spec.js',
    'iss007-image-snapshot-real.spec.js',
    'shared-report-templates.spec.js',
    'quote-editor-mobile-actions.spec.js',
  ],
  additionalDeferredExclusion: 'iss037-print-output-acceptance.spec.js',
  deferredSpecRun: false,
  runs: summary,
}
const summaryPath = path.join(reportRoot, 'playwright-suite-summary.json')
await writeFile(summaryPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8')
console.log(`Playwright suite stability: ${allPassed ? 'passed' : 'failed'}; summary ${summaryPath}`)
if (!allPassed) process.exitCode = 1
