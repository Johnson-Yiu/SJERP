import { test, expect } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

const evidence = path.resolve('../docs/uat-evidence/iss-029-quote-recipient-snapshot')

test('real Django: recipient A/B, empty/invalid email, master changes, saved PI and XLSX', async ({ page }) => {
  const fixture = JSON.parse(await fs.readFile(path.join(evidence, 'fixture.json'), 'utf8'))
  const records = []
  const api = async (method, url, data) => {
    const response = await page.request[method](`/api${url}`, data === undefined ? {} : { data })
    const body = await response.json()
    records.push({ method, url, status: response.status(), body })
    expect(response.ok(), JSON.stringify(body)).toBeTruthy()
    return body
  }
  await page.setViewportSize({ width: 1440, height: 1100 })
  await page.goto(`/quotes?create=1&customer=${fixture.customer}`)
  const editor = page.getByRole('form', { name: '报价编辑器' })
  await expect(editor.getByLabel('买方邮箱', { exact: true })).toHaveValue('primary@example.com')
  await expect(editor.getByLabel('收件人', { exact: true })).toHaveValue('Original Primary')
  await expect(editor.getByLabel('买方地址', { exact: true })).toHaveValue('Original Berlin Address')
  await editor.locator('.sku-picker-options label').filter({ hasText: 'ISS029-SKU' }).locator('input[type=checkbox]').check()
  await editor.getByLabel('收件人', { exact: true }).fill('Version A Recipient')
  await editor.getByLabel('买方地址', { exact: true }).fill('Version A Berlin Address')
  await editor.getByLabel('买方电话', { exact: true }).fill('+49 222 A')
  await editor.getByLabel('买方邮箱', { exact: true }).fill('invalid-email')
  const rejected = page.waitForResponse(r => r.url().endsWith('/api/quotes/') && r.request().method() === 'POST')
  await editor.getByRole('button', { name: '保存报价', exact: true }).click()
  const invalidResponse = await rejected
  expect(invalidResponse.status()).toBe(400)
  records.push({ method: 'POST', url: '/quotes/', status: 400, body: await invalidResponse.json() })
  await expect(editor.getByLabel('买方邮箱', { exact: true })).toHaveValue('invalid-email')
  await editor.getByLabel('买方邮箱', { exact: true }).fill('version-a@example.com')
  const created = page.waitForResponse(r => r.url().endsWith('/api/quotes/') && r.request().method() === 'POST')
  await editor.getByRole('button', { name: '保存报价', exact: true }).click()
  const createdResponse = await created
  expect(createdResponse.status()).toBe(201)
  const a = await createdResponse.json()
  records.push({ method: 'POST', url: '/quotes/', status: 201, body: a })
  await expect(editor).toHaveCount(0)
  let master = await api('get', `/contacts/${fixture.contact}/`)
  expect(master.email).toBe('primary@example.com')

  await page.goto(`/quotes?detail=${a.id}`)
  await page.getByRole('button', { name: '标记已发送', exact: true }).click()
  await expect(page.locator('.detail-badge')).toHaveText('已发送')
  await page.getByRole('button', { name: '创建修订版', exact: true }).click()
  await expect(editor.getByLabel('买方邮箱', { exact: true })).toHaveValue('version-a@example.com')
  await expect(editor.getByLabel('买方电话', { exact: true })).toHaveValue('+49 222 A')
  await expect(editor.getByLabel('买方地址', { exact: true })).toHaveValue('Version A Berlin Address')
  await editor.getByLabel('收件人', { exact: true }).fill('Version B Recipient')
  await editor.getByLabel('买方邮箱', { exact: true }).fill('')
  await editor.getByLabel('买方电话', { exact: true }).fill('+49 333 B')
  await editor.getByLabel('买方地址', { exact: true }).fill('Version B Berlin Address')
  await editor.locator('.revision-summary textarea').fill('ISS029 收件人改为版本 B，邮箱留空')
  await editor.getByLabel('买方邮箱', { exact: true }).scrollIntoViewIfNeeded()
  await page.screenshot({ path: path.join(evidence, 'chrome-version-b-editor-1440.png') })
  const revised = page.waitForResponse(r => r.url().endsWith(`/api/quotes/${a.id}/revise/`))
  const downloadedB = page.waitForEvent('download')
  await editor.getByRole('button', { name: '保存并导出 Excel', exact: true }).click()
  const revisionResponse = await revised
  expect(revisionResponse.status()).toBe(201)
  const b = await revisionResponse.json()
  expect(b.buyer_email).toBe('')
  records.push({ method: 'POST', url: `/quotes/${a.id}/revise/`, status: 201, body: b })
  await (await downloadedB).saveAs(path.join(evidence, 'version-b-empty-email.xlsx'))
  await expect(editor).toHaveCount(0)

  // Changes are made only to this dedicated synthetic customer/contact.
  await api('patch', `/contacts/${fixture.contact}/`, { name: 'Changed Primary', email: 'changed-master@example.com', phone: '+49 999' })
  await api('patch', `/customers/${fixture.customer}/`, { address: 'Changed Current Master Address' })
  for (const [quote, recipient, email, address] of [[a, 'Version A Recipient', 'version-a@example.com', 'Version A Berlin Address'], [b, 'Version B Recipient', '', 'Version B Berlin Address']]) {
    const detail = await api('get', `/quotes/${quote.id}/`)
    const pi = await api('get', `/quotes/${quote.id}/pi-data/?buyer_email=unsaved@example.com`)
    expect(detail.recipient_name).toBe(recipient)
    expect(detail.buyer_email).toBe(email)
    expect(detail.buyer_address).toBe(address)
    expect(pi.buyer.name).toBe(recipient)
    expect(pi.buyer.email).toBe(email)
    await page.goto(`/quotes?detail=${quote.id}`)
    await page.getByRole('button', { name: '预览 PI', exact: true }).first().click()
    const preview = page.getByRole('dialog', { name: '报价单预览' })
    await expect(preview).toContainText('已保存报价预览')
    await expect(preview).toContainText(recipient)
    await expect(preview).toContainText(address)
    if (email) await expect(preview).toContainText(email)
    await expect(preview).not.toContainText('changed-master@example.com')
    await page.screenshot({ path: path.join(evidence, `chrome-version-${quote.id === a.id ? 'a' : 'b'}-saved-pi-1440.png`) })
    if (quote.id === b.id) {
      await page.setViewportSize({ width: 700, height: 1000 })
      await page.screenshot({ path: path.join(evidence, 'chrome-version-b-saved-pi-700.png') })
      await page.setViewportSize({ width: 1440, height: 1100 })
    }
    await preview.getByRole('button', { name: '关闭预览', exact: true }).click()
    const download = page.waitForEvent('download')
    await page.getByRole('button', { name: '导出 Excel', exact: true }).click()
    await (await download).saveAs(path.join(evidence, quote.id === a.id ? 'version-a.xlsx' : 'version-b-empty-email.xlsx'))
  }
  // Reopen the saved draft as the starting point of a revision; a dirty input
  // cannot alter the original PI or export endpoint.
  await page.goto(`/quotes?edit=${b.id}`)
  await expect(editor.getByLabel('买方邮箱', { exact: true })).toHaveValue('')
  await expect(editor.getByLabel('收件人', { exact: true })).toHaveValue('Version B Recipient')
  await editor.getByLabel('买方邮箱', { exact: true }).fill('unsaved@example.com')
  const savedPi = await api('get', `/quotes/${b.id}/pi-data/`)
  expect(savedPi.buyer.email).toBe('')
  const savedExport = await page.request.get(`/api/quotes/${b.id}/export/?buyer_email=unsaved@example.com`)
  expect(savedExport.status()).toBe(200)
  await fs.writeFile(path.join(evidence, 'version-b-with-unsaved-input.xlsx'), await savedExport.body())
  await fs.writeFile(path.join(evidence, 'api-evidence.json'), JSON.stringify({ database: fixture.database, a: a.id, b: b.id, records }, null, 2))
})
