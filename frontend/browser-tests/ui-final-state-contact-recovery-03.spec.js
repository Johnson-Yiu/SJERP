import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('contact detail recovers from a delayed failure and returns to its follow-up', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
    'Requires a dedicated seeded database; run this spec through the isolated runner.')
  test.setTimeout(600000)
  const root = process.env.ISOLATED_TEST_ROOT
  const output = path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-contact-recovery')
  await mkdir(output, { recursive: true })
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-final-state-closeout-03/seed.py', import.meta.url))
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, CLOSEOUT_CONTACT_RECOVERY: '1' },
  }))
  const context = await chromium.launchPersistentContext(path.join(root, 'contact-recovery'), {
    channel: 'chrome', viewport: { width: 390, height: 844 },
  })
  const results = []
  let failure
  let browser
  try {
    const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
    await context.addCookies(auth.cookies)
    const settings = context.pages()[0]
    const page = await context.newPage()
    const cdp = await context.newCDPSession(page)
    browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    await settings.goto('chrome://settings/appearance', { waitUntil: 'domcontentloaded', timeout: 100000 })
    const zoomSelect = settings.locator('settings-appearance-page select').filter({ has: settings.locator('option[value="1.25"]') })
    const contactEndpoint = url => url.pathname === '/api/context/contacts/' + fixture.closeout_contact + '/'
    for (const zoom of [1, 1.25]) {
      await zoomSelect.selectOption(String(zoom))
      const screenshot = async state => {
        expect(await page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
        const png = state + '-' + zoom * 100 + '.png'
        await page.screenshot({ path: path.join(output, png) })
        results.push({ state, png, zoom, width: 390, height: 844 })
      }
      let release
      const delayed = new Promise(resolve => { release = resolve })
      await page.route(contactEndpoint, async route => {
        await delayed
        await route.fulfill({ status: 400, json: { detail: '暂时无法读取联系人' } })
      }, { times: 1 })
      await page.goto(new URL('/follow-ups?detail=' + fixture.closeout_followup, baseURL).href)
      const followUp = page.getByRole('dialog', { name: '跟进详情' })
      await expect(followUp.getByText('合成跟进回看', { exact: true }).first()).toBeVisible()
      const contact = page.getByRole('dialog', { name: '联系人详情' })
      try {
        await followUp.getByRole('button', { name: /合成采购联系人/ }).click()
        await expect(contact.getByRole('status')).toContainText('正在整理关联数据')
        await screenshot('contact-loading')
      } finally { release() }
      await expect(contact.getByRole('alert')).toContainText('详情加载失败')
      await screenshot('contact-failed')
      const retrieved = page.waitForResponse(r => contactEndpoint(new URL(r.url())) && r.ok())
      await contact.getByRole('button', { name: '重试' }).click()
      expect((await retrieved).status()).toBe(200)
      await expect(contact.getByText('主联系人', { exact: true }).first()).toBeVisible()
      await screenshot('contact-recovered')
      await contact.getByRole('button', { name: '返回 合成跟进回看' }).click()
      await expect(followUp.getByText('合成跟进回看', { exact: true }).first()).toBeVisible()
      await screenshot('followup-returned')
    }
  } catch (error) {
    failure = String(error.message)
    throw error
  } finally {
    await writeFile(path.join(output, 'run.json'), JSON.stringify({ source, browser, results, failure }, null, 2) + '\n')
    await context.close()
  }
})
