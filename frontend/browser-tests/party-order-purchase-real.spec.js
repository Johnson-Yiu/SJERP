import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome' })
let fixture
const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT || '.', 'party-order-purchase')

test.beforeAll(() => {
  expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  const source = path.resolve('../docs/uat-evidence/core-workspace-ux-batch-20261104/seed_workspace.py')
  const result = spawnSync(process.env.ISOLATED_TEST_PYTHON, [source], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' })
  expect(result.status, result.stderr).toBe(0)
  fixture = JSON.parse(result.stdout.trim().split('\n').at(-1))
  fs.mkdirSync(evidence, { recursive: true })
})

for (const width of [1440, 390]) {
  for (const [kind, route, label] of [
    ['order', 'orders', '订单工作台'], ['purchase', 'purchase-orders', '采购工作台'],
  ]) test(`${kind} party display at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 })
    const response = await page.request.get(`/api/${route}/${fixture[kind]}/`)
    expect(response.status()).toBe(200)
    const data = await response.json()
    if (kind === 'order') expect(data.customer_name_snapshot).toBe('')
    else expect(data.supplier_name_snapshot).toContain('合成办公供应商')
    await page.goto(`/${route}?detail=${fixture[kind]}`)
    const detail = page.getByRole('dialog', { name: label })
    await expect(detail).toBeVisible()
    await expect(detail).toContainText(kind === 'order' ? '历史主体未记录' : data.supplier_name_snapshot)
    await page.screenshot({ path: path.join(evidence, `${kind}-${width}.png`) })
    fs.writeFileSync(path.join(evidence, `${kind}-${width}.json`), JSON.stringify({ status: response.status(), snapshot: kind === 'order' ? data.customer_name_snapshot : data.supplier_name_snapshot }, null, 2))
  })
}
