import { test, expect } from '@playwright/test'
import { mockApi } from './reporting-fixtures'
import path from 'node:path'

const evidenceDir = path.resolve(process.cwd(), '../docs/uat-evidence/iss-041-detail-drill')

for (const width of [1440, 700]) {
  test(`ISS-041-B raw detail evidence at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 })
    await mockApi(page)
    await page.goto('/reports')
    if (width <= 700) await page.waitForTimeout(350)
    await page.getByRole('combobox', { name: '统计维度', exact: true }).selectOption('country')
    await page.getByRole('combobox', { name: '第二统计维度（可选）', exact: true }).selectOption('customer')
    await page.getByRole('button', { name: '查询报表', exact: true }).click()
    await page.getByRole('button', { name: '查看构成明细', exact: true }).first().click()
    await expect(page.locator('.report-detail-panel')).toContainText('SO-DETAIL-1')
    await expect(page.locator('.report-detail-panel')).toContainText('明细记录 3 条')
    await page.screenshot({ path: path.join(evidenceDir, `reports-detail-${width}.png`), fullPage: true })
  })
}
