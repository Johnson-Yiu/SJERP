# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui-coverage-02-related-order.spec.js >> customer related order selected status and intercepted payload
- Location: browser-tests\ui-coverage-02-related-order.spec.js:6:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator:  getByText('草稿', { exact: true }).first()
Expected: visible
Received: hidden
Timeout:  5000ms

Call log:
  - Expect "toBeVisible" getByText('草稿', { exact: true }).first() with timeout 5000ms
  - waiting for getByText('草稿', { exact: true }).first()
    13 × locator resolved to <option value="draft" data-v-dfaf05d4="">草稿</option>
       - unexpected value "hidden"

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
    - tab "订单管理"
    - button "关闭 订单管理": ×
    - button "订单管理 标签操作": ⋮
    - tab "订单管理 · 新建 1" [selected]
    - button "关闭 订单管理 · 新建 1": ×
    - button "订单管理 · 新建 1 标签操作": ⋮
  - tabpanel "订单管理 · 新建 1":
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
    - heading "新建订单" [level=3]
    - button
    - text: 订单号
    - textbox: 保存后由系统自动生成
    - text: 客户 *
    - combobox:
      - option "请选择" [selected]
      - option "Workspace Beta"
      - option "Workspace Alpha"
    - text: 订单日期 *
    - textbox "年份": "2026"
    - text: /
    - textbox "月份": "11"
    - text: /
    - textbox "日期": "10"
    - button "打开日期选择器"
    - textbox: 2026-11-10
    - text: 预计交期
    - spinbutton "交期天数"
    - text: 天
    - textbox "年份"
    - text: /
    - textbox "月份"
    - text: /
    - textbox "日期"
    - button "打开日期选择器"
    - textbox
    - text: 状态
    - textbox: 草稿
    - text: 保存后为草稿；确认订单后进入履约。 来源报价（可选）
    - combobox "来源报价（可选）":
      - option "不关联报价" [selected]
    - text: 币种
    - combobox "单据币种":
      - option "USD" [selected]
      - option "CNY"
      - option "EUR"
      - option "GBP"
    - text: 对人民币汇率
    - spinbutton "对人民币汇率": "7.2"
    - strong: 产品明细
    - text: 先选择一个或多个 SKU，再填写数量与价格
    - strong: 选择 SKU
    - searchbox "搜索 SKU、型号或描述"
    - button "按产品分类筛选": 全部分类
    - 'checkbox "Workspace Light SKU: WS-SKU001 Sales Model: — USD 10.00"'
    - text: "Workspace Light SKU: WS-SKU001 Sales Model: —"
    - emphasis: USD 10.00
    - complementary:
      - paragraph: 从左侧勾选 SKU 后，可在这里查看详情。
    - text: SKU 数量 * 单价 * 成本 小计
    - paragraph: 请先从上方选择至少一个 SKU。
    - text: 运费
    - spinbutton "运费": "0.00"
    - text: 折扣
    - spinbutton "折扣": "0.00"
    - text: 商品小计 USD 0.00 合计
    - strong: USD 0.00
    - text: 条款 / 备注
    - textbox
    - button "取消"
    - button "保存销售订单草稿"
```

# Test source

```ts
  1  | import {test,expect} from '@playwright/test'
  2  | import {mkdir,writeFile} from 'node:fs/promises'
  3  | import {createHash} from 'node:crypto'
  4  | import path from 'node:path'
  5  | test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
  6  | test('customer related order selected status and intercepted payload',async({page,browser})=>{
  7  |  test.setTimeout(90000);const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT;await mkdir(path.join(root,'originals'),{recursive:true})
  8  |  let payload=null
  9  |  await page.route('**/api/orders/',async route=>{if(route.request().method()==='POST'){payload=route.request().postDataJSON();await route.fulfill({status:503,contentType:'application/json',body:'{"detail":"隔离拦截，不创建订单"}'})}else await route.continue()})
  10 |  await page.goto('/customers',{waitUntil:'domcontentloaded'});await page.getByRole('row').filter({hasText:'Workspace Alpha'}).click()
  11 |  await page.getByRole('button',{name:/订单记录/}).first().click();await page.getByRole('button',{name:/新增订单/}).first().click()
  12 |  const modal=page.locator('.related-create-modal');await expect(modal).toBeVisible()
  13 |  const status=modal.locator('.field').filter({hasText:'状态'}).locator('select');await status.selectOption('confirmed')
  14 |  await status.scrollIntoViewIfNeeded();await page.evaluate(()=>document.fonts.ready)
  15 |  const statusTime=new Date().toISOString(),statusBytes=await page.screenshot({path:path.join(root,'originals','ULR019-B-status.png'),fullPage:false})
  16 |  await writeFile(path.join(root,'related-order-status-manifest.json'),JSON.stringify({evidence_id:'ULR019-B-status.png',surface_id:'S017',expanded_case_id:'ULR019-B-status',related_ulr:['ULR-019'],source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',source_branch:'codex/first-release-independent-review-02',browser_version:browser.version(),route:new URL(page.url()).pathname+new URL(page.url()).search,viewport_actual:{width:1366,height:768},dpr:1,zoom:1,role:'authenticated codex test superuser',fixture:'Workspace Alpha / WS-SKU001',steps:['客户列表打开 Workspace Alpha','订单记录','新增订单','状态选择已确认'],selected_status:await status.inputValue(),capture_time_utc:statusTime,simulated:false,file:'originals/ULR019-B-status.png',sha256:createHash('sha256').update(statusBytes).digest('hex'),pixels:{width:statusBytes.readUInt32BE(16),height:statusBytes.readUInt32BE(20)}},null,2))
  17 |  await modal.locator('.sku-picker-options label').filter({hasText:'WS-SKU001'}).locator('input').check()
  18 |  const shot=path.join(root,'originals','ULR019-B-selected.png'),b=await page.screenshot({path:shot,fullPage:false})
  19 |  const response=page.waitForResponse(r=>r.url().endsWith('/api/orders/')&&r.request().method()==='POST')
  20 |  await modal.getByRole('button',{name:'保存',exact:true}).click();const res=await response
  21 |  await writeFile(path.join(root,'related-order-result.json'),JSON.stringify({selected_status:'confirmed',request_payload:payload,status:res.status(),intercepted_before_service:true},null,2))
  22 |  await writeFile(path.join(root,'related-order-manifest.json'),JSON.stringify([{evidence_id:'ULR019-B-selected.png',surface_id:'S017',expanded_case_id:'ULR019-B-selected',related_ulr:['ULR-019'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),route:page.url(),viewport_actual:{width:1366,height:768},dpr:1,zoom:1,role:'authenticated codex test superuser',data:'isolated Workspace Alpha and WS-SKU001',simulated:'POST intercepted before service',capture_time_utc:new Date().toISOString(),file:'originals/ULR019-B-selected.png',sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}}],null,2))
> 23 |  const other=await page.context().newPage();await other.goto('/orders',{waitUntil:'domcontentloaded'});await other.getByRole('button',{name:/新建订单/}).first().click();await expect(other.getByText('草稿',{exact:true}).first()).toBeVisible();await other.evaluate(()=>document.fonts.ready)
     |                                                                                                                                                                                                                               ^ Error: expect(locator).toBeVisible() failed
  24 |  const at=new Date().toISOString(),c=await other.screenshot({path:path.join(root,'originals','ULR019-B-normal.png'),fullPage:false})
  25 |  await writeFile(path.join(root,'related-order-normal-manifest.json'),JSON.stringify({evidence_id:'ULR019-B-normal.png',surface_id:'S002',expanded_case_id:'ULR019-B-normal',related_ulr:['ULR-019'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),route:new URL(other.url()).pathname+new URL(other.url()).search,viewport_actual:{width:1366,height:768},dpr:1,zoom:1,role:'authenticated codex test superuser',fixture:'isolated workspace fixture',steps:['订单管理','新建订单'],capture_time_utc:at,simulated:false,file:'originals/ULR019-B-normal.png',sha256:createHash('sha256').update(c).digest('hex'),pixels:{width:c.readUInt32BE(16),height:c.readUInt32BE(20)}},null,2));await other.close()
  26 | })
  27 | 
```