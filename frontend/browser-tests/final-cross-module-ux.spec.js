import { expect, test } from '@playwright/test'
for (const width of [1440, 1280, 1024]) for (const type of ['quotes', 'orders']) {
  test(`R0-F9 ${type} customer column and filters ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 })
    const customer = { id: 1, name: '照明工程采购长名称客户有限公司' }
    const row = { id: 1, quote_no: 'F9-Q001', order_no: 'F9-O001', customer: 1, customer_name: customer.name, quote_date: '2026-10-16', order_date: '2026-10-16', updated_at: '2026-10-16T10:00:00Z', status: type === 'quotes' ? 'sent' : 'confirmed', status_display: type === 'quotes' ? '已发送' : '已确认', items: [], currency: 'USD', total_amount: '20.00', root_quote: null, parent_quote: null, revision_no: 0 }
    await page.route('**/api/**', route => {
      const path = new URL(route.request().url()).pathname
      const data = path.includes('current-operator') ? {development_superadmin:true,has_all_permissions:true,name:'R0F9 fixture'} : path === `/api/${type}/` ? [row] : path === '/api/customers/' ? [customer] : []
      return route.fulfill({json:data})
    })
    await page.goto(`/${type}`)
    await expect(page.getByRole('cell', {name:customer.name,exact:true})).toBeVisible()
    if (type === 'quotes') {
      const width = await page.getByRole('cell', {name:customer.name,exact:true}).evaluate(el => el.getBoundingClientRect().width)
      expect(width).toBeGreaterThanOrEqual(200)
    } else {
      for (const name of ['按订单状态筛选','按订单待办筛选']) {
        const style = await page.getByRole('combobox',{name,exact:true}).evaluate(el => ({height:el.getBoundingClientRect().height,radius:getComputedStyle(el).borderRadius}))
        expect(style.height).toBeGreaterThanOrEqual(42)
        expect(style.radius).toBe('8px')
      }
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  })
}
