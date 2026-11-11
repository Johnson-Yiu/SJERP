import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('contact detail recovers from a delayed failure and returns to its follow-up', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
    'Requires a dedicated seeded database; run this spec through the isolated runner.')
  test.setTimeout(2400000)
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
        await expect(followUp.locator('.detail-loading')).toContainText('正在整理关联数据')
        await screenshot('contact-loading')
      } finally { release() }
      await expect(followUp.getByRole('alert')).toContainText('详情加载失败')
      await screenshot('contact-failed')
      const retrieved = page.waitForResponse(r => contactEndpoint(new URL(r.url())) && r.ok())
      await followUp.getByRole('button', { name: '重试' }).click()
      expect((await retrieved).status()).toBe(200)
      await expect(contact.getByText('主联系人', { exact: true }).first()).toBeVisible()
      await screenshot('contact-recovered')
      await contact.getByRole('button', { name: '返回 合成跟进回看' }).click()
      await expect(followUp.getByText('合成跟进回看', { exact: true }).first()).toBeVisible()
      await screenshot('followup-returned')
    }
    for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
      for (const zoom of [1, 1.25]) {
        await zoomSelect.selectOption(String(zoom))
        await page.setViewportSize({ width, height })
        const suffix = width + '-' + zoom * 100
        const screenshot = async state => {
          expect(await page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
          const png = state + '-' + suffix + '.png'
          await page.screenshot({ path: path.join(output, png) })
          results.push({ state, png, zoom, width, height })
        }
        const row = page.locator('.follow-up-list-table tbody tr').filter({ hasText: '合成跟进回看' })
        const dialog = page.getByRole('dialog', { name: '编辑跟进记录' })
        const edit = () => row.getByRole('button', { name: '编辑跟进记录' }).click()
        const saved = name => dialog.locator('.follow-up-attachment-editor-item.saved').filter({ hasText: name })
        const save = dialog.getByRole('button', { name: '保存跟进', exact: true })
        const add = name => dialog.locator('input[type="file"]').setInputFiles({
          name, mimeType: 'text/plain', buffer: Buffer.from(name + '\n'),
        })
        const oldName = 'original-notes-' + suffix + '.txt'
        const newName = 'updated-notes-' + suffix + '.txt'
        const uploadPath = '/api/follow-ups/' + fixture.closeout_followup + '/attachments/'
        const uploaded = () => page.waitForResponse(r => new URL(r.url()).pathname === uploadPath && r.request().method() === 'POST')
        await page.goto(new URL('/follow-ups', baseURL).href)
        await edit()
        await add(oldName)
        const initial = uploaded()
        await save.click()
        expect((await initial).ok()).toBeTruthy()
        await expect(dialog).toHaveCount(0)
        await page.reload()
        await edit()
        await expect(saved(oldName)).toHaveCount(1)

        let release
        let entered
        const gate = new Promise(resolve => { release = resolve })
        const intercepted = new Promise(resolve => { entered = resolve })
        await page.route(url => url.pathname === uploadPath, async route => {
          entered()
          await gate
          await route.continue()
        }, { times: 1 })
        await add(newName)
        const replacement = uploaded()
        try {
          await save.click()
          await Promise.race([intercepted, replacement])
          await expect(dialog.getByRole('button', { name: '保存中…', exact: true })).toBeDisabled()
          await screenshot('attachment-upload-pending')
        } finally { release() }
        expect((await replacement).ok()).toBeTruthy()
        await expect(dialog).toHaveCount(0)
        await page.reload()
        await edit()
        const remove = async () => {
          await dialog.getByRole('button', { name: '删除已保存附件 ' + oldName, exact: true }).click()
          await page.getByRole('button', { name: '确认删除', exact: true }).click()
        }
        await page.route(url => url.pathname.startsWith(uploadPath) && url.pathname !== uploadPath,
          route => route.fulfill({ status: 400, json: { detail: '合成删除失败，请重试' } }), { times: 1 })
        await remove()
        await expect(page.locator('.toast')).toContainText('合成删除失败，请重试')
        await expect(saved(oldName)).toHaveCount(1)
        await screenshot('attachment-delete-failed')
        await remove()
        await expect(saved(oldName)).toHaveCount(0)
        await page.reload()
        await edit()
        await expect(saved(oldName)).toHaveCount(0)
        await expect(saved(newName)).toHaveCount(1)
        const href = await saved(newName).getByRole('link', { name: '查看' }).getAttribute('href')
        const file = await page.request.get(new URL(href, baseURL).href)
        expect(file.ok()).toBeTruthy()
        expect(await file.text()).toBe(newName + '\n')
        await saved(newName).scrollIntoViewIfNeeded()
        await screenshot('attachment-replaced-and-reopened')
      }
    }
  } catch (error) {
    failure = String(error.message)
    throw error
  } finally {
    await writeFile(path.join(output, 'run.json'), JSON.stringify({ source, browser, results, failure }, null, 2) + '\n')
    await context.close()
  }
})
