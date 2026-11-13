import {test,expect} from '@playwright/test'
import {execFileSync} from 'node:child_process'
import path from 'node:path'
import {writeFile} from 'node:fs/promises'
test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE!=='prelaunch-history-correction-02.spec.js','Dedicated authenticated isolated Chrome profile required.')
test('historical correction groups preserve actual submitted and read back values',async({page},info)=>{
 test.setTimeout(120000)
 const fixture=JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON,[path.resolve('../docs/uat-evidence/cost-currency-integrity-02/seed-browser.py')],{encoding:'utf8'}).trim().split('\n').at(-1))
 for(const [width,height] of [[1366,768],[1920,1080]]) {
  await page.setViewportSize({width,height});await page.goto('/history-takeover?application='+fixture.application)
  const form=page.locator('form').filter({has:page.getByRole('button',{name:'提交追溯更正申请'})})
  await form.getByLabel('追溯类型').selectOption('correction')
  await form.getByRole('button',{name:'提交追溯更正申请'}).click()
  await expect(form.getByText('请填写原系统记录号或业务单据号。',{exact:true})).toBeVisible()
  await form.getByLabel('原系统记录号',{exact:true}).fill('SYNTH-CORRECTION-'+width)
  await form.getByLabel('原系统业务单据号',{exact:true}).fill('SYNTH-DOC-'+width)
  await form.getByLabel('更正明细（原值、更正值）',{exact:true}).fill('合成备注：原值 A，更正值 B；仅申请不正式执行。')
  await form.getByLabel('提交原因（必填）',{exact:true}).fill('合成表单字段验证 '+width)
  await expect(form.getByRole('group',{name:'定位原始记录'})).toBeVisible()
  await expect(form.getByRole('group',{name:'补充资料'})).toBeVisible()
  await page.screenshot({path:info.outputPath(`history-correction-${width}.png`)})
  const submitted=page.waitForResponse(r=>r.url().endsWith('/correction/')&&r.request().method()==='POST')
  await form.getByRole('button',{name:'提交追溯更正申请'}).click();const r=await submitted;expect(r.ok(),await r.text()).toBe(true)
  const sent=r.request().postDataJSON();expect(sent.details.source_record_id).toBe('SYNTH-CORRECTION-'+width)
  await page.reload()
  const app=await (await page.request.get('/api/import/history-takeovers/'+fixture.application+'/')).json()
  expect(JSON.stringify(app)).toContain('SYNTH-CORRECTION-'+width)
  expect(JSON.stringify(app)).toContain('合成表单字段验证 '+width)
  await writeFile(info.outputPath(`history-correction-${width}.json`),JSON.stringify({sent,readback:app},null,2))
 }
})
