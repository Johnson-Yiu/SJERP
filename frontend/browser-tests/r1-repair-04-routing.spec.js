import { expect, test } from '@playwright/test'
import { installRepair04Diagnostics } from './r1-repair-04-diagnostics.js'

test('R1-REPAIR-04 font interception is registered before navigation', async ({ page }) => {
  const diagnostics = await installRepair04Diagnostics(page, 'font-route-registration-probe')

  expect(diagnostics.fontRoutesRegistered).toBe(true)
  expect(diagnostics.fontInterceptionCount).toBe(0)

  await page.goto('data:text/html,<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter&display=swap"><main>font route probe</main>')

  await expect.poll(() => diagnostics.fontInterceptionCount).toBeGreaterThan(0)
})
