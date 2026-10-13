import { test, expect } from '@playwright/test'
for (const route of ['receivables','payables']) {
  for (const width of [1440,1280,1024,640,390]) {
    test(`${route}: computed filter layout at ${width}px`, async ({page}) => {
      await page.setViewportSize({width,height:1000})
      await page.route('**/api/**', async request => {
        const operator = {development_superadmin:true, has_all_permissions:true, authenticated:true, name:'浏览器回归'}
        await request.fulfill({json: request.request().url().includes('current-operator') ? operator : []})
      })
      await page.goto(`/${route}?search=Supplier&status=settled&overdue=true&due_from=2026-10-01&due_to=2026-10-31`)
      const form = page.getByRole('form',{name:'收付款计划筛选'})
      await expect(form).toBeVisible()
      await expect(page.getByRole('button',{name:'查询',exact:true})).toBeEnabled()
      const layout = await form.evaluate(el=>{
        const bounds = el.getBoundingClientRect()
        const rect = e => {const r=e.getBoundingClientRect(); return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}}
        return {columns:getComputedStyle(el).gridTemplateColumns.split(' ').length, gap:getComputedStyle(el).gap, overflow:el.scrollWidth>el.clientWidth,bounds:rect(el),items:[...el.querySelectorAll('input,select,button')].map(rect)}
      })
      expect(layout.columns).toBe(width>1100?6:width>650?3:2)
      expect(layout.gap).toBe('10px'); expect(layout.overflow).toBe(false)
      for (const r of layout.items) {
        expect(r.width).toBeGreaterThan(10); expect(r.height).toBeGreaterThan(10)
        expect(r.x).toBeGreaterThanOrEqual(layout.bounds.x); expect(r.right).toBeLessThanOrEqual(layout.bounds.right)
        expect(r.x).toBeGreaterThanOrEqual(0); expect(r.right).toBeLessThanOrEqual(width)
      }
      for(let i=0;i<layout.items.length;i++) for(let j=i+1;j<layout.items.length;j++) {
        const a=layout.items[i], b=layout.items[j]
        expect(a.right<=b.x || b.right<=a.x || a.bottom<=b.y || b.bottom<=a.y).toBe(true)
      }
      await expect(page.getByRole('searchbox')).toHaveValue('Supplier')
      await expect(page.getByLabel('收付款计划状态')).toHaveValue('settled')
      await expect(page.getByLabel('仅看逾期')).toBeChecked()
      await expect(page.getByLabel('到期日从')).toHaveValue('2026-10-01')
      await expect(page.getByLabel('到期日至')).toHaveValue('2026-10-31')
      await page.reload(); await expect(page.getByRole('searchbox')).toHaveValue('Supplier')
      await page.getByRole('button',{name:'重置',exact:true}).click()
      await expect(page).toHaveURL(new RegExp(`/${route}\\?status=open$`))
    })
  }
}
