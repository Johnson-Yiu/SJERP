import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome' })
test('extended replacement: two accounts, facts, unknown and explicit empty', async ({ browser, baseURL }) => {
  test.setTimeout(240000)
  const root = path.resolve('../docs/uat-evidence/party-version-closeout-20261105/browser-acceptance-20261106')
  const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'extended')
  fs.mkdirSync(evidence, { recursive: true })
  const run = (name, args = []) => {
    const x = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(root, name), ...args], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' })
    expect(x.status, x.stderr).toBe(0)
    return JSON.parse(x.stdout.trim().split('\n').at(-1))
  }
  const f = run('seed_extended.py'), api = process.env.ISOLATED_PLAYWRIGHT_API_BASE_URL
  const snapshot = () => run('snapshot_extended.py', [String(f.order), String(f.purchase)])
  const before = snapshot()
  fs.writeFileSync(path.join(evidence, 'source-before.json'), JSON.stringify(before, null, 2))
  expect(before.transactions).toHaveLength(2); expect(before.receipts).toHaveLength(1); expect(before.shipments).toHaveLength(1)
  const a = await browser.newContext({ viewport: { width: 1440, height: 900 } }), b = await browser.newContext({ viewport: { width: 390, height: 844 } })
  const logs = []
  async function login(c, user) {
    const p = await c.newPage(); await p.goto(`${api}/admin/login/`); await p.locator('[name=username]').fill(user); await p.locator('[name=password]').fill('synthetic-only-password'); await p.locator('input[type=submit]').click(); await expect(p).not.toHaveURL(/admin\/login/); await p.close()
  }
  try {
    await login(a, f.first_username); await login(b, f.second_username)
    for (const kind of ['order', 'purchase']) {
      const isOrder = kind === 'order', route = isOrder ? 'orders' : 'purchase-orders', id = f[kind], side = isOrder ? 'buyer' : 'seller', target = isOrder ? f.replacement_customer : f.replacement_supplier
      const maker = await a.newPage(), reviewer = await b.newPage(), url = new URL(`/${route}?detail=${id}`, baseURL).toString()
      async function open(page) { await page.goto(url); await page.getByRole('button', { name: '查看主体版本与更正' }).click(); await expect(page.locator('.document-party-versions')).toContainText('当前有效主体资料') }
      await open(maker); let panel = maker.locator('.document-party-versions')
      await panel.getByRole('button', { name: '申请更换法律主体' }).click()
      let form = panel.locator('.replacement-form')
      await form.getByLabel(isOrder ? '目标客户' : '目标供应商').selectOption(String(target))
      const basic = form.locator(':scope > label').filter({ hasText: /^拟议/ })
      for (let i = 0; i < await basic.count(); i++) { const btn = basic.nth(i).getByRole('button', { name: '确认留空' }); if (await btn.count()) await btn.click() }
      const extended = form.locator('fieldset').filter({ has: maker.getByText(isOrder ? '买方扩展资料' : '卖方扩展资料', { exact: true }) })
      await extended.getByLabel('账单地址').fill(`Synthetic new ${kind} billing`)
      await extended.locator('label').filter({ hasText: /^税号/ }).getByRole('button', { name: '确认留空' }).click()
      await form.getByLabel('已核对，未填写的扩展资料均为未知').check()
      await form.getByLabel('原因', { exact: true }).fill('Synthetic replacement reason'); await form.getByLabel('依据', { exact: true }).fill('Synthetic evidence')
      await extended.scrollIntoViewIfNeeded(); await maker.screenshot({ path: path.join(evidence, `${kind}-entry-desktop.png`) })
      const proposed = maker.waitForResponse(r => r.url().endsWith('/party-change/') && r.request().method() === 'POST')
      await form.getByRole('button', { name: '提交替换申请' }).click(); const proposalResponse = await proposed
      if (!proposalResponse.ok()) console.log('proposal error', kind, await proposalResponse.text())
      expect(proposalResponse.status()).toBe(201)
      const proposal = await proposalResponse.json()
      expect(proposal.proposed_snapshot.address).toBe('')
      expect(proposal.proposed_snapshot.contact).toBe('')
      expect(proposal.proposed_snapshot.party_details[side].tax_id).toBe('')
      expect(proposal.proposed_snapshot.party_details[side].phone).toBeNull()
      await open(reviewer); const review = reviewer.locator('.document-party-versions'), diff = review.locator('.party-details-changes')
      async function assertBasicDifferences(p) {
        const grid = p.locator('.party-row .party-grid').first()
        const value = label => grid.locator('dt').filter({ hasText: new RegExp(`^${label}$`) }).locator('xpath=following-sibling::dd[1]')
        await expect(value('地址')).toHaveText(isOrder ? 'Synthetic old buyer → 已留空' : 'Synthetic old seller → 已留空')
        if (isOrder) await expect(value('国家 / 地区')).toHaveText('Germany → 已留空')
        else await expect(value('联系人')).toHaveText('未记录 → 已留空')
      }
      await assertBasicDifferences(reviewer)
      await expect(diff).toContainText('Synthetic original billing'); await expect(diff).toContainText(`Synthetic new ${kind} billing`); await expect(diff).toContainText('未知 → 已留空')
      await diff.scrollIntoViewIfNeeded(); await reviewer.screenshot({ path: path.join(evidence, `${kind}-review-390.png`) })
      await maker.reload(); await maker.getByRole('button', { name: '查看主体版本与更正' }).click(); await assertBasicDifferences(maker); await maker.locator('.party-details-changes').scrollIntoViewIfNeeded(); await maker.screenshot({ path: path.join(evidence, `${kind}-review-desktop.png`) })
      await review.getByLabel('审批意见 / 处理原因').fill('Independent synthetic approval')
      const approved = reviewer.waitForResponse(r => r.url().includes('/approve/') && r.request().method() === 'POST')
      await review.getByRole('button', { name: '批准主体替换' }).click(); expect((await approved).status()).toBe(200)
      await review.getByRole('button', { name: '填写关联新单' }).click(); form = review.locator('.replacement-form')
      await form.getByLabel('单据日期').fill('2026-11-05'); await form.getByLabel('币种').fill('USD'); await form.getByLabel('汇率').fill('7.2')
      if (isOrder) { await form.getByLabel('运费').fill('0'); await form.getByLabel('折扣').fill('0'); await form.getByLabel('尾货策略').selectOption('SAME_CARTON') } else await form.getByLabel('付款计划').selectOption('none')
      await form.getByLabel('SKU').selectOption(String(f.sku)); await form.getByLabel('数量').fill('3'); await form.getByLabel('单价').fill('5'); await form.getByLabel('已核对全部新单资料和条款').check()
      const created = reviewer.waitForResponse(r => r.url().includes('/create-replacement/') && r.request().method() === 'POST')
      await form.getByRole('button', { name: '创建关联草稿' }).click(); const response = await created
      if (!response.ok()) console.log('creation error', kind, await response.text())
      expect(response.status()).toBe(200)
      const result = await response.json(), resultId = result[isOrder ? 'result_order_id' : 'result_purchase_order_id']
      const detailsResponse = await reviewer.request.get(`${api}/api/${route}/${resultId}/party-details/`); expect(detailsResponse.status()).toBe(200)
      const details = await detailsResponse.json(); console.log('RESULT DETAILS', kind, JSON.stringify(details))
      fs.writeFileSync(path.join(evidence, `${kind}-result-details.json`), JSON.stringify(details, null, 2))
      const party = details.details || details
      expect(party[side].tax_id).toBe(''); expect(party[side].phone).toBeNull(); expect(party[side].billing_address).toBe(`Synthetic new ${kind} billing`)
      logs.push({ kind, proposal: proposalResponse.status(), approval: 200, created: response.status(), resultId, proposalSnapshot: proposal.proposed_snapshot })
      await maker.close(); await reviewer.close()
    }
    const after = snapshot(); fs.writeFileSync(path.join(evidence, 'source-after.json'), JSON.stringify(after, null, 2)); expect(after).toEqual(before)
    fs.writeFileSync(path.join(evidence, 'http-results.json'), JSON.stringify(logs, null, 2))
  } finally { await a.close(); await b.close() }
})
