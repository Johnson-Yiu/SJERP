import { createHash } from 'node:crypto'
import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { syntheticVoucherPdf } from './helpers/bank-voucher.js'

import { expect, test } from '@playwright/test'

const evidenceDir = process.env.SALES_ORDER_IMPORT_EVIDENCE_DIR
if (!evidenceDir) throw new Error('SALES_ORDER_IMPORT_EVIDENCE_DIR must be set by the isolated test runner.')

test.use({ acceptDownloads: true, viewport: { width: 1600, height: 1000 } })

test('authenticated codex superuser imports XLSX and downloads the actual error CSV', async ({ page }) => {
  test.setTimeout(90000)
  const identityResponse = await page.request.get('/api/session/current-operator/')
  expect(identityResponse.status()).toBe(200)
  const identity = await identityResponse.json()
  expect(identity).toMatchObject({
    name: 'codex',
    role: '超级管理员',
    authenticated: true,
    development_superadmin: false,
    rbac_enforcement: false,
    has_all_permissions: true,
  })

  const fixture = JSON.parse(await readFile(path.join(evidenceDir, 'fixture.json'), 'utf8'))
  const workbookPath = path.join(evidenceDir, fixture.workbook)
  await page.goto('/import')
  await page.getByRole('tab', { name: '销售订单', exact: true }).click()

  const templateDownloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: /下载销售订单 XLSX 模板/ }).click()
  const templateDownload = await templateDownloadPromise
  expect(templateDownload.suggestedFilename()).toBe('sales-order-import-template.xlsx')
  const templatePath = path.join(evidenceDir, templateDownload.suggestedFilename())
  await templateDownload.saveAs(templatePath)
  const templateBytes = await readFile(templatePath)
  expect(templateBytes.subarray(0, 2).toString('hex')).toBe('504b')

  await page.locator('input[type="file"][accept*=".xlsx"]').setInputFiles(workbookPath)
  await page.getByRole('button', { name: '预览并校验', exact: true }).click()
  await page.getByText('共 3 条明细、2 张订单：1 张可导入，1 张待修正', { exact: true }).waitFor()
  await page.getByText(`找不到 SKU：${fixture.invalid_sku}。`, { exact: true }).waitFor()

  let savedResult, resolveSaved, releaseResponse
  const saved = new Promise(resolve => { resolveSaved = resolve })
  const released = new Promise(resolve => { releaseResponse = resolve })
  await page.route('**/api/import/orders/execute/', async route => {
    const token = route.request().postData().match(/name="preview_token"\r\n\r\n([^\r\n]+)/)?.[1]
    expect(token).toBeTruthy()
    const response = await page.request.post(route.request().url(), { headers: { 'X-CSRFToken': route.request().headers()['x-csrftoken'] }, multipart: { file: { name:path.basename(workbookPath), mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer:await readFile(workbookPath) }, preview_token:token } })
    savedResult = await response.json(); await writeFile(path.join(evidenceDir, 'lost-response-result.json'), JSON.stringify({status:response.status(),body:savedResult},null,2)); resolveSaved()
    await released; await route.abort('failed')
  })
  await page.getByRole('button', { name: '确认导入 1 张草稿', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toContainText('导入不会确认订单、占库存、生成应收计划或登记发货。')
  await page.getByRole('button', {name:'关闭 数据导入',exact:true}).press('Enter')
  await expect(dialog).toBeVisible()
  await page.getByTestId('dialog-confirm').click()
  await saved
  await page.getByRole('button', {name:'关闭 数据导入',exact:true}).press('Enter')
  await expect(page.getByRole('tab', {name:'数据导入',exact:true})).toBeVisible()
  releaseResponse()
  await page.getByRole('alert').filter({hasText:'提交结果待核对'}).waitFor()
  await page.unroute('**/api/import/orders/execute/')
  await page.reload()
  await page.getByRole('tab', {name:'销售订单',exact:true}).click()
  await page.locator('input[type="file"][accept*=".xlsx"]').setInputFiles(workbookPath)
  await expect(page.getByRole('alert').filter({ hasText: '已恢复待核对导入批次' })).toBeVisible()
  const executeResponsePromise = page.waitForResponse(response => new URL(response.url()).pathname === '/api/import/orders/execute/' && response.request().method() === 'POST')
  await page.getByRole('button', {name:'确认导入 1 张草稿',exact:true}).click()
  await page.getByTestId('dialog-confirm').click()
  const executeResponse = await executeResponsePromise
  expect(executeResponse.status()).toBe(200)
  const result = await executeResponse.json()
  expect(result.batch_id).toBe(savedResult.batch_id)
  expect(result).toMatchObject({ created_orders: 1, failed_orders: 1, total_orders: 2 })
  expect(result.orders).toHaveLength(1)
  expect(result.orders[0]).toMatchObject({ source_order_no: fixture.valid_source_order, status: 'draft', line_count: 2 })
  await page.getByText('已创建 1 张草稿，1 张未创建', { exact: true }).waitFor()

  const errorDownloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载错误清单 CSV', exact: true }).click()
  const errorDownload = await errorDownloadPromise
  expect(errorDownload.suggestedFilename()).toBe('sales-order-import-errors.csv')
  const csvPath = path.join(evidenceDir, errorDownload.suggestedFilename())
  await errorDownload.saveAs(csvPath)
  const csvBytes = await readFile(csvPath)
  const csvText = csvBytes.toString('utf8')
  expect(csvText.startsWith('\ufeff')).toBe(true)
  expect(csvText).toContain(fixture.invalid_source_order)
  expect(csvText).toContain(fixture.invalid_sku)
  expect(csvText).toContain('找不到 SKU')

  const resultLookup = await page.request.get(`/api/import/orders/results/${result.batch_id}/`)
  expect(resultLookup.status()).toBe(200)
  expect(await resultLookup.json()).toEqual(result)

  const desktopScreenshot = path.join(evidenceDir, 'sales-order-import-1600.png')
  await page.screenshot({ path: desktopScreenshot, fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect.poll(() => page.locator('.sidebar').evaluate(element => element.getBoundingClientRect().right)).toBeLessThanOrEqual(1)
  const mobileScreenshot = path.join(evidenceDir, 'sales-order-import-390.png')
  await page.screenshot({ path: mobileScreenshot, fullPage: true })
  const dimensions = await page.evaluate(() => ({
    viewportWidth: document.documentElement.clientWidth,
    documentWidth: document.documentElement.scrollWidth,
  }))
  expect(dimensions.documentWidth).toBeLessThanOrEqual(dimensions.viewportWidth)

  await writeFile(path.join(evidenceDir, 'browser-results.json'), JSON.stringify({
    identity: {
      username: identity.name,
      role: identity.role,
      authenticated: identity.authenticated,
      development_superadmin: identity.development_superadmin,
      rbac_enforcement: identity.rbac_enforcement,
    },
    template: { filename: templateDownload.suggestedFilename(), bytes: templateBytes.length },
    import: {
      rows: result.total_rows,
      orders: result.total_orders,
      created: result.created_orders,
      failed: result.failed_orders,
      order_no: result.orders[0].order_no,
      status: result.orders[0].status,
    },
    csv: {
      filename: errorDownload.suggestedFilename(),
      bytes: csvBytes.length,
      sha256: createHash('sha256').update(csvBytes).digest('hex'),
      hasUtf8Bom: csvBytes.subarray(0, 3).equals(Buffer.from([0xef, 0xbb, 0xbf])),
      includesInvalidSourceAndSku: csvText.includes(fixture.invalid_source_order) && csvText.includes(fixture.invalid_sku),
    },
    desktopScreenshot: path.basename(desktopScreenshot),
    mobileScreenshot: path.basename(mobileScreenshot),
    mobileDimensions: dimensions,
  }, null, 2), 'utf8')
})


test('history page downloads the current workbook CSV without business writes', async ({page}) => {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../docs/uat-evidence/history-preflight-web-fix-01')
  const workbook = path.join(root, 'workbook-B-duplicate.xlsx')
  const workbookA = path.join(root, 'workbook-A-valid.xlsx')
  const snapshot = async () => {
    const result = {}
    for (const endpoint of ['orders','transactions','payment-plans','inventory-movements','import/history-takeovers']) {
      const response=await page.request.get(`/api/${endpoint}/`); expect(response.status()).toBe(200); result[endpoint]=await response.json()
    }
    return result
  }
  const before=await snapshot()
  await page.goto('/history-preflight')
  let releaseA, signalA
  const heldA=new Promise(resolve=>{signalA=resolve}), releasedA=new Promise(resolve=>{releaseA=resolve})
  await page.route('**/api/import/history-preflight/',async route=>{
    if (!route.request().postData().includes('workbook-A-valid.xlsx')) return route.continue()
    const response=await page.request.post(route.request().url(),{headers:{'X-CSRFToken':route.request().headers()['x-csrftoken']},multipart:{file:{name:path.basename(workbookA),mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:await readFile(workbookA)}}})
    signalA(); await releasedA; await route.fulfill({response})
  })
  await page.locator('input[type="file"]').setInputFiles(workbookA)
  await page.getByRole('button',{name:'开始预检',exact:true}).click(); await heldA
  await page.locator('input[type="file"]').setInputFiles(workbook)
  await page.getByRole('button',{name:'开始预检',exact:true}).click()
  await expect(page.locator('.preflight-summary')).toContainText('workbook-B-duplicate.xlsx')
  await expect(page.locator('.history-preflight-page')).toContainText('FIXB-SO-1')
  const lateA=page.waitForResponse(response=>response.request().postData()?.includes('workbook-A-valid.xlsx')&&new URL(response.url()).pathname==='/api/import/history-preflight/')
  releaseA(); await lateA
  await expect(page.locator('.preflight-summary')).toContainText('workbook-B-duplicate.xlsx')
  await page.unroute('**/api/import/history-preflight/')
  const downloadPromise=page.waitForEvent('download')
  await page.getByRole('button',{name:/下载 CSV/}).click()
  const download=await downloadPromise, output=path.join(evidenceDir,'integrated-history-preflight.csv')
  await download.saveAs(output)
  const bytes=await readFile(output), csv=bytes.toString('utf8')
  expect(csv).toContain('FIXB-SO-1'); expect(csv).not.toContain('FIXA-SO-1')
  expect(bytes.subarray(0,3).equals(Buffer.from([0xef,0xbb,0xbf]))).toBe(true)
  let staleDownloads=0, releaseCsv, signalCsv
  page.on('download',()=>{staleDownloads++})
  const heldCsv=new Promise(resolve=>{signalCsv=resolve}), releasedCsv=new Promise(resolve=>{releaseCsv=resolve})
  await page.route('**/api/import/history-preflight/?report=csv',async route=>{
    const response=await page.request.post(route.request().url(),{headers:{'X-CSRFToken':route.request().headers()['x-csrftoken']},multipart:{file:{name:path.basename(workbook),mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:await readFile(workbook)}}})
    signalCsv(); await releasedCsv; await route.fulfill({response})
  })
  await page.getByRole('button',{name:/下载 CSV/}).click(); await heldCsv
  await page.locator('input[type="file"]').setInputFiles(workbookA)
  const oldCsv=page.waitForResponse(response=>response.url().includes('report=csv'))
  releaseCsv(); await oldCsv
  await page.getByRole('button',{name:'开始预检',exact:true}).click()
  await expect(page.locator('.preflight-summary')).toContainText('workbook-A-valid.xlsx')
  expect(staleDownloads).toBe(0)
  expect(await snapshot()).toEqual(before)
  await writeFile(path.join(evidenceDir,'history-readonly-snapshot.json'),JSON.stringify(before,null,2))
  await page.screenshot({path:path.join(evidenceDir,'integrated-history-preflight.png'),fullPage:true})
  for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
    await page.setViewportSize({ width, height })
    if (width === 390) await expect.poll(() => page.locator('.sidebar').evaluate(element => element.getBoundingClientRect().right)).toBeLessThanOrEqual(1)
    await expect(page.getByRole('button', { name: /下载 CSV/ })).toBeVisible()
    await page.screenshot({ path: path.join(evidenceDir, `history-preflight-${width}.png`), fullPage: true })
  }
})

test('finance overview presents the noncash reduction and downloads its CSV', async ({ page }) => {
  const loaded = page.waitForResponse(response => new URL(response.url()).pathname === '/api/finance-dashboard/' && response.ok())
  await page.goto('/finance')
  const dashboard = await (await loaded).json()
  const metric = page.locator('article').filter({ hasText: '核准非现金抵减' }).first()
  await expect(metric).toBeVisible()
  const drill = page.waitForResponse(response => response.url().includes('/finance-dashboard/details/') && response.ok())
  await metric.getByRole('button', { name: '查看构成明细' }).click()
  expect(Number((await (await drill).json()).total_amount)).toBe(Number(dashboard.metrics.receivable_reduction_rmb))
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: '导出 CSV', exact: true }).click()
  const download = await downloadPromise
  const output = path.join(evidenceDir, 'finance-overview.csv')
  await download.saveAs(output)
  const reductionRow = (await readFile(output, 'utf8')).split(/\r?\n/).find(row => row.startsWith('核准非现金抵减,'))
  expect(reductionRow).toBeDefined()
  expect(Number(reductionRow.split(',')[1])).toBe(Number(dashboard.metrics.receivable_reduction_rmb))
  for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
    await page.setViewportSize({ width, height })
    if (width === 390) await expect.poll(() => page.locator('.sidebar').evaluate(element => element.getBoundingClientRect().right)).toBeLessThanOrEqual(1)
    await expect(metric).toBeVisible()
    await page.screenshot({ path: path.join(evidenceDir, `finance-overview-${width}.png`), fullPage: true })
  }
})


async function fillReceiptFee(form, proof, amount, handling) {
  await form.getByRole('button', { name: '添加扣减明细' }).click()
  const line = form.locator('.adjustment-card').last()
  await line.getByLabel('性质').selectOption('bank_fee')
  await line.getByLabel('金额（USD）', { exact: true }).fill(String(amount))
  await line.getByLabel('处理方式').selectOption(handling === 'unknown' ? 'pending' : handling)
  await line.getByLabel('原因', { exact: true }).fill('Synthetic bank fee responsibility checked')
  await line.getByLabel('依据凭证').setInputFiles(proof)
  await line.getByRole('button', { name: '上传凭证' }).click()
  await expect(line).toContainText(proof.name)
}

test('inventory draft guards the form and replays the same write after a lost response', async ({ page }) => {
  test.setTimeout(60000)
  await page.goto('/finance')
  await page.getByRole('link', { name: '库存流水', exact: true }).click()
  await page.getByRole('button', { name: '新建库存调整', exact: true }).click()
  const form = page.getByRole('dialog', { name: '新建手工库存流水' })
  await form.locator('label').filter({ hasText: 'UAT-IMP-SKU-002' }).getByRole('checkbox').check()
  const quantity = form.getByRole('spinbutton', { name: 'UAT-IMP-SKU-002 数量' })
  await quantity.fill('2')
  await quantity.hover()
  await page.mouse.wheel(0, 180)
  await expect(quantity).toHaveValue('2')
  await quantity.press('ArrowUp')
  await expect(quantity).toHaveValue('2.01')
  await form.getByRole('button', { name: '取消', exact: true }).click()
  await page.getByRole('button', { name: '继续编辑', exact: true }).click()
  await expect(quantity).toHaveValue('2.01')
  const movementTab = page.getByRole('tab', { name: /^库存流水/, selected: true })
  const financeTab = page.getByRole('tab', { name: '财务概览', exact: true })
  const draftPanel = await movementTab.getAttribute('aria-controls')
  await movementTab.press('Home')
  await expect(financeTab).toHaveAttribute('aria-selected', 'true')
  await expect(form).toBeHidden()
  await financeTab.press('End')
  await expect(movementTab).toHaveAttribute('aria-controls', draftPanel)
  await expect(quantity).toBeVisible()
  await expect(quantity).toHaveValue('2.01')
  const attempts = []
  await page.route('**/api/inventory-movements/batch/', async route => {
    attempts.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData() })
    if (attempts.length === 1) {
      const written = await route.fetch()
      expect(written.status()).toBe(201)
      await route.abort()
    } else await route.continue()
  })
  const save = form.getByRole('button', { name: '保存 1 条流水', exact: true })
  await save.click()
  await expect(form.getByRole('alert')).toContainText('保存结果尚未确认')
  const replay = page.waitForResponse(response => response.url().endsWith('/inventory-movements/batch/') && response.ok())
  await save.click()
  expect((await replay).headers()['idempotent-replay']).toBe('true')
  expect(attempts[0].key).toBeTruthy()
  expect(attempts[1]).toEqual(attempts[0])
  await expect(form).toBeHidden()
})

test('finance receipt separates cash fee credit refund capacity and inline settlement', async ({page}) => {
  test.setTimeout(90000)
  const proof={name:'synthetic-review.pdf',mimeType:'application/pdf',buffer:syntheticVoucherPdf()}
  await page.goto('/transactions')
  await page.getByRole('button',{name:'新增记账',exact:true}).click()
  const form=page.getByRole('dialog',{name:'新增记账',exact:true})
  await form.getByLabel(/^类型/).selectOption('customer_receipt')
  await form.getByPlaceholder('客户或订单号').fill('SYN-FIN-COMPANY')
  await form.getByRole('button',{name:/SYN-FIN-COMPANY/}).click()
  await form.getByLabel('银行实际到账原币金额',{exact:true}).fill('980')
  await form.getByLabel('客户实际汇款金额（USD）',{exact:true}).fill('1000')
  await fillReceiptFee(form, proof, 20, 'company')
  await page.mouse.click(350,150)
  await expect(form.getByLabel('银行实际到账原币金额',{exact:true})).toHaveValue('980.00')
  await form.getByRole('button',{name:'登记收汇记录',exact:true}).click()
  await form.getByRole('button',{name:'保存收款并继续',exact:true}).click()
  await expect(form).toContainText('收款已保存')
  const inline=form.locator('.inline-cash-entry')
  await expect(inline).toContainText('980.00')
  await inline.getByLabel('扣费前兑换额（CNY）',{exact:true}).fill('6958')
  await inline.getByRole('combobox',{name:'手续费',exact:true}).selectOption('included')
  await inline.getByLabel('手续费（CNY）',{exact:true}).fill('30')
  await inline.getByRole('combobox',{name:'来源账户',exact:true}).selectOption('SYNTH_FX')
  await inline.getByRole('combobox',{name:'人民币账户',exact:true}).selectOption('SYNTH_CNY')
  await inline.getByLabel('本次兑换金额', { exact: true }).fill('980')
  await inline.locator('.allocation-table input[type="checkbox"]').check()
  await inline.getByLabel('银行参考号',{exact:true}).fill('SYN-INTEGRATED-FX-01')
  await inline.getByLabel('核对说明',{exact:true}).fill('Synthetic bank receipt and source amounts checked')
  await inline.getByLabel('银行凭证文件',{exact:true}).setInputFiles(proof)
  await inline.getByRole('button',{name:'上传并校验凭证',exact:true}).click()
  await expect(inline).toContainText('凭证已上传')
  await inline.getByRole('button',{name:'预览结汇信息',exact:true}).click()
  await expect(inline).toContainText('银行净额 CNY 6,928.00')
  await inline.getByRole('button',{name:'登记待确认结汇',exact:true}).click()
  await inline.getByRole('checkbox', { name: /我已核对银行凭证和来源分配/ }).check()
  await inline.getByRole('button',{name:'确认银行凭证',exact:true}).click()
  await expect(inline).toContainText('已确认')
  const cash=await page.request.get('/api/actual-rmb-cash/'); expect(cash.status()).toBe(200)
  const cashData=await cash.json(); expect(cashData.totals.inflow).toBe('6928.00')
  await page.screenshot({path:path.join(evidenceDir,'finance-inline-confirmed.png'),fullPage:true})
  const orders=(await (await page.request.get('/api/orders/?search=SYN-FIN-COMPANY')).json()).results
  expect(Number(orders[0].paid_amount)).toBe(980)
  const plans=(await (await page.request.get('/api/payment-plans/')).json()).results
  const plan=plans.find(row=>row.order===orders[0].id); expect(Number(plan.remaining_amount)).toBe(0)
  await writeFile(path.join(evidenceDir,'finance-inline-result.json'),JSON.stringify({cash:cashData,order:orders[0],plan},null,2))
})


test('finance fee scenarios refuse excess refunds and reverse writeoffs without cash', async ({page}) => {
  test.setTimeout(90000)
  await page.goto('/transactions')
  const proof={name:'synthetic-review.pdf',mimeType:'application/pdf',buffer:syntheticVoucherPdf()}
  async function receipt(suffix, responsibility, amount='980', remittance='1000') {
    await page.getByRole('button',{name:'新增记账',exact:true}).click()
    const form=page.getByRole('dialog',{name:'新增记账',exact:true})
    await form.getByLabel(/^类型/).selectOption('customer_receipt')
    await form.getByPlaceholder('客户或订单号').fill('SYN-FIN-'+suffix)
    await form.getByRole('button',{name:new RegExp('SYN-FIN-'+suffix)}).click()
    await form.getByLabel('银行实际到账原币金额',{exact:true}).fill(amount)
    await form.getByLabel('客户实际汇款金额（USD）',{exact:true}).fill(remittance)
    if (responsibility) {
      await fillReceiptFee(form, proof, Number(remittance) - Number(amount), responsibility)
    }
    const responsePromise=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/transactions/'&&response.request().method()==='POST')
    await form.getByRole('button',{name:'保存',exact:true}).click()
    const response=await responsePromise; expect(response.status()).toBe(201)
    await expect(form).not.toBeVisible(); return response.json()
  }
  await receipt('CUSTOMER','customer'); await receipt('UNKNOWN','unknown'); const refundable = await receipt('REFUND','company')
  let plans=(await (await page.request.get('/api/payment-plans/')).json()).results
  for (const suffix of ['CUSTOMER','UNKNOWN']) expect(Number(plans.find(row=>row.contract_no==='SYN-FIN-'+suffix).remaining_amount)).toBe(20)
  await page.getByRole('row').filter({ hasText: refundable.transaction_no }).getByRole('button', { name: '详情', exact: true }).click()
  await page.getByRole('button', { name: '从本笔登记退款' }).click()
  const form=page.getByRole('dialog',{name:'登记退款',exact:true})
  const refundOrder = form.getByLabel('退款对应订单')
  await refundOrder.selectOption({ label: await refundOrder.locator('option').filter({ hasText: 'SYN-FIN-REFUND' }).innerText() })
  await form.getByLabel('实际退款金额（USD）',{exact:true}).fill('981')
  await form.getByLabel('退款依据').fill('Synthetic refund above remaining cash')
  await form.getByLabel('实际退款凭证').setInputFiles(proof)
  await form.getByRole('button', { name: '上传凭证' }).click()
  await expect(form).toContainText('凭证已上传')
  const refusalPromise=page.waitForResponse(response=>new URL(response.url()).pathname.endsWith('/refund-cash/')&&response.request().method()==='POST')
  await form.getByRole('button',{name:'确认登记',exact:true}).click()
  const refused=await refusalPromise; expect(refused.status()).toBe(400)
  await expect(form.locator('.error')).toContainText('退款')
  await page.screenshot({path:path.join(evidenceDir,'finance-refund-refused.png'),fullPage:true})
  await form.getByRole('button',{name:'关闭退款',exact:true}).click(); await page.getByTestId('dialog-confirm').click()
  await page.getByRole('button', { name: '关闭详情', exact: true }).click()
  const source=await receipt('WRITEOFF',null,'80','80')
  const before=(await (await page.request.get('/api/transactions/')).json()).count
  await page.getByRole('row').filter({hasText:source.transaction_no}).getByRole('button',{name:'详情',exact:true}).click()
  await page.getByRole('button',{name:'登记授权抹零',exact:true}).click()
  const writeoff=page.getByRole('dialog',{name:'登记授权抹零',exact:true})
  await writeoff.getByRole('combobox').selectOption({label:await writeoff.locator('option').nth(1).innerText()})
  await writeoff.getByLabel('抹零金额（USD）',{exact:true}).fill('10')
  await writeoff.getByLabel('授权原因',{exact:true}).fill('Synthetic authorized rounding acceptance')
  await writeoff.getByRole('button',{name:'确认并登记',exact:true}).click()
  await expect(writeoff).not.toBeVisible()
  await page.getByRole('button',{name:'更正抹零',exact:true}).click()
  const correction=page.getByRole('dialog',{name:'更正授权抹零',exact:true})
  await correction.getByLabel('更正金额（USD）',{exact:true}).fill('10')
  await correction.getByLabel('更正原因',{exact:true}).fill('Synthetic correction restores receivable')
  await page.mouse.click(350,150); await expect(correction.getByLabel('更正金额（USD）',{exact:true})).toHaveValue('10')
  await correction.getByRole('button',{name:'追加更正',exact:true}).click()
  await expect(correction).not.toBeVisible()
  plans=(await (await page.request.get('/api/payment-plans/')).json()).results
  const restored=plans.find(row=>row.contract_no==='SYN-FIN-WRITEOFF')
  expect(Number(restored.remaining_amount)).toBe(10); expect(restored.status).toBe('open')
  expect((await (await page.request.get('/api/transactions/')).json()).count).toBe(before)
  await page.screenshot({path:path.join(evidenceDir,'finance-writeoff-corrected.png'),fullPage:true})
  await writeFile(path.join(evidenceDir,'finance-correction-result.json'),JSON.stringify({refundStatus:refused.status(),restored,transactionsUnchanged:true},null,2))
})

test('codex logout clears the workspaces and returns to sign-in', async ({ page }) => {
  await page.goto('/finance')
  await expect(page.locator('.workspace-pane')).toBeVisible()
  const logout = page.waitForResponse(response => response.url().endsWith('/api/session/logout/') && response.ok())
  await page.getByRole('button', { name: '退出登录', exact: true }).click()
  await logout
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.locator('.workspace-pane')).toHaveCount(0)
  expect((await (await page.request.get('/api/session/current-operator/')).json()).authenticated).toBe(false)
})
