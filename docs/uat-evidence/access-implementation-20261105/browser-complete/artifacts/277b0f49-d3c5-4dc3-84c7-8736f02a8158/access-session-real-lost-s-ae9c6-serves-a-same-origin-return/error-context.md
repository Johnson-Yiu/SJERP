# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: access-session-real.spec.js >> lost session shows expiry and preserves a same-origin return
- Location: browser-tests\access-session-real.spec.js:37:1

# Error details

```
Error: expect(page).toHaveURL(expected) failed

Expected pattern: /\/login\?reason=expired/
Received string:  "http://127.0.0.1:3650/customers"
Timeout: 5000ms

Call log:
  - Expect "toHaveURL" with timeout 5000ms
    13 × locator resolved to <html lang="zh-CN">…</html>
       - unexpected value "http://127.0.0.1:3650/customers"

```

```yaml
- complementary:
  - text: S
  - strong: 森爵照明管理系统
  - text: 客户 · 销售 · 产品
  - navigation:
    - text: 客户
    - link "客户管理":
      - /url: /customers
  - text: I
  - strong: 当前账号：ISS-055 隔离负责人
  - text: ISS-055 仅本人客户查看 · 按账号授权
  - button "退出登录"
- main:
  - text: 客户资料
  - heading "客户管理" [level=1]
  - text: 11月5日周四 I
  - paragraph: 维护客户资料和负责人。客户阶段会随报价和订单自动更新。
  - region "页面小计":
    - article:
      - text: 客户总数
      - strong: "1"
      - text: 全部客户档案
    - article:
      - text: 正式客户
      - strong: "0"
      - text: 已有正式订单
    - article:
      - text: 待开发
      - strong: "1"
      - text: 尚未成交
    - article:
      - text: 累计销售额
      - strong: ¥ 0.00
      - text: 当前列表累计
  - text: 搜索
  - textbox "搜索客户":
    - /placeholder: 名称、编号、国家/地区或负责人
  - text: 负责人
  - combobox "按负责人筛选客户":
    - option "全部负责人" [selected]
    - option "ISS-055 隔离负责人 · ISS-055 隔离销售部"
  - text: 国家/地区
  - combobox "按国家/地区筛选客户":
    - option "全部国家/地区" [selected]
    - option "中国"
  - text: 状态
  - combobox "按客户状态筛选":
    - option "全部状态" [selected]
    - option "线索"
    - option "已联系"
    - option "商机"
    - option "正式客户"
    - option "返单客户"
  - button "重置"
  - button "刷新"
  - table:
    - rowgroup:
      - row "客户名称 客户编号 状态 国家/地区 业务区域 负责人 下次跟进 订单数 累计销售额 操作":
        - columnheader "客户名称"
        - columnheader "客户编号"
        - columnheader "状态"
        - columnheader "国家/地区"
        - columnheader "业务区域"
        - columnheader "负责人"
        - columnheader "下次跟进"
        - columnheader "订单数"
        - columnheader "累计销售额"
        - columnheader "操作"
    - rowgroup:
      - row "ISS-055 有权客户 ISS055-VISIBLE 线索 中国 — ISS-055 隔离负责人 — — — 查看详情":
        - cell "ISS-055 有权客户"
        - cell "ISS055-VISIBLE"
        - cell "线索"
        - cell "中国"
        - cell "—"
        - cell "ISS-055 隔离负责人"
        - cell "—"
        - cell "—"
        - cell "—"
        - cell "查看详情":
          - button "查看详情"
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
  25 |     const storage = await page.evaluate(() => JSON.stringify(localStorage))
  26 |     expect(storage).not.toContain(process.env.ISS055_UI_PASSWORD)
  27 |     expect(storage).not.toContain('sessionid')
  28 |     await page.screenshot({ path: path.join(process.env.EVIDENCE_DIR, `session-${name}.png`), fullPage: true })
  29 |     if (name === 'narrow') await page.locator('.mobile-menu').click()
  30 |     const logout = page.getByRole('button', { name: '退出登录' })
  31 |     await logout.click()
  32 |     await expect(page).toHaveURL(/\/login/)
  33 |     expect((await (await page.request.get('/api/session/current-operator/')).json()).authenticated).toBe(false)
  34 |   })
  35 | }
  36 |
  37 | test('lost session shows expiry and preserves a same-origin return', async ({ page }) => {
  38 |   await page.goto('/login?next=%2Fcustomers')
  39 |   await page.getByLabel('账号').fill(process.env.ISS055_UI_USERNAME)
  40 |   await page.getByLabel('密码').fill(process.env.ISS055_UI_PASSWORD)
  41 |   await page.getByRole('button', { name: '登录', exact: true }).click()
  42 |   await expect(page).toHaveURL(/\/customers/)
  43 |   // Remove only this test browser context's cookies to simulate a lost session.
  44 |   await page.context().clearCookies()
  45 |   await page.evaluate(async () => { try { await (await import('/src/api.js')).api.get('/customers/') } catch {} })
> 46 |   await expect(page).toHaveURL(/\/login\?reason=expired/)
     |                      ^ Error: expect(page).toHaveURL(expected) failed
  47 |   await expect(page.getByText('登录已过期，请重新登录。')).toBeVisible()
  48 | })
  49 |
  50 | test('external return target is never navigated', async ({ page }) => {
  51 |   await page.goto('/login?next=%2F%2Foutside.example.invalid')
  52 |   const originalOrigin = new URL(page.url()).origin
  53 |   await page.getByLabel('账号').fill(process.env.ISS055_UI_USERNAME)
  54 |   await page.getByLabel('密码').fill(process.env.ISS055_UI_PASSWORD)
  55 |   await page.getByRole('button', { name: '登录', exact: true }).click()
  56 |   await expect(page).not.toHaveURL(/\/login/)
  57 |   expect(new URL(page.url()).origin).toBe(originalOrigin)
  58 | })
  59 |
```