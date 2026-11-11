import { expect } from '@playwright/test'

export function syntheticVoucherPdf() {
  const content = 'BT /F1 14 Tf 50 780 Td (SYNTHETIC FINANCE VOUCHER - NOT REAL MONEY) Tj ET\n'
  const objects = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>', '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>', `<< /Length ${Buffer.byteLength(content)} >>\nstream\n${content}endstream`, '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
  let text = '%PDF-1.4\n', offsets = [0]
  for (const [i, object] of objects.entries()) { offsets.push(Buffer.byteLength(text)); text += `${i + 1} 0 obj\n${object}\nendobj\n` }
  const xref = Buffer.byteLength(text)
  text += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n` + offsets.slice(1).map(n => `${String(n).padStart(10, '0')} 00000 n \n`).join('')
  text += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`
  return Buffer.from(text)
}
const file = () => ({ name: 'synthetic-bank-voucher.pdf', mimeType: 'application/pdf', buffer: syntheticVoucherPdf() })

export async function uploadBankVoucherViaApi(page, sources) {
  const response = await page.request.post('/api/rmb-cash-events/voucher-upload/', { multipart: { file: file(), sources: JSON.stringify(sources) } })
  const result = await response.json()
  expect(response.status(), JSON.stringify(result)).toBe(201)
  return result.id
}

export async function uploadBankVoucherThroughUi(page) {
  await page.getByLabel('银行凭证文件', { exact: true }).setInputFiles(file())
  const response = page.waitForResponse(r => r.url().endsWith('/api/rmb-cash-events/voucher-upload/') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '上传并校验凭证', exact: true }).click()
  expect((await response).status()).toBe(201)
  await expect(page.getByText(/凭证已上传：/)).toBeVisible()
}
