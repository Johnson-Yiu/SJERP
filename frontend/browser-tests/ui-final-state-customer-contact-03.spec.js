import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect as playwrightExpect, test } from '@playwright/test'

const expect = playwrightExpect.configure({ timeout: 30000 })

test('customer creation selects an employee and preserves nested contacts after a rejected save', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
    'Requires a dedicated seeded database; run this spec through the isolated runner.')
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-customer-contact')
  await mkdir(output, { recursive: true })
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-final-state-closeout-03/seed.py', import.meta.url))
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, CLOSEOUT_CUSTOMER_CONTACT: '1' },
  }))
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'customer-contact-chrome'), {
    channel: 'chrome', viewport: { width: 390, height: 844 },
  })
  const states = []
  let browser
  let failure
  const save = () => writeFile(path.join(output, 'run.json'), JSON.stringify({ source, browser, states, failure }, null, 2) + '\n')
  try {
    const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
    await context.addCookies(auth.cookies)
    const settings = context.pages()[0]
    const page = await context.newPage()
    page.setDefaultTimeout(90000)
    const cdp = await context.newCDPSession(page)
    browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    await settings.goto('chrome://settings/appearance', { waitUntil: 'commit', timeout: 240000 })
    const zoomControl = settings.locator('settings-appearance-page select').filter({ has: settings.locator('option[value="1.25"]') })
    let zoom = 1.25
    await zoomControl.selectOption(String(zoom), { timeout: 180000 })
    const go = route => page.goto(new URL(route, baseURL).href, { waitUntil: 'commit', timeout: 240000 })

    for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
      for (const scale of [1, 1.25]) {
        zoom = scale
        await zoomControl.selectOption(String(zoom))
        await page.setViewportSize({ width, height })
        const capture = async id => {
          expect(await page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
          const png = id + '-' + width + '-' + zoom * 100 + '.png'
          const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
          await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
          states.push({ id, width, height, zoom, png })
          await save()
        }
        const ownerEndpoint = url => url.pathname === '/api/customers/owner-options/'
        await context.route(ownerEndpoint, route => route.fulfill({ status: 400, json: { detail: '暂时无法读取人员资料' } }))
        await go('/customers')
        const rejectedOptions = page.waitForResponse(response =>
          ownerEndpoint(new URL(response.url())) && response.status() === 400)
        await page.getByRole('button', { name: '新建客户', exact: true }).click()
        await rejectedOptions
        const editor = page.getByRole('dialog', { name: '新建客户' })
        const ownerError = editor.getByRole('alert').filter({ hasText: '负责人资料加载失败' })
        await expect(ownerError).toBeVisible()
        await ownerError.scrollIntoViewIfNeeded()
        await capture('customer-owner-options-failed')
        await context.unroute(ownerEndpoint)
        const recoveredOptions = page.waitForResponse(response =>
          ownerEndpoint(new URL(response.url())) && response.ok())
        await ownerError.getByRole('button', { name: '重新加载', exact: true }).click()
        await recoveredOptions
        await expect(ownerError).toHaveCount(0)
        const employee = editor.locator('.field').filter({ has: page.getByText('负责人', { exact: true }) }).locator('select')
        const name = '合成客户联系人分支-' + width + '-' + zoom * 100
        const contactName = '合成采购联系人'
        await editor.getByLabel('客户名称', { exact: true }).fill(name)
        await expect(employee.locator('option', { hasText: '合成负责人 · 合成业务部' })).toHaveCount(1)
        await employee.selectOption(String(fixture.owner))
        await editor.getByRole('button', { name: '新增联系人' }).click()
        await editor.locator('.contact-create-card').first().locator('input').nth(1).fill('合成原联系人')
        const addedContact = editor.locator('.contact-create-card').last().locator('.contact-fields input').first()
        await addedContact.fill(contactName)
        const submit = editor.getByRole('button', { name: '保存客户', exact: true })
        const customerWrite = response => new URL(response.url()).pathname === '/api/customers/' && response.request().method() === 'POST'
        let release
        const gate = new Promise(resolve => { release = resolve })
        const customerEndpoint = url => url.pathname === '/api/customers/'
        await page.route(customerEndpoint, async route => {
          if (route.request().method() !== 'POST') return route.continue()
          await gate
          await route.fulfill({ status: 400, json: { detail: '合成校验失败，请重试' } })
        })
        const rejected = page.waitForResponse(customerWrite)
        try {
          await submit.click()
          const pending = editor.getByRole('button', { name: '保存中…', exact: true })
          await expect(pending).toBeDisabled()
          await pending.scrollIntoViewIfNeeded()
          await capture('customer-create-pending')
        } finally { release() }
        expect((await rejected).status()).toBe(400)
        await page.unroute(customerEndpoint)
        await expect(employee).toHaveValue(String(fixture.owner))
        await expect(addedContact).toHaveValue(contactName)
        await expect(submit).toBeEnabled()
        const created = page.waitForResponse(customerWrite)
        await submit.click()
        const response = await created
        expect(response.status(), await response.text()).toBe(201)
        const { id } = await response.json()
        await expect(editor).toHaveCount(0)
        await go('/customers?detail=' + id + '&tab=contacts')
        const detail = page.getByRole('dialog', { name: '客户详情' })
        await expect(detail.getByText(/负责人：合成负责人/)).toBeVisible()
        const contact = detail.getByText(contactName, { exact: true }).first()
        await expect(contact).toBeVisible()
        await contact.scrollIntoViewIfNeeded()
        await capture('customer-owner-and-contact-readback')
        await detail.getByRole('button', { name: '新增联系人', exact: true }).click()
        const related = page.locator('form.related-create-modal').filter({ has: page.getByRole('heading', { name: '新增联系人', exact: true }) })
        const contactField = label => related.locator('.field').filter({ has: page.locator('label').filter({ hasText: label }) })
        const relatedCustomer = contactField('所属客户').locator('select')
        await expect(relatedCustomer).toHaveValue(String(id))
        await expect(relatedCustomer).toBeDisabled()
        const nestedName = '合成详情新增联系人'
        await contactField('姓名').locator('input').fill(nestedName)
        const nestedResponse = page.waitForResponse(r => new URL(r.url()).pathname === '/api/contacts/' && r.request().method() === 'POST')
        await related.getByRole('button', { name: '保存', exact: true }).click()
        const nested = await nestedResponse
        expect(nested.status(), await nested.text()).toBe(201)
        expect((await nested.json()).customer).toBe(id)
        await expect(related).toHaveCount(0)
        const returnedContact = detail.getByText(nestedName, { exact: true }).first()
        await expect(returnedContact).toBeVisible()
        await expect(async () => { await returnedContact.scrollIntoViewIfNeeded(); await expect(returnedContact).toBeInViewport({ timeout: 2000 }) }).toPass({ timeout: 15000 })
        await capture('customer-related-contact-returned')
      }
    }
  } catch (error) {
    failure = String(error.message)
    throw error
  } finally {
    await save()
    await context.close()
  }
})
