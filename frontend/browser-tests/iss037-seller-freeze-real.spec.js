import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome' })
const report = path.resolve('../docs/uat-evidence/r1-iss037-seller-template-freeze-20261103')
const evidence = path.join(report, 'screenshots')
let fixture

test.beforeAll(() => {
  expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(report, 'seed_browser.py')], {
    cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  })
  expect(seed.status, seed.stderr).toBe(0)
  fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  fs.mkdirSync(evidence, { recursive: true })
})

for (const width of [1440, 390]) {
  test(`saved PI and Chrome print entry ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(`/quotes?detail=${fixture.id}`)
    const detail = page.getByRole('dialog', { name: '报价工作台' })
    await expect(detail).toBeVisible()
    const response = page.waitForResponse(r => r.url().includes(`/quotes/${fixture.id}/pi-data/`))
    await detail.getByRole('button', { name: '预览 PI' }).first().click()
    const pi = await response
    expect(pi.status()).toBe(200)
    const data = await pi.json()
    const preview = page.getByRole('dialog', { name: 'PI 预览' })
    await expect(page.frameLocator('iframe[title="已保存 PI"]').locator('body')).toContainText(data.seller.name)
    await page.locator('iframe[title="已保存 PI"]').evaluate(frame => {
      frame.contentWindow.addEventListener('beforeprint', () => { frame.dataset.printObserved = 'yes' })
    })
    await preview.getByRole('button', { name: '导出 PI PDF' }).scrollIntoViewIfNeeded()
    await page.screenshot({ path: path.join(evidence, `saved-pi-${width}.png`) })
    await preview.getByRole('button', { name: '导出 PI PDF' }).click()
    await expect(page.locator('iframe[title="已保存 PI"]')).toHaveAttribute('data-print-observed', 'yes')
    fs.writeFileSync(path.join(report, `browser-http-${width}.json`), JSON.stringify({ status: pi.status(), seller: data.seller, sha256: data.template_sha256, synthetic_quote: fixture.quote_no }, null, 2))
  })
}

test('unsaved revision preview uses the parent seller and retains print action', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto(`/quotes?detail=${fixture.id}`)
  const detail = page.getByRole('dialog', { name: '报价工作台' })
  await expect(detail).toBeVisible()
  await detail.getByRole('button', { name: '创建修订版' }).click()
  const editor = page.locator('form.quote-editor-modal')
  await expect(editor).toBeVisible()
  await editor.locator('.revision-summary textarea').fill('Synthetic revision')
  const response = page.waitForResponse(r => r.url().includes('/quotes/preview-template/'))
  await editor.getByRole('button', { name: '预览报价单' }).click()
  expect((await response).status()).toBe(200)
  const preview = page.getByRole('dialog', { name: 'PI 预览' })
  await expect(preview).toContainText('Synthetic Seller')
  await expect(preview.getByRole('button', { name: '导出 PI PDF' })).toBeVisible()
  await page.screenshot({ path: path.join(evidence, 'revision-draft-preview-1440.png') })
})
