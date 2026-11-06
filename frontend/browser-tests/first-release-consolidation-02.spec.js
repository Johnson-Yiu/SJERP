import { expect, test } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

const evidenceDir = path.resolve(process.env.FIRST_RELEASE_CONSOLIDATION_EVIDENCE_DIR || '')

test('finance navigation and historical preflight CSV work in isolated Chrome', async ({ page }) => {
  test.setTimeout(90_000)
  await fs.mkdir(evidenceDir, { recursive: true })
  const fixture = JSON.parse(await fs.readFile(path.join(evidenceDir, 'fixture.json'), 'utf8'))
  expect(fixture.synthetic_only).toBe(true)
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/finance')
  const identity = await page.evaluate(async () => {
    const response = await fetch('/api/session/current-operator/')
    return { status: response.status, ...(await response.json()) }
  })
  expect(identity.status).toBe(200)
  expect(identity.name).toBe('codex')
  expect(identity.role).toBe('超级管理员')
  expect(identity.authenticated).toBe(true)
  expect(identity.development_superadmin).toBe(false)
  expect(identity.rbac_enforcement).toBe(false)
  expect(identity.has_all_permissions).toBe(true)
  expect(identity.permissions.transactions.view).toBe(true)

  await expect(page.getByRole('heading', { name: '财务概览', exact: true })).toBeVisible()
  const sidebarLink = page.locator('.sidebar nav').getByRole('link', { name: '银行资金记录', exact: true })
  const shortcutLink = page.locator('.finance-links').getByRole('link', { name: '银行资金记录', exact: true })
  await expect(sidebarLink).toHaveAttribute('href', '/rmb-cash-events')
  await expect(shortcutLink).toHaveAttribute('href', '/rmb-cash-events')
  const financeNav = await page.locator('.sidebar nav').innerText()
  expect(financeNav).not.toContain('银行结汇与凭证')
  await page.screenshot({ path: path.join(evidenceDir, 'finance-dashboard-1440.png'), fullPage: true })

  await shortcutLink.click()
  await expect(page).toHaveURL(/\/rmb-cash-events$/)
  await expect(page.locator('.cash-events-page h2')).toHaveText('银行资金记录')
  expect(await page.locator('body').innerText()).not.toContain('银行结汇与凭证')
  await page.screenshot({ path: path.join(evidenceDir, 'bank-funds-1440.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect.poll(() => page.locator('.sidebar').evaluate(node => node.getBoundingClientRect().right), { timeout: 2_000 })
    .toBeLessThanOrEqual(0)
  const dimensions = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }))
  expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport)
  const sidebar = await page.locator('.sidebar').evaluate(node => ({ open: node.classList.contains('open'), right: node.getBoundingClientRect().right }))
  expect(sidebar.open).toBe(false)
  await page.screenshot({ path: path.join(evidenceDir, 'bank-funds-390.png'), fullPage: true })

  await page.evaluate(async () => {
    await fetch('/api/session/csrf/', { credentials: 'same-origin' })
    const csrf = document.cookie.split('; ').find(value => value.startsWith('csrftoken='))?.split('=')[1] || ''
    document.body.innerHTML = `<main><h1>历史资料只读预检验收</h1><form method="post" action="/api/import/history-preflight/?report=csv" enctype="multipart/form-data"><input type="hidden" name="csrfmiddlewaretoken" value="${csrf}"><label>选择合成历史工作簿<input type="file" name="file" accept=".xlsx" required></label><button type="submit">预检并下载 CSV</button></form></main>`
  })
  await page.locator('input[type="file"][name="file"]').setInputFiles(path.join(evidenceDir, 'synthetic-history-preflight.xlsx'))
  const responsePromise = page.waitForResponse(response =>
    new URL(response.url()).pathname === '/api/import/history-preflight/' && response.request().method() === 'POST')
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: '预检并下载 CSV', exact: true }).click()
  const [response, download] = await Promise.all([responsePromise, downloadPromise])
  expect(response.status()).toBe(200)
  expect(response.headers()['content-type']).toContain('text/csv')
  expect(response.headers()['content-disposition']).toContain('history-preflight.csv')
  expect(download.suggestedFilename()).toBe('history-preflight.csv')
  const csvPath = path.join(evidenceDir, download.suggestedFilename())
  await download.saveAs(csvPath)
  const csvBytes = await fs.readFile(csvPath)
  expect([...csvBytes.subarray(0, 3)]).toEqual([239, 187, 191])
  const csv = csvBytes.toString('utf8')
  expect(csv).toContain('工作表,原行号,原系统记录编号,来源关联组编号,结果,原因,关联记录,建议动作')
  expect(csv).toContain(fixture.source_order_id)
  expect(csv).toContain(fixture.source_group_id)
  expect(csv).toContain('警告')
  expect(csv).not.toContain('Synthetic historical address')
  await fs.writeFile(path.join(evidenceDir, 'history-preflight-browser.json'), JSON.stringify({
    browser: await page.evaluate(() => navigator.userAgent),
    identity: {
      username: 'codex', role: identity.role, authenticated: identity.authenticated,
      development_superadmin: identity.development_superadmin, rbac_enforcement: identity.rbac_enforcement,
    },
    financeNavigation: {
      sidebar: { label: '银行资金记录', path: '/rmb-cash-events', module: 'transactions', viewPermission: identity.permissions.transactions.view },
      dashboardShortcut: { label: '银行资金记录', path: '/rmb-cash-events' },
      routeTitle: '银行资金记录', sidebar, dimensions,
    },
    historyPreflight: {
      status: response.status(), contentType: response.headers()['content-type'],
      filename: download.suggestedFilename(), bytes: csvBytes.length,
      bom: [...csvBytes.subarray(0, 3)], sourceOrderId: fixture.source_order_id,
      containsUnknownPersonalFields: csv.includes('Synthetic historical address'),
    },
  }, null, 2), 'utf8')
})
