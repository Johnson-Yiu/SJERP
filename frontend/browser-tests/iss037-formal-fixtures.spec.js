import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test('formal synthetic PI matrix creates saved API and XLSX evidence', async () => {
  if (process.env.ISS037_IAB_HANDOFF === '1') test.setTimeout(600000)
  expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  const fixtureRoot = path.resolve('../docs/uat-evidence/r1-iss037-print-output-acceptance-20261104')
  const evidence = process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT
    ? path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'print-output')
    : fixtureRoot
  const result = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(fixtureRoot, 'seed_formal_matrix.py')], {
    cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  })
  expect(result.status, result.stderr).toBe(0)
  const fixture = JSON.parse(result.stdout.trim().split('\n').at(-1))
  expect(fixture.samples).toHaveLength(3)
  expect(fixture.samples.every(sample => sample.status === 'sent')).toBe(true)
  fs.cpSync(fixture.output, path.join(evidence, 'formal-matrix'), { recursive: true })
  console.log('FORMAL_PI_SAMPLES=' + JSON.stringify(fixture.samples))
  if (process.env.ISS037_IAB_HANDOFF === '1') await new Promise(resolve => setTimeout(resolve, 540000))
})
