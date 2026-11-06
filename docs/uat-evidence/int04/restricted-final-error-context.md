# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: access-session-real.spec.js >> lost session shows expiry and preserves a same-origin return
- Location: browser-tests\access-session-real.spec.js:43:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.goto: Test timeout of 30000ms exceeded.
Call log:
  - navigating to "http://127.0.0.1:1842/login?next=%2Fcustomers", waiting until "load"

```

# Page snapshot

```yaml
- main [ref=e3]:
  - generic [ref=e4]:
    - heading "登录森爵管理系统" [level=1] [ref=e5]
    - paragraph [ref=e6]: 请输入分配给你的账号。
    - generic [ref=e7]:
      - text: 账号
      - textbox "账号" [ref=e8]
    - generic [ref=e9]:
      - text: 密码
      - textbox "密码" [ref=e10]
    - button "登录" [ref=e11] [cursor=pointer]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | import fs from 'node:fs/promises'
  3  | import path from 'node:path'
  4  | 
  5  | for (const [name, viewport] of [['desktop', { width: 1440, height: 900 }], ['narrow', { width: 390, height: 844 }]]) {
  6  |   test(`ERP login and logout use the isolated real session (${name})`, async ({ page }) => {
  7  |     await page.setViewportSize(viewport)
  8  |     await page.goto('/login?next=%2Fcustomers')
  9  |     await fs.mkdir(process.env.EVIDENCE_DIR, { recursive: true })
  10 |     await page.screenshot({ path: path.join(process.env.EVIDENCE_DIR, `login-${name}.png`), fullPage: true })
  11 |     await page.getByLabel('账号').fill(process.env.ISS055_UI_USERNAME)
  12 |     await page.getByLabel('密码').fill('wrong-synthetic-password')
  13 |     await page.getByRole('button', { name: '登录', exact: true }).click()
  14 |     await expect(page.getByRole('alert')).toContainText('账号或密码不正确')
  15 |     await page.getByLabel('密码').fill(process.env.ISS055_UI_PASSWORD)
  16 |     await page.getByRole('button', { name: '登录', exact: true }).click()
  17 |     await expect(page).toHaveURL(/\/customers/)
  18 |     const operator = await (await page.request.get('/api/session/current-operator/')).json()
  19 |     expect(operator.authenticated).toBe(true)
  20 |     expect(operator.development_superadmin).toBe(false)
  21 |     expect(operator.permissions.customers.view).toBe(true)
  22 |     const fixture = JSON.parse(await fs.readFile(path.join(process.env.ISS055_EVIDENCE_DIR, 'fixture.json'), 'utf8'))
  23 |     expect((await page.request.get(`/api/context/customers/${fixture.hidden_id}/`)).status()).toBe(404)
  24 |     expect((await page.request.get(`/api/media/${fixture.hidden_attachment}`)).status()).toBe(404)
  25 |     const deniedStatus = await page.evaluate(async () => {
  26 |       try { await (await import('/src/api.js')).api.post('/customers/', {}) } catch (error) { return error.status }
  27 |       return 200
  28 |     })
  29 |     expect(deniedStatus).toBe(403)
  30 |     await expect(page).toHaveURL(/\/customers/)
  31 |     const storage = await page.evaluate(() => JSON.stringify(localStorage))
  32 |     expect(storage).not.toContain(process.env.ISS055_UI_PASSWORD)
  33 |     expect(storage).not.toContain('sessionid')
  34 |     await page.screenshot({ path: path.join(process.env.EVIDENCE_DIR, `session-${name}.png`), fullPage: true })
  35 |     if (name === 'narrow') await page.locator('.mobile-menu').click()
  36 |     const logout = page.getByRole('button', { name: '退出登录' })
  37 |     await logout.click()
  38 |     await expect(page).toHaveURL(/\/login/)
  39 |     expect((await (await page.request.get('/api/session/current-operator/')).json()).authenticated).toBe(false)
  40 |   })
  41 | }
  42 | 
  43 | test('lost session shows expiry and preserves a same-origin return', async ({ page }) => {
> 44 |   await page.goto('/login?next=%2Fcustomers')
     |              ^ Error: page.goto: Test timeout of 30000ms exceeded.
  45 |   await page.getByLabel('账号').fill(process.env.ISS055_UI_USERNAME)
  46 |   await page.getByLabel('密码').fill(process.env.ISS055_UI_PASSWORD)
  47 |   await page.getByRole('button', { name: '登录', exact: true }).click()
  48 |   await expect(page).toHaveURL(/\/customers/)
  49 |   // Remove only this test browser context's cookies to simulate a lost session.
  50 |   await page.context().clearCookies()
  51 |   await page.evaluate(async () => { try { await (await import('/src/api.js')).api.get('/customers/') } catch {} })
  52 |   await expect(page).toHaveURL(/\/login\?reason=expired/)
  53 |   await expect(page.getByText('登录已过期，请重新登录。')).toBeVisible()
  54 | })
  55 | 
  56 | test('external return target is never navigated', async ({ page }) => {
  57 |   await page.goto('/login?next=%2F%2Foutside.example.invalid', { waitUntil: 'domcontentloaded' })
  58 |   const originalOrigin = new URL(page.url()).origin
  59 |   await page.getByLabel('账号').fill(process.env.ISS055_UI_USERNAME)
  60 |   await page.getByLabel('密码').fill(process.env.ISS055_UI_PASSWORD)
  61 |   await page.getByRole('button', { name: '登录', exact: true }).click()
  62 |   await expect(page).not.toHaveURL(/\/login/)
  63 |   expect(new URL(page.url()).origin).toBe(originalOrigin)
  64 | })
  65 | 
```