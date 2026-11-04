import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome' })

test('saved PI refuses printing after a font loading failure', async ({ page }) => {
  expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.resolve('../docs/uat-evidence/r1-iss037-seller-template-freeze-20261103/seed_browser.py')], {
    cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  })
  expect(seed.status, seed.stderr).toBe(0)
  const fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto(`/quotes?detail=${fixture.id}`)
  const detail = page.getByRole('dialog', { name: '报价工作台' })
  await expect(detail).toBeVisible()
  await detail.getByRole('button', { name: '预览 PI' }).first().click()
  const frame = page.locator('iframe[title="已保存 PI"]')
  await expect(frame).toBeVisible()
  const status = await frame.evaluate(async el => {
    el.contentWindow.print = () => { el.dataset.printCalled = 'yes' }
    const font = new el.contentWindow.FontFace('SyntheticMissingFont', 'url(/synthetic-missing-iss037.woff2)')
    el.contentDocument.fonts.add(font)
    try { await font.load() } catch { /* Failure is the scenario under test. */ }
    return font.status
  })
  expect(status).toBe('error')
  await page.getByRole('dialog', { name: 'PI 预览' }).getByRole('button', { name: '导出 PI PDF' }).click()
  await expect(page.getByRole('alert')).toContainText('字体加载失败')
  await expect(frame).not.toHaveAttribute('data-print-called', 'yes')
  const evidence = path.resolve('../docs/uat-evidence/r1-iss037-print-output-acceptance-20261104')
  fs.mkdirSync(evidence, { recursive: true })
  await page.screenshot({ path: path.join(evidence, 'font-failure-1440.png') })
})
