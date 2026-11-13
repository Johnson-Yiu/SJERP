# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: product-draft-protection-01.spec.js >> C editors, batch results and product logs retain real state
- Location: browser-tests\product-draft-protection-01.spec.js:7:1

# Error details

```
TimeoutError: locator.click: Timeout 15000ms exceeded.
Call log:
  - waiting for getByRole('button', { name: '＋ 添加规则', exact: true })

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
        - text: 产品资料
        - heading "产品管理" [level=1] [ref=e209]
      - generic [ref=e210]:
        - generic [ref=e211]: 11月14日周六
        - generic "codex" [ref=e212]: C
    - tablist "业务工作区" [ref=e214]:
      - generic [ref=e215]:
        - tab "C 合成轨道灯产品" [selected] [ref=e216] [cursor=pointer]
        - button "关闭 C 合成轨道灯产品" [ref=e217] [cursor=pointer]: ×
        - button "C 合成轨道灯产品 标签操作" [ref=e218] [cursor=pointer]: ⋮
    - tabpanel "C 合成轨道灯产品" [ref=e220]:
      - generic [ref=e221]:
        - generic [ref=e222]:
          - generic [ref=e223]:
            - heading "产品管理" [level=2] [ref=e224]
            - paragraph [ref=e225]: 维护产品名称、分类和销售状态；SKU 编码请在“SKU 管理”中维护。
          - button "新建产品" [ref=e226] [cursor=pointer]
        - region "页面小计" [ref=e229]:
          - article [ref=e230]:
            - generic [ref=e231]: 产品总数
            - strong [ref=e232]: "2"
            - generic [ref=e233]: 当前筛选范围
          - article [ref=e237]:
            - generic [ref=e238]: 在售产品
            - strong [ref=e239]: "2"
            - generic [ref=e240]: 可继续添加 SKU
          - article [ref=e244]:
            - generic [ref=e245]: 开发中
            - strong [ref=e246]: "0"
            - generic [ref=e247]: 尚未正式销售
          - article [ref=e251]:
            - generic [ref=e252]: SKU 总数
            - strong [ref=e253]: "2"
            - generic [ref=e254]: 产品下的 SKU
        - generic [ref=e258]:
          - textbox "搜索产品" [ref=e263]:
            - /placeholder: 搜索产品编号或名称
          - combobox "产品分类筛选" [ref=e266] [cursor=pointer]:
            - option "全部分类" [selected]
          - combobox "产品排序" [ref=e267]:
            - option "产品编号顺序" [selected]
            - option "产品名称顺序"
            - option "SKU 数量最多"
          - button "查询" [ref=e268] [cursor=pointer]
          - button "重置" [ref=e269] [cursor=pointer]
          - button "刷新" [ref=e270] [cursor=pointer]
        - table [ref=e273]:
          - rowgroup [ref=e274]:
            - row [ref=e275]:
              - columnheader "产品编号" [ref=e276]
              - columnheader "产品名称" [ref=e277]
              - columnheader "销售型号前缀" [ref=e278]
              - columnheader "主分类" [ref=e279]
              - columnheader "状态" [ref=e280]
              - columnheader "SKU" [ref=e281]
              - columnheader "参数" [ref=e282]
              - columnheader "证书" [ref=e283]
              - columnheader [ref=e284]
          - rowgroup [ref=e285]:
            - row [ref=e286] [cursor=pointer]:
              - cell "C-P001" [ref=e287]
              - cell "C 合成轨道灯产品 未填写英文名称" [ref=e288]:
                - strong [ref=e289]: C 合成轨道灯产品
                - generic [ref=e290]: 未填写英文名称
              - cell "—" [ref=e291]
              - cell "未分类" [ref=e292]
              - cell "在售" [ref=e293]
              - cell "2" [ref=e295]
              - cell "0" [ref=e296]
              - cell "0" [ref=e297]
              - cell [ref=e298]:
                - generic [ref=e299]:
                  - button "编辑产品" [ref=e300]
                  - button "删除产品" [ref=e304]
            - row [ref=e308] [cursor=pointer]:
              - cell "C-PKG-P" [ref=e309]
              - cell "合成包装选择验收产品 未填写英文名称" [ref=e310]:
                - strong [ref=e311]: 合成包装选择验收产品
                - generic [ref=e312]: 未填写英文名称
              - cell "—" [ref=e313]
              - cell "未分类" [ref=e314]
              - cell "在售" [ref=e315]
              - cell "0" [ref=e317]
              - cell "0" [ref=e318]
              - cell "0" [ref=e319]
              - cell [ref=e320]:
                - generic [ref=e321]:
                  - button "编辑产品" [ref=e322]
                  - button "删除产品" [ref=e326]
        - article "关联详情" [ref=e331]:
          - generic [ref=e332]:
            - generic [ref=e333]:
              - generic [ref=e334]: 产品管理 / 产品详情
              - generic [ref=e336]:
                - link "查看经营分析" [ref=e337] [cursor=pointer]:
                  - /url: /reports?source=sales&group_by=product&filter_product=2&title=%E4%BA%A7%E5%93%81%E9%94%80%E5%94%AE%E5%88%86%E6%9E%90&returnTo=/products?detail=2%26tab=suppliers
                - button "编辑主档" [ref=e342] [cursor=pointer]
                - button "关闭详情" [ref=e346] [cursor=pointer]:
                  - generic [ref=e350]: 关闭
            - generic [ref=e351]:
              - generic [ref=e352]:
                - text: C-P001 · 未分类
                - heading "C 合成轨道灯产品" [level=2] [ref=e353]
              - generic [ref=e354]: 在售
            - generic [ref=e355]:
              - generic [ref=e356]:
                - generic [ref=e357]: SKU
                - strong [ref=e358]: "2"
              - generic [ref=e359]:
                - generic [ref=e360]: 供应商
                - strong [ref=e361]: "0"
              - generic [ref=e362]:
                - generic [ref=e363]: 当前库存
                - strong [ref=e364]: "0"
              - generic [ref=e365]:
                - generic [ref=e366]: 参数
                - strong [ref=e367]: "0"
          - generic [ref=e368]:
            - navigation "产品详情导航" [ref=e369]:
              - button "总览" [ref=e370] [cursor=pointer]
              - button "SKU 管理2" [ref=e371] [cursor=pointer]
              - button "供应能力规则0" [ref=e372] [cursor=pointer]
              - button "订单记录0" [ref=e373] [cursor=pointer]
              - button "销售统计" [ref=e374] [cursor=pointer]
              - button "出入库流水0" [ref=e375] [cursor=pointer]
              - button "产品参数0" [ref=e376] [cursor=pointer]
              - button "证书档案0" [ref=e377] [cursor=pointer]
              - button "销售规则" [ref=e378] [cursor=pointer]
              - button "操作日志" [ref=e379] [cursor=pointer]
            - main [ref=e380]:
              - region "SKU 参数与供应商管理" [ref=e381]:
                - generic [ref=e383]:
                  - heading "供应能力规则" [level=3] [ref=e384]
                  - paragraph [ref=e385]: 一份 SKU 清单管理规格与供货候选；实际采购供应商在销售订单或采购单中确认。
                - paragraph [ref=e386]: 正在加载…
```

# Test source

```ts
  1   | import './product-packaging-p2-05.spec.js'
  2   | import { execFileSync } from 'node:child_process'
  3   | import { fileURLToPath } from 'node:url'
  4   | import path from 'node:path'
  5   | import { expect, test } from '@playwright/test'
  6   | 
  7   | test('C editors, batch results and product logs retain real state', async ({ page }, info) => {
  8   |   test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)), 'Dedicated isolated Chrome profile only.')
  9   |   test.setTimeout(600000)
  10  |   page.setDefaultTimeout(15000)
  11  |   const repository = new URL('../../', import.meta.url)
  12  |   const seed = fileURLToPath(new URL('docs/uat-evidence/product-draft-protection-01/seed.py', repository))
  13  |   const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {cwd:fileURLToPath(new URL('backend/',repository)),encoding:'utf8'}).replace(/^\uFEFF/,''))
  14  |   const shot = name => page.screenshot({path:info.outputPath(`${name}.png`)})
  15  |   for (const width of [1366,1920,390]) {
  16  |     await page.setViewportSize({width,height:width===1366?768:width===1920?1080:844})
  17  |     await page.goto(`/products?detail=${fixture.product}&tab=suppliers`)
> 18  |     await page.getByRole('button',{name:'＋ 添加规则',exact:true}).click()
      |                                                               ^ TimeoutError: locator.click: Timeout 15000ms exceeded.
  19  |     const name=page.getByLabel('规则名称',{exact:true})
  20  |     await name.fill(`合成能力规则 ${width}`)
  21  |     await page.locator('form.editor select').selectOption(String(fixture.supplier))
  22  |     await page.getByLabel('共同供货特点',{exact:true}).fill('包装：合成测试纸盒')
  23  |     await shot(`rule-filled-${width}`)
  24  |     await page.getByRole('button',{name:'预览匹配',exact:true}).click()
  25  |     await expect(page.getByText('匹配 2 个现有 SKU：',{exact:false})).toBeVisible()
  26  |     await shot(`rule-preview-before-save-${width}`)
  27  |     await page.getByRole('button',{name:'预览匹配',exact:true}).press('Enter')
  28  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  29  |     await page.getByTestId('dialog-cancel').click()
  30  |     await expect(name).toHaveValue(`合成能力规则 ${width}`)
  31  |     await shot(`rule-retained-${width}`)
  32  |     if (width !== 390) {
  33  |       await page.getByRole('link',{name:'客户管理',exact:true}).click()
  34  |       await expect(page).toHaveURL(/customers/)
  35  |       await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  36  |       await page.getByRole('tab',{name:/C 合成轨道灯产品/}).click()
  37  |       await expect(name).toHaveValue(`合成能力规则 ${width}`)
  38  |       await page.getByRole('button',{name:'关闭 C 合成轨道灯产品',exact:true}).click()
  39  |       await page.getByTestId('dialog-cancel').click()
  40  |       await expect(name).toHaveValue(`合成能力规则 ${width}`)
  41  |       const dialogEvent=page.waitForEvent('dialog')
  42  |       const refresh=page.reload().catch(()=>{})
  43  |       const refreshDialog=await dialogEvent
  44  |       expect(refreshDialog.type()).toBe('beforeunload')
  45  |       await refreshDialog.dismiss(); await refresh
  46  |       await expect(name).toHaveValue(`合成能力规则 ${width}`)
  47  |     }
  48  |     // A rejected save must retain values and the dirty guard.
  49  |     await page.route('**/api/supplier-capabilities/', async route => route.request().method()==='POST' ? route.fulfill({status:400,json:{detail:'合成保存失败，请重试'}}) : route.continue())
  50  |     await page.getByRole('button',{name:'保存规则',exact:true}).click()
  51  |     await expect(name).toHaveValue(`合成能力规则 ${width}`)
  52  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  53  |     await page.getByTestId('dialog-cancel').click()
  54  |     await page.unroute('**/api/supplier-capabilities/')
  55  |     await page.getByRole('button',{name:'保存规则',exact:true}).click()
  56  |     await expect(name).toHaveCount(0)
  57  |     const rules=await (await page.request.get(`/api/supplier-capabilities/?product=${fixture.product}`)).json()
  58  |     expect((rules.results||rules).some(rule=>rule.name===`合成能力规则 ${width}` && rule.characteristics['包装']==='合成测试纸盒')).toBeTruthy()
  59  |     await shot(`rule-saved-${width}`)
  60  |     await page.getByRole('button',{name:'＋ 添加规则',exact:true}).click()
  61  |     await name.fill('明确放弃的合成规则')
  62  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  63  |     await page.getByTestId('dialog-confirm').click()
  64  |     await expect(name).toHaveCount(0)
  65  |     await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  66  |     await page.getByRole('button',{name:'操作日志',exact:true}).click()
  67  |     await expect(page).toHaveURL(/tab=operation_logs/)
  68  |     await page.reload()
  69  |     await expect(page.getByRole('button',{name:'操作日志',exact:true})).toHaveClass(/active/)
  70  |     await expect(page.locator('.operation-log-panel')).toBeVisible()
  71  |     await shot(`log-reopened-${width}`)
  72  |     await page.goto(`/products?detail=${fixture.product}&tab=skus`)
  73  |     await page.locator('.parameter-plan-panel summary').click()
  74  |     await page.getByRole('button',{name:/创建参数方案草稿|继续 V\d+ 草稿/}).click()
  75  |     await expect(page.locator('.parameter-plan-panel .editor')).toBeVisible()
  76  |     if (await page.getByLabel('参数名称',{exact:true}).count()===0) await page.getByRole('button',{name:'＋ 新增参数',exact:true}).click()
  77  |     const parameter=page.getByLabel('参数名称',{exact:true}).first()
  78  |     await parameter.fill(`合成参数 ${width}`)
  79  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  80  |     await page.getByTestId('dialog-cancel').click()
  81  |     await expect(parameter).toHaveValue(`合成参数 ${width}`)
  82  |     await page.getByRole('button',{name:/继续 V\d+ 草稿/}).click()
  83  |     await page.getByTestId('dialog-cancel').click()
  84  |     await expect(parameter).toHaveValue(`合成参数 ${width}`)
  85  |     await shot(`plan-retained-${width}`)
  86  |     if (width !== 390) {
  87  |       await page.getByRole('button',{name:'关闭 C 合成轨道灯产品',exact:true}).click()
  88  |       await page.getByTestId('dialog-cancel').click()
  89  |       await expect(parameter).toHaveValue(`合成参数 ${width}`)
  90  |     }
  91  |     await page.route(`**/api/products/${fixture.product}/sku-plan/`, route=>route.request().method()==='PATCH'?route.fulfill({status:400,json:{detail:'合成方案保存失败'}}):route.continue())
  92  |     await page.getByRole('button',{name:'保存草稿并分析影响',exact:true}).click()
  93  |     await expect(page.getByText('合成方案保存失败',{exact:true})).toBeVisible()
  94  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  95  |     await page.getByTestId('dialog-cancel').click()
  96  |     await expect(parameter).toHaveValue(`合成参数 ${width}`)
  97  |     await page.unroute(`**/api/products/${fixture.product}/sku-plan/`)
  98  |     await page.getByRole('button',{name:'保存草稿并分析影响',exact:true}).click()
  99  |     await expect(page.getByRole('heading',{name:'发布前核对',exact:true})).toBeVisible()
  100 |     const plan=await (await page.request.get(`/api/products/${fixture.product}/sku-plan/`)).json()
  101 |     expect(plan.plans.find(p=>p.status==='draft').definitions[0].name).toBe(`合成参数 ${width}`)
  102 |     await shot(`plan-saved-readback-${width}`)
  103 |     await page.getByRole('button',{name:'总览',exact:true}).click()
  104 |     await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  105 |     await page.goto(`/products?detail=${fixture.product}&tab=skus`)
  106 |     await page.locator('.parameter-plan-panel summary').click()
  107 |     await page.getByRole('button',{name:/继续 V\d+ 草稿/}).click()
  108 |     await expect(parameter).toHaveValue(`合成参数 ${width}`)
  109 |     await parameter.fill('明确放弃的合成参数')
  110 |     await page.getByRole('button',{name:'总览',exact:true}).click()
  111 |     await page.getByTestId('dialog-confirm').click()
  112 |     await expect(parameter).toHaveCount(0)
  113 |     await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  114 |   }
  115 |   await page.setViewportSize({width:1366,height:768})
  116 |   await page.goto(`/products?detail=${fixture.product}&tab=skus`)
  117 |   const rows=page.locator('.candidate-table tbody tr')
  118 |   await expect(rows).toHaveCount(2)
```