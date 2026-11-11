import { chromium, expect } from '@playwright/test'
import path from 'node:path'

export async function partyContext(browser, viewport, actor) {
  if (process.env.SALES_PARTY_NATIVE_ZOOM !== '1.25') {
    return browser.newContext({ storageState: { cookies: [], origins: [] }, viewport })
  }
  const context = await chromium.launchPersistentContext(
    path.join(process.env.ISOLATED_TEST_ROOT, 'sales-party-' + actor),
    { channel: 'chrome', viewport },
  )
  try {
    const settings = context.pages()[0]
    await settings.goto('chrome://settings/appearance', { waitUntil: 'domcontentloaded' })
    await settings.locator('settings-appearance-page select').filter({
      has: settings.locator('option[value="1.25"]'),
    }).selectOption('1.25', { timeout: 75000 })
    return context
  } catch (error) {
    await context.close()
    throw error
  }
}

export async function verifyPartyZoom(page) {
  if (process.env.SALES_PARTY_NATIVE_ZOOM === '1.25') {
    await expect.poll(() => page.evaluate(() => window.devicePixelRatio)).toBe(1.25)
  }
}
