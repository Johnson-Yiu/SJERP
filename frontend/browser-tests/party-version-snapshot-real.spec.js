import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome' })

for (const width of [1440, 390]) test(`saved buyer country and PI use the saved quotation after master change (${width}px)`, async ({ page }) => {
  expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  const fixtureRoot = path.resolve('../docs/uat-evidence/party-version-closeout-20261105')
  const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(fixtureRoot, 'seed_browser.py')], {
    cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  })
  expect(seed.status, seed.stderr).toBe(0)
  const fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'party-version')
  fs.mkdirSync(evidence, { recursive: true })
  const sent = await page.request.post(`/api/quotes/${fixture.id}/mark-sent/`)
  expect(sent.status()).toBe(200)
  const before = await page.request.get(`/api/quotes/${fixture.id}/`)
  expect(before.status()).toBe(200)
  const quote = await before.json()
  expect(quote.status).toBe('sent')
  expect(quote.buyer_country_snapshot).toBe('Germany')
  expect(quote.buyer_tax_id).toBe('00123-SYNTHETIC')
  const changed = await page.request.patch(`/api/customers/${quote.customer}/`, { data: { country: 'France' } })
  expect(changed.status()).toBe(200)
  const after = await page.request.get(`/api/quotes/${fixture.id}/`)
  expect(after.status()).toBe(200)
  expect((await after.json()).buyer_country_snapshot).toBe('Germany')
  const revision = await page.request.post(`/api/quotes/${fixture.id}/revise/`, { data: { revision_summary: 'Synthetic revision' } })
  expect(revision.status()).toBe(201)
  expect((await revision.json()).buyer_country_snapshot).toBe('Germany')
  expect((await revision.json()).buyer_tax_id).toBe('00123-SYNTHETIC')
  const exported = await page.request.get(`/api/quotes/${fixture.id}/export/`)
  expect(exported.status()).toBe(200)
  fs.writeFileSync(path.join(evidence, `synthetic-saved-quote-${width}.xlsx`), await exported.body())
  const results = { markSent: sent.status(), before: before.status(), customerPatch: changed.status(), after: after.status(), revision: revision.status(), xlsx: exported.status(), savedCountry: 'Germany' }
  await page.setViewportSize({ width, height: width === 390 ? 844 : 900 })
  await page.goto(`/quotes?detail=${fixture.id}`)
  const detail = page.getByRole('dialog', { name: '报价工作台' })
  await expect(detail).toBeVisible()
  const response = page.waitForResponse(r => r.url().includes(`/quotes/${fixture.id}/pi-data/`))
  await detail.getByRole('button', { name: '预览 PI' }).first().click()
  const pi = await response
  expect(pi.status()).toBe(200)
  const data = await pi.json()
  await expect(page.frameLocator('iframe[title="已保存 PI"]').locator('body')).toContainText('Synthetic Seller')
  await expect(page.frameLocator('iframe[title="已保存 PI"]').locator('body')).toContainText(quote.buyer_company_name)
  await expect(page.frameLocator('iframe[title="已保存 PI"]').locator('body')).toContainText('00123-SYNTHETIC')
  await page.screenshot({ path: path.join(evidence, `saved-pi-${width}.png`) })
  results[`pi${width}`] = { status: pi.status(), buyer: data.buyer, seller: data.seller }
  fs.writeFileSync(path.join(evidence, `http-${width}.json`), JSON.stringify(results, null, 2))
})
