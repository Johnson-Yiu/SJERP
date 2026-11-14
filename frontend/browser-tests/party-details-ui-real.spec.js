import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome' })
test('draft party details can be saved and reopened on all three documents', async ({ page, baseURL }) => {
  expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  const root = path.resolve('../docs/uat-evidence/party-version-closeout-02')
  const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(root, 'seed_party_details_ui.py')], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' })
  expect(seed.status, seed.stderr).toBe(0)
  const fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  await page.goto(`${process.env.ISOLATED_PLAYWRIGHT_API_BASE_URL}/admin/login/`)
  await page.locator('[name="username"]').fill(fixture.username)
  await page.locator('[name="password"]').fill('synthetic-only-password')
  await page.locator('input[type="submit"]').click()
  await expect(page).not.toHaveURL(/\/admin\/login/)
  const evidence = path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'party-details-ui')
  fs.mkdirSync(evidence, { recursive: true })
  for (const [kind, route] of [['quote', 'quotes'], ['order', 'orders'], ['purchase', 'purchase-orders']]) {
    await page.goto(new URL(`/${route}?detail=${fixture[kind]}`, baseURL).toString(), { waitUntil: 'domcontentloaded' })
    const panel = page.locator('.party-details-panel')
    await expect(panel.getByRole('heading', { name: '草稿双方资料' })).toBeVisible()
    await panel.getByLabel('买方账单地址').fill(`Synthetic ${kind} billing`)
    await panel.getByLabel('卖方税号').fill('SYNTHETIC-TAX')
    const saved = page.waitForResponse(r => r.url().endsWith('/party-details/') && r.request().method() === 'PUT')
    await panel.getByRole('button', { name: '保存双方资料' }).click()
    expect((await saved).status()).toBe(200)
    await page.reload()
    await expect(panel.getByLabel('买方账单地址')).toHaveValue(`Synthetic ${kind} billing`)
    await expect(panel.getByLabel('卖方税号')).toHaveValue('SYNTHETIC-TAX')
    await page.screenshot({ path: path.join(evidence, `${kind}.png`), fullPage: true })
  }
})
