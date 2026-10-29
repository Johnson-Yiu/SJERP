# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: iss055-customer-404-real.spec.js >> authorized customer detail keeps secure Chinese 404 semantics (desktop)
- Location: browser-tests\iss055-customer-404-real.spec.js:66:5

# Error details

```
Error: expect(received).toMatchObject(expected)

- Expected  - 3
+ Received  + 3

  Object {
    "authenticated": true,
-   "data_scope": "self",
-   "development_superadmin": false,
-   "has_all_permissions": false,
+   "data_scope": "all",
+   "development_superadmin": true,
+   "has_all_permissions": true,
  }
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | import fs from 'node:fs/promises'
  3  | import path from 'node:path'
  4  | 
  5  | const backendBase = 'http://127.0.0.1:55154'
  6  | const visibleId = Number(process.env.ISS055_VISIBLE_ID)
  7  | const hiddenId = Number(process.env.ISS055_HIDDEN_ID)
  8  | const evidenceDir = process.env.ISS055_EVIDENCE_DIR || 'test-results/iss055-evidence'
  9  | const password = process.env.ISS055_UI_PASSWORD
  10 | 
  11 | if (!visibleId || !hiddenId || !process.env.ISS055_UI_USERNAME || !password) {
  12 |   throw new Error('ISS-055 browser test requires isolated fixture IDs and local UI credentials.')
  13 | }
  14 | 
  15 | async function loginIsolatedAccount(page) {
  16 |   const loginUrl = `${backendBase}/admin/login/?next=/`
  17 |   const loginPage = await page.request.get(loginUrl)
  18 |   expect(loginPage.ok()).toBeTruthy()
  19 |   const html = await loginPage.text()
  20 |   const csrf = html.match(/name="csrfmiddlewaretoken" value="([^"]+)"/)?.[1]
  21 |   expect(csrf).toBeTruthy()
  22 |   const response = await page.request.post(`${backendBase}/admin/login/`, {
  23 |     form: {
  24 |       csrfmiddlewaretoken: csrf,
  25 |       username: process.env.ISS055_UI_USERNAME,
  26 |       password,
  27 |       next: '/',
  28 |     },
  29 |     headers: { Referer: loginUrl },
  30 |     maxRedirects: 0,
  31 |   })
  32 |   expect(response.status()).toBe(302)
  33 |   const operator = await page.request.get(`${backendBase}/api/session/current-operator/`)
  34 |   expect(operator.status()).toBe(200)
  35 |   const payload = await operator.json()
> 36 |   expect(payload).toMatchObject({
     |                   ^ Error: expect(received).toMatchObject(expected)
  37 |     authenticated: true,
  38 |     development_superadmin: false,
  39 |     has_all_permissions: false,
  40 |     data_scope: 'self',
  41 |   })
  42 | }
  43 | 
  44 | async function saveEvidence(page, name, requests) {
  45 |   await fs.mkdir(evidenceDir, { recursive: true })
  46 |   await page.screenshot({ path: path.join(evidenceDir, `${name}.png`), fullPage: true })
  47 |   await fs.writeFile(path.join(evidenceDir, `${name}-browser-log.json`), JSON.stringify({
  48 |     browser: 'chrome',
  49 |     viewport: await page.evaluate(() => ({ width: window.innerWidth, height: window.innerHeight })),
  50 |     requests,
  51 |   }, null, 2))
  52 | }
  53 | 
  54 | const scenarios = [
  55 |   ['authorized', visibleId, true],
  56 |   ['unauthorized', hiddenId, false],
  57 |   ['unknown', 999999, false],
  58 | ]
  59 | const viewports = [
  60 |   ['desktop', { width: 1440, height: 900 }],
  61 |   ['narrow', { width: 390, height: 844 }],
  62 | ]
  63 | 
  64 | for (const [scenario, id, allowed] of scenarios) {
  65 |   for (const [viewportName, viewport] of viewports) {
  66 |     test(`${scenario} customer detail keeps secure Chinese 404 semantics (${viewportName})`, async ({ page }) => {
  67 |       await page.setViewportSize(viewport)
  68 |       const requests = []
  69 |       page.on('response', response => {
  70 |         if (response.url().includes('/api/')) requests.push({ url: response.url(), status: response.status() })
  71 |       })
  72 |       await loginIsolatedAccount(page)
  73 |       await page.goto(`/customers?detail=${id}`)
  74 |       await expect(page.getByRole('dialog', { name: '客户详情' })).toBeVisible()
  75 |       if (allowed) {
  76 |         await expect(page.getByRole('dialog', { name: '客户详情' })).toContainText('ISS-055 有权客户')
  77 |         await expect(page.locator('.detail-error')).toHaveCount(0)
  78 |       } else {
  79 |         const error = page.locator('.detail-error')
  80 |         await expect(error).toContainText('客户不存在或当前账号无权访问。')
  81 |         await expect(error).not.toContainText('No Customer')
  82 |         await expect(error).not.toContainText('Customer matches the given query')
  83 |         await expect(error).not.toContainText('Customer.DoesNotExist')
  84 |       }
  85 |       await saveEvidence(page, `${scenario}-${viewportName}`, requests)
  86 |     })
  87 |   }
  88 | }
  89 | 
```