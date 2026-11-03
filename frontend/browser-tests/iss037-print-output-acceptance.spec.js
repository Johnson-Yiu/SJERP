import { test, expect, chromium } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome' })
let fixture
const evidence = path.resolve('../docs/uat-evidence/r1-iss037-print-output-acceptance-20261104')

test.beforeAll(() => {
  expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.resolve('../docs/uat-evidence/r1-iss037-seller-template-freeze-20261103/seed_browser.py')], {
    cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  })
  expect(seed.status, seed.stderr).toBe(0)
  fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  fs.mkdirSync(evidence, { recursive: true })
})

test('saved PI blocks printing when a document image fails', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto(`/quotes?detail=${fixture.id}`)
  const detail = page.getByRole('dialog', { name: '报价工作台' })
  await expect(detail).toBeVisible()
  await detail.getByRole('button', { name: '预览 PI' }).first().click()
  const frame = page.locator('iframe[title="已保存 PI"]')
  await expect(frame).toBeVisible()
  await frame.evaluate(el => {
    el.contentWindow.print = () => { el.dataset.printCalled = 'yes' }
    const img = el.contentDocument.createElement('img')
    img.src = '/synthetic-missing-iss037.png'
    el.contentDocument.body.append(img)
  })
  await expect.poll(() => frame.evaluate(el => {
    const img = el.contentDocument.querySelector('img[src="/synthetic-missing-iss037.png"]')
    return img.complete && img.naturalWidth === 0
  })).toBe(true)
  await page.getByRole('dialog', { name: 'PI 预览' }).getByRole('button', { name: '导出 PI PDF' }).click()
  await expect(page.getByRole('dialog', { name: 'PI 预览' })).toContainText('图片加载失败')
  await expect(frame).not.toHaveAttribute('data-print-called', 'yes')
  await page.screenshot({ path: path.join(evidence, 'image-failure-1440.png') })
})

test('saved PI permits printing after resources load on narrow screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`/quotes?detail=${fixture.id}`)
  const detail = page.getByRole('dialog', { name: '报价工作台' })
  await expect(detail).toBeVisible()
  await detail.getByRole('button', { name: '预览 PI' }).first().click()
  const frame = page.locator('iframe[title="已保存 PI"]')
  await expect(frame).toBeVisible()
  await frame.evaluate(el => { el.contentWindow.print = () => { el.dataset.printCalled = 'yes' } })
  await page.screenshot({ path: path.join(evidence, 'saved-preview-390.png') })
  await page.getByRole('dialog', { name: 'PI 预览' }).getByRole('button', { name: '导出 PI PDF' }).click()
  await expect(frame).toHaveAttribute('data-print-called', 'yes')
  // Independent Chrome PDF rendering, not the UI print-dialog output.
  const html = await frame.evaluate(el => el.contentDocument.documentElement.outerHTML)
  const rendered = await page.context().newPage()
  await rendered.setContent(html, { waitUntil: 'load' })
  await rendered.pdf({ path: path.join(evidence, 'independent-chrome-render.pdf'), format: 'A4', printBackground: true })
  await rendered.close()
})

test('Chrome UI print to PDF', async ({ baseURL }, testInfo) => {
  const profile = testInfo.outputPath('chrome-profile')
  const output = testInfo.outputPath('print-output')
  fs.mkdirSync(path.join(profile, 'Default'), { recursive: true })
  fs.mkdirSync(output, { recursive: true })
  fs.writeFileSync(path.join(profile, 'Default', 'Preferences'), JSON.stringify({
    printing: { print_preview_sticky_settings: { appState: JSON.stringify({
      recentDestinations: [{ id: 'Save as PDF', origin: 'local', account: '' }],
      selectedDestinationId: 'Save as PDF', version: 2,
    }) } },
    savefile: { default_directory: output },
    download: { default_directory: output, prompt_for_download: false },
  }))
  const browser = await chromium.launchPersistentContext(profile, { channel: 'chrome', headless: false, args: ['--kiosk-printing'] })
  try {
    const page = await browser.newPage()
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto(`${baseURL}/quotes?detail=${fixture.id}`)
    const detail = page.getByRole('dialog', { name: '报价工作台' })
    await expect(detail).toBeVisible()
    await detail.getByRole('button', { name: '预览 PI' }).first().click()
    await expect(page.locator('iframe[title="已保存 PI"]')).toBeVisible()
    await page.getByRole('dialog', { name: 'PI 预览' }).getByRole('button', { name: '导出 PI PDF' }).click()
    await expect.poll(() => fs.readdirSync(output).filter(name => name.endsWith('.pdf')), { timeout: 20000 }).not.toHaveLength(0)
    const file = fs.readdirSync(output).find(name => name.endsWith('.pdf'))
    fs.copyFileSync(path.join(output, file), path.join(evidence, 'chrome-ui-print.pdf'))
  } finally {
    await browser.close()
  }
})
