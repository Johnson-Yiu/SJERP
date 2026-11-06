import { chromium } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

export default async function setupCodexTestSession() {
  if (process.env.ISOLATED_CODEX_TEST_SUPERADMIN !== '1') return
  const baseURL = process.env.ISOLATED_PLAYWRIGHT_BASE_URL
  const username = process.env.CODEX_TEST_USERNAME
  const password = process.env.CODEX_TEST_PASSWORD
  const statePath = path.join(process.env.ISOLATED_TEST_ROOT, 'codex-auth.json')
  if (!baseURL || username !== 'codex' || !password) throw new Error('The isolated codex test session is not configured.')

  const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || undefined })
  try {
    const context = await browser.newContext()
    const page = await context.newPage()
    await page.goto(`${baseURL}/login`)
    await page.getByLabel('账号').fill(username)
    await page.getByLabel('密码').fill(password)
    const loginResponsePromise = page.waitForResponse(response =>
      new URL(response.url()).pathname === '/api/session/login/' && response.request().method() === 'POST')
    await page.getByRole('button', { name: '登录', exact: true }).click()
    const loginResponse = await loginResponsePromise
    if (loginResponse.status() !== 200) throw new Error(`Isolated codex login returned HTTP ${loginResponse.status()}.`)

    const identityResponse = await context.request.get(`${baseURL}/api/session/current-operator/`)
    const identity = await identityResponse.json()
    if (identityResponse.status() !== 200 || identity.name !== 'codex' || identity.role !== '超级管理员'
      || identity.authenticated !== true || identity.development_superadmin !== false
      || identity.rbac_enforcement !== false || identity.has_all_permissions !== true) {
      throw new Error('The isolated browser session did not resolve to the authenticated codex superuser profile.')
    }
    await fs.writeFile(path.join(process.env.ISOLATED_TEST_ROOT, 'codex-identity.json'), JSON.stringify({
      username: 'codex', role: identity.role, authenticated: identity.authenticated,
      development_superadmin: identity.development_superadmin, rbac_enforcement: identity.rbac_enforcement,
      has_all_permissions: identity.has_all_permissions,
    }, null, 2), 'utf8')
    const evidenceRoot = process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT
    if (evidenceRoot) {
      const identityEvidencePath = path.join(evidenceRoot, 'browser', 'codex-identity.json')
      await fs.mkdir(path.dirname(identityEvidencePath), { recursive: true })
      await fs.writeFile(identityEvidencePath, JSON.stringify({
        username: 'codex', role: identity.role, authenticated: identity.authenticated,
        development_superadmin: identity.development_superadmin, rbac_enforcement: identity.rbac_enforcement,
        has_all_permissions: identity.has_all_permissions,
      }, null, 2), 'utf8')
    }
    await context.storageState({ path: statePath })
    await context.close()
    console.log('Isolated Chrome session: authenticated codex superuser; dev identity off; RBAC unchanged/off for this test database.')
  } finally {
    await browser.close()
  }
}
