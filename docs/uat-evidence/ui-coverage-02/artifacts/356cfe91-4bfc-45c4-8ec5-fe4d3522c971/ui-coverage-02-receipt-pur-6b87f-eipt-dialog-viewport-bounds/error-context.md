# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui-coverage-02-receipt.spec.js >> purchase receipt dialog viewport bounds
- Location: browser-tests\ui-coverage-02-receipt.spec.js:6:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('dialog', { name: '验货入库' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('dialog', { name: '验货入库' }) with timeout 5000ms
  - waiting for getByRole('dialog', { name: '验货入库' })

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
  - text: Procurement desk
  - heading "采购管理" [level=1]
  - text: 11月9日周一 C
  - tablist "业务工作区":
    - tab "采购管理"
    - button "关闭 采购管理": ×
    - button "采购管理 标签操作": ⋮
    - tab "UXPO356CFE91" [selected]
    - button "关闭 UXPO356CFE91": ×
    - button "UXPO356CFE91 标签操作": ⋮
  - tabpanel "UXPO356CFE91":
    - paragraph: 管理采购下单、到货与供应商应付。
    - button "刷新"
    - button "新建采购单"
    - region "页面小计":
      - article:
        - text: 执行中
        - strong: "1"
        - text: 已下单 / 部分到货
      - article:
        - text: 待到货
        - strong: "1"
        - text: 尚未全部到货
      - article:
        - text: 待付款
        - strong: "1"
        - text: 仍有应付余额
      - article:
        - text: 已完成
        - strong: "0"
        - text: 已完成采购
    - text: 搜索
    - searchbox "搜索采购单号、供应商、来源订单"
    - text: 状态
    - combobox "按状态筛选":
      - option "全部状态" [selected]
      - option "草稿"
      - option "已下单"
      - option "部分到货"
      - option "已完成"
      - option "已取消"
    - checkbox "仅看待到货"
    - text: 仅看待到货
    - button "重置" [disabled]
    - table:
      - rowgroup:
        - row "采购单号 供应商 来源订单 下单日期 预计到货 状态 采购金额 已付 / 未付 操作":
          - columnheader "采购单号"
          - columnheader "供应商"
          - columnheader "来源订单"
          - columnheader "下单日期"
          - columnheader "预计到货"
          - columnheader "状态"
          - columnheader "采购金额"
          - columnheader "已付 / 未付"
          - columnheader "操作"
      - rowgroup:
        - row "UXPO356CFE91 合成办公供应商 356CFE91 查看来源订单 UXSO356CFE91 2026-11-09 — 已下单 CNY 20.00 0.00 / 20.00 查看采购单 UXPO356CFE91":
          - cell "UXPO356CFE91"
          - cell "合成办公供应商 356CFE91"
          - cell "查看来源订单 UXSO356CFE91":
            - link "查看来源订单 UXSO356CFE91":
              - /url: /orders?detail=1&tab=overview&returnTo=/purchase-orders?detail=1%26tab=receipt
              - text: UXSO356CFE91
          - cell "2026-11-09"
          - cell "—"
          - cell "已下单"
          - cell "CNY 20.00"
          - cell "0.00 / 20.00"
          - cell "查看采购单 UXPO356CFE91":
            - button "查看采购单 UXPO356CFE91"
    - dialog "采购工作台":
      - button "关闭采购详情": 关闭
      - text: 采购工作台
      - paragraph: 合成办公供应商 356CFE91 · 下单日期 2026-11-09
      - heading "UXPO356CFE91 已下单" [level=2]
      - paragraph: 预计到货 —
      - button "取消采购单"
      - navigation "采购工作台页签":
        - button "概览"
        - button "采购明细"
        - button "收货" [pressed]
        - button "供应商应付"
        - button "关联销售订单"
      - main:
        - paragraph: 核对型号、数量和外观后登记合格数量。不合格品不计可用库存，请备注拒收或待补货情况。
        - article:
          - heading "UXSKU356CFE91 · 合成柔性灯带完整规格及包装名称合成柔性灯带完整规格及包装名称合成柔性灯带完整规格及包装名称合成柔性灯带完整规格及包装名称" [level=3]
          - paragraph: 下单 10.00 pcs · 已到 0.00 pcs · 剩余 10.00 pcs
          - button "验货入库"
          - heading "入库记录" [level=4]
          - paragraph: 暂无入库记录
    - dialog "验货合格入库":
      - heading "验货合格入库" [level=3]
      - paragraph: UXPO356CFE91 · UXSKU356CFE91 / 合成柔性灯带完整规格及包装名称合成柔性灯带完整规格及包装名称合成柔性灯带完整规格及包装名称合成柔性灯带完整规格及包装名称
      - paragraph: 供应商：合成办公供应商 356CFE91
      - text: 下单数量
      - strong: 10.00 pcs
      - text: 已到货
      - strong: 0.00 pcs
      - text: 当前待到
      - strong: 10.00 pcs
      - paragraph: 不合格或拒收数量请写入备注，等待补货后再登记入库。
      - text: 实际入库日期 *
      - textbox "实际入库日期 *": 2026-11-09
      - text: 交易单位 / 包装规格
      - combobox "交易单位与包装规格":
        - option "pcs（基础单位）" [selected]
      - text: 本次合格入库数量 *
      - spinbutton "本次合格入库数量 *": "10"
      - text: 本次入库：10 pcs
      - strong: 入库后预计待到：0 pcs
      - text: 实际采购单价（CNY） *
      - spinbutton "实际采购单价（CNY） *": "2"
      - text: 验货备注 / 异常说明
      - textbox "验货备注 / 异常说明":
        - /placeholder: 例如：拒收破损 2 件，已联系供应商补货
      - checkbox "已核对型号、数量及外观，仅登记合格品"
      - text: 已核对型号、数量及外观，仅登记合格品
      - checkbox "指定入库仓库和批次"
      - text: 指定入库仓库和批次 保存后将立即更新：库存、订单预留、采购到货数量、在途数量。
      - button "取消"
      - button "确认入库" [disabled]
```

# Test source

```ts
  1  | import {test,expect} from '@playwright/test'
  2  | import {mkdir,writeFile} from 'node:fs/promises'
  3  | import path from 'node:path'
  4  | import {createHash} from 'node:crypto'
  5  | test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
  6  | test('purchase receipt dialog viewport bounds',async({page,browser})=>{
  7  |  test.setTimeout(120000)
  8  |  const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
  9  |  async function capture(stage){
  10 |   await page.evaluate(()=>document.fonts.ready)
  11 |   const info=await page.evaluate(()=>{
  12 |    const read=sel=>{const e=document.querySelector(sel);if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {rect:{x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom},clientHeight:e.clientHeight,scrollHeight:e.scrollHeight,scrollTop:e.scrollTop,maxHeight:s.maxHeight,overflow:s.overflow,zIndex:s.zIndex,centerHit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.outerHTML.slice(0,200)}}
  13 |    return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,workspaceTop:getComputedStyle(document.documentElement).getPropertyValue('--workspace-top'),mask:read('.receipt-mask'),dialog:read('.goods-receipt-dialog'),footer:read('.goods-receipt-dialog footer')}
  14 |   })
  15 |   const name=`ULR009-B-${stage}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  16 |   entries.push({evidence_id:name,surface_id:'S040',expanded_case_id:`ULR009-B-${stage}`,related_ulr:['ULR-009'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...info,role:'authenticated codex test superuser',data:'existing core-workspace synthetic formal purchase and pending item; no receipt submitted',steps:['open /purchase-orders','open isolated UXPO purchase','select 收货','open 验货入库','expand location and scroll'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  17 |   await writeFile(path.join(root,'receipt-manifest.json'),JSON.stringify(entries,null,2))
  18 |  }
  19 |  await page.goto('/purchase-orders',{waitUntil:'domcontentloaded'})
  20 |  await page.getByRole('row').filter({hasText:'UXPO'}).first().click()
  21 |  await page.getByRole('button',{name:'收货',exact:true}).click()
  22 |  await page.getByRole('button',{name:'验货入库',exact:true}).first().click()
> 23 |  const dialog=page.getByRole('dialog',{name:'验货入库'});await expect(dialog).toBeVisible()
     |                                                                           ^ Error: expect(locator).toBeVisible() failed
  24 |  await capture('1366-top')
  25 |  await dialog.getByLabel('指定入库仓库和批次').check({timeout:6000})
  26 |  await page.mouse.move(900,600);await page.mouse.wheel(0,3000);await page.waitForTimeout(400);await capture('1366-location-bottom')
  27 |  await page.setViewportSize({width:1920,height:1080});await page.mouse.move(1200,700);await page.mouse.wheel(0,3000);await page.waitForTimeout(400);await capture('1920-location-bottom')
  28 | })
  29 | 
```