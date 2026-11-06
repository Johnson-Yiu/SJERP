import { expect, test } from '@playwright/test'
const active = page => page.locator('.workspace-pane[aria-hidden="false"]')

function gate() {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}
async function setup(page, entity) {
  const customer = { id: 1, name: 'Saving lifecycle buyer' }
  const row = entity === 'contacts'
    ? { id: 7, customer: 1, customer_name: customer.name, name: 'Original contact', is_primary: false }
    : { id: 7, customer: 1, customer_name: customer.name, subject: 'Original follow-up', content: 'Original content', type: 'email', followed_at: '2026-10-15T09:00:00+08:00', next_follow_up_mode: 'keep', attachments: [] }
  const state = { writes: [], rows: [row], gate: gate(), reads: 0 }
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    const method = route.request().method()
    if (path === '/api/session/current-operator/') return route.fulfill({ json: { name: 'Isolated developer', authenticated: true, development_superadmin: true, has_all_permissions: true } })
    if (path === '/api/customers/') return route.fulfill({ json: [customer] })
    if (path === '/api/follow-ups/methods/') return route.fulfill({ json: [{ value: 'email', label: '邮件' }] })
    if (path === `/api/${entity}/` && method === 'GET') { state.reads++; return route.fulfill({ json: state.rows }) }
    if (path === `/api/${entity}/7/` && method === 'GET') return route.fulfill({ json: row })
    if (path.startsWith(`/api/${entity}/`) && ['POST', 'PUT'].includes(method)) {
      const data = route.request().postDataJSON()
      state.writes.push({ method, data })
      const result = await state.gate.promise
      if (result === 'fail') return route.fulfill({ status: 503, json: { detail: '可控保存失败，请重试' } })
      const saved = { ...row, ...data }
      state.rows = [saved]
      return route.fulfill({ json: saved })
    }
    return route.fulfill({ json: [] })
  })
  await page.goto('/customers', { waitUntil: 'domcontentloaded' })
  await page.getByRole('link', { name: entity === 'contacts' ? '联系人' : '跟进记录', exact: true }).click()
  await expect(active(page).locator('.page-head .btn-primary')).toBeVisible()
  return state
}
async function editFields(page, entity) {
  const id = await active(page).getAttribute('data-workspace')
  const dialog = page.locator(`[data-workspace="${id}"] form.crm-editor`)
  await dialog.getByLabel(entity === 'contacts' ? '所属客户' : '客户', { exact: true }).selectOption('1')
  if (entity === 'contacts') await dialog.getByLabel('姓名', { exact: true }).fill('Pending browser contact')
  else {
    await dialog.getByLabel('主题', { exact: true }).fill('Pending browser follow-up')
    await dialog.getByLabel('沟通记录', { exact: true }).fill('Keep this input on failure')
    await dialog.getByLabel('跟进方式', { exact: true }).fill('邮件')
    await dialog.getByLabel('跟进方式', { exact: true }).press('Enter')
  }
  return dialog
}
async function tryLeave(page, entity, dialog) {
  const url = page.url()
  await expect(dialog.getByRole('button', { name: '保存中…' })).toBeDisabled()
  await expect(dialog.getByRole('button', { name: '取消', exact: true })).toBeDisabled()
  const close = dialog.getByRole('button', { name: entity === 'contacts' ? '关闭联系人表单' : '关闭跟进表单' })
  await expect(close).toBeDisabled()
  await close.click({ force: true })
  await page.locator('.modal-backdrop').click({ position: { x: 2, y: 2 } })
  await expect(dialog).toBeVisible()
  // A sidebar task switch retains the pending editor; browser Back returns to it.
  await page.getByRole('link', { name: '客户管理', exact: true }).dispatchEvent('click')
  await expect(page).toHaveURL(/\/customers$/)
  await expect(dialog).toHaveCount(1)
  await expect(dialog).toBeHidden()
  await page.goBack()
  await expect(page).toHaveURL(url)
  await expect(dialog).toBeVisible()
  await expect(page.getByRole('heading', { name: '未保存修改', exact: true })).toHaveCount(0)
}

for (const entity of ['contacts', 'follow-ups']) {
  for (const width of [1440, 1280, 1024]) test(`${entity} pending POST resists close and navigation at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 })
    const state = await setup(page, entity)
    await page.getByRole('button', { name: entity === 'contacts' ? '新建联系人' : '新建跟进记录', exact: true }).click()
    const dialog = await editFields(page, entity)
    const reads = state.reads
    await dialog.locator('.modal-foot .btn-primary').dblclick()
    await expect.poll(() => state.writes.length).toBe(1)
    await tryLeave(page, entity, dialog)
    expect(state.writes).toHaveLength(1)
    state.gate.resolve('success')
    await expect(dialog).toHaveCount(0)
    await expect.poll(() => state.reads).toBe(reads + 1)
    await expect(active(page).locator('.data-table tbody')).toContainText(entity === 'contacts' ? 'Pending browser contact' : 'Pending browser follow-up')
    await page.getByRole('link', { name: '客户管理', exact: true }).click()
    await expect(page).toHaveURL(/\/customers$/)
  })
  test(`${entity} pending PUT failure preserves fields and quick retry sends one request`, async ({ page }) => {
    const state = await setup(page, entity)
    await page.getByRole('button', { name: entity === 'contacts' ? '编辑联系人' : '编辑跟进记录', exact: true }).click()
    const dialog = await editFields(page, entity)
    await dialog.locator('.modal-foot .btn-primary').dblclick()
    await expect.poll(() => state.writes.length).toBe(1)
    await tryLeave(page, entity, dialog)
    state.gate.resolve('fail')
    await expect(page.locator('.toast.error')).toHaveText('服务器暂时不可用，请稍后重试。')
    await expect(dialog.getByLabel(entity === 'contacts' ? '姓名' : '主题', { exact: true })).toHaveValue(entity === 'contacts' ? 'Pending browser contact' : 'Pending browser follow-up')
    state.gate = gate()
    await dialog.locator('.modal-foot .btn-primary').dblclick()
    await expect.poll(() => state.writes.length).toBe(2)
    expect(state.writes[0]).toEqual(state.writes[1])
    state.gate.resolve('success')
    await expect(dialog).toHaveCount(0)
  })
}
