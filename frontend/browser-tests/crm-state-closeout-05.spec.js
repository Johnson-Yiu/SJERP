import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect as playwrightExpect, test } from '@playwright/test'

const expect = playwrightExpect.configure({ timeout: 15000 })
const spec = path.basename(fileURLToPath(import.meta.url))
const evidence = fileURLToPath(new URL('../../docs/uat-evidence/crm-state-closeout-05/', import.meta.url))
const active = page => page.locator('.workspace-pane[aria-hidden="false"]')
const button = (scope, name) => scope.getByRole('button', { name, exact: true })
const dialog = (page, name) => active(page).getByRole('dialog', { name, exact: true })
const editor = page => active(page).getByRole('region', { name: '新品需求详情' })
const byId = (endpoint, id) => `/api/${endpoint}/${id}/`
const reminderPath = '/api/new-product-reminders/'
const requestFor = (pathname, method) => request => new URL(request.url()).pathname === pathname && request.method() === method

async function json(page, url) {
  const response = await page.request.get(url)
  expect(response.ok()).toBe(true)
  return response.json()
}
async function go(page, baseURL, route) {
  await page.goto(new URL(route, baseURL).href, { waitUntil: 'commit', timeout: 60000 })
}
async function saveAndReject(page, pathname, method, save, pending, rejection, during) {
  const writes = []
  let release
  const gate = new Promise(resolve => { release = resolve })
  const url = url => url.pathname === pathname
  const handler = async route => {
    if (!requestFor(pathname, method)(route.request())) return route.continue()
    writes.push(route.request().postDataJSON())
    await gate
    await route.fulfill({ status: 400, json: { detail: rejection } })
  }
  await page.route(url, handler)
  const rejected = page.waitForResponse(result => requestFor(pathname, method)(result.request()))
  try {
    await save.dblclick()
    await expect(pending).toBeDisabled()
    await expect.poll(() => writes.length).toBe(1)
    await during()
    expect(writes).toHaveLength(1)
  } finally {
    release()
    await rejected
    await page.unroute(url, handler)
  }
  await expect(save).toBeEnabled()
  await expect(active(page).getByRole('alert').filter({ hasText: rejection })).toBeInViewport()
  return writes[0]
}
async function realSave(page, pathname, method, control, expected) {
  await page.bringToFront()
  const response = page.waitForResponse(result => requestFor(pathname, method)(result.request()), { timeout: 45000 })
  await control.click()
  const saved = await response
  expect(saved.status()).toBe(expected)
  return { body: await saved.json(), request: saved.request().postDataJSON() }
}

async function createReminder(page, baseURL, fixture, snap) {
  const [buyer] = fixture.buyers
  const requirement = buyer.name + ' NPD-01'
  const customerRows = () => json(page, reminderPath + '?customer=' + buyer.id)
  await go(page, baseURL, `/new-product-reminders?customer=${buyer.id}`)
  const before = (await customerRows()).count
  await button(active(page), '记录新品需求').click()
  const form = editor(page)
  await form.getByLabel('查找客户').fill(buyer.name)
  await button(form, '查找客户').click()
  await form.locator('form select').first().selectOption(String(buyer.id))
  await form.getByLabel('所找产品').fill(requirement)
  await form.getByLabel('规格', { exact: true }).fill('IP65')
  const save = button(form, '保存需求')
  const payload = await saveAndReject(page, reminderPath, 'POST', save, button(form, '正在保存…'), 'C5 受控拒绝新品需求', () => snap('pending'))
  await expect(form.getByLabel('所找产品')).toHaveValue(requirement)
  await expect(form.getByLabel('规格', { exact: true })).toHaveValue('IP65')
  await snap('rejected')
  const { body, request } = await realSave(page, reminderPath, 'POST', save, 201)
  expect(request.request_key).toBe(payload.request_key)
  await expect(form.getByText(requirement, { exact: true })).toBeVisible()
  const after = await customerRows()
  expect(after.count).toBe(before + 1)
  expect(after.results.filter(row => row.requirement === requirement)).toHaveLength(1)
  expect((await json(page, byId('new-product-reminders', body.id))).customer).toBe(buyer.id)
  await form.getByText(requirement, { exact: true }).scrollIntoViewIfNeeded()
  await snap('saved')
}

async function editConcurrently(page, baseURL, fixture, snap) {
  const detail = `/new-product-reminders?detail=${fixture.reminder}`
  const other = await page.context().newPage()
  try {
    await Promise.all([go(page, baseURL, detail), go(other, baseURL, detail)])
    const current = editor(page), stale = editor(other)
    await button(current, '修改需求').click()
    await button(stale, '修改需求').click()
    await current.getByLabel('规格', { exact: true }).fill('C5 当前版本')
    await stale.getByLabel('规格', { exact: true }).fill('C5 过期版本')
    const endpoint = byId('new-product-reminders', fixture.reminder)
    const { body } = await realSave(page, endpoint, 'PATCH', button(current, '保存需求'), 200)
    await other.bringToFront()
    const refused = other.waitForResponse(result => requestFor(endpoint, 'PATCH')(result.request()), { timeout: 45000 })
    await button(stale, '保存需求').click()
    const response = await refused
    expect(response.status()).toBe(409)
    const conflict = await response.json()
    expect(conflict.detail).toMatch(/版本|已变更|修改/)
    await expect(stale.getByRole('alert')).toBeInViewport()
    await expect(stale.getByLabel('规格', { exact: true })).toHaveValue('C5 过期版本')
    await snap('stale', other)
    await expect(button(stale, '保存需求')).toBeDisabled()
    await button(stale, '查看最新版本').click()
    await button(other.getByRole('dialog', { name: '未保存修改' }), '继续编辑').click()
    await expect(stale.getByLabel('规格', { exact: true })).toHaveValue('C5 过期版本')
    await button(stale, '查看最新版本').click()
    await button(other.getByRole('dialog', { name: '未保存修改' }), '放弃修改').click()
    await expect(stale).toContainText('C5 当前版本')
    await expect(stale).toContainText(fixture.buyers[0].name)
    expect((await json(other, endpoint)).version).toBe(body.version)
    await stale.getByText('规格：C5 当前版本', { exact: true }).scrollIntoViewIfNeeded()
    await snap('latest', other)
    await button(stale, '修改需求').click()
    await stale.getByLabel('规格', { exact: true }).fill('C5 重新处理')
    const retry = await realSave(other, endpoint, 'PATCH', button(stale, '保存需求'), 200)
    expect(retry.request.version).toBe(body.version)
    expect(await json(other, endpoint)).toMatchObject({
      customer: fixture.buyers[0].id, specification: 'C5 重新处理', version: body.version + 1,
    })
  } finally {
    await other.close()
  }
}

async function voidReminder(page, baseURL, fixture, snap) {
  await go(page, baseURL, `/new-product-reminders?detail=${fixture.reminder}`)
  const detail = editor(page)
  await button(detail, '作废').click()
  await expect(button(detail, '确认作废')).toBeDisabled()
  await detail.getByLabel('作废原因').fill('不应提交')
  await button(detail, '取消作废').click()
  const endpoint = byId('new-product-reminders', fixture.reminder)
  expect((await json(page, endpoint)).voided_at).toBeNull()
  await button(detail, '作废').click()
  await expect(detail.getByLabel('作废原因')).toHaveValue('')
  await expect(button(detail, '确认作废')).toBeDisabled()
  await detail.getByLabel('作废原因').fill('C5 合成资料重复录入')
  await realSave(page, endpoint + 'void/', 'POST', button(detail, '确认作废'), 200)
  await go(page, baseURL, `/new-product-reminders?state=void&detail=${fixture.reminder}`)
  await expect(detail.locator('.voided')).toContainText('C5 合成资料重复录入')
  await expect(button(detail, '修改需求')).toHaveCount(0)
  await expect(button(detail, '作废')).toHaveCount(0)
  await expect(button(detail, '删除')).toHaveCount(0)
  await expect(detail.locator('summary').filter({ hasText: '作废' })).toBeVisible()
  expect((await json(page, endpoint)).void_reason).toBe('C5 合成资料重复录入')
  await detail.locator('.voided').scrollIntoViewIfNeeded()
  await snap('void')
}

async function customerRecovery(page, baseURL, fixture, snap) {
  const [buyer, other] = fixture.buyers
  const [contact] = fixture.contacts
  await go(page, baseURL, `/customers?detail=${buyer.id}`)
  await button(dialog(page, '客户详情'), '编辑客户').click()
  const form = active(page).locator('form.customer-editor')
  const name = buyer.name + ' 已更新'
  await form.getByLabel('客户名称', { exact: true }).fill(name)
  await form.getByLabel('业务区域', { exact: true }).fill('C5 更新区域')
  const endpoint = byId('customers', buyer.id)
  const save = button(form, '保存客户')
  const payload = await saveAndReject(page, endpoint, 'PUT', save, button(form, '保存中…'), 'C5 受控拒绝客户保存', () => snap('pending'))
  await expect(form.getByLabel('客户名称', { exact: true })).toHaveValue(name)
  await expect(form.getByLabel('业务区域', { exact: true })).toHaveValue('C5 更新区域')
  await snap('rejected')
  const { request } = await realSave(page, endpoint, 'PUT', save, 200)
  expect(request).toEqual(payload)
  await page.reload({ waitUntil: 'domcontentloaded' })
  await expect(dialog(page, '客户详情')).toContainText(name)
  expect((await json(page, endpoint)).region).toBe('C5 更新区域')
  expect((await json(page, '/api/customers/?search=' + encodeURIComponent(name))).count).toBe(1)
  expect((await json(page, byId('customers', other.id))).name).toBe(other.name)
  expect(await json(page, byId('contacts', contact.id))).toMatchObject({ customer: buyer.id, phone: '010-5550100' })
  await snap('saved')
}

async function contactRecovery(page, baseURL, fixture, snap) {
  const [buyer] = fixture.buyers
  const [contact] = fixture.contacts
  await go(page, baseURL, '/contacts')
  await button(active(page), '新建联系人').click()
  const form = dialog(page, '新建联系人')
  await form.getByLabel('所属客户').selectOption(String(buyer.id))
  await form.getByLabel('姓名', { exact: true }).fill(contact.name)
  await expect(form.getByText(/该客户已有相同姓名或联系方式/)).toBeVisible()
  await form.getByLabel('职位', { exact: true }).fill('合成采购经理')
  await saveAndReject(page, '/api/contacts/', 'POST', button(form, '保存联系人'), button(form, '保存中…'), 'C5 受控拒绝联系人保存', () => snap('pending'))
  await expect(form.getByLabel('姓名', { exact: true })).toHaveValue(contact.name)
  await expect(form.getByLabel('所属客户')).toHaveValue(String(buyer.id))
  await expect(form.getByLabel('职位', { exact: true })).toHaveValue('合成采购经理')
  await snap('rejected')
  const name = contact.name + ' 修正'
  await form.getByLabel('姓名', { exact: true }).fill(name)
  const { body } = await realSave(page, '/api/contacts/', 'POST', button(form, '保存联系人'), 201)
  await go(page, baseURL, `/contacts?detail=${body.id}`)
  await expect(dialog(page, '联系人详情')).toContainText(name)
  expect((await json(page, '/api/contacts/?search=' + encodeURIComponent(name))).count).toBe(1)
  expect((await json(page, byId('contacts', body.id))).customer).toBe(buyer.id)
  await snap('saved')
}

async function readOnly(page, baseURL, fixture, snap, nested) {
  // Keep authenticated backend reads and project only the frontend session's existing read-only permission shape.
  const original = await json(page, '/api/session/current-operator/')
  await page.route(url => url.pathname === '/api/session/current-operator/', route => {
    return route.fulfill({ json: {
      ...original, development_superadmin: false, has_all_permissions: false,
      can_manage_permissions: false, rbac_enforcement: true,
      permissions: { dashboard: { view: true }, customers: { view: true }, contacts: { view: true } },
    } })
  })
  const [buyer, other] = fixture.buyers
  const [contact] = fixture.contacts
  await go(page, baseURL, `/customers?detail=${buyer.id}${nested ? '&tab=contacts' : ''}`)
  const customer = dialog(page, '客户详情')
  await expect(customer).toContainText(buyer.name)
  await expect(button(customer, '编辑客户')).toHaveCount(0)
  await snap('customer')
  if (nested) {
    const trigger = customer.getByText(contact.name, { exact: true }).first()
    await trigger.click()
    const contactDetail = dialog(page, '联系人详情')
    await expect(contactDetail).toContainText(contact.name)
    await expect(contactDetail).toContainText(buyer.name)
    await expect(contactDetail).toContainText('010-5550100')
    await expect(button(contactDetail, '编辑联系人')).toHaveCount(0)
    await snap('nested')
    await contactDetail.getByRole('button', { name: /返回/ }).click()
    await expect(customer).toContainText(contact.name)
    await expect(customer).not.toContainText(other.name)
    await expect(page).toHaveURL(/tab=contacts/)
    await snap('returned')
    const focus = await customer.evaluate(node => ({
      inside: node.contains(document.activeElement),
      tag: document.activeElement?.tagName,
      role: document.activeElement?.getAttribute('role'),
    }))
    expect(focus.inside || focus.role === 'tab', `CRM-03 return focus: ${JSON.stringify(focus)}`).toBe(true)
  }
  await button(customer, '关闭详情').click()
  await expect(customer).toBeHidden()
  await expect(page.getByRole('textbox', { name: '搜索客户' })).toBeVisible()
}

async function workspaceDrafts(page, baseURL, fixture, snap) {
  const [buyer, other] = fixture.buyers
  const [contact, otherContact] = fixture.contacts
  await go(page, baseURL, `/follow-ups?customer=${buyer.id}`)
  await expect(button(active(page), '新建跟进记录')).toBeVisible()
  const followListId = await page.getByRole('tab', { selected: true }).getAttribute('aria-controls')
  if (await page.locator('.mobile-menu').isVisible()) await page.locator('.mobile-menu').click()
  await page.getByRole('link', { name: '联系人', exact: true }).click()
  await button(active(page), '新建联系人').click()
  const contactForm = dialog(page, '新建联系人')
  const lookupUrl = url => url.pathname === '/api/contacts/' && url.searchParams.get('customer') === String(other.id)
  let releaseLookup
  const lookupGate = new Promise(resolve => { releaseLookup = resolve })
  const onLookup = async route => {
    await lookupGate
    await route.continue()
  }
  await page.route(lookupUrl, onLookup)
  let contactTabId
  try {
    const sent = page.waitForRequest(request => request.method() === 'GET' && lookupUrl(new URL(request.url())))
    await contactForm.getByLabel('所属客户').selectOption(String(other.id))
    await sent
    await contactForm.getByLabel('姓名', { exact: true }).fill(otherContact.name + ' 草稿')
    contactTabId = await page.getByRole('tab', { selected: true }).getAttribute('aria-controls')
    await page.locator(`[role="tab"][aria-controls="${followListId}"]`).click()
  } finally {
    const completed = page.waitForResponse(response => lookupUrl(new URL(response.url())), { timeout: 5000 })
    releaseLookup()
    await completed
    await page.unroute(lookupUrl, onLookup)
  }
  await button(active(page), '新建跟进记录').click()
  const follow = dialog(page, '新建跟进记录')
  await expect(follow.getByLabel('客户', { exact: true })).toHaveValue(String(buyer.id))
  await follow.getByLabel('联系人', { exact: true }).selectOption(String(contact.id))
  await follow.getByLabel('主题', { exact: true }).fill('C5 甲工作区主题')
  await follow.getByLabel('沟通记录').fill('C5 甲工作区正文')
  await follow.locator('input[type=file]').setInputFiles({ name: 'c5-local-draft.txt', mimeType: 'text/plain', buffer: Buffer.from('C5 synthetic draft') })
  const followTabId = await page.getByRole('tab', { selected: true }).getAttribute('aria-controls')
  await page.locator(`[role="tab"][aria-controls="${contactTabId}"]`).click()
  await expect(contactForm.getByLabel('所属客户')).toHaveValue(String(other.id))
  await page.locator(`[role="tab"][aria-controls="${followTabId}"]`).click()
  await expect(follow.getByLabel('客户', { exact: true })).toHaveValue(String(buyer.id))
  await expect(follow.getByLabel('联系人', { exact: true })).toHaveValue(String(contact.id))
  await expect(follow.getByLabel('沟通记录')).toHaveValue('C5 甲工作区正文')
  await expect(follow.getByText('c5-local-draft.txt')).toBeVisible()
  await snap('follow-up')
  await button(follow, '取消').click()
  await button(page.getByRole('dialog', { name: '未保存修改' }), '继续编辑').click()
  await expect(follow.getByLabel('主题', { exact: true })).toHaveValue('C5 甲工作区主题')
  await button(follow, '取消').click()
  await button(page.getByRole('dialog', { name: '未保存修改' }), '放弃修改').click()
  await expect(follow).toBeHidden()
  await page.locator(`[role="tab"][aria-controls="${contactTabId}"]`).click()
  await expect(contactForm.getByLabel('所属客户')).toHaveValue(String(other.id))
  await expect(contactForm.getByLabel('姓名', { exact: true })).toHaveValue(otherContact.name + ' 草稿')
  await snap('contact')
}

const scenarios = {
  'CRM-01': (page, baseURL, fixture, snap) => readOnly(page, baseURL, fixture, snap, false),
  'CRM-02': customerRecovery,
  'CRM-03': (page, baseURL, fixture, snap) => readOnly(page, baseURL, fixture, snap, true),
  'CRM-04': contactRecovery,
  'CRM-05': workspaceDrafts,
  'NPD-01': createReminder,
  'NPD-02': editConcurrently,
  'NPD-03': voidReminder,
}
if (process.env.C5_CASE && !(process.env.C5_CASE in scenarios)) throw new Error('Unknown C5 scenario.')

for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
  for (const zoom of [1, 1.25]) {
    if (process.env.C5_GEOMETRY && process.env.C5_GEOMETRY !== `${width}-${zoom * 100}`) continue
    test(`C5 CRM states at ${width}×${height} Chrome ${zoom * 100}%`, async ({ baseURL }) => {
      test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== spec, 'Dedicated C5 seed and browser profile require the isolated runner.')
      test.setTimeout(900000)
      const root = process.env.ISOLATED_TEST_ROOT
      const output = path.join(evidence, process.env.C5_CASE ? 'chrome-recheck' : 'chrome', `${width}-${zoom * 100}`)
      await mkdir(output, { recursive: true })
      const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
      const states = []
      for (const [id, scenario] of Object.entries(scenarios)) {
        if (process.env.C5_CASE && process.env.C5_CASE !== id) continue
        const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [
          path.join(evidence, 'seed.py'), `C5-${width}-${zoom * 100}-${id}`,
        ], { cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, PYTHONUTF8: '1' } }))
        const context = await chromium.launchPersistentContext(path.join(root, `c5-${width}-${zoom * 100}-${id}`), {
          channel: 'chrome', baseURL, viewport: { width, height },
        })
        const entry = { id, screenshots: [] }
        try {
          const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
          await context.addCookies(auth.cookies)
          const settings = context.pages()[0]
          await settings.setViewportSize({ width: 1440, height: 900 })
          await settings.goto('chrome://settings/appearance', { waitUntil: 'domcontentloaded' })
          await settings.getByRole('combobox', { name: /网页缩放|Page zoom/ }).selectOption(String(zoom))
          const page = await context.newPage()
          page.setDefaultTimeout(15000)
          const snap = async (state, target = page) => {
            const cdp = await context.newCDPSession(target)
            try {
              const geometry = await target.evaluate(() => ({ width: innerWidth, height: innerHeight, dpr: devicePixelRatio }))
              expect(geometry.dpr).toBeCloseTo(zoom, 2)
              expect(Math.abs(geometry.width - width / zoom)).toBeLessThan(2)
              entry.browser = (await cdp.send('Browser.getVersion')).product
              expect(entry.browser).toMatch(/^Chrome\//)
              const filename = `${id}-${state}.png`
              const shot = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
              await writeFile(path.join(output, filename), Buffer.from(shot.data, 'base64'))
              entry.screenshots.push({ filename, ...geometry })
            } finally { await cdp.detach() }
          }
          try { await scenario(page, baseURL, fixture, snap); entry.result = 'PASS' }
          catch (error) {
            entry.result = 'FAIL'; entry.error = String(error).replace(/\x1b\[[0-9;]*m/g, '')
            if (!page.isClosed()) await snap('failure').catch(() => {})
          }
        } catch (error) {
          entry.result = 'FAIL'; entry.error = String(error)
        } finally {
          await context.close()
          states.push(entry)
          await writeFile(path.join(output, process.env.C5_CASE ? `${id}.json` : 'run.json'), JSON.stringify({ source, width, height, zoom, states }, null, 2) + '\n')
        }
      }
      expect(states).toHaveLength(process.env.C5_CASE ? 1 : Object.keys(scenarios).length)
      expect(states.filter(row => row.result !== 'PASS')).toEqual([])
    })
  }
}
