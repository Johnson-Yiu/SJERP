# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui-coverage-02-order-quote-failure.spec.js >> order source quote overwrite confirmation cancellation
- Location: browser-tests\ui-coverage-02-order-quote-failure.spec.js:6:1

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: 1
Received: 2
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
      - link "银行资金记录" [ref=e164] [cursor=pointer]:
        - /url: /rmb-cash-events
      - link "账户余额与对账" [ref=e170] [cursor=pointer]:
        - /url: /finance-ledger
      - link "数据导入" [ref=e176] [cursor=pointer]:
        - /url: /import
      - link "历史资料预检" [ref=e181] [cursor=pointer]:
        - /url: /history-preflight
      - link "历史资料承接" [ref=e187] [cursor=pointer]:
        - /url: /history-takeover
      - generic [ref=e193]: 组织与系统
      - link "组织与权限" [ref=e194] [cursor=pointer]:
        - /url: /organization
    - generic [ref=e199]:
      - generic [ref=e200]: C
      - generic [ref=e202]:
        - strong [ref=e203]: 当前账号：codex
        - generic [ref=e204]: 超级管理员 · 全部功能与数据权限
      - button "退出登录" [ref=e205] [cursor=pointer]
  - main [ref=e206]:
    - generic [ref=e207]:
      - generic [ref=e208]:
        - text: Sales orders
        - heading "订单管理" [level=1] [ref=e209]
      - generic [ref=e210]:
        - generic [ref=e211]: 11月10日周二
        - generic "codex" [ref=e212]: C
    - tablist "业务工作区" [ref=e214]:
      - generic [ref=e215]:
        - tab "订单管理" [ref=e216] [cursor=pointer]
        - button "关闭 订单管理" [ref=e217] [cursor=pointer]: ×
        - button "订单管理 标签操作" [ref=e218] [cursor=pointer]: ⋮
      - generic [ref=e219]:
        - tab "订单管理 · 新建 1未保存" [selected] [ref=e220] [cursor=pointer]: 订单管理 · 新建 1 ●
        - button "关闭 订单管理 · 新建 1" [ref=e221] [cursor=pointer]: ×
        - button "订单管理 · 新建 1 标签操作" [ref=e222] [cursor=pointer]: ⋮
    - tabpanel "订单管理 · 新建 1" [ref=e224]:
      - generic [ref=e225]:
        - generic [ref=e226]:
          - paragraph [ref=e227]: 管理销售订单、履约与回款。
          - button "新建订单" [ref=e228] [cursor=pointer]
        - region "页面小计" [ref=e231]:
          - article [ref=e232]:
            - generic [ref=e233]: 执行中
            - strong [ref=e234]: "0"
            - generic [ref=e235]: 已确认 / 生产中 / 已发货
          - article [ref=e239]:
            - generic [ref=e240]: 待出库
            - strong [ref=e241]: "0"
            - generic [ref=e242]: 尚未完成发货
          - article [ref=e246]:
            - generic [ref=e247]: 待收款
            - strong [ref=e248]: "0"
            - generic [ref=e249]: 仍有应收余额
          - article [ref=e253]:
            - generic [ref=e254]: 已完成
            - strong [ref=e255]: "0"
            - generic [ref=e256]: 已完成交付
        - generic [ref=e260]:
          - textbox "搜索订单号或客户" [ref=e265]
          - combobox "按订单状态筛选" [ref=e266]:
            - option "全部状态" [selected]
            - option "草稿"
            - option "已确认"
            - option "生产中"
            - option "已发货"
            - option "已完成"
            - option "已取消"
          - combobox "按订单待办筛选" [ref=e267]:
            - option "全部待办" [selected]
            - option "待出库"
            - option "交期已到"
          - button "重置" [ref=e268] [cursor=pointer]
        - status [ref=e273]:
          - heading "暂无订单" [level=3] [ref=e274]
          - paragraph [ref=e275]: 点击“新建订单”开始录入。
        - generic [ref=e277]:
          - generic [ref=e278]:
            - heading "新建订单" [level=3] [ref=e280]
            - button [ref=e281] [cursor=pointer]
          - generic [ref=e285]:
            - generic [ref=e286]:
              - generic [ref=e287]:
                - generic [ref=e288]: 订单号
                - textbox [ref=e289]: 保存后由系统自动生成
              - generic [ref=e290]:
                - generic [ref=e291]: 客户 *
                - combobox [disabled] [ref=e292]:
                  - option "请选择" [selected]
                  - option "ISS007 隔离验收客户"
              - generic [ref=e293]:
                - generic [ref=e294]: 订单日期 *
                - generic [ref=e295]:
                  - textbox "年份" [ref=e296]: "2026"
                  - generic [ref=e297]: /
                  - textbox "月份" [ref=e298]: "11"
                  - generic [ref=e299]: /
                  - textbox "日期" [ref=e300]: "10"
                  - button "打开日期选择器" [ref=e301] [cursor=pointer]
                  - textbox: 2026-11-10
              - generic [ref=e304]:
                - generic [ref=e305]: 预计交期
                - generic [ref=e306]:
                  - spinbutton "交期天数" [ref=e307]: "7"
                  - generic [ref=e308]: 天
                  - generic [ref=e309]:
                    - textbox "年份" [ref=e310]: "2026"
                    - generic [ref=e311]: /
                    - textbox "月份" [ref=e312]: "11"
                    - generic [ref=e313]: /
                    - textbox "日期" [ref=e314]: "17"
                    - button "打开日期选择器" [ref=e315] [cursor=pointer]
                    - textbox: 2026-11-17
              - generic [ref=e318]:
                - generic [ref=e319]: 状态
                - textbox [ref=e320]: 草稿
                - text: 保存后为草稿；确认订单后进入履约。
              - generic [ref=e321]:
                - generic [ref=e322]: 来源报价（可选）
                - combobox "来源报价（可选）" [disabled] [ref=e323]:
                  - option "不关联报价" [selected]
                  - option "ISS007-Q001"
              - generic [ref=e324]:
                - generic [ref=e325]: 币种
                - combobox "单据币种" [ref=e326]:
                  - option "USD" [selected]
                  - option "CNY"
                  - option "EUR"
                  - option "GBP"
              - generic [ref=e327]:
                - generic [ref=e328]: 对人民币汇率
                - spinbutton "对人民币汇率" [ref=e329]: "7.2"
            - generic [ref=e331]:
              - strong [ref=e332]: 产品明细
              - generic [ref=e333]: 先选择一个或多个 SKU，再填写数量与价格
            - generic [ref=e334]:
              - generic [ref=e335]:
                - generic [ref=e336]:
                  - strong [ref=e337]: 选择 SKU
                  - generic [ref=e338]:
                    - searchbox "搜索 SKU、型号或描述" [ref=e339]
                    - button "按产品分类筛选" [ref=e340] [cursor=pointer]:
                      - generic [ref=e341]: 全部分类
                - generic [ref=e345] [cursor=pointer]:
                  - 'checkbox "ISS007 可上传图片 SKU SKU: ISS007-SKU001 Sales Model: ISS7-001 USD 0.00" [ref=e346]'
                  - generic [ref=e347]:
                    - generic [ref=e348]: ISS007 可上传图片 SKU
                    - generic [ref=e349]:
                      - generic [ref=e350]: "SKU: ISS007-SKU001"
                      - generic [ref=e351]: "Sales Model: ISS7-001"
                  - emphasis [ref=e352]: USD 0.00
              - complementary [ref=e353]:
                - paragraph [ref=e354]: 从左侧勾选 SKU 后，可在这里查看详情。
            - generic [ref=e355]:
              - generic [ref=e356]:
                - generic [ref=e357]: SKU
                - generic [ref=e358]: 数量 *
                - generic [ref=e359]: 单价 *
                - generic [ref=e360]: 成本
                - generic [ref=e361]: 小计
              - paragraph [ref=e362]: 请先从上方选择至少一个 SKU。
            - generic [ref=e363]:
              - generic [ref=e364]:
                - text: 运费
                - spinbutton "运费" [ref=e365]: "0.00"
              - generic [ref=e366]:
                - text: 折扣
                - spinbutton "折扣" [ref=e367]: "0.00"
              - generic [ref=e368]:
                - text: 商品小计 USD 0.00
                - generic [ref=e369]: 合计
                - strong [ref=e370]: USD 0.00
            - generic [ref=e371]:
              - generic [ref=e372]: 条款 / 备注
              - textbox [ref=e373]
          - generic [ref=e374]:
            - button "取消" [ref=e375] [cursor=pointer]
            - button "保存销售订单草稿" [disabled] [ref=e376] [cursor=pointer]
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
> 9  |  await capture('ORDER-QUOTE-FAIL-CONFIRM-B-1366',['new order','enter lead time','select source quote']);await confirm.getByRole('button',{name:'取消',exact:true}).click();await expect(modal.getByLabel('交期天数')).toHaveValue('7');await expect(source).toHaveValue('');expect(writes).toBe(0);expect(loads).toBe(0);await capture('ORDER-QUOTE-FAIL-CANCEL-B-1366',['cancel overwrite','verify draft preserved']);await source.selectOption({label:'ISS007-Q001'});await confirm.getByRole('button',{name:'载入报价'}).click();await expect.poll(()=>loads).toBe(1);await page.waitForTimeout(200);await expect(modal.getByLabel('交期天数')).toHaveValue('7');await expect(source).toHaveValue('');expect(loads).toBe(1);expect(writes).toBe(0);await capture('ORDER-QUOTE-FAIL-B-1366',['confirm quote load','intercept GET with simulated 503'])
     |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          ^ Error: expect(received).toBe(expected) // Object.is equality
  10 | })
  11 | 
```