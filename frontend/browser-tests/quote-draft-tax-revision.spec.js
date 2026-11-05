import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
test.use({ channel: 'chrome' })
function seed() {
  const script=path.resolve('../docs/uat-evidence/party-version-closeout-20261105/seed_browser.py')
  const run=spawnSync(process.env.ISOLATED_TEST_PYTHON,[script],{cwd:path.resolve('../backend'),env:process.env,encoding:'utf8'})
  expect(run.status,run.stderr).toBe(0)
  return JSON.parse(run.stdout.trim().split('\n').at(-1))
}
test('draft tax revision is editable and saves a new version',async({page})=>{
  const fixture=seed()
  await page.goto(`/quotes?detail=${fixture.id}`)
  await page.getByRole('dialog',{name:'报价工作台'}).getByRole('button',{name:'创建修订版'}).click()
  const tax=page.locator('#quote-buyer-tax-id')
  await expect(tax).toBeEditable()
  await tax.fill('00999-TEST')
  await page.locator('.revision-summary textarea').fill('更正草稿税号')
  for (const width of [1440,390]) {
    await page.setViewportSize({width,height:width===390?844:900})
    await tax.scrollIntoViewIfNeeded()
    await expect(tax).toBeVisible()
    await expect(tax).toHaveValue('00999-TEST')
    const evidence=path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,'draft-tax-revision')
    fs.mkdirSync(evidence,{recursive:true})
    await page.screenshot({path:path.join(evidence,`draft-${width}.png`)})
  }
  const response=page.waitForResponse(r=>r.url().includes(`/api/quotes/${fixture.id}/revise/`) && r.request().method()==='POST')
  await page.locator('.quote-action-save').click()
  const result=await response
  expect(result.status()).toBe(201)
  expect((await result.json()).buyer_tax_id).toBe('00999-TEST')
  expect((await (await page.request.get(`/api/quotes/${fixture.id}/`)).json()).buyer_tax_id).toBe('00123-SYNTHETIC')
})
test('formal quote revision remains read only',async({page})=>{
  const fixture=seed()
  const sent=await page.request.post(`/api/quotes/${fixture.id}/mark-sent/`)
  expect(sent.status()).toBe(200)
  await page.goto(`/quotes?detail=${fixture.id}`)
  await page.getByRole('dialog',{name:'报价工作台'}).getByRole('button',{name:'创建修订版'}).click()
  await expect(page.locator('#quote-buyer-tax-id')).toHaveAttribute('readonly','')
})

