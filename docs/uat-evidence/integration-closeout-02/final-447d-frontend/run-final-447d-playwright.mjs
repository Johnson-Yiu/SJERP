import { spawn } from 'node:child_process'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const repositoryRoot = path.resolve(scriptDirectory, '../../../../')
const frontendRoot = path.join(repositoryRoot, 'frontend')
const runnerPath = path.join(frontendRoot, 'scripts', 'run-isolated-browser-tests.mjs')
const logsRoot = path.join(scriptDirectory, 'logs', 'playwright-profiles')
const python = 'D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/.tmp/closeout-python312/Scripts/python.exe'
const openssl = 'D:/Program Files/Git/usr/bin/openssl.exe'

const originalBusinessExclusions = [
  'iss022-moq-real.spec.js',
  'iss028-035-category-schema.spec.js',
  'iss055-customer-404-real.spec.js',
  'iss006-frontend-storage-chrome.spec.js',
  'iss007-attachment-real.spec.js',
  'iss007-image-snapshot-real.spec.js',
  'shared-report-templates.spec.js',
  'quote-editor-mobile-actions.spec.js',
]
const deferredSpec = 'iss037-print-output-acceptance.spec.js'
const businessArgs = [
  '--all-business-tests',
  ...originalBusinessExclusions.flatMap(name => ['--exclude-business-test', name]),
  '--exclude-business-test', deferredSpec,
]
const runs = [
  { name: 'business-suite', args: businessArgs },
  { name: 'shared-report-templates-isolated', args: ['--business-test', 'shared-report-templates.spec.js'] },
  { name: 'quote-editor-isolated', args: ['--business-test', 'quote-editor-mobile-actions.spec.js'] },
  { name: 'iss006-storage-isolated', args: ['--business-test', 'iss006-frontend-storage-chrome.spec.js'] },
  { name: 'iss007-attachment-isolated', args: ['--business-test', 'iss007-attachment-real.spec.js'] },
  { name: 'iss007-image-snapshot-isolated', args: ['--business-test', 'iss007-image-snapshot-real.spec.js'] },
  { name: 'iss022-isolated', args: ['--business-test', 'iss022-moq-real.spec.js'] },
  { name: 'iss028-035-isolated', args: ['--business-test', 'iss028-035-category-schema.spec.js'] },
  { name: 'iss055-rbac', args: ['--business-test', 'iss055-customer-404-real.spec.js'] },
]

if (runs.length !== 9 || originalBusinessExclusions.length !== 8) {
  throw new Error('Final Playwright profile/exclusion contract changed unexpectedly.')
}
await mkdir(logsRoot, { recursive: true })

const evidenceRoot = scriptDirectory
const results = []

for (const run of runs) {
  const stdout = []
  const stderr = []
  const env = {
    ...process.env,
    ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT: evidenceRoot,
    ISOLATED_TEST_PYTHON: python,
    PYTHONUTF8: '1',
    OPS_TEST_OPENSSL: openssl,
  }
  // Let run-isolated-browser-tests.mjs and individual test.use() declarations
  // decide the browser channel exactly as in the frozen checkout.
  delete env.PLAYWRIGHT_CHANNEL
  process.stdout.write(`\n[final-447d] START ${run.name}: node ${runnerPath} ${run.args.join(' ')}\n`)
  const child = spawn(process.execPath, [runnerPath, ...run.args], {
    cwd: frontendRoot,
    env,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  child.stdout.on('data', chunk => stdout.push(chunk))
  child.stderr.on('data', chunk => stderr.push(chunk))
  const outcome = await new Promise(resolve => {
    child.once('error', error => resolve({ code: null, signal: null, spawnError: error.message }))
    child.once('close', (code, signal) => resolve({ code, signal, spawnError: null }))
  })

  const stdoutPath = path.join(logsRoot, `${run.name}.stdout.log`)
  const stderrPath = path.join(logsRoot, `${run.name}.stderr.log`)
  await Promise.all([
    writeFile(stdoutPath, Buffer.concat(stdout)),
    writeFile(stderrPath, Buffer.concat(stderr)),
  ])
  const combined = Buffer.concat([...stdout, ...stderr]).toString('utf8')
  const countMatches = [...combined.matchAll(/^\s*(\d+)\s+(passed|failed|skipped|flaky|interrupted|timed out)\b[^\r\n]*$/gim)]
  const counts = {}
  for (const [, rawCount, label] of countMatches) counts[label.toLowerCase()] = Number(rawCount)
  const item = {
    name: run.name,
    command: [process.execPath, runnerPath, ...run.args],
    exitCode: outcome.code,
    signal: outcome.signal,
    spawnError: outcome.spawnError,
    parsedPlaywrightSummary: countMatches.length ? counts : null,
    stdout: path.relative(evidenceRoot, stdoutPath).replaceAll('\\', '/'),
    stderr: path.relative(evidenceRoot, stderrPath).replaceAll('\\', '/'),
  }
  results.push(item)
  await writeFile(path.join(scriptDirectory, 'playwright-profiles.partial.json'), `${JSON.stringify({ results }, null, 2)}\n`, 'utf8')
  process.stdout.write(`[final-447d] END ${run.name}: exit=${outcome.code} signal=${outcome.signal || 'none'} summary=${JSON.stringify(item.parsedPlaywrightSummary)}\n`)
}

const allPassed = results.length === 9 && results.every(item => item.exitCode === 0 && !item.signal && !item.spawnError)
const summary = {
  allPassed,
  checkoutHeadProvided: '447d7816ead2e971e249cb2e762b1a6f7009b9c0',
  coordinator: path.relative(repositoryRoot, fileURLToPath(import.meta.url)).replaceAll('\\', '/'),
  originalRunner: path.relative(repositoryRoot, runnerPath).replaceAll('\\', '/'),
  profiles: results,
  businessSuiteExclusions: {
    originalEightPreserved: originalBusinessExclusions,
    additionalUserDeferredSpec: deferredSpec,
    noOtherCoordinatorExclusionsAdded: true,
  },
  deferredAcceptance: {
    spec: deferredSpec,
    state: 'NOT_RUN_USER_DEFERRED',
    userStatedScenarioCount: 6,
    sourceDeclaredTestCaseCount: 7,
    sourceScenarioNames: [
      'saved PI blocks printing when a document image fails',
      'saved PI permits printing after resources load on narrow screen',
      'Chrome UI print to PDF complete 1440px headers=false',
      'Chrome UI print to PDF complete 1440px headers=true',
      'Chrome UI print to PDF complete 390px headers=false',
      'Chrome UI print to PDF multipage 1440px headers=false',
      'Chrome UI print to PDF optional-empty 1440px headers=false',
    ],
    scenarioCountMismatch: 'The instruction says six; static inspection of the frozen spec finds two direct tests plus five parameterized cases. The entire spec remains excluded.',
    note: 'The entire spec is excluded from the business suite; no isolated profile invokes it.',
  },
  runtime: {
    python,
    pythonUtf8: '1',
    openssl,
    playwrightChannel: 'unchanged isolated-runner behavior; Chromium default except runner/test-level Chrome selections',
    coordinatorOverridesPlaywrightChannel: false,
  },
}
await writeFile(path.join(scriptDirectory, 'playwright-suite-summary.json'), `${JSON.stringify(summary, null, 2)}\n`, 'utf8')
await writeFile(path.join(scriptDirectory, 'playwright-profiles.partial.json'), `${JSON.stringify({ results, completed: true }, null, 2)}\n`, 'utf8')
console.log(`[final-447d] All nine profiles ${allPassed ? 'passed' : 'have failures'}; summary saved.`)
if (!allPassed) process.exitCode = 1
