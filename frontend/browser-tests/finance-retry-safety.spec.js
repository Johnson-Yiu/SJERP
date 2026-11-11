import { test, expect } from '@playwright/test'
// MOCKED_TEST: transport gating here; real committed-response loss has separate DB evidence.
test('finance pending submission and ambiguous retry preserve identity and guard departure', async ({ page }) => {
  let release
  const pending = new Promise(resolve => { release = resolve })
  const writes = []
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/session/current-operator/') return route.fulfill({ json: { name: 'Developer', development_superadmin: true, has_all_permissions: true } })
    if (path === '/api/transactions/' && route.request().method() === 'POST') {
      writes.push(route.request().postDataJSON())
      if (writes.length === 1) { await pending; return route.abort('failed') }
      return route.fulfill({ status: 400, json: { transaction_no: ['已存在'] } })
    }
    return route.fulfill({ json: [] })
  })
  await page.goto('/transactions')
  await page.getByRole('button', { name: '新增记账', exact: true }).click()
  const form = page.getByRole('dialog', { name: '新增记账', exact: true })
  await form.getByLabel('原币金额', { exact: true }).fill('12.34')
  await form.getByRole('button', { name: '保存', exact: true }).click()
  await expect(form.getByRole('button', { name: '保存中…' })).toBeDisabled()
  await expect(form.getByRole('button', { name: '取消', exact: true })).toBeDisabled()
  await expect(form.getByRole('button', { name: '关闭', exact: true })).toBeDisabled()
  await page.locator('.mask').click({ position: { x: 2, y: 2 } })
  await page.getByRole('link', { name: '订单管理', exact: true }).dispatchEvent('click')
  await expect(page).toHaveURL('/orders')
  await page.evaluate(() => history.back())
  await expect(page).toHaveURL(/transactions$/)
  await expect(form).toBeVisible()
  expect(writes).toHaveLength(1)
  release()
  await expect(form.getByRole('alert')).toContainText('记账结果尚未确认')
  await form.getByRole('button', { name: '按原编号重试', exact: true }).click()
  await expect(form).toContainText('编号重复不代表本次保存成功')
  expect(writes).toHaveLength(2)
  expect(writes[0]).toEqual(writes[1])
  await form.getByRole('button', { name: '取消', exact: true }).click()
  const warning = page.getByRole('dialog', { name: '记账结果尚未确认', exact: true })
  await expect(warning).toContainText(writes[0].transaction_no)
  await warning.getByRole('button', { name: '返回核对', exact: true }).click()
  await expect(form.getByLabel('原币金额', { exact: true })).toHaveValue('12.34')
  await form.getByRole('button', { name: '取消', exact: true }).click()
  await expect(warning).toContainText(writes[0].transaction_no)
  await warning.getByRole('button', { name: '返回核对', exact: true }).click()
  const dialogSeen = new Promise(resolve => page.once('dialog', async dialog => { expect(dialog.type()).toBe('beforeunload'); await dialog.dismiss(); resolve() }))
  await page.reload({ timeout: 3000 }).catch(() => {})
  await dialogSeen
  await expect(form).toBeVisible()
})


