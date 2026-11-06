import { test, expect } from '@playwright/test'
import path from 'node:path'

const evidence = process.env.WORKSPACE_EVIDENCE_DIR
const active = page => page.locator('.workspace-pane[aria-hidden="false"]')
const name = page => active(page).locator('.customer-editor .field').filter({ hasText: '客户名称' }).locator('input').first()

async function login(page, suffix = '') {
  await page.getByLabel('账号').fill(process.env.ISS055_UI_USERNAME + suffix)
  await page.getByLabel('密码').fill(process.env.ISS055_UI_PASSWORD)
  const signedIn = page.waitForResponse(r => r.url().endsWith('/api/session/login/') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  expect((await signedIn).status()).toBe(200)
  await expect.poll(() => new URL(page.url()).pathname, { timeout: 15000 }).toBe('/customers')
  const operator = await (await page.request.get('/api/session/current-operator/')).json()
  expect(operator.authenticated).toBe(true)
  expect(operator.development_superadmin).toBe(false)
  expect(operator.user_id).toEqual(expect.any(Number))
  return operator
}

async function draft(page, value) {
  await active(page).getByRole('button', { name: '新建客户', exact: true }).click()
  await name(page).fill(value)
  return active(page).getAttribute('data-workspace')
}

async function start(page) {
  await page.goto('/customers?search=Workspace', { waitUntil: 'domcontentloaded' })
  await expect(page).toHaveURL(/\/login\?next=/)
  await expect(page.getByRole('tablist')).toHaveCount(0)
  return login(page)
}

test('real logout protects a dirty draft and clears it before a same-name account signs in', async ({ page }) => {
  test.setTimeout(90000)
  await page.setViewportSize({ width: 1440, height: 900 })
  const first = await start(page)
  const id = await draft(page, 'Private logout draft')
  const logout = page.getByRole('button', { name: '退出登录' })
  let logoutRequests = 0
  page.on('request', req => { if (req.method() === 'POST' && req.url().endsWith('/api/session/logout/')) logoutRequests++ })
  await logout.click()
  await page.getByRole('button', { name: '继续编辑' }).click()
  await expect(name(page)).toHaveValue('Private logout draft')
  expect(logoutRequests).toBe(0)
  await logout.click()
  const response = page.waitForResponse(r => r.url().endsWith('/api/session/logout/') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '放弃修改' }).click()
  expect((await response).status()).toBe(200)
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.locator('.workspace-pane')).toHaveCount(0)
  expect((await (await page.request.get('/api/session/current-operator/')).json()).authenticated).toBe(false)
  await page.screenshot({ path: path.join(evidence, 'desktop-after-logout.png') })
  await page.evaluate(() => history.back())
  await expect(page).toHaveURL(/\/login\?next=/)
  const second = await login(page, '-second')
  expect(second.name).toBe(first.name)
  expect(second.user_id).not.toBe(first.user_id)
  await expect(page.locator(`[data-workspace="${id}"]`)).toHaveCount(0)
  await draft(page, 'Second account draft')
  await expect(name(page)).toHaveValue('Second account draft')
  expect(await page.evaluate(() => JSON.stringify([localStorage, sessionStorage]))).not.toContain('Private logout draft')
})

test('real session expiry removes dirty workspaces and rejects a late authenticated response', async ({ page }) => {
  test.setTimeout(90000)
  await page.setViewportSize({ width: 390, height: 844 })
  const first = await start(page)
  const id = await draft(page, 'Private expired draft')
  let release, fetched
  const waiting = new Promise(resolve => { release = resolve })
  const captured = new Promise(resolve => { fetched = resolve })
  await page.route('**/api/customers/?search=delayed-session-response', async route => {
    const response = await route.fetch()
    fetched(response.status())
    await waiting
    await route.fulfill({ response })
  })
  await page.evaluate(async () => {
    const { api } = await import('/src/api.js')
    window.lateWorkspaceResponse = api.get('/customers/?search=delayed-session-response').then(() => 'accepted', () => 'rejected')
  })
  expect(await captured).toBe(200)
  try {
    await page.context().clearCookies()
    const denied = await page.evaluate(async () => {
      try { await (await import('/src/api.js')).api.get('/customers/') } catch (error) { return error.status }
      return 200
    })
    expect([401, 403]).toContain(denied)
    await expect(page.getByText('登录已过期，请重新登录。')).toBeVisible()
    await expect(page.locator('.workspace-pane')).toHaveCount(0)
    expect(new URL(page.url()).searchParams.get('next')).toBe('/customers?search=Workspace')
    await page.screenshot({ path: path.join(evidence, '390-session-expired.png') })
    const second = await login(page, '-second')
    expect(second.user_id).not.toBe(first.user_id)
  } finally { release() }
  expect(await page.evaluate(() => window.lateWorkspaceResponse)).toBe('rejected')
  await expect(page.locator(`[data-workspace="${id}"]`)).toHaveCount(0)
  await expect(page.getByRole('tab')).toHaveCount(1)
})

test('parallel customer drafts adopt the saved object and return to the original filtered list', async ({ page }) => {
  test.setTimeout(90000)
  await start(page)
  const listId = await active(page).getAttribute('data-workspace')
  const a = await draft(page, 'Workspace Integration A')
  await page.getByRole('tab', { name: '客户管理', exact: true }).click()
  const b = await draft(page, 'Workspace Integration B')
  expect(b).not.toBe(a)
  await page.getByRole('tab', { name: /新建 1/ }).click()
  await expect(name(page)).toHaveValue('Workspace Integration A')
  await active(page).locator('.contact-create-card .contact-fields input').first().fill('Integration contact')
  const saved = page.waitForResponse(r => r.url().endsWith('/api/customers/') && r.request().method() === 'POST')
  await active(page).getByRole('button', { name: '保存客户', exact: true }).click()
  const response = await saved
  expect(response.status()).toBe(201)
  const record = await response.json()
  await expect(page).toHaveURL(new RegExp(`[?&]detail=${record.id}`))
  await expect(active(page)).toHaveAttribute('data-workspace', a)
  await active(page).getByRole('button', { name: '关闭详情', exact: true }).click()
  await expect(active(page)).toHaveAttribute('data-workspace', listId)
  await expect(page).toHaveURL(/\/customers\?search=Workspace$/)
  await page.getByRole('tab', { name: /新建 2/ }).click()
  await expect(name(page)).toHaveValue('Workspace Integration B')
  await page.screenshot({ path: path.join(evidence, 'desktop-parallel-drafts.png') })
})

test('customer reminder entries keep separate context and preserve an in-progress need', async ({ page }) => {
  test.setTimeout(90000)
  await start(page)
  const open = name => active(page).getByRole('row').filter({ hasText: name }).getByRole('link', { name: '新品提醒' }).click()
  await open('Workspace Alpha')
  await expect(active(page).getByRole('heading', { name: '客户产品需求' })).toBeVisible()
  const alpha = await active(page).getAttribute('data-workspace')
  const alphaCustomer = new URL(page.url()).searchParams.get('customer')
  expect(alphaCustomer).toMatch(/^\d+$/)
  await active(page).getByRole('button', { name: '记录新品需求' }).click()
  await active(page).getByLabel('所找产品').fill('Integration reminder draft')
  await page.getByRole('tab', { name: '客户管理', exact: true }).click()
  await open('Workspace Beta')
  await expect(active(page).getByRole('heading', { name: '客户产品需求' })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('customer')).not.toBe(alphaCustomer)
  expect(await active(page).getAttribute('data-workspace')).not.toBe(alpha)
  await page.locator(`[aria-controls="workspace-panel-${alpha}"]`).click()
  await expect(active(page).getByLabel('所找产品')).toHaveValue('Integration reminder draft')
  await expect(active(page).locator('.editor select').first()).toHaveValue(alphaCustomer)
  const saved = page.waitForResponse(r => r.url().endsWith('/api/new-product-reminders/') && r.request().method() === 'POST')
  await active(page).getByRole('button', { name: '保存需求' }).click()
  const result = await saved
  expect(result.status()).toBe(201)
  expect((await result.json()).customer).toBe(Number(alphaCustomer))
  await expect(active(page)).toHaveAttribute('data-workspace', alpha)
  await expect(active(page).getByRole('heading', { name: '新品需求详情' })).toBeVisible()
  await page.screenshot({ path: path.join(evidence, 'desktop-reminder.png') })
})
