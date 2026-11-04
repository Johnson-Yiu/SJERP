import { test, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test('isolated core workspace fixture and real API contracts', async ({ request }) => {
  test.setTimeout(process.env.CORE_WORKSPACE_IAB === '1' ? 3600000 : 120000)
  const root = path.resolve('..')
  const fixtureRoot = path.join(root, 'docs/uat-evidence/core-workspace-ux-batch-20261104')
  const evidence = process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT
    ? path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'core-workspace')
    : fixtureRoot
  const result = execFileSync(process.env.ISOLATED_TEST_PYTHON, [path.join(fixtureRoot, 'seed_workspace.py')], { cwd: path.join(root, 'backend'), env: process.env, encoding: 'utf8' })
  const fixture = JSON.parse(result.trim().split('\n').at(-1))
  const http = []
  for (const endpoint of ['customers/', 'contacts/', 'follow-ups/', 'products/', 'skus/inventory-list/', `orders/${fixture.order}/`, `purchase-orders/${fixture.purchase}/`]) {
    const response = await request.get(`/api/${endpoint}`)
    http.push({ method: 'GET', endpoint, status: response.status(), data: await response.json() })
    expect(response.status()).toBe(200)
  }
  fs.mkdirSync(evidence, { recursive: true })
  const fixtureJson = JSON.stringify({ fixture, http }, null, 2)
  fs.writeFileSync(path.join(evidence, `real-api-fixture-${fixture.suffix}.json`), fixtureJson)
  if (!fs.existsSync(path.join(evidence, 'real-api-fixture.json'))) fs.writeFileSync(path.join(evidence, 'real-api-fixture.json'), fixtureJson)
  console.log(JSON.stringify({ baseURL: process.env.ISOLATED_PLAYWRIGHT_BASE_URL, fixture }))
  if (process.env.CORE_WORKSPACE_IAB === '1') {
    const done = path.join(process.env.ISOLATED_TEST_ROOT, 'core-workspace-handoff-complete')
    while (!fs.existsSync(done)) await new Promise(resolve => setTimeout(resolve, 1000))
  }
})
