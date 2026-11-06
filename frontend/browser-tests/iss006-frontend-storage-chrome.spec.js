import { test, expect } from '@playwright/test'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'

const evidenceDir = process.env.ISS006_STORAGE_EVIDENCE_DIR
if (!evidenceDir) throw new Error('ISS006_STORAGE_EVIDENCE_DIR must point to the isolated evidence directory.')
const fixtures = JSON.parse(await readFile(path.join(evidenceDir, 'fixture.json'), 'utf8'))
const caseNames = ['property-getter', 'get-item', 'set-item-recovery', 'remove-item-recovery', 'lost-response']
const successfulCaseNames = new Set(['set-item-recovery', 'remove-item-recovery', 'lost-response'])
let currentTrace = null
const completedCases = []

function installStorageFault({ mode }) {
  const prefix = 'sunjack:fulfillment-idempotency:'
  const originalWindowDescriptor = Object.getOwnPropertyDescriptor(window, 'sessionStorage')
  const storage = originalWindowDescriptor.get.call(window)
  const methodNames = ['getItem', 'setItem', 'removeItem']
  const originalMethods = Object.fromEntries(methodNames.map(name => [name, Object.getOwnPropertyDescriptor(Storage.prototype, name)]))

  window.__iss006StorageCandidateId = null

  window.__iss006RestoreStorage = () => {
    Object.defineProperty(window, 'sessionStorage', originalWindowDescriptor)
    for (const name of methodNames) Object.defineProperty(Storage.prototype, name, originalMethods[name])
  }

  if (mode === 'property-getter') {
    Object.defineProperty(window, 'sessionStorage', {
      configurable: true,
      get() { throw new DOMException('Session storage access denied for test.', 'SecurityError') },
    })
    return
  }

  const method = { 'get-item': 'getItem', 'set-item': 'setItem', 'remove-item': 'removeItem' }[mode]
  if (!method) return
  Object.defineProperty(Storage.prototype, method, {
    configurable: true,
    writable: true,
    value(key, ...args) {
      if (String(key).startsWith(prefix)) {
        if (method === 'setItem') window.__iss006StorageCandidateId = JSON.parse(args[0]).requestId
        throw new DOMException(`Blocked ${method} for test.`, 'SecurityError')
      }
      return originalMethods[method].value.call(this, key, ...args)
    },
  })
  void storage
}

async function beginCase(page, operation, caseName, faultMode) {
  const fixture = fixtures[operation][caseName]
  const endpoint = operation === 'receive'
    ? `/api/purchase-orders/${fixture.purchase_id}/receive/`
    : `/api/orders/${fixture.order_id}/ship/`
  currentTrace = {
    case_key: `${operation}:${caseName}`,
    operation,
    scenario: caseName,
    fixture,
    endpoint,
    requests: [],
    responses: [],
    failed_requests: [],
    screenshots: [],
    console_errors: [],
    page_errors: [],
    user_agent: null,
    candidate_id: null,
    upstream_status: null,
  }
  page.on('request', request => {
    const url = new URL(request.url())
    if (url.pathname !== endpoint || request.method() !== 'POST') return
    currentTrace.requests.push({
      method: request.method(),
      url: `${url.origin}${url.pathname}`,
      idempotency_key: request.headers()['idempotency-key'] || null,
      post_data: request.postData(),
    })
  })
  page.on('response', response => {
    const url = new URL(response.url())
    if (url.pathname === endpoint && response.request().method() === 'POST') {
      currentTrace.responses.push({ status: response.status(), url: `${url.origin}${url.pathname}` })
    }
  })
  page.on('requestfailed', request => {
    const url = new URL(request.url())
    if (url.pathname === endpoint && request.method() === 'POST') {
      currentTrace.failed_requests.push({ failure: request.failure()?.errorText || 'unknown' })
    }
  })
  page.on('console', message => {
    if (message.type() === 'error') currentTrace.console_errors.push(message.text())
  })
  page.on('pageerror', error => currentTrace.page_errors.push(error.message))
  await page.addInitScript(installStorageFault, { mode: faultMode })
  const route = operation === 'receive'
    ? `/purchase-orders?detail=${fixture.purchase_id}`
    : `/orders?detail=${fixture.order_id}`
  await page.goto(route, { waitUntil: 'domcontentloaded' })
  currentTrace.user_agent = await page.evaluate(() => navigator.userAgent)
  expect(currentTrace.user_agent).toContain('Chrome/')

  if (operation === 'receive') {
    await expect(page.getByRole('dialog', { name: '采购工作台' })).toBeVisible()
    await page.getByRole('button', { name: '收货', exact: true }).click()
    await page.getByRole('button', { name: '验货入库' }).click()
    const dialog = page.getByRole('dialog', { name: '验货合格入库' })
    await expect(dialog).toBeVisible()
    await dialog.getByRole('checkbox', { name: /已核对型号、数量及外观/ }).check()
    return {
      dialog,
      submit: dialog.getByRole('button', { name: '确认入库', exact: true }),
      alert: dialog.getByRole('alert'),
      page,
    }
  }

  await expect(page.getByRole('dialog', { name: '订单工作台' })).toBeVisible()
  await page.getByRole('button', { name: '采购与发货', exact: true }).click()
  await page.getByRole('button', { name: '确认发货', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '确认发货' })
  await expect(dialog).toBeVisible()
  return {
    dialog,
    submit: dialog.getByRole('button', { name: '确认发货', exact: true }),
    alert: dialog.getByRole('alert'),
    page,
  }
}

async function expectBlockedAndReady(workflow) {
  await expect(workflow.alert).toBeVisible()
  const text = await workflow.alert.innerText()
  expect(text).toContain('已阻止提交')
  await expect(workflow.submit).toBeEnabled()
  await expect(workflow.dialog).toBeVisible()
}

async function screenshot(page, fileName) {
  const folder = path.join(evidenceDir, 'screenshots')
  await mkdir(folder, { recursive: true })
  const absolutePath = path.join(folder, fileName)
  await page.screenshot({ path: absolutePath, fullPage: true })
  currentTrace.screenshots.push(path.relative(evidenceDir, absolutePath).replaceAll('\\', '/'))
}

test.beforeAll(async ({ browser }) => {
  const probe = await browser.newPage()
  const userAgent = await probe.evaluate(() => navigator.userAgent)
  await probe.close()
  await writeFile(path.join(evidenceDir, 'browser-environment.json'), JSON.stringify({
    browserVersion: browser.version(),
    channel: process.env.PLAYWRIGHT_CHANNEL || null,
    headless: process.env.PLAYWRIGHT_HEADLESS !== '0',
    userAgent,
    isolatedDatabase: fixtures.database,
    isolatedMediaRoot: process.env.MEDIA_ROOT,
    runId: fixtures.run_id,
  }, null, 2), 'utf8')
})

test.afterEach(async ({}, testInfo) => {
  if (!currentTrace) return
  currentTrace.status = testInfo.status
  currentTrace.failure = testInfo.error?.message || null
  currentTrace.request_count = currentTrace.requests.length
  currentTrace.idempotency_keys = currentTrace.requests.map(request => request.idempotency_key)
  completedCases.push(currentTrace)
  await writeFile(path.join(evidenceDir, 'browser-results.json'), JSON.stringify({
    run_id: fixtures.run_id,
    cases: completedCases.map(({ fixture: _fixture, ...result }) => result),
  }, null, 2), 'utf8')
  currentTrace = null
})

for (const operation of ['receive', 'ship']) {
  const operationLabel = operation === 'receive' ? '采购收货' : '订单发货'

  test(`${operationLabel}: sessionStorage 属性读取异常时阻止提交`, async ({ page }) => {
    const workflow = await beginCase(page, operation, 'property-getter', 'property-getter')
    await workflow.submit.click()
    await expectBlockedAndReady(workflow)
    expect(currentTrace.requests).toHaveLength(0)
    await screenshot(page, `${operation}-property-getter-blocked.png`)
  })

  test(`${operationLabel}: sessionStorage.getItem 异常时阻止提交`, async ({ page }) => {
    const workflow = await beginCase(page, operation, 'get-item', 'get-item')
    await workflow.submit.click()
    await expectBlockedAndReady(workflow)
    expect(currentTrace.requests).toHaveLength(0)
    await screenshot(page, `${operation}-get-item-blocked.png`)
  })

  test(`${operationLabel}: setItem 异常后恢复存储，沿用原请求 ID`, async ({ page }) => {
    const workflow = await beginCase(page, operation, 'set-item-recovery', 'set-item')
    await workflow.submit.click()
    await expectBlockedAndReady(workflow)
    expect(currentTrace.requests).toHaveLength(0)
    currentTrace.candidate_id = await page.evaluate(() => window.__iss006StorageCandidateId)
    expect(currentTrace.candidate_id).toMatch(/^[0-9a-f-]{36}$/i)
    await screenshot(page, `${operation}-set-item-blocked.png`)
    await page.evaluate(() => window.__iss006RestoreStorage())
    await workflow.submit.click()
    await expect(workflow.dialog).toBeHidden()
    expect(currentTrace.requests).toHaveLength(1)
    expect(currentTrace.requests[0].idempotency_key).toBe(currentTrace.candidate_id)
    await screenshot(page, `${operation}-set-item-recovered.png`)
  })

  test(`${operationLabel}: removeItem 异常提示核对服务器结果，恢复后重试不重复建单`, async ({ page }) => {
    const workflow = await beginCase(page, operation, 'remove-item-recovery', 'remove-item')
    await workflow.submit.click()
    await expect(workflow.alert).toBeVisible()
    const warning = await workflow.alert.innerText()
    expect(warning).toContain('服务器已确认收货/发货成功')
    expect(warning).toContain('请先核对业务记录')
    await expect(workflow.submit).toBeEnabled()
    expect(currentTrace.requests).toHaveLength(1)
    await screenshot(page, `${operation}-remove-item-server-may-have-succeeded.png`)
    await page.evaluate(() => window.__iss006RestoreStorage())
    await workflow.submit.click()
    await expect(workflow.dialog).toBeHidden()
    expect(currentTrace.requests).toHaveLength(2)
    expect(new Set(currentTrace.requests.map(request => request.idempotency_key)).size).toBe(1)
    await screenshot(page, `${operation}-remove-item-retry-deduplicated.png`)
  })

  test(`${operationLabel}: 服务器成功但网络响应丢失，重试只生成一条记录`, async ({ page }) => {
    const workflow = await beginCase(page, operation, 'lost-response', null)
    let loseFirstResponse = true
    await page.route(`**${currentTrace.endpoint}`, async route => {
      if (route.request().method() !== 'POST' || !loseFirstResponse) return route.continue()
      const upstream = await route.fetch()
      currentTrace.upstream_status = upstream.status()
      loseFirstResponse = false
      await route.abort('failed')
    })
    await workflow.submit.click()
    await expect(workflow.alert).toBeVisible()
    await expect(workflow.submit).toBeEnabled()
    expect(currentTrace.upstream_status).toBe(201)
    expect(currentTrace.requests).toHaveLength(1)
    await screenshot(page, `${operation}-response-lost-before-retry.png`)
    await workflow.submit.click()
    await expect(workflow.dialog).toBeHidden()
    expect(currentTrace.requests).toHaveLength(2)
    expect(new Set(currentTrace.requests.map(request => request.idempotency_key)).size).toBe(1)
    await screenshot(page, `${operation}-response-lost-retried.png`)
  })
}
