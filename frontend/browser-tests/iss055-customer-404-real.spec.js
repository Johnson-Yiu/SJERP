import { test, expect } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

const backendBase = 'http://127.0.0.1:55154'
const visibleId = Number(process.env.ISS055_VISIBLE_ID)
const hiddenId = Number(process.env.ISS055_HIDDEN_ID)
const evidenceDir = process.env.ISS055_EVIDENCE_DIR || 'test-results/iss055-evidence'
const password = process.env.ISS055_UI_PASSWORD

if (!visibleId || !hiddenId || !process.env.ISS055_UI_USERNAME || !password) {
  throw new Error('ISS-055 browser test requires isolated fixture IDs and local UI credentials.')
}

async function loginIsolatedAccount(page) {
  const loginUrl = `${backendBase}/admin/login/?next=/`
  const loginPage = await page.request.get(loginUrl)
  expect(loginPage.ok()).toBeTruthy()
  const html = await loginPage.text()
  const csrf = html.match(/name="csrfmiddlewaretoken" value="([^"]+)"/)?.[1]
  expect(csrf).toBeTruthy()
  const response = await page.request.post(`${backendBase}/admin/login/`, {
    form: {
      csrfmiddlewaretoken: csrf,
      username: process.env.ISS055_UI_USERNAME,
      password,
      next: '/',
    },
    headers: { Referer: loginUrl },
    maxRedirects: 0,
  })
  expect(response.status()).toBe(302)
  const operator = await page.request.get(`${backendBase}/api/session/current-operator/`)
  expect(operator.status()).toBe(200)
  const payload = await operator.json()
  expect(payload).toMatchObject({
    authenticated: true,
    development_superadmin: false,
    has_all_permissions: false,
    data_scope: 'self',
  })
}

async function saveEvidence(page, name, requests) {
  await fs.mkdir(evidenceDir, { recursive: true })
  await page.screenshot({ path: path.join(evidenceDir, `${name}.png`), fullPage: true })
  await fs.writeFile(path.join(evidenceDir, `${name}-browser-log.json`), JSON.stringify({
    browser: 'chrome',
    viewport: await page.evaluate(() => ({ width: window.innerWidth, height: window.innerHeight })),
    requests,
  }, null, 2))
}

const scenarios = [
  ['authorized', visibleId, true],
  ['unauthorized', hiddenId, false],
  ['unknown', 999999, false],
]
const viewports = [
  ['desktop', { width: 1440, height: 900 }],
  ['narrow', { width: 390, height: 844 }],
]

for (const [scenario, id, allowed] of scenarios) {
  for (const [viewportName, viewport] of viewports) {
    test(`${scenario} customer detail keeps secure Chinese 404 semantics (${viewportName})`, async ({ page }) => {
      await page.setViewportSize(viewport)
      const requests = []
      page.on('response', response => {
        if (response.url().includes('/api/')) requests.push({ url: response.url(), status: response.status() })
      })
      await loginIsolatedAccount(page)
      await page.goto(`/customers?detail=${id}`)
      await expect(page.getByRole('dialog', { name: '客户详情' })).toBeVisible()
      if (allowed) {
        await expect(page.getByRole('dialog', { name: '客户详情' })).toContainText('ISS-055 有权客户')
        await expect(page.locator('.detail-error')).toHaveCount(0)
      } else {
        const error = page.locator('.detail-error')
        await expect(error).toContainText('客户不存在或当前账号无权访问。')
        await expect(error).not.toContainText('No Customer')
        await expect(error).not.toContainText('Customer matches the given query')
        await expect(error).not.toContainText('Customer.DoesNotExist')
      }
      await saveEvidence(page, `${scenario}-${viewportName}`, requests)
    })
  }
}
