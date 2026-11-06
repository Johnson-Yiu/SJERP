# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: quote-draft-tax-revision.spec.js >> draft tax revision is editable and saves a new version
- Location: browser-tests\quote-draft-tax-revision.spec.js:12:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.waitForResponse: Test timeout of 30000ms exceeded.
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
      - generic [ref=e194]: J
      - generic [ref=e196]:
        - strong [ref=e197]: 开发身份：Johnson
        - generic [ref=e198]: 超级管理员 · 全部功能与数据权限
  - main [ref=e199]:
    - generic [ref=e200]:
      - button [ref=e201] [cursor=pointer]
      - generic [ref=e203]:
        - text: Quotation desk
        - heading "报价管理" [level=1] [ref=e204]
      - generic "Johnson" [ref=e206]: J
    - generic [ref=e208]:
      - generic [ref=e209]:
        - paragraph [ref=e210]: 管理报价、修订版及转单进度。
        - button "新建报价" [ref=e211] [cursor=pointer]
      - region "报价汇总" [ref=e213]:
        - article [ref=e214]:
          - generic [ref=e215]: 报价主单
          - strong [ref=e216]: "1"
          - generic [ref=e220]: 主单数量
        - article [ref=e221]:
          - generic [ref=e222]: 报价修订版
          - strong [ref=e223]: "1"
          - generic [ref=e228]: 含全部版本
        - article [ref=e229]:
          - generic [ref=e230]: 跟进中
          - strong [ref=e231]: "1"
          - generic [ref=e236]: 草稿或已发送
        - article [ref=e237]:
          - generic [ref=e238]: 客户已接受
          - strong [ref=e239]: "0"
          - generic [ref=e244]: 已接受报价
      - generic [ref=e245]:
        - textbox "搜索报价单号或客户" [ref=e250]
        - combobox "按报价状态筛选" [ref=e251]:
          - option "全部状态" [selected]
          - option "草稿"
          - option "已发送"
          - option "已接受"
          - option "已拒绝"
          - option "已过期"
        - combobox "按客户筛选" [ref=e252]:
          - option "全部客户" [selected]
          - option "Synthetic Buyer C6A350C8"
        - combobox "报价排序" [ref=e253]:
          - option "最近更新时间" [selected]
          - option "最早更新时间"
          - option "报价日期（新到旧）"
          - option "报价日期（旧到新）"
        - button "重置" [ref=e254] [cursor=pointer]
      - table [ref=e260]:
        - rowgroup [ref=e261]:
          - row [ref=e262]:
            - columnheader "报价单 / 层级" [ref=e263]
            - columnheader "客户" [ref=e264]
            - columnheader "更新时间" [ref=e265]
            - columnheader "状态" [ref=e266]
            - columnheader "明细" [ref=e267]
            - columnheader "金额" [ref=e268]
            - columnheader "操作" [ref=e269]
        - rowgroup [ref=e270]:
          - row [ref=e271] [cursor=pointer]:
            - cell "PVS-C6A350C8 原始报价" [ref=e272]:
              - generic [ref=e278]:
                - strong [ref=e279]: PVS-C6A350C8
                - generic [ref=e280]: 原始报价
            - cell "Synthetic Buyer C6A350C8" [ref=e281]
            - cell "2026/11/05 15:40" [ref=e282]
            - cell "草稿" [ref=e283]
            - cell "1 项" [ref=e285]
            - cell "USD 10.00" [ref=e286]
            - cell [ref=e287]:
              - generic [ref=e288]:
                - button "查看 PVS-C6A350C8" [ref=e289]
                - button "创建修订版 PVS-C6A350C8" [ref=e293]
                - button "导出 PVS-C6A350C8" [ref=e297]
      - form "报价编辑器" [ref=e302]:
        - generic [ref=e303]:
          - generic [ref=e304]:
            - heading "创建报价修订版" [level=3] [ref=e305]
            - generic [ref=e306]: 基于 PVS-C6A350C8 创建修订版；原报价保留。
          - button "关闭报价编辑器" [ref=e307] [cursor=pointer]
        - group [ref=e312]:
          - generic [ref=e313]:
            - generic [ref=e314]:
              - generic [ref=e315]: 客户 *
              - combobox [disabled] [ref=e316]:
                - option "请选择"
                - option "Synthetic Buyer C6A350C8" [selected]
            - generic [ref=e317]:
              - generic [ref=e318]: 报价单号
              - textbox [disabled] [ref=e319]: PVS-C6A350C8
            - generic [ref=e320]:
              - generic [ref=e321]: 报价日期 *
              - generic [ref=e322]:
                - textbox "年份" [ref=e323]: "2026"
                - generic [ref=e324]: /
                - textbox "月份" [ref=e325]: "11"
                - generic [ref=e326]: /
                - textbox "日期" [ref=e327]: "05"
                - button "打开日期选择器" [ref=e328] [cursor=pointer]
                - textbox: 2026-11-05
            - generic [ref=e331]:
              - generic [ref=e332]: 有效期
              - generic [ref=e333]:
                - spinbutton "有效期天数" [ref=e334]: "30"
                - generic [ref=e335]: 天
                - generic [ref=e336]:
                  - textbox "年份" [ref=e337]: "2026"
                  - generic [ref=e338]: /
                  - textbox "月份" [ref=e339]: "12"
                  - generic [ref=e340]: /
                  - textbox "日期" [ref=e341]: "05"
                  - button "打开日期选择器" [ref=e342] [cursor=pointer]
                  - textbox: 2026-12-05
            - generic [ref=e345]:
              - generic [ref=e346]: 状态
              - textbox [ref=e347]: 草稿
            - generic [ref=e348]:
              - generic [ref=e349]: 币种
              - combobox "单据币种" [ref=e350]:
                - option "USD" [selected]
                - option "CNY"
                - option "EUR"
                - option "GBP"
            - generic [ref=e351]:
              - generic [ref=e352]: 对人民币汇率
              - spinbutton "对人民币汇率" [ref=e353]: "1"
            - generic [ref=e354]:
              - generic [ref=e355]: 交期（天）
              - spinbutton [ref=e356]: "10"
            - generic [ref=e357]:
              - generic [ref=e358]: 定金比例（%）
              - spinbutton [ref=e359]: "0"
            - generic [ref=e360]:
              - generic [ref=e361]: 修订说明 *
              - textbox "例如：调整数量、价格、交期或付款条款" [active] [ref=e362]: 更正草稿税号
              - text: 说明本次调整内容。
          - generic [ref=e364]:
            - strong [ref=e365]: 报价明细
            - generic [ref=e366]: 选择 SKU 后填写数量、交易单位和单价。
          - generic [ref=e367]:
            - generic [ref=e368]:
              - generic [ref=e369]:
                - strong [ref=e370]: 选择 SKU
                - generic [ref=e371]:
                  - searchbox "搜索 SKU、型号或描述" [ref=e372]
                  - button "按产品分类筛选" [ref=e373] [cursor=pointer]:
                    - generic [ref=e374]: 全部分类
              - generic [ref=e377] [cursor=pointer]:
                - 'checkbox "Synthetic Product SKU: PVS-C6A350C8 Sales Model: PVS-C6A350C8 USD 0.00" [checked] [ref=e378]'
                - generic [ref=e379]:
                  - generic [ref=e380]: Synthetic Product
                  - generic [ref=e381]:
                    - generic [ref=e382]: "SKU: PVS-C6A350C8"
                    - generic [ref=e383]: "Sales Model: PVS-C6A350C8"
                - emphasis [ref=e384]: USD 0.00
            - complementary [ref=e385]:
              - generic [ref=e386]: 已选 SKU 详情
              - strong [ref=e387]: Synthetic Product
              - generic [ref=e388]:
                - generic [ref=e389]:
                  - term [ref=e390]: SKU Code
                  - definition [ref=e391]: PVS-C6A350C8
                - generic [ref=e392]:
                  - term [ref=e393]: Sales Model
                  - definition [ref=e394]: PVS-C6A350C8
                - generic [ref=e395]:
                  - term [ref=e396]: 单位 / 默认单价
                  - definition [ref=e397]: pcs / USD 0.00
              - generic [ref=e398]:
                - text: 客户版产品描述可按本次报价调整
                - textbox "已选 SKU 的客户版产品描述" [ref=e399]: Synthetic Product
          - generic [ref=e400]:
            - generic [ref=e401]:
              - generic [ref=e402]: SKU
              - generic [ref=e403]: Model
              - generic [ref=e404]: 数量 *
              - generic [ref=e405]: 单价 *
              - generic [ref=e406]: 产品描述
              - generic [ref=e407]: 小计
            - generic [ref=e408]:
              - generic [ref=e409]:
                - text: PVS-C6A350C8
                - combobox "交易单位与包装规格" [ref=e411]:
                  - option "pcs（基础单位）" [selected]
                - button "增加规格行" [ref=e412] [cursor=pointer]
              - textbox "报价型号" [ref=e413]:
                - /placeholder: 可按客户要求修改
                - text: PVS-C6A350C8
              - spinbutton "数量" [ref=e414]: "1.00"
              - spinbutton "单价" [ref=e415]: "10.00"
              - textbox "产品描述" [ref=e416]: Synthetic Product
              - generic [ref=e417]: "10.00"
              - button "取消选择该 SKU" [ref=e418] [cursor=pointer]
          - region "库存参考" [ref=e421]:
            - generic [ref=e422]:
              - generic [ref=e423]:
                - strong [ref=e424]: 库存参考 · 按 SKU 基础单位
                - generic [ref=e425]: 最近刷新 15:40:38
              - button "刷新库存" [ref=e426] [cursor=pointer]
            - paragraph [ref=e430]: 库存数据为当前参考值，报价不会锁定库存。在途数量不计入当前可用量，最终以订单确认时的库存及采购状态为准。
            - paragraph [ref=e431]: 本报价参考交期：10 天
            - article [ref=e433]:
              - generic [ref=e434]:
                - strong [ref=e435]: PVS-C6A350C8 · Synthetic Product
                - generic [ref=e436]: 库存不足
              - generic [ref=e437]:
                - generic [ref=e438]:
                  - term [ref=e439]: 实际
                  - definition [ref=e440]: 0 pcs
                - generic [ref=e441]:
                  - term [ref=e442]: 预留
                  - definition [ref=e443]: 0 pcs
                - generic [ref=e444]:
                  - term [ref=e445]: 可用
                  - definition [ref=e446]: 0 pcs
                - generic [ref=e447]:
                  - term [ref=e448]: 本报价需求
                  - definition [ref=e449]: 1 pcs
                - generic [ref=e450]:
                  - term [ref=e451]: 在途
                  - definition [ref=e452]: 0 pcs
              - paragraph [ref=e453]: 缺口：1 pcs
          - generic [ref=e455]:
            - generic [ref=e456]:
              - text: 预计装箱方案
              - heading "按 SKU 默认包装配置估算" [level=4] [ref=e457]
            - button "生成预计装箱方案" [ref=e458] [cursor=pointer]
          - generic [ref=e462]:
            - generic [ref=e463]:
              - text: 运费
              - spinbutton "运费" [ref=e464]: "0.00"
            - generic [ref=e465]:
              - text: 折扣
              - spinbutton "折扣" [ref=e466]: "0.00"
            - generic [ref=e467]:
              - text: 商品小计 USD 10.00
              - generic [ref=e468]: 合计
              - strong [ref=e469]: USD 10.00
          - strong [ref=e471]: 收件信息 / 条款
          - generic [ref=e472]:
            - generic [ref=e473]:
              - generic [ref=e474]: 收件人
              - textbox "收件人" [ref=e475]
            - generic [ref=e476]:
              - generic [ref=e477]: 买方税号（选填）
              - textbox "买方税号（选填）" [ref=e478]:
                - /placeholder: ""
                - text: 00999-TEST
            - generic [ref=e479]:
              - generic [ref=e480]: 买方地址
              - textbox "买方地址" [ref=e481]
            - generic [ref=e482]:
              - generic [ref=e483]: 买方邮箱
              - textbox "买方邮箱" [ref=e484]
            - generic [ref=e485]:
              - generic [ref=e486]: 买方电话
              - textbox "买方电话" [ref=e487]
          - generic [ref=e488]:
            - generic [ref=e489]:
              - generic [ref=e490]: 贸易条款
              - textbox [ref=e491]: FOB Shenzhen
            - generic [ref=e492]:
              - generic [ref=e493]: 运输信息
              - textbox [ref=e494]
            - generic [ref=e495]:
              - generic [ref=e496]: 补充备注
              - textbox [ref=e497]
        - generic [ref=e498]:
          - button "取消" [ref=e499] [cursor=pointer]
          - button "预览报价单" [ref=e500] [cursor=pointer]
          - button "保存报价" [ref=e504] [cursor=pointer]
          - button "保存并导出 Excel" [ref=e509] [cursor=pointer]
      - dialog "报价工作台" [ref=e515]:
        - generic [ref=e516]:
          - generic [ref=e518]:
            - button "关闭报价详情" [ref=e519] [cursor=pointer]
            - generic [ref=e523]: 报价工作台 · PVS-C6A350C8
          - generic [ref=e524]:
            - generic [ref=e525]:
              - paragraph [ref=e526]: Synthetic Buyer C6A350C8 · 原始报价
              - heading "PVS-C6A350C8" [level=2] [ref=e527]
              - text: 原始报价：PVS-C6A350C8
            - generic [ref=e528]: 草稿
          - generic "报价状态操作" [ref=e529]:
            - button "标记为已发送" [ref=e530] [cursor=pointer]
            - button "标记为客户已接受" [ref=e531] [cursor=pointer]
            - button "标记为客户已拒绝" [ref=e532] [cursor=pointer]
          - generic [ref=e533]:
            - button "创建修订版" [ref=e534] [cursor=pointer]
            - button "预览 PI" [ref=e538] [cursor=pointer]
            - button "导出 Excel" [ref=e542] [cursor=pointer]
            - button "创建销售订单" [ref=e546] [cursor=pointer]
        - main [ref=e551]:
          - navigation "报价详情分页" [ref=e552]:
            - button "概览" [ref=e553] [cursor=pointer]
            - button "报价明细 (1)" [ref=e554] [cursor=pointer]
            - button "版本谱系 (1)" [ref=e555] [cursor=pointer]
            - button "订单 (0)" [ref=e556] [cursor=pointer]
            - button "主体更正" [ref=e557] [cursor=pointer]
            - button "重要备注 (0)" [ref=e558] [cursor=pointer]
            - button "操作日志 (0)" [ref=e559] [cursor=pointer]
          - generic [ref=e560]:
            - generic [ref=e561]:
              - heading "报价概览" [level=3] [ref=e562]
              - generic [ref=e563]:
                - generic [ref=e564]:
                  - generic [ref=e565]: 报价总额
                  - strong [ref=e566]: USD 10.00
                - generic [ref=e567]:
                  - generic [ref=e568]: 有效期至
                  - strong [ref=e569]: —
                - generic [ref=e570]:
                  - generic [ref=e571]: 商品明细
                  - strong [ref=e572]: 1 项
            - generic [ref=e573]:
              - heading "基础信息" [level=3] [ref=e574]
              - generic [ref=e575]:
                - term [ref=e576]: 报价日期
                - definition [ref=e577]: 2026-11-05
                - term [ref=e578]: 币种 / 汇率
                - definition [ref=e579]: USD / 1
                - term [ref=e580]: 收件人
                - definition [ref=e581]: —
                - term [ref=e582]: 条款备注
                - definition [ref=e583]: —
            - generic [ref=e584]:
              - generic [ref=e585]:
                - generic [ref=e586]:
                  - heading "修订摘要" [level=3] [ref=e587]
                  - paragraph [ref=e592]: 共 1 个版本，当前查看 原始报价。
                - button "查看修订历史" [ref=e593] [cursor=pointer]
              - article [ref=e595]:
                - generic [ref=e596]:
                  - strong [ref=e597]: PVS-C6A350C8
                  - generic [ref=e598]: 原始报价
                  - generic [ref=e599]: 2026/11/05 15:40
                  - generic [ref=e600]: 草稿
                - generic [ref=e601]:
                  - text: USD 10.00
                  - generic [ref=e602]:
                    - button "预览 PI" [ref=e603] [cursor=pointer]
                    - button "查看详情" [disabled] [ref=e604] [cursor=pointer]
            - generic [ref=e605]:
              - heading "销售订单摘要" [level=3] [ref=e606]
              - paragraph [ref=e611]: 已生成 0 张销售订单。
              - button "查看关联销售订单" [ref=e612] [cursor=pointer]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | import { spawnSync } from 'node:child_process'
  3  | import fs from 'node:fs'
  4  | import path from 'node:path'
  5  | test.use({ channel: 'chrome' })
  6  | function seed() {
  7  |   const script=path.resolve('../docs/uat-evidence/party-version-closeout-20261105/seed_browser.py')
  8  |   const run=spawnSync(process.env.ISOLATED_TEST_PYTHON,[script],{cwd:path.resolve('../backend'),env:process.env,encoding:'utf8'})
  9  |   expect(run.status,run.stderr).toBe(0)
  10 |   return JSON.parse(run.stdout.trim().split('\n').at(-1))
  11 | }
  12 | test('draft tax revision is editable and saves a new version',async({page})=>{
  13 |   const fixture=seed()
  14 |   await page.goto(`/quotes?detail=${fixture.id}`)
  15 |   await page.getByRole('dialog',{name:'报价工作台'}).getByRole('button',{name:'创建修订版'}).click()
  16 |   const tax=page.locator('#quote-buyer-tax-id')
  17 |   await expect(tax).toBeEditable()
  18 |   await tax.fill('00999-TEST')
  19 |   await page.locator('.revision-summary textarea').fill('更正草稿税号')
  20 |   for (const width of [1440,390]) {
  21 |     await page.setViewportSize({width,height:width===390?844:900})
  22 |     await tax.scrollIntoViewIfNeeded()
  23 |     await expect(tax).toBeVisible()
  24 |     const evidence=path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,'draft-tax-revision')
  25 |     fs.mkdirSync(evidence,{recursive:true})
  26 |     await page.screenshot({path:path.join(evidence,`draft-${width}.png`)})
  27 |   }
> 28 |   const response=page.waitForResponse(r=>r.url().includes(`/api/quotes/${fixture.id}/revise/`) && r.request().method()==='POST')
     |                       ^ Error: page.waitForResponse: Test timeout of 30000ms exceeded.
  29 |   await page.locator('.quote-action-save').click()
  30 |   const result=await response
  31 |   expect(result.status()).toBe(201)
  32 |   expect((await result.json()).buyer_tax_id).toBe('00999-TEST')
  33 |   expect((await (await page.request.get(`/api/quotes/${fixture.id}/`)).json()).buyer_tax_id).toBe('00123-SYNTHETIC')
  34 | })
  35 | test('formal quote revision remains read only',async({page})=>{
  36 |   const fixture=seed()
  37 |   const sent=await page.request.post(`/api/quotes/${fixture.id}/mark-sent/`)
  38 |   expect(sent.status()).toBe(200)
  39 |   await page.goto(`/quotes?detail=${fixture.id}`)
  40 |   await page.getByRole('dialog',{name:'报价工作台'}).getByRole('button',{name:'创建修订版'}).click()
  41 |   await expect(page.locator('#quote-buyer-tax-id')).toHaveAttribute('readonly','')
  42 | })
  43 | 
```