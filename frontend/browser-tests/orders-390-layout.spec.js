import path from 'node:path'
import { mkdir, writeFile } from 'node:fs/promises'
import { expect, test } from '@playwright/test'

const evidenceDir = process.env.R1_REPAIR_07_EVIDENCE_DIR
  ? path.resolve(process.env.R1_REPAIR_07_EVIDENCE_DIR)
  : path.resolve(process.cwd(), '..', 'docs', 'uat-evidence', 'r1-repair-07')
const phase = process.env.R1_REPAIR_07_PHASE || 'after'
const widths = [390, 700, 1024, 1440]

const customer = { id: 1, name: 'R1-REPAIR-07 窄屏订单客户有限公司' }
const rows = [
  { id: 1, order_no: 'SO-R1-390-001', customer: 1, customer_name: customer.name, order_date: '2026-10-28', expected_ship_date: '2026-11-03', status: 'confirmed', status_display: '已确认', items: [{ id: 1 }], currency: 'CNY', total_amount: '123456.00', paid_amount: '100.00', balance_amount: '123356.00' },
  { id: 2, order_no: 'SO-R1-390-002', customer: 1, customer_name: customer.name, order_date: '2026-10-27', expected_ship_date: '2026-11-04', status: 'production', status_display: '生产中', items: [{ id: 2 }, { id: 3 }], currency: 'USD', total_amount: '9876.50', paid_amount: '0.00', balance_amount: '9876.50' },
]

async function mockApi(page) {
  await page.route('**/api/**', route => {
    const pathName = new URL(route.request().url()).pathname
    if (pathName.includes('current-operator')) return route.fulfill({ json: { authenticated: true, development_superadmin: true, has_all_permissions: true } })
    if (pathName === '/api/orders/') return route.fulfill({ json: rows })
    if (pathName === '/api/customers/') return route.fulfill({ json: [customer] })
    return route.fulfill({ json: [] })
  })
}

async function collectMetrics(page) {
  return page.evaluate(() => {
    const toolbar = document.querySelector('.order-toolbar, .toolbar')
    const reset = document.querySelector('.filter-reset')
    const tableWrap = document.querySelector('.order-list-table')?.closest('.table-wrap')
    const table = document.querySelector('.order-list-table')
    const rect = element => {
      if (!element) return null
      const box = element.getBoundingClientRect()
      return { x: box.x, right: box.right, width: box.width, height: box.height }
    }
    return {
      viewport: innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      bodyWidth: document.body.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      toolbar: rect(toolbar),
      toolbarOverflowX: toolbar ? getComputedStyle(toolbar).overflowX : null,
      reset: { ...rect(reset), whiteSpace: reset ? getComputedStyle(reset).whiteSpace : null, scrollWidth: reset?.scrollWidth || null, clientWidth: reset?.clientWidth || null },
      tableWrap: { ...rect(tableWrap), clientWidth: tableWrap?.clientWidth || null, scrollWidth: tableWrap?.scrollWidth || null, overflowX: tableWrap ? getComputedStyle(tableWrap).overflowX : null, scrollLeft: tableWrap?.scrollLeft || 0 },
      table: { ...rect(table), width: table?.getBoundingClientRect().width || null, scrollWidth: table?.scrollWidth || null },
      headers: [...document.querySelectorAll('.order-list-table thead th')].map(element => ({ text: element.textContent.trim(), ...rect(element) })),
    }
  })
}

for (const width of widths) {
  test(`R1-REPAIR-07 orders layout ${phase} ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await mockApi(page)
    await page.goto('/orders?search=SO-R1')
    await expect(page.locator('.order-list-table tbody tr')).toHaveCount(2)

    const metrics = await collectMetrics(page)
    await mkdir(evidenceDir, { recursive: true })
    await writeFile(path.join(evidenceDir, `${phase}-dom-${width}.json`), JSON.stringify(metrics, null, 2))
    await page.screenshot({ path: path.join(evidenceDir, `${phase}-${width}.png`), fullPage: true })

    if (phase === 'after') {
      expect(metrics.documentWidth, JSON.stringify(metrics)).toBeLessThanOrEqual(width)
      expect(metrics.bodyWidth, JSON.stringify(metrics)).toBeLessThanOrEqual(width)
      expect(metrics.reset.whiteSpace).toBe('nowrap')
      expect(metrics.reset.right, JSON.stringify(metrics)).toBeLessThanOrEqual(width + 1)
      expect(metrics.tableWrap.overflowX).toMatch(/auto|scroll/)
      if (width <= 1024) {
        expect(metrics.tableWrap.scrollWidth).toBeGreaterThan(metrics.tableWrap.clientWidth)
        expect(metrics.table.scrollWidth).toBeGreaterThan(metrics.tableWrap.clientWidth)

        const beforeScroll = await page.locator('.order-list-table').evaluate(table => table.closest('.table-wrap').scrollLeft)
        await page.locator('.order-list-table').evaluate(table => { const wrap = table.closest('.table-wrap'); wrap.scrollLeft = wrap.scrollWidth })
        const afterScroll = await page.locator('.order-list-table').evaluate(table => ({ scrollLeft: table.closest('.table-wrap').scrollLeft, max: table.closest('.table-wrap').scrollWidth - table.closest('.table-wrap').clientWidth }))
        expect(beforeScroll).toBe(0)
        expect(afterScroll.scrollLeft).toBe(afterScroll.max)
        expect(afterScroll.max).toBeGreaterThan(0)
        await page.locator('.table-wrap').screenshot({ path: path.join(evidenceDir, `${phase}-${width}-table-right.png`) })
      }
    }

    await page.evaluate((value) => {
      document.body.dataset.r1Repair07Metrics = JSON.stringify(value)
    }, metrics)
  })
}
