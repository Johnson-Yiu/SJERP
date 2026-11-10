import { chromium, expect, test } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

test.use({ channel: 'chrome' })

test('quote correction separates proposal, approval and resulting draft', async ({ baseURL }) => {
  test.setTimeout(2400000)
  const evidence = path.resolve(process.env.SALES_STATE_EVIDENCE_DIR)
  await mkdir(evidence, { recursive: true })
  const password = randomBytes(24).toString('hex')
  const seed = path.resolve('../docs/uat-evidence/ui-sales-state-evidence-01/seed-party.py')
  const output = execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8',
    env: { ...process.env, SALES_EVIDENCE_REVIEWER_PASSWORD: password },
  })
  const { id } = JSON.parse(output.trim().split('\n').at(-1))
  const route = '/quotes?detail=' + id
  const results = []
  let browserVersion
  const save = () => writeFile(path.join(evidence, 'run.json'), JSON.stringify({
    browser: browserVersion, results,
  }, null, 2))
  async function post(actor, suffix, name, status) {
    const [response] = await Promise.all([
      actor.waitForResponse(r => new URL(r.url()).pathname.endsWith(suffix)
        && r.request().method() === 'POST', { timeout: 75000 }),
      actor.getByRole('button', { name, exact: true }).click(),
    ])
    results.push({ action: name, status: response.status() })
    await save()
    expect(response.status()).toBe(status)
    return response.json()
  }
  async function shots(actor, marker, state) {
    const settings = actor.context().pages()[0]
    await settings.goto('chrome://settings/appearance')
    const zoomControl = settings.locator('settings-appearance-page select').filter({
      has: settings.locator('option[value="1.25"]'),
    })
    for (const zoom of [1, 1.25]) {
      await zoomControl.selectOption(String(zoom))
      for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
        await actor.setViewportSize({ width, height })
        if (width === 390) {
          await expect.poll(() => actor.locator('.sidebar').evaluate(sidebar => sidebar.getBoundingClientRect().right)).toBeLessThanOrEqual(1)
        }
        await marker.scrollIntoViewIfNeeded()
        const dpr = await actor.evaluate(() => devicePixelRatio)
        expect(dpr).toBeCloseTo(zoom, 2)
        const file = state + '-' + width + '-' + zoom * 100 + '.png'
        await actor.screenshot({ path: path.join(evidence, file), animations: 'disabled', timeout: 75000 })
        results.push({ state, width, height, zoom, dpr, file })
        await save()
      }
    }
    await zoomControl.selectOption('1')
    await actor.setViewportSize({ width: 1440, height: 900 })
  }

  const launch = name => chromium.launchPersistentContext(path.join(process.env.ISOLATED_TEST_ROOT, name), {
    channel: 'chrome', viewport: { width: 1440, height: 900 },
  })
  const first = await launch('party-applicant')
  const other = await launch('party-reviewer')
  const page = await first.newPage()
  page.setDefaultTimeout(75000)
  const cdp = await first.newCDPSession(page)
  browserVersion = (await cdp.send('Browser.getVersion')).product
  expect(browserVersion).toMatch(/^Chrome\//)
  async function login(actor, username, secret) {
    await actor.goto(new URL('/login', baseURL).href)
    await actor.getByLabel('账号').fill(username)
    await actor.getByLabel('密码').fill(secret)
    await post(actor, '/api/session/login/', '登录', 200)
    await expect(actor).not.toHaveURL(/\/login/, { timeout: 25000 })
  }
  try {
    await login(page, process.env.CODEX_TEST_USERNAME, process.env.CODEX_TEST_PASSWORD)
    await page.goto(new URL(route, baseURL).href)
    await post(page, '/mark-sent/', '标记为已发送', 200)
    const original = await (await page.request.get(new URL('/api/quotes/' + id + '/', baseURL).href)).json()
    await page.getByRole('button', { name: '主体更正', exact: true }).click()
    await page.locator('#party-address').fill('Synthetic corrected address 123')
    await page.getByLabel('原因', { exact: true }).fill('Synthetic correction reason')
    await page.getByLabel('依据', { exact: true }).fill('Synthetic supporting evidence')
    await page.getByLabel('我已核对依据，确认法律主体未变').check()
    await post(page, '/party-change/', '提交更正申请', 201)
    const selfReview = page.getByText('申请人不能审批自己的申请。')
    await expect(selfReview).toBeVisible({ timeout: 25000 })
    await shots(page, selfReview, 'Q07-pending-self-review')

    const reviewer = await other.newPage()
    reviewer.setDefaultTimeout(75000)
    await reviewer.goto(new URL('/login', baseURL).href)
    await reviewer.getByLabel('账号').fill('sales-evidence-reviewer')
    await reviewer.getByLabel('密码').fill(password)
    await post(reviewer, '/api/session/login/', '登录', 200)
    await expect(reviewer).not.toHaveURL(/\/login/, { timeout: 25000 })
    await reviewer.goto(new URL(route, baseURL).href)
    await reviewer.getByRole('button', { name: '主体更正', exact: true }).click()
    await reviewer.getByLabel('审批意见').fill('Synthetic independent review')
    await shots(reviewer, reviewer.getByRole('button', { name: '批准更正', exact: true }), 'Q07-review')
    await post(reviewer, '/approve/', '批准更正', 200)
    await shots(reviewer, reviewer.getByText('Synthetic independent review'), 'Q07-approved')

    await page.goto(new URL(route, baseURL).href)
    await expect(page.getByLabel('账号').or(page.getByRole('button', { name: '主体更正', exact: true }))).toBeVisible({ timeout: 25000 })
    if (await page.getByLabel('账号').isVisible()) {
      await page.getByLabel('账号').fill(process.env.CODEX_TEST_USERNAME)
      await page.getByLabel('密码').fill(process.env.CODEX_TEST_PASSWORD)
      await post(page, '/api/session/login/', '登录', 200)
      await expect(page).not.toHaveURL(/\/login/, { timeout: 25000 })
      await page.goto(new URL(route, baseURL).href)
    }
    await page.getByRole('button', { name: '主体更正', exact: true }).click()
    const result = await post(page, '/apply/', '生成报价草稿', 200)
    const source = await (await page.request.get(new URL('/api/quotes/' + id + '/', baseURL).href)).json()
    const child = await (await page.request.get(new URL('/api/quotes/' + result.result_quote_id + '/', baseURL).href)).json()
    expect(source.buyer_address).toBe(original.buyer_address)
    expect(child.buyer_address).toBe('Synthetic corrected address 123')
    expect(child.status).toBe('draft')
    expect(child.total_amount).toBe(source.total_amount)
    results.push({ state: 'resulting-draft', sourceUnchanged: true, addressApplied: true, totalMatches: true })
    await save()
  } finally {
    await Promise.all([first.close(), other.close()])
  }
})
