import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome' })

function seed() {
  const script = path.resolve('../docs/uat-evidence/party-version-closeout-20261105/seed_browser.py')
  const result = spawnSync(process.env.ISOLATED_TEST_PYTHON, [script], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' })
  expect(result.status, result.stderr).toBe(0)
  return JSON.parse(result.stdout.trim().split('\n').at(-1))
}

test('new quote tax input works at desktop and narrow widths', async ({ page }) => {
  test.setTimeout(90000)
  const fixture = seed()
  const original = await (await page.request.get(`/api/quotes/${fixture.id}/`)).json()
  await page.goto(`/quotes?create=1&customer=${original.customer}`)
  const editor = page.locator('form.quote-editor-modal')
  const tax = editor.locator('#quote-buyer-tax-id')
  await expect(tax).toBeEditable()
  await tax.fill('0000123-A')
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 })
    await tax.scrollIntoViewIfNeeded()
    await expect(tax).toBeVisible()
    const fits = await tax.evaluate(el => {
      const rect = el.getBoundingClientRect()
      return rect.left >= 0 && rect.right <= innerWidth
    })
    expect(fits).toBe(true)
    const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT || path.join(process.env.ISOLATED_TEST_ROOT, 'evidence'), 'quote-tax')
    fs.mkdirSync(evidence, { recursive: true })
    await page.screenshot({ path: path.join(evidence, `editor-${width}.png`) })
  }
})

test('formal revision displays saved tax read-only', async ({ page }) => {
  const fixture = seed()
  expect((await page.request.post(`/api/quotes/${fixture.id}/mark-sent/`)).status()).toBe(200)
  await page.goto(`/quotes?detail=${fixture.id}`)
  const detail = page.getByRole('dialog', { name: '报价工作台' })
  await detail.getByRole('button', { name: '创建修订版' }).click()
  const tax = page.locator('#quote-buyer-tax-id')
  await expect(tax).toBeVisible()
  await expect(tax).toHaveAttribute('readonly', '')
  await expect(tax).toHaveValue('00123-SYNTHETIC')
})
