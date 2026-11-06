# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: import-ux.spec.js >> import real computed bounds and long error table 1440
- Location: browser-tests\import-ux.spec.js:7:37

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.goto: Test timeout of 30000ms exceeded.
Call log:
  - navigating to "http://127.0.0.1:12452/import", waiting until "load"

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - generic [ref=e5]:
      - generic [ref=e6]: S
      - generic [ref=e7]:
        - strong [ref=e8]: 森爵照明管理系统
        - text: 客户 · 销售 · 产品
    - navigation [ref=e9]:
      - generic [ref=e10]: 经营
      - link "经营概览" [ref=e11] [cursor=pointer]:
        - /url: /
      - link "报表中心" [ref=e18] [cursor=pointer]:
        - /url: /reports
      - link "历史订单分析" [ref=e25] [cursor=pointer]:
        - /url: /historical-orders
      - generic [ref=e31]: 客户
      - link "客户管理" [ref=e32] [cursor=pointer]:
        - /url: /customers
      - link "联系人" [ref=e39] [cursor=pointer]:
        - /url: /contacts
      - link "跟进记录" [ref=e45] [cursor=pointer]:
        - /url: /follow-ups
      - generic [ref=e49]: 销售
      - link "报价管理" [ref=e50] [cursor=pointer]:
        - /url: /quotes
      - link "订单管理" [ref=e55] [cursor=pointer]:
        - /url: /orders
      - generic [ref=e61]: 采购与库存
      - link "供应商管理" [ref=e62] [cursor=pointer]:
        - /url: /suppliers
      - link "采购管理" [ref=e69] [cursor=pointer]:
        - /url: /purchase-orders
      - link "库存" [ref=e75] [cursor=pointer]:
        - /url: /inventory
      - link "库存流水" [ref=e80] [cursor=pointer]:
        - /url: /inventory-movements
      - generic [ref=e85]: 产品资料
      - link "产品管理" [ref=e86] [cursor=pointer]:
        - /url: /products
      - link "SKU 管理" [ref=e92] [cursor=pointer]:
        - /url: /skus
      - link "产品分类" [ref=e104] [cursor=pointer]:
        - /url: /categories
      - link "产品参数" [ref=e110] [cursor=pointer]:
        - /url: /product-parameters
      - link "包装管理" [ref=e113] [cursor=pointer]:
        - /url: /sku-packaging
      - link "交易单位" [ref=e119] [cursor=pointer]:
        - /url: /sku-trade-units
      - link "产品证书" [ref=e131] [cursor=pointer]:
        - /url: /product-certificates
      - link "HS 编码维护" [ref=e136] [cursor=pointer]:
        - /url: /hs-codes
      - generic [ref=e139]: 财务与工具
      - link "财务概览" [ref=e140] [cursor=pointer]:
        - /url: /finance
      - link "应收计划" [ref=e146] [cursor=pointer]:
        - /url: /receivables
      - link "应付计划" [ref=e152] [cursor=pointer]:
        - /url: /payables
      - link "财务流水" [ref=e158] [cursor=pointer]:
        - /url: /transactions
      - link "人民币资金" [ref=e164] [cursor=pointer]:
        - /url: /rmb-cash-events
      - link "账户资金" [ref=e170] [cursor=pointer]:
        - /url: /finance-ledger
      - link "数据导入" [ref=e176] [cursor=pointer]:
        - /url: /import
      - link "历史资料承接" [ref=e181] [cursor=pointer]:
        - /url: /history-takeover
      - generic [ref=e187]: 组织与系统
      - link "组织与权限" [ref=e188] [cursor=pointer]:
        - /url: /organization
    - generic [ref=e193]:
      - generic [ref=e194]: —
      - generic [ref=e196]:
        - strong [ref=e197]: 开发身份：
        - generic [ref=e198]: · 全部功能与数据权限
  - main [ref=e199]:
    - generic [ref=e200]:
      - generic [ref=e201]:
        - text: Data onboarding
        - heading "数据导入" [level=1] [ref=e202]
      - generic [ref=e203]:
        - generic [ref=e204]: 11月6日周五
        - generic [ref=e205]: —
    - generic [ref=e207]:
      - generic [ref=e208]:
        - generic [ref=e209]:
          - heading "数据导入" [level=2] [ref=e210]
          - paragraph [ref=e211]: 先校验 CSV，再确认写入；预览不会保存业务数据。
        - link "受控历史资料承接" [ref=e212] [cursor=pointer]:
          - /url: /history-takeover
      - generic [ref=e213]:
        - generic [ref=e214]:
          - generic [ref=e215]:
            - generic [ref=e216]: "01"
            - generic [ref=e217]:
              - heading "选择数据类型" [level=3] [ref=e218]
              - paragraph [ref=e219]: 客户、产品和 SKU 按编号匹配；更新会经过当前业务规则校验，不会绕过主数据保护。
          - generic [ref=e220]:
            - generic [ref=e221] [cursor=pointer]:
              - radio "客户 按客户编号匹配" [checked] [ref=e222]
              - strong [ref=e226]: 客户
              - generic [ref=e227]: 按客户编号匹配
            - generic [ref=e228] [cursor=pointer]:
              - radio "产品 分类须预先建立" [ref=e229]
              - strong [ref=e233]: 产品
              - generic [ref=e234]: 分类须预先建立
            - generic [ref=e235] [cursor=pointer]:
              - radio "SKU 按 SKU 与产品编号匹配" [ref=e236]
              - strong [ref=e240]: SKU
              - generic [ref=e241]: 按 SKU 与产品编号匹配
            - generic [ref=e242] [cursor=pointer]:
              - radio "财务流水 只新增，不覆盖" [ref=e243]
              - strong [ref=e247]: 财务流水
              - generic [ref=e248]: 只新增，不覆盖
          - generic [ref=e249]:
            - generic [ref=e250]: "02"
            - generic [ref=e251]:
              - heading "准备并上传 CSV" [level=3] [ref=e252]
              - paragraph [ref=e253]: 文件须为 UTF-8（支持 BOM），最多 5,000 条记录。选择文件后仍须预览校验，第一行保留模板字段名。
          - button "下载 客户 CSV 模板 code · name · notes" [ref=e254] [cursor=pointer]:
            - generic [ref=e258]:
              - strong [ref=e259]: 下载 客户 CSV 模板
              - generic [ref=e260]: code · name · notes
          - generic [ref=e261] [cursor=pointer]:
            - strong [ref=e265]: 点击选择 CSV 文件
            - generic [ref=e266]: 单次建议不超过 5,000 行
          - button "预览并校验" [disabled] [ref=e267]
          - status [ref=e268]: 尚未选择文件
        - complementary [ref=e269]:
          - heading "导入规则" [level=3] [ref=e270]
          - list [ref=e271]:
            - listitem [ref=e272]:
              - generic [ref=e273]: "1"
              - generic [ref=e274]:
                - strong [ref=e275]: 客户
                - generic [ref=e276]: 按客户编号匹配
            - listitem [ref=e277]:
              - generic [ref=e278]: "2"
              - generic [ref=e279]:
                - strong [ref=e280]: 产品
                - generic [ref=e281]: 分类须预先建立
            - listitem [ref=e282]:
              - generic [ref=e283]: "3"
              - generic [ref=e284]:
                - strong [ref=e285]: SKU
                - generic [ref=e286]: 按 SKU 与产品编号匹配
            - listitem [ref=e287]:
              - generic [ref=e288]: "4"
              - generic [ref=e289]:
                - strong [ref=e290]: 财务流水
                - generic [ref=e291]: 只新增，不覆盖
          - generic [ref=e292]:
            - strong [ref=e293]: 关联与历史安全
            - paragraph [ref=e294]: 客户、产品和 SKU 按编号匹配。更新时空白字段可能清除原有内容，请先备份并核对。财务流水只新增；重复流水号会报错，绝不覆盖原记录。
            - paragraph [ref=e295]: 正式订单导入暂未开放，请通过订单业务流程创建；避免绕过报价、库存预留和收款计划。
```

# Test source

```ts
  1  | import {test,expect} from '@playwright/test'
  2  | import {readFile} from 'node:fs/promises'
  3  | const valid={total:1,created:1,updated:0,errors:[],preview_token:'token'}
  4  | function gate(){let resolve;const promise=new Promise(r=>resolve=r);return{resolve,promise}}
  5  | async function fixture(page){const state={posts:[],pending:null,templateFail:false,readOnly:false,preview:valid,execute:{total:1,created:1,updated:0}};await page.route('**/api/**',async route=>{const path=new URL(route.request().url()).pathname;if(path.includes('current-operator'))return route.fulfill({json:state.readOnly?{authenticated:true,rbac_enforcement:true,permissions:{imports:{view:true,import:false}}}:{authenticated:true,development_superadmin:true,has_all_permissions:true}});if(path==='/api/import/templates/')return route.fulfill(state.templateFail?{status:403,json:{detail:'模板查询被拒绝'}}:{json:{customers:['code','name','notes'],products:['code','name']}});if(path.includes('/import/csv/')){state.posts.push(path);if(state.pending)await state.pending.promise;return route.fulfill({json:path.includes('preview')?state.preview:state.execute})}return route.fulfill({json:[]})});return state}
  6  | async function choose(page,name='synthetic.csv'){await page.locator('input[type=file]').setInputFiles({name,mimeType:'text/csv',buffer:Buffer.from('code,name\nF8B,合成客户')})}
> 7  | for(const width of [1440,1280,1024])test(`import real computed bounds and long error table ${width}`,async({page})=>{await page.setViewportSize({width,height:1000});const s=await fixture(page);s.preview={...valid,preview_token:null,errors:Array.from({length:25},(_,i)=>({row:i+2,key:'长业务编号'.repeat(15),message:'错误原因, 包含引号"与换行\n以及中文'.repeat(12)}))};await page.goto('/import');await choose(page,'长文件名称'.repeat(20)+'.csv');await page.getByRole('button',{name:'预览并校验',exact:true}).click();await expect(page.getByText('校验未通过，尚未写入',{exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);for(const e of await page.locator('.import-main,.template-btn,.upload-btn,.type-grid label').all()){const b=await e.boundingBox();expect(b.x).toBeGreaterThanOrEqual(0);expect(b.x+b.width).toBeLessThanOrEqual(width+1)}await expect(page.locator('.error-table tbody tr')).toHaveCount(20);await page.getByRole('button',{name:'下一页',exact:true}).click();await expect(page.locator('.error-table tbody tr')).toHaveCount(5);await expect(page.getByRole('button',{name:'确认执行导入',exact:true})).toHaveCount(0)})
     |                                                                                                                                                                                                                                                                                                                                                                        ^ Error: page.goto: Test timeout of 30000ms exceeded.
  8  | async function traceImportDownload(page) {
  9  |   const started = Date.now()
  10 |   const emit = (event, extra = {}) => console.log('IMPORT_DOWNLOAD_TRACE ' + JSON.stringify({ event, elapsedMs: Date.now() - started, ...extra }))
  11 |   await page.exposeFunction('__importDownloadDiagnostic', (event, details) => emit(event, details))
  12 |   await page.addInitScript(() => {
  13 |     const revoke = URL.revokeObjectURL.bind(URL)
  14 |     URL.revokeObjectURL = value => {
  15 |       if (String(value).startsWith('blob:')) void window.__importDownloadDiagnostic('blob-revoke', {})
  16 |       return revoke(value)
  17 |     }
  18 |     const click = HTMLAnchorElement.prototype.click
  19 |     HTMLAnchorElement.prototype.click = function () {
  20 |       if (this.hasAttribute('download')) void window.__importDownloadDiagnostic('download-anchor-click', { scheme: this.href.split(':')[0] })
  21 |       return click.call(this)
  22 |     }
  23 |   })
  24 |   page.on('download', download => emit('download-start', { filename: download.suggestedFilename() }))
  25 |   const isFontRequest = request => ['fonts.googleapis.com', 'fonts.gstatic.com'].includes(new URL(request.url()).hostname)
  26 |   page.on('request', request => { if (isFontRequest(request)) emit('external-font-request', { host: new URL(request.url()).hostname }) })
  27 |   page.on('requestfinished', request => { if (isFontRequest(request)) emit('external-font-finished', { host: new URL(request.url()).hostname }) })
  28 |   page.on('requestfailed', request => { if (isFontRequest(request)) emit('external-font-failed', { host: new URL(request.url()).hostname, reason: request.failure()?.errorText }) })
  29 |   page.on('load', () => emit('page-load'))
  30 |   page.on('framenavigated', frame => { if (frame === page.mainFrame()) emit('main-frame-navigation', { url: frame.url() }) })
  31 |   page.on('close', () => emit('page-close'))
  32 |   page.context().on('close', () => emit('context-close'))
  33 | }
  34 | test('downloads contain actual UTF8 BOM headers and correctly quoted failure rows',async({page},testInfo)=>{await traceImportDownload(page);const s=await fixture(page);await page.goto('/import');let p=page.waitForEvent('download');await page.locator('.template-btn').click();let d=await p;await d.saveAs(testInfo.outputPath('customer-template.csv'));let bytes=await readFile(await d.path());expect([...bytes.subarray(0,3)]).toEqual([239,187,191]);expect(bytes.toString('utf8')).toBe('\ufeffcode,name,notes\r\n');s.preview={...valid,preview_token:null,errors:[{row:3,key:'KEY,"1"',message:'原因, "引号"\n第二行'}]};await choose(page);await page.getByRole('button',{name:'预览并校验',exact:true}).click();p=page.waitForEvent('download');await page.getByRole('button',{name:'下载失败清单 CSV',exact:true}).click();d=await p;await d.saveAs(testInfo.outputPath('failure-report.csv'));bytes=await readFile(await d.path());expect(bytes.toString('utf8')).toBe('\ufeffrow,key,message\r\n"3","KEY,""1""","原因, ""引号""\n第二行"')})
  35 | test('pending preview and execute block back/navigation, duplicates and changes; cancel never writes',async({page})=>{await traceImportDownload(page);const s=await fixture(page);await page.goto('/customers',{waitUntil:'domcontentloaded'});await page.getByRole('link',{name:'数据导入',exact:true}).click();await choose(page);s.pending=gate();await page.getByRole('button',{name:'预览并校验',exact:true}).click();await expect(page.locator('input[type=file]')).toBeDisabled();await page.getByRole('link',{name:'客户管理',exact:true}).click();await expect(page).toHaveURL(/\/import$/);await page.goBack();await expect(page).toHaveURL(/\/import$/);expect(s.posts).toHaveLength(1);s.pending.resolve();await expect(page.getByRole('button',{name:'确认执行导入',exact:true})).toBeEnabled();s.pending=null;await page.getByRole('button',{name:'确认执行导入',exact:true}).click();await page.getByRole('button',{name:'取消',exact:true}).click();expect(s.posts).toHaveLength(1);await page.getByRole('button',{name:'确认执行导入',exact:true}).click();s.pending=gate();await page.getByRole('button',{name:'确认导入',exact:true}).click();await expect(page.getByText('正在执行导入，请勿离开',{exact:true})).toBeVisible();await page.getByRole('link',{name:'客户管理',exact:true}).click();await page.goBack();await expect(page).toHaveURL(/\/import$/);expect(s.posts).toHaveLength(2);s.pending.resolve();await expect(page.getByText('导入完成，已写入数据库',{exact:true})).toBeVisible();await page.getByRole('link',{name:'前往客户',exact:true}).click();await expect(page).toHaveURL(/\/customers$/)})
  36 | test('restricted import entry and template retry',async({page})=>{const s=await fixture(page);s.readOnly=true;s.templateFail=true;await page.goto('/import');await expect(page.locator('.template-btn')).toBeDisabled();await expect(page.locator('input[type=file]')).toBeDisabled();await expect(page.getByText('当前账号仅可查看导入说明，不能预览或执行导入。')).toBeVisible();s.templateFail=false;await page.getByRole('button',{name:'重新加载模板',exact:true}).click();await expect(page.locator('.template-btn')).toBeEnabled();expect(s.posts).toHaveLength(0)})
  37 | 
```