# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui-coverage-02-order-quote-failure.spec.js >> order source quote overwrite confirmation cancellation
- Location: browser-tests\ui-coverage-02-order-quote-failure.spec.js:6:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText(/无法载入报价/)
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByText(/无法载入报价/) with timeout 5000ms
  - waiting for getByText(/无法载入报价/)

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
    - tab "订单管理 · 新建 1未保存" [selected]: 订单管理 · 新建 1 ●
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
    - status:
      - heading "暂无订单" [level=3]
      - paragraph: 点击“新建订单”开始录入。
    - heading "新建订单" [level=3]
    - button
    - text: 订单号
    - textbox: 保存后由系统自动生成
    - text: 客户 *
    - combobox [disabled]:
      - option "请选择" [selected]
      - option "ISS007 隔离验收客户"
    - text: 订单日期 *
    - textbox "年份": "2026"
    - text: /
    - textbox "月份": "11"
    - text: /
    - textbox "日期": "10"
    - button "打开日期选择器"
    - textbox: 2026-11-10
    - text: 预计交期
    - spinbutton "交期天数": "7"
    - text: 天
    - textbox "年份": "2026"
    - text: /
    - textbox "月份": "11"
    - text: /
    - textbox "日期": "17"
    - button "打开日期选择器"
    - textbox: 2026-11-17
    - text: 状态
    - textbox: 草稿
    - text: 保存后为草稿；确认订单后进入履约。 来源报价（可选）
    - combobox "来源报价（可选）" [disabled]:
      - option "不关联报价" [selected]
      - option "ISS007-Q001"
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
    - 'checkbox "ISS007 可上传图片 SKU SKU: ISS007-SKU001 Sales Model: ISS7-001 USD 0.00"'
    - text: "ISS007 可上传图片 SKU SKU: ISS007-SKU001 Sales Model: ISS7-001"
    - emphasis: USD 0.00
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
    - button "保存销售订单草稿" [disabled]
```

# Test source

```ts
  1  | import {test,expect} from '@playwright/test'
  2  | import {mkdir,writeFile} from 'node:fs/promises'
  3  | import {createHash} from 'node:crypto'
  4  | import path from 'node:path'
  5  | test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
  6  | test('order source quote overwrite confirmation cancellation',async({page,browser})=>{
  7  |  test.setTimeout(90000);const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true});let writes=0,loads=0;await page.route('**/api/**',async r=>{const q=r.request();if(!['GET','HEAD','OPTIONS'].includes(q.method())){writes++;await r.abort()}else {if(q.url().includes('/order-draft/')){loads++;await r.fulfill({status:503,contentType:'application/json',body:'{"detail":"simulated"}'})}else await r.continue()}});await page.goto('/orders',{waitUntil:'networkidle'});await page.getByRole('button',{name:'新建订单',exact:true}).click();const modal=page.locator('.modal-backdrop .modal');await modal.getByLabel('交期天数').fill('7');const source=modal.getByLabel('来源报价（可选）');await expect(source.locator('option',{hasText:'ISS007-Q001'})).toHaveCount(1);await source.selectOption({label:'ISS007-Q001'});const confirm=page.getByRole('dialog',{name:'从报价载入'});await expect(confirm).toContainText('覆盖');
  8  |  async function capture(id,steps){const state=await page.evaluate(()=>({route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,visibleText:document.body.innerText.slice(0,5000)})),n=id+'.png',b=await page.screenshot({path:path.join(root,'originals',n)});entries.push({evidence_id:id,surface_id:'S016',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role:'authenticated codex test superuser',data:'isolated ISS007 quote and unsaved order draft',steps,writes,loads,simulated:true,capture_time_utc:new Date().toISOString(),file:`originals/${n}`,sha256:createHash('sha256').update(b).digest('hex'),review:'NOT_REVIEWED',limitation:'quote draft GET intercepted and simulated 503; no order save'});await writeFile(path.join(root,'order-source-quote-failure-manifest.json'),JSON.stringify(entries,null,2))}
> 9  |  await capture('ORDER-QUOTE-FAIL-CONFIRM-B-1366',['new order','enter lead time','select source quote']);await confirm.getByRole('button',{name:'取消',exact:true}).click();await expect(modal.getByLabel('交期天数')).toHaveValue('7');await expect(source).toHaveValue('');expect(writes).toBe(0);expect(loads).toBe(0);await capture('ORDER-QUOTE-FAIL-CANCEL-B-1366',['cancel overwrite','verify draft preserved']);await source.selectOption({label:'ISS007-Q001'});await confirm.getByRole('button',{name:'载入报价'}).click();await expect(page.getByText(/无法载入报价/)).toBeVisible();await expect(modal.getByLabel('交期天数')).toHaveValue('7');await expect(source).toHaveValue('');expect(loads).toBe(1);expect(writes).toBe(0);await capture('ORDER-QUOTE-FAIL-B-1366',['confirm quote load','intercept GET with simulated 503'])
     |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  ^ Error: expect(locator).toBeVisible() failed
  10 | })
  11 | 
```