import { test, expect } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

// Uses the existing isolated runner and actual Django/Vite services, no API mocks.
for (const [name, viewport] of [['desktop', { width: 1440, height: 900 }], ['narrow', { width: 390, height: 844 }]]) {
  test(`highest role reflects API effective permissions and is read-only (${name})`, async ({ page }) => {
    await page.setViewportSize(viewport)
    const response = await page.request.get('/api/organization/overview/')
    expect(response.status()).toBe(200)
    const data = await response.json()
    const role = data.roles.find(item => item.code === 'superadmin')
    expect(role?.has_all_permissions).toBe(true)
    expect(role.effective_permissions).toHaveLength(data.modules.length)
    for (const row of role.effective_permissions) {
      for (const key of ['can_view', 'can_create', 'can_update', 'can_delete', 'can_export', 'can_import']) expect(row[key]).toBe(true)
    }
    const denied = await page.request.post(`/api/access-roles/${role.id}/permission-matrix/`, { data: { permissions: [] } })
    expect(denied.status()).toBe(400)
    await page.goto('/organization')
    const matrix = page.getByRole('region', { name: '角色权限矩阵，可横向及纵向滚动' })
    await expect(matrix).toBeVisible()
    await expect(page.getByText('此最高角色不可修改', { exact: false })).toBeVisible()
    const boxes = matrix.locator('tbody input[type=checkbox]')
    await expect(boxes).toHaveCount(data.modules.length * 6)
    const state = await boxes.evaluateAll(elements => elements.map(element => ({ checked: element.checked, disabled: element.disabled })))
    expect(state).toHaveLength(data.modules.length * 6)
    expect(state.filter(item => !item.checked || !item.disabled)).toEqual([])
    await fs.mkdir(process.env.EVIDENCE_DIR, { recursive: true })
    await page.screenshot({ path: path.join(process.env.EVIDENCE_DIR, `highest-role-${name}.png`), fullPage: true })
    console.log(JSON.stringify({ viewport: name, modules: data.modules.length, checkedDisabled: await boxes.count(), matrixWrite: denied.status() }))
  })
}
