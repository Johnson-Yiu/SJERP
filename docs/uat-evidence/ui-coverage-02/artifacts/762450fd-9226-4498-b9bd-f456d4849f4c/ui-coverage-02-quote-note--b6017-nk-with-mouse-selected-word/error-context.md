# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui-coverage-02-quote-note-mouse.spec.js >> quote note link with mouse-selected word
- Location: browser-tests\ui-coverage-02-quote-note-mouse.spec.js:6:1

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: "linkword"
Received: ""
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
        - text: Quotation desk
        - heading "报价管理" [level=1] [ref=e209]
      - generic [ref=e210]:
        - generic [ref=e211]: 11月10日周二
        - generic "codex" [ref=e212]: C
    - tablist "业务工作区" [ref=e214]:
      - generic [ref=e215]:
        - tab "报价管理" [ref=e216] [cursor=pointer]
        - button "关闭 报价管理" [ref=e217] [cursor=pointer]: ×
        - button "报价管理 标签操作" [ref=e218] [cursor=pointer]: ⋮
      - generic [ref=e219]:
        - tab "ISS007-Q001" [selected] [ref=e220] [cursor=pointer]
        - button "关闭 ISS007-Q001" [ref=e221] [cursor=pointer]: ×
        - button "ISS007-Q001 标签操作" [ref=e222] [cursor=pointer]: ⋮
    - tabpanel "ISS007-Q001" [ref=e224]:
      - generic [ref=e225]:
        - generic [ref=e226]:
          - paragraph [ref=e227]: 管理报价、修订版及转单进度。
          - button "新建报价" [ref=e228] [cursor=pointer]
        - region "报价汇总" [ref=e230]:
          - article [ref=e231]:
            - generic [ref=e232]: 报价主单
            - strong [ref=e233]: "1"
            - generic [ref=e237]: 主单数量
          - article [ref=e238]:
            - generic [ref=e239]: 报价修订版
            - strong [ref=e240]: "1"
            - generic [ref=e245]: 含全部版本
          - article [ref=e246]:
            - generic [ref=e247]: 跟进中
            - strong [ref=e248]: "1"
            - generic [ref=e253]: 草稿或已发送
          - article [ref=e254]:
            - generic [ref=e255]: 客户已接受
            - strong [ref=e256]: "0"
            - generic [ref=e261]: 已接受报价
        - generic [ref=e262]:
          - textbox "搜索报价单号或客户" [ref=e267]
          - combobox "按报价状态筛选" [ref=e268]:
            - option "全部状态" [selected]
            - option "草稿"
            - option "已发送"
            - option "已接受"
            - option "已拒绝"
            - option "已过期"
          - combobox "按客户筛选" [ref=e269]:
            - option "全部客户" [selected]
            - option "ISS007 隔离验收客户"
          - combobox "报价排序" [ref=e270]:
            - option "最近更新时间" [selected]
            - option "最早更新时间"
            - option "报价日期（新到旧）"
            - option "报价日期（旧到新）"
          - button "重置" [ref=e271] [cursor=pointer]
        - table [ref=e277]:
          - rowgroup [ref=e278]:
            - row [ref=e279]:
              - columnheader "报价单 / 层级" [ref=e280]
              - columnheader "客户" [ref=e281]
              - columnheader "更新时间" [ref=e282]
              - columnheader "状态" [ref=e283]
              - columnheader "明细" [ref=e284]
              - columnheader "金额" [ref=e285]
              - columnheader "操作" [ref=e286]
          - rowgroup [ref=e287]:
            - row [ref=e288] [cursor=pointer]:
              - cell "ISS007-Q001 原始报价" [ref=e289]:
                - generic [ref=e295]:
                  - strong [ref=e296]: ISS007-Q001
                  - generic [ref=e297]: 原始报价
              - cell "ISS007 隔离验收客户" [ref=e298]
              - cell "2026/11/10 09:00" [ref=e299]
              - cell "草稿" [ref=e300]
              - cell "1 项" [ref=e302]
              - cell "USD 25.00" [ref=e303]
              - cell [ref=e304]:
                - generic [ref=e305]:
                  - button "查看 ISS007-Q001" [ref=e306]
                  - button "创建修订版 ISS007-Q001" [ref=e310]
                  - button "导出 ISS007-Q001" [ref=e314]
        - dialog "报价工作台" [ref=e319]:
          - generic [ref=e320]:
            - generic [ref=e322]:
              - button "关闭报价详情" [ref=e323] [cursor=pointer]:
                - generic [ref=e327]: 关闭
              - generic [ref=e328]: 报价工作台 · ISS007-Q001
            - generic [ref=e329]:
              - generic [ref=e330]:
                - paragraph [ref=e331]: ISS007 隔离验收客户 · 原始报价
                - heading "ISS007-Q001" [level=2] [ref=e332]
                - text: 原始报价：ISS007-Q001
              - generic [ref=e333]: 草稿
            - generic "报价状态操作" [ref=e334]:
              - button "标记为已发送" [ref=e335] [cursor=pointer]
              - button "标记为客户已接受" [ref=e336] [cursor=pointer]
              - button "标记为客户已拒绝" [ref=e337] [cursor=pointer]
            - generic [ref=e338]:
              - button "创建修订版" [ref=e339] [cursor=pointer]
              - button "预览 PI" [ref=e343] [cursor=pointer]
              - button "导出 Excel" [ref=e347] [cursor=pointer]
              - button "创建销售订单" [ref=e351] [cursor=pointer]
          - main [ref=e356]:
            - navigation "报价详情分页" [ref=e357]:
              - button "概览" [ref=e358] [cursor=pointer]
              - button "报价明细 (1)" [ref=e359] [cursor=pointer]
              - button "版本谱系 (1)" [ref=e360] [cursor=pointer]
              - button "订单 (0)" [ref=e361] [cursor=pointer]
              - button "主体更正" [ref=e362] [cursor=pointer]
              - button "重要备注 (0)" [ref=e363] [cursor=pointer]
              - button "操作日志 (0)" [ref=e364] [cursor=pointer]
            - generic [ref=e365]:
              - paragraph [ref=e369]: 备注可能已过时或不适用于最终订单，请核对来源版本和沟通记录。
              - generic [ref=e371]:
                - heading "重要备注" [level=3] [ref=e372]
                - paragraph [ref=e376]: 备注关联当前报价版本。
              - generic [ref=e377]:
                - generic "富文本工具栏" [ref=e378]:
                  - button "段落" [ref=e379] [cursor=pointer]: P
                  - button "加粗" [ref=e380] [cursor=pointer]
                  - button "项目列表" [ref=e383] [cursor=pointer]
                  - button "编号列表" [ref=e385] [cursor=pointer]
                  - button "插入链接" [ref=e389] [cursor=pointer]
                  - generic [ref=e393]: 支持段落、加粗、列表和链接
                - textbox [active] [ref=e394]
              - generic [ref=e395]:
                - button "取消" [ref=e396] [cursor=pointer]
                - button "保存重要备注" [ref=e397] [cursor=pointer]
              - strong [ref=e402]: 暂无重要备注
```

# Test source

```ts
  1 | import {test,expect} from '@playwright/test'
  2 | import {mkdir,writeFile} from 'node:fs/promises'
  3 | import {createHash} from 'node:crypto'
  4 | import path from 'node:path'
  5 | test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
  6 | test('quote note link with mouse-selected word',async({page,browser})=>{
> 7 |  test.setTimeout(90000);const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT;await mkdir(path.join(root,'originals'),{recursive:true});let writes=0;await page.route('**/api/quotes/**',async r=>{if(!['GET','HEAD','OPTIONS'].includes(r.request().method())){writes++;await r.abort()}else await r.continue()});await page.goto('/quotes',{waitUntil:'networkidle'});await page.getByRole('row').filter({hasText:'ISS007-Q001'}).click();const quote=page.getByRole('dialog',{name:'报价工作台'});await quote.getByRole('button',{name:/重要备注/}).click();await quote.getByRole('button',{name:'新增备注'}).click();const editor=quote.locator('[contenteditable=true]');await editor.fill('linkword');await editor.dblclick();const selectedBefore=await page.evaluate(()=>getSelection().toString());expect(selectedBefore).toBe('linkword');await quote.getByRole('button',{name:'插入链接'}).click();const dialog=page.getByRole('dialog',{name:'插入链接'});await dialog.getByLabel('链接地址').fill('https://example.com');await dialog.getByRole('button',{name:'插入链接'}).click();const anchor=editor.locator('a');await expect(anchor).toHaveAttribute('href','https://example.com');const anchorText=await anchor.innerText(),editorText=await editor.innerText();expect(writes).toBe(0);const id='QUOTE-NOTE-LINK-MOUSE-B-1366',n=id+'.png',b=await page.screenshot({path:path.join(root,'originals',n)});await writeFile(path.join(root,'quote-note-link-mouse-manifest.json'),JSON.stringify([{evidence_id:id,surface_id:'S005',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),viewport:{width:1366,height:768},role:'authenticated codex test superuser',data:'isolated ISS007-Q001',steps:['type linkword','double click word','insert https URL'],selectedBefore,anchorText,editorText,writes,simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${n}`,sha256:createHash('sha256').update(b).digest('hex'),review:'NOT_REVIEWED',limitation:'one mouse selection, unsaved note'}],null,2))
    |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          ^ Error: expect(received).toBe(expected) // Object.is equality
  8 | })
  9 | 
```