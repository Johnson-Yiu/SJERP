import {execFileSync} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import path from 'node:path'
import {expect,test} from '@playwright/test'
test('P2-05 SKU packaging long candidate, empty search and new entry',async({page},info)=>{
 test.skip(![path.basename(fileURLToPath(import.meta.url)), 'product-draft-protection-01.spec.js'].includes(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE),'Dedicated isolation only')
 test.setTimeout(180000);page.setDefaultTimeout(20000)
 const repo=new URL('../../',import.meta.url)
 const f=JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON,[fileURLToPath(new URL('docs/uat-evidence/product-draft-protection-01/seed-packaging.py',repo))],{cwd:fileURLToPath(new URL('backend/',repo)),encoding:'utf8'}).replace(/^\uFEFF/,''))
 for(const width of [1366,1920]) {
  await page.setViewportSize({width,height:width===1366?768:1080})
  await page.goto(`/skus?create=1&product=${f.product}`)
  const input=page.getByPlaceholder('未配置，输入任意文字搜索').first()
  await input.fill('合成长文本')
  const candidate=page.locator('.packaging-options').getByRole('button',{name:f.name,exact:true})
  await expect(candidate).toBeVisible()
  await candidate.scrollIntoViewIfNeeded()
  await page.screenshot({path:info.outputPath(`packaging-long-${width}.png`)})
  await candidate.click()
  await expect(input).toHaveValue(f.name)
  await expect(page.locator('.packaging-options')).toHaveCount(0)
  await input.fill('不存在的合成包装搜索')
  await expect(page.locator('.packaging-options button')).toHaveCount(2)
  await page.screenshot({path:info.outputPath(`packaging-empty-${width}.png`)})
  await page.getByRole('button',{name:'＋ 新建包装',exact:true}).click()
  await expect(page.locator('.inline-packaging-modal')).toBeVisible()
  await page.locator('.inline-packaging-modal input').first().fill(`合成新包装 ${width}`)
  await page.screenshot({path:info.outputPath(`packaging-new-${width}.png`)})
  await page.locator('.inline-packaging-modal').getByRole('button',{name:'取消',exact:true}).click()
  await page.getByTestId('dialog-confirm').click()
  await expect(page.locator('.inline-packaging-modal')).toHaveCount(0)
  await page.getByRole('button',{name:'关闭 SKU 窗口',exact:true}).click()
  await page.getByTestId('dialog-confirm').click()
 }
})
test.afterEach(async({page},info)=>{if(info.status!==info.expectedStatus)await page.screenshot({path:info.outputPath('failure.png')})})
