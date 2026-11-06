import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { chromium } from '@playwright/test'

const origin = process.env.HISTORY_UAT_ORIGIN, dir = process.env.HISTORY_UAT_SESSION_DIR, evidence = process.env.HISTORY_UAT_EVIDENCE_DIR
if (!origin || !dir || !evidence) throw new Error('Isolated UAT environment is required')
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(origin) || !path.basename(dir).startsWith('sunjack-history-operational-closeout-')) throw new Error('Only a marked loopback synthetic UAT environment is allowed')
const { sessionid, csrftoken } = JSON.parse(await readFile(path.join(dir, 'session.json'), 'utf8'))
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
await context.addCookies([{ name: 'sessionid', value: sessionid, url: origin, httpOnly: true, sameSite: 'Lax' }, { name: 'csrftoken', value: csrftoken, url: origin, sameSite: 'Lax' }])
const page = await context.newPage()
try {
  await page.goto(`${origin}/history-takeover`, { waitUntil: 'networkidle' })
  const identity = await page.evaluate(async () => (await fetch('/api/import/history-takeovers/1/')).json())
  if (identity.source_file_name !== 'synthetic-history-uAT.xlsx' || identity.groups?.[0]?.source_system !== 'Synthetic browser UAT') throw new Error('The API is not the marked synthetic workbook')
  async function post(url, payload, key) {
    const result = await page.evaluate(async ({ url, payload, key }) => {
      const csrf = decodeURIComponent(document.cookie.split('; ').find(v => v.startsWith('csrftoken='))?.slice(10) || '')
      const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, ...(key ? { 'Idempotency-Key': key } : {}) }, body: JSON.stringify(payload) })
      return { status: response.status, replay: response.headers.get('Idempotent-Replay'), body: await response.json() }
    }, { url, payload, key })
    if (result.status < 200 || result.status >= 300) throw new Error(`${url}: ${JSON.stringify(result)}`)
    return result
  }
  const endpoint = '/api/import/history-takeovers/1/groups/1/operational-status/'
  const before = (await post(endpoint, {})).body
  const sale = before.links.find(link => link.record_type === '销售订单')
  const purchase = before.links.find(link => link.record_type === '采购订单')
  if (!sale || !purchase || before.overall.state !== 'connected') throw new Error('Missing reviewed and confirmed continuation')
  const location = { warehouse_type: '自有仓', warehouse: 'SYN-WH-01', lot_reference: 'LOT-HT-01' }
  const receiptData = { purchase_item: purchase.line_links[0].continuation_item_id, receipt_date: '2025-01-03', quantity: '3', unit_cost: '3', ...location }
  const shipmentData = { shipment_date: '2025-01-04', items: [{ order_item: sale.line_links[0].continuation_item_id, quantity: '6', ...location }] }
  const receipt = await post(`/api/purchase-orders/${purchase.continuation_id}/receive/`, receiptData, 'synthetic-history-receipt-uat-1')
  const receiptReplay = await post(`/api/purchase-orders/${purchase.continuation_id}/receive/`, receiptData, 'synthetic-history-receipt-uat-1')
  const shipment = await post(`/api/orders/${sale.continuation_id}/ship/`, shipmentData, 'synthetic-history-shipment-uat-1')
  const shipmentReplay = await post(`/api/orders/${sale.continuation_id}/ship/`, shipmentData, 'synthetic-history-shipment-uat-1')
  if (receipt.body.id !== receiptReplay.body.id || shipment.body.id !== shipmentReplay.body.id || receiptReplay.replay !== 'true' || shipmentReplay.replay !== 'true') throw new Error('Fulfillment replay was not idempotent')
  for (const [link, amount] of [[sale, '20'], [purchase, '4']]) {
    const plan = link.plans[0]
    if (Number(plan.settled_amount) === 0) await post(`/api/payment-plans/${plan.id}/settle/`, { amount, currency: 'USD', exchange_rate: '1', transaction_date: '2025-01-05' })
    else if (Number(plan.settled_amount) !== Number(amount)) throw new Error('Unexpected pre-existing synthetic settlement')
  }
  const after = (await post(endpoint, {})).body
  const saleAfter = after.links.find(link => link.record_type === '销售订单')
  const purchaseAfter = after.links.find(link => link.record_type === '采购订单')
  if (Number(saleAfter.outstanding_balance) !== 40 || Number(purchaseAfter.outstanding_balance) !== 6) throw new Error('Synthetic remaining balances disagree')
  const summary = { chrome: browser.version(), database: 'isolated synthetic SQLite', before: before.links, receipt: receipt.body, receiptReplay: receiptReplay.replay, shipment: shipment.body, shipmentReplay: shipmentReplay.replay, after: after.links }
  await writeFile(path.join(evidence, 'chrome-fulfillment.json'), JSON.stringify(summary, null, 2) + '\n')
  await page.reload({ waitUntil: 'networkidle' })
  await page.getByText('未结余额与剩余业务', { exact: true }).click()
  await page.getByRole('button', { name: '加载合同与未结来源' }).click()
  await page.locator('.takeover-execution').scrollIntoViewIfNeeded()
  await page.screenshot({ path: path.join(evidence, 'history-operational-settled-1440.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 }); await page.waitForTimeout(700)
  await page.screenshot({ path: path.join(evidence, 'history-operational-settled-390.png'), fullPage: true })
  console.log(JSON.stringify(summary, null, 2))
} finally { await browser.close() }
