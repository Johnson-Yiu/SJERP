# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui-coverage-02-order-delete-failure.spec.js >> order delete simulated service failure
- Location: browser-tests\ui-coverage-02-order-delete-failure.spec.js:6:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('隔离模拟订单删除失败')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByText('隔离模拟订单删除失败') with timeout 5000ms
  - waiting for getByText('隔离模拟订单删除失败')

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
  - text: Sales orders
  - heading "订单管理" [level=1]
  - text: 11月10日周二 C
  - tablist "业务工作区":
    - tab "订单管理" [selected]
    - button "关闭 订单管理": ×
    - button "订单管理 标签操作": ⋮
  - tabpanel "订单管理":
    - paragraph: 管理销售订单、履约与回款。
    - button "新建订单"
    - region "页面小计":
      - article:
        - text: 执行中
        - strong: "0"
        - text: 已确认 / 生产中 / 已发货
      - article:
        - text: 待出库
        - strong: "0"
        - text: 尚未完成发货
      - article:
        - text: 待收款
        - strong: "0"
        - text: 仍有应收余额
      - article:
        - text: 已完成
        - strong: "0"
        - text: 已完成交付
    - textbox "搜索订单号或客户"
    - combobox "按订单状态筛选":
      - option "全部状态" [selected]
      - option "草稿"
      - option "已确认"
      - option "生产中"
      - option "已发货"
      - option "已完成"
      - option "已取消"
    - combobox "按订单待办筛选":
      - option "全部待办" [selected]
      - option "待出库"
      - option "交期已到"
    - button "重置"
    - table:
      - rowgroup:
        - row "订单号 客户 订单日期 预计出货日期 履约状态 明细 订单总额 已收 / 待收 操作":
          - columnheader "订单号"
          - columnheader "客户"
          - columnheader "订单日期"
          - columnheader "预计出货日期"
          - columnheader "履约状态"
          - columnheader "明细"
          - columnheader "订单总额"
          - columnheader "已收 / 待收"
          - columnheader "操作"
      - rowgroup:
        - row "WS-SO001 Workspace Alpha 2026-11-10 未设置 草稿 1 项 USD 100.00 0.00 / 尚未生效 编辑 WS-SO001 删除 WS-SO001":
          - cell "WS-SO001"
          - cell "Workspace Alpha"
          - cell "2026-11-10"
          - cell "未设置"
          - cell "草稿"
          - cell "1 项"
          - cell "USD 100.00"
          - cell "0.00 / 尚未生效"
          - cell "编辑 WS-SO001 删除 WS-SO001":
            - button "编辑 WS-SO001"
            - button "删除 WS-SO001"
```

# Test source

```ts
  1  | import {test,expect} from '@playwright/test'
  2  | import {mkdir,writeFile} from 'node:fs/promises'
  3  | import {createHash} from 'node:crypto'
  4  | import path from 'node:path'
  5  | test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
  6  | test('order delete simulated service failure',async({page,browser})=>{
> 7  |  test.setTimeout(90000);const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT;await mkdir(path.join(root,'originals'),{recursive:true});let deletes=0;await page.route('**/api/orders/**',async route=>{if(route.request().method()==='DELETE'){deletes++;await route.fulfill({status:503,contentType:'application/json',body:'{"detail":"隔离模拟订单删除失败"}'})}else await route.continue()});await page.goto('/orders',{waitUntil:'networkidle'});const row=page.getByRole('row').filter({hasText:'WS-SO001'});await row.getByRole('button',{name:'删除 WS-SO001'}).click();const dialog=page.getByRole('dialog',{name:'确认删除订单'});await dialog.getByRole('button',{name:'确认删除'}).click();await expect(dialog).toHaveCount(0);await expect(page.getByText('隔离模拟订单删除失败')).toBeVisible();await expect(row).toBeVisible();expect(deletes).toBe(1);
     |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     ^ Error: expect(locator).toBeVisible() failed
  8  |  const id='ORDER-DELETE-FAILURE-B-1366',state=await page.evaluate(()=>({route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,visibleText:document.body.innerText.slice(0,3500)})),n=id+'.png',b=await page.screenshot({path:path.join(root,'originals',n)});await writeFile(path.join(root,'order-delete-failure-manifest.json'),JSON.stringify([{evidence_id:id,surface_id:'S015',expanded_case_id:'D021-order-delete-simulated-failure',source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role:'authenticated codex test superuser',data:'isolated workspace fixture; order draft WS-SO001',steps:['open order list','click delete WS-SO001','confirm deletion','intercept DELETE and return simulated 503','verify failure message and order row'],delete_requests_intercepted:deletes,simulated:true,capture_time_utc:new Date().toISOString(),file:`originals/${n}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)},review:'NOT_REVIEWED',limitation:'DELETE fulfilled with simulated 503 before reaching service; no order deleted'}],null,2))
  9  | })
  10 | 
```