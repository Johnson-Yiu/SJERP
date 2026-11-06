import { test, expect } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

for (const [name, viewport] of [['desktop', { width: 1440, height: 900 }], ['narrow', { width: 390, height: 844 }]]) {
  test(`ERP login and logout use the isolated real session (${name})`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await page.goto('/login?next=%2Fcustomers', { waitUntil: 'domcontentloaded' })
    await fs.mkdir(process.env.EVIDENCE_DIR, { recursive: true })
    await page.screenshot({ path: path.join(process.env.EVIDENCE_DIR, `login-${name}.png`), fullPage: true })
    await page.getByLabel('账号').fill(process.env.ISS055_UI_USERNAME)
    await page.getByLabel('密码').fill('wrong-synthetic-password')
    await page.getByRole('button', { name: '登录', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('账号或密码不正确')
    await page.getByLabel('密码').fill(process.env.ISS055_UI_PASSWORD)
    await page.getByRole('button', { name: '登录', exact: true }).click()
    await expect(page).toHaveURL(/\/customers/)
    const operator = await (await page.request.get('/api/session/current-operator/')).json()
    expect(operator.authenticated).toBe(true)
    expect(operator.development_superadmin).toBe(false)
    expect(operator.permissions.customers.view).toBe(true)
    const fixture = JSON.parse(await fs.readFile(path.join(process.env.ISS055_EVIDENCE_DIR, 'fixture.json'), 'utf8'))
    expect((await page.request.get(`/api/context/customers/${fixture.hidden_id}/`)).status()).toBe(404)
    expect((await page.request.get(`/api/media/${fixture.hidden_attachment}`)).status()).toBe(404)
    const deniedStatus = await page.evaluate(async () => {
      try { await (await import('/src/api.js')).api.post('/customers/', {}) } catch (error) { return error.status }
      return 200
    })
    expect(deniedStatus).toBe(403)
    await expect(page).toHaveURL(/\/customers/)
    const storage = await page.evaluate(() => JSON.stringify(localStorage))
    expect(storage).not.toContain(process.env.ISS055_UI_PASSWORD)
    expect(storage).not.toContain('sessionid')
    await page.screenshot({ path: path.join(process.env.EVIDENCE_DIR, `session-${name}.png`), fullPage: true })
    if (name === 'narrow') await page.locator('.mobile-menu').click()
    const logout = page.getByRole('button', { name: '退出登录' })
    await logout.click()
    await expect(page).toHaveURL(/\/login/)
    expect((await (await page.request.get('/api/session/current-operator/')).json()).authenticated).toBe(false)
  })
}

test('lost session shows expiry and preserves a same-origin return', async ({ page }) => {
  await page.goto('/login?next=%2Fcustomers', { waitUntil: 'domcontentloaded' })
  await page.getByLabel('账号').fill(process.env.ISS055_UI_USERNAME)
  await page.getByLabel('密码').fill(process.env.ISS055_UI_PASSWORD)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page).toHaveURL(/\/customers/)
  // Remove only this test browser context's cookies to simulate a lost session.
  await page.context().clearCookies()
  await page.evaluate(async () => { try { await (await import('/src/api.js')).api.get('/customers/') } catch {} })
  await expect(page).toHaveURL(/\/login\?reason=expired/)
  await expect(page.getByText('登录已过期，请重新登录。')).toBeVisible()
})

test('external return target is never navigated', async ({ page }) => {
  await page.goto('/login?next=%2F%2Foutside.example.invalid', { waitUntil: 'domcontentloaded' })
  const originalOrigin = new URL(page.url()).origin
  await page.getByLabel('账号').fill(process.env.ISS055_UI_USERNAME)
  await page.getByLabel('密码').fill(process.env.ISS055_UI_PASSWORD)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page).not.toHaveURL(/\/login/)
  expect(new URL(page.url()).origin).toBe(originalOrigin)
})
