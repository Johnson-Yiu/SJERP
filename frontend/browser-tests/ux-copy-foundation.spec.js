import fs from 'node:fs'
import path from 'node:path'
import { expect, test } from '@playwright/test'
import { mockApi } from './reporting-fixtures.js'

const evidenceDir = path.resolve(process.env.UX_COPY_EVIDENCE_DIR || '../docs/uat-evidence/r1-ux-copy-foundation/screenshots')
const pages = [
  ['home', '/', '经营概览'],
  ['customers', '/customers', '客户管理'],
  ['contacts', '/contacts', '联系人'],
  ['follow-ups', '/follow-ups', '跟进记录'],
  ['products', '/products', '产品管理'],
  ['skus', '/skus', 'SKU 管理'],
  ['categories', '/categories', '产品分类'],
]

fs.mkdirSync(evidenceDir, { recursive: true })

for (const [name, route, title] of pages) {
  for (const viewport of [{ name: 'desktop', width: 1440, height: 960 }, { name: 'narrow', width: 390, height: 844 }]) {
    test(`${name} copy renders in Chrome at ${viewport.width}px`, async ({ page }) => {
      await mockApi(page, { empty: true })
      await page.setViewportSize({ width: viewport.width, height: viewport.height })
      await page.goto(route, { waitUntil: 'domcontentloaded' })
      await expect(page.locator('.page-identity h1')).toHaveText(title)
      await expect(page.locator('.content')).toBeVisible()
      const workspace = page.getByRole('tabpanel', { name: title, exact: true })
      await expect(workspace).toBeVisible()
      await expect(workspace.locator('.spinner, [aria-busy="true"]')).toHaveCount(0)

      const pageWidth = await page.evaluate(() => document.documentElement.scrollWidth)
      expect(pageWidth).toBeLessThanOrEqual(viewport.width + 1)
      await page.screenshot({
        path: path.join(evidenceDir, `${name}-${viewport.name}.png`),
        fullPage: true,
      })
    })
  }
}
