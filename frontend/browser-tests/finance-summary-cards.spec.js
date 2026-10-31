import { test, expect } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const evidenceRoot = process.env.R1_UX_FINANCE_SUMMARY_EVIDENCE_DIR
  ? resolve(process.env.R1_UX_FINANCE_SUMMARY_EVIDENCE_DIR)
  : resolve(dirname(fileURLToPath(import.meta.url)), '../../docs/uat-evidence/r1-ux-finance-summary-20261029/screenshots')
const fullAmount = '¥ 20,000,000,000.00'

const operator = {
  authenticated: true,
  development_superadmin: true,
  has_all_permissions: true,
  name: '财务汇总卡片回归',
}

const transactionRows = [{
  id: 1,
  transaction_date: '2026-10-29',
  transaction_no: 'TX-UAT-001',
  direction: 'income',
  direction_display: '收入',
  status: 'confirmed',
  status_display: '已确认',
  kind: 'customer_receipt',
  category: '销售回款',
  amount: '20000000000',
  rmb_amount: '20000000000',
  currency: 'CNY',
  customer_name: '汇总卡片测试客户',
}]

const planRows = direction => [{
  id: direction === 'receivable' ? 11 : 12,
  direction,
  due_date: '2026-11-30',
  contract_no: direction === 'receivable' ? 'SO-UAT-001' : 'PO-UAT-001',
  counterparty_name: direction === 'receivable' ? '汇总卡片测试客户' : '汇总卡片测试供应商',
  currency: 'CNY',
  planned_amount: '20000000000',
  settled_amount: '0',
  remaining_amount: '20000000000',
  remaining_rmb: '20000000000',
  status: 'open',
  is_overdue: false,
}]

async function mockFinanceApi(page) {
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const path = url.pathname.replace(/^\/api/, '')
    if (path === '/session/current-operator/' || path === '/session/current-operator') {
      await route.fulfill({ json: operator })
      return
    }
    if (path === '/transactions/' || path === '/transactions') {
      await route.fulfill({ json: { results: transactionRows, next: null } })
      return
    }
    if (path === '/payment-plans/' || path === '/payment-plans') {
      await route.fulfill({ json: { results: planRows(url.searchParams.get('direction')), next: null } })
      return
    }
    await route.fulfill({ json: { results: [], next: null } })
  })
}

async function assertCards(page, expectedAmount, screenshotName) {
  const cards = page.locator('section.summary-cards')
  await expect(cards).toBeVisible()
  const amount = cards.locator('strong').filter({ hasText: expectedAmount }).first()
  if (expectedAmount) await expect(amount).toHaveText(expectedAmount)
  const layout = await cards.evaluate(section => {
    const shell = section.parentElement
    const values = [...section.querySelectorAll('article strong')]
    const rect = element => {
      const bounds = element.getBoundingClientRect()
      return { width: bounds.width, height: bounds.height, scrollWidth: element.scrollWidth, clientWidth: element.clientWidth, text: element.textContent }
    }
    return {
      shellWidth: shell.getBoundingClientRect().width,
      columns: getComputedStyle(section).gridTemplateColumns.trim().split(/\s+/).length,
      values: values.map(rect),
      styles: values.map(element => {
        const style = getComputedStyle(element)
        return { whiteSpace: style.whiteSpace, textOverflow: style.textOverflow, overflowWrap: style.overflowWrap }
      }),
    }
  })
  expect(layout.values.length).toBeGreaterThan(0)
  for (const value of layout.values) {
    expect(value.text).not.toContain('…')
    expect(value.scrollWidth).toBeLessThanOrEqual(value.clientWidth + 1)
  }
  for (const style of layout.styles) {
    expect(style.whiteSpace).not.toBe('nowrap')
    expect(style.textOverflow).not.toBe('ellipsis')
  }
  mkdirSync(evidenceRoot, { recursive: true })
  await page.screenshot({ path: resolve(evidenceRoot, screenshotName), fullPage: true })
  return layout
}

for (const width of [1440, 1024, 390]) {
  for (const [route, label, expectedAmount] of [
    ['transactions', '财务流水', fullAmount],
    ['receivables', '应收计划', fullAmount],
    ['payables', '应付计划', fullAmount],
  ]) {
    test(`${label}在${width}px完整显示汇总金额`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1000 })
      await mockFinanceApi(page)
      await page.goto(`/${route}`)
      const layout = await assertCards(page, expectedAmount, `${route}-${width}.png`)
      const expectedColumns = width === 1440 ? 4 : width === 1024 ? 2 : 1
      expect(layout.columns).toBe(expectedColumns)
      if (width === 1024) expect(layout.shellWidth).toBeLessThan(760)
    })
  }
}

for (const route of ['/customers', '/suppliers', '/purchase-orders']) {
  test(`其他汇总卡片页面保持可用：${route}`, async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 1000 })
    await mockFinanceApi(page)
    await page.goto(route)
    const cards = page.locator('section.summary-cards')
    await expect(cards).toBeVisible()
    const diagnostics = await cards.evaluate(section => [...section.querySelectorAll('article strong')].map(element => ({
      text: element.textContent,
      scrollWidth: element.scrollWidth,
      clientWidth: element.clientWidth,
    })))
    expect(diagnostics.length).toBeGreaterThan(0)
    expect(diagnostics.every(value => value.scrollWidth <= value.clientWidth + 1)).toBe(true)
  })
}
