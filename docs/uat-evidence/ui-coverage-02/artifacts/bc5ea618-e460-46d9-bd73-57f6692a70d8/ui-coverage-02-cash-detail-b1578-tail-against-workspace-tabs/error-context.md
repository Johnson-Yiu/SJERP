# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui-coverage-02-cash-detail.spec.js >> confirmed cash event detail against workspace tabs
- Location: browser-tests\ui-coverage-02-cash-detail.spec.js:6:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('row').filter({ hasText: 'CSV-BANK-09' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('row').filter({ hasText: 'CSV-BANK-09' }) with timeout 5000ms
  - waiting for getByRole('row').filter({ hasText: 'CSV-BANK-09' })

```

```yaml
- complementary:
  - text: S
  - strong: 森爵照明管理系统
  - text: 客户 · 销售 · 产品
  - navigation:
    - text: 经营
    - link "经营概览":
      - /url: /
    - link "报表中心":
      - /url: /reports
    - link "历史订单分析":
      - /url: /historical-orders
    - text: 客户
    - link "客户管理":
      - /url: /customers
    - link "联系人":
      - /url: /contacts
    - link "跟进记录":
      - /url: /follow-ups
    - text: 销售
    - link "报价管理":
      - /url: /quotes
    - link "订单管理":
      - /url: /orders
    - text: 采购与库存
    - link "供应商管理":
      - /url: /suppliers
    - link "采购管理":
      - /url: /purchase-orders
    - link "库存":
      - /url: /inventory
    - link "库存流水":
      - /url: /inventory-movements
    - text: 产品资料
    - link "产品管理":
      - /url: /products
    - link "SKU 管理":
      - /url: /skus
    - link "产品分类":
      - /url: /categories
    - link "产品参数":
      - /url: /product-parameters
    - link "包装管理":
      - /url: /sku-packaging
    - link "交易单位":
      - /url: /sku-trade-units
    - link "产品证书":
      - /url: /product-certificates
    - link "HS 编码维护":
      - /url: /hs-codes
    - text: 财务与工具
    - link "财务概览":
      - /url: /finance
    - link "应收计划":
      - /url: /receivables
    - link "应付计划":
      - /url: /payables
    - link "财务流水":
      - /url: /transactions
    - link "银行资金记录":
      - /url: /rmb-cash-events
    - link "账户余额与对账":
      - /url: /finance-ledger
    - link "数据导入":
      - /url: /import
    - link "历史资料预检":
      - /url: /history-preflight
    - link "历史资料承接":
      - /url: /history-takeover
    - text: 组织与系统
    - link "组织与权限":
      - /url: /organization
  - text: C
  - strong: 当前账号：codex
  - text: 超级管理员 · 全部功能与数据权限
  - button "退出登录"
- main:
  - text: Bank cash facts
  - heading "银行资金记录" [level=1]
  - text: 11月9日周一 C
  - tablist "业务工作区":
    - tab "银行资金记录" [selected]
    - button "关闭 银行资金记录": ×
    - button "银行资金记录 标签操作": ⋮
  - tabpanel "银行资金记录":
    - paragraph: 人民币资金
    - heading "银行资金记录" [level=2]
    - paragraph: 登记实际到账信息。只有完成凭证核验的资金事件才计入银行资金汇总；客户收款和应收核销仍按原流程保存。
    - link "查看财务流水":
      - /url: /transactions
    - button "新增资金事件"
    - paragraph:
      - strong: 核对口径：
      - text: 银行净额以实际凭证为准；手续费已计入净额时不再重复扣除。仅已核对并绑定实际银行凭证的事件可以确认。
    - form "人民币资金筛选":
      - text: 状态
      - combobox "状态":
        - option "全部状态" [selected]
        - option "待确认"
        - option "已确认"
        - option "已放弃"
      - text: 搜索
      - searchbox "搜索"
      - button "刷新"
    - paragraph: 列表包含待确认、已确认和已放弃记录；只有已确认事件计入银行资金汇总。
    - status:
      - heading "没有符合当前条件的记录" [level=3]
      - paragraph: 请调整搜索或筛选条件。
      - button "清除筛选"
```

# Test source

```ts
  1  | import {test,expect} from '@playwright/test'
  2  | import {mkdir,writeFile} from 'node:fs/promises'
  3  | import {createHash} from 'node:crypto'
  4  | import path from 'node:path'
  5  | test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
  6  | test('confirmed cash event detail against workspace tabs',async({page,browser})=>{
  7  |  test.setTimeout(120000)
  8  |  const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
  9  |  await page.goto('/rmb-cash-events',{waitUntil:'domcontentloaded'})
> 10 |  const row=page.getByRole('row').filter({hasText:'CSV-BANK-09'});await expect(row).toBeVisible();await row.getByRole('button',{name:'查看详情'}).click()
     |                                                                                    ^ Error: expect(locator).toBeVisible() failed
  11 |  await expect(page.locator('.cash-detail-panel')).toBeVisible();await page.evaluate(()=>document.fonts.ready)
  12 |  for(const [width,height] of [[1366,768],[1920,1080]]){
  13 |   await page.setViewportSize({width,height})
  14 |   const info=await page.evaluate(()=>{
  15 |    const read=sel=>{const e=document.querySelector(sel);if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {rect:{x:r.x,y:r.y,width:r.width,height:r.height},zIndex:s.zIndex,centerHit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.outerHTML.slice(0,240)}}
  16 |    return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,detail:read('.cash-detail-panel'),title:read('#cash-detail-title'),close:read('[aria-label="关闭资金详情"]'),workspaceBar:read('.workspace-bar')}
  17 |   })
  18 |   const name=`ULR010-B-${width}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  19 |   entries.push({evidence_id:name,surface_id:'F022',expanded_case_id:`ULR010-B-${width}`,related_ulr:['ULR-010'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...info,role:'authenticated codex test superuser',object_reference:'CSV-BANK-09, confirmed',data:'existing export-stability isolated synthetic fixture',steps:['open /rmb-cash-events','open confirmed CSV-BANK-09','capture viewport'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  20 |   await writeFile(path.join(root,'cash-detail-manifest.json'),JSON.stringify(entries,null,2))
  21 |  }
  22 | })
  23 | 
```