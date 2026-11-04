import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test('formal synthetic PI matrix creates saved API and XLSX evidence', async () => {
  expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  const evidence = path.resolve('../docs/uat-evidence/r1-iss037-print-output-acceptance-20261104')
  const result = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(evidence, 'seed_formal_matrix.py')], {
    cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  })
  expect(result.status, result.stderr).toBe(0)
  const fixture = JSON.parse(result.stdout.trim().split('\n').at(-1))
  expect(fixture.samples).toHaveLength(3)
  expect(fixture.samples.every(sample => sample.status === 'sent')).toBe(true)
  fs.cpSync(fixture.output, path.join(evidence, 'formal-matrix'), { recursive: true })
})
