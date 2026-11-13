# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: product-draft-protection-01.spec.js >> C editors, batch results and product logs retain real state
- Location: browser-tests\product-draft-protection-01.spec.js:6:1

# Error details

```
TimeoutError: locator.click: Timeout 15000ms exceeded.
Call log:
  - waiting for getByRole('button', { name: '预览匹配', exact: true })

```

# Page snapshot

```yaml
- generic [ref=f3e3]:
  - complementary [ref=f3e4]:
    - generic [ref=f3e5]:
      - generic [ref=f3e6]: S
      - generic [ref=f3e7]:
        - strong [ref=f3e8]: 森爵照明管理系统
        - text: 客户 · 销售 · 产品
    - navigation [ref=f3e9]:
      - generic [ref=f3e10]: 经营
      - link "经营概览" [ref=f3e11] [cursor=pointer]:
        - /url: /
      - link "报表中心" [ref=f3e18] [cursor=pointer]:
        - /url: /reports
      - link "历史订单分析" [ref=f3e25] [cursor=pointer]:
        - /url: /historical-orders
      - generic [ref=f3e31]: 客户
      - link "客户管理" [ref=f3e32] [cursor=pointer]:
        - /url: /customers
      - link "联系人" [ref=f3e39] [cursor=pointer]:
        - /url: /contacts
      - link "跟进记录" [ref=f3e45] [cursor=pointer]:
        - /url: /follow-ups
      - generic [ref=f3e49]: 销售
      - link "报价管理" [ref=f3e50] [cursor=pointer]:
        - /url: /quotes
      - link "订单管理" [ref=f3e55] [cursor=pointer]:
        - /url: /orders
      - generic [ref=f3e61]: 采购与库存
      - link "供应商管理" [ref=f3e62] [cursor=pointer]:
        - /url: /suppliers
      - link "采购管理" [ref=f3e69] [cursor=pointer]:
        - /url: /purchase-orders
      - link "库存" [ref=f3e75] [cursor=pointer]:
        - /url: /inventory
      - link "库存流水" [ref=f3e80] [cursor=pointer]:
        - /url: /inventory-movements
      - generic [ref=f3e85]: 产品资料
      - link "产品管理" [ref=f3e86] [cursor=pointer]:
        - /url: /products
      - link "SKU 管理" [ref=f3e92] [cursor=pointer]:
        - /url: /skus
      - link "产品分类" [ref=f3e104] [cursor=pointer]:
        - /url: /categories
      - link "产品参数" [ref=f3e110] [cursor=pointer]:
        - /url: /product-parameters
      - link "包装管理" [ref=f3e113] [cursor=pointer]:
        - /url: /sku-packaging
      - link "交易单位" [ref=f3e119] [cursor=pointer]:
        - /url: /sku-trade-units
      - link "产品证书" [ref=f3e131] [cursor=pointer]:
        - /url: /product-certificates
      - link "HS 编码维护" [ref=f3e136] [cursor=pointer]:
        - /url: /hs-codes
      - generic [ref=f3e139]: 财务与工具
      - link "财务概览" [ref=f3e140] [cursor=pointer]:
        - /url: /finance
      - link "应收计划" [ref=f3e146] [cursor=pointer]:
        - /url: /receivables
      - link "应付计划" [ref=f3e152] [cursor=pointer]:
        - /url: /payables
      - link "财务流水" [ref=f3e158] [cursor=pointer]:
        - /url: /transactions
      - link "银行资金记录" [ref=f3e164] [cursor=pointer]:
        - /url: /rmb-cash-events
      - link "账户余额与对账" [ref=f3e170] [cursor=pointer]:
        - /url: /finance-ledger
      - link "数据导入" [ref=f3e176] [cursor=pointer]:
        - /url: /import
      - link "历史资料预检" [ref=f3e181] [cursor=pointer]:
        - /url: /history-preflight
      - link "历史资料承接" [ref=f3e187] [cursor=pointer]:
        - /url: /history-takeover
      - generic [ref=f3e193]: 组织与系统
      - link "组织与权限" [ref=f3e194] [cursor=pointer]:
        - /url: /organization
    - generic [ref=f3e199]:
      - generic [ref=f3e200]: C
      - generic [ref=f3e202]:
        - strong [ref=f3e203]: 当前账号：codex
        - generic [ref=f3e204]: 超级管理员 · 全部功能与数据权限
      - button "退出登录" [ref=f3e205] [cursor=pointer]
  - main [ref=f3e206]:
    - generic [ref=f3e207]:
      - generic [ref=f3e208]:
        - text: 产品资料
        - heading "产品管理" [level=1] [ref=f3e209]
      - generic [ref=f3e210]:
        - generic [ref=f3e211]: 11月14日周六
        - generic "codex" [ref=f3e212]: C
    - tablist "业务工作区" [ref=f3e214]:
      - generic [ref=f3e215]:
        - tab "C 合成轨道灯产品" [selected] [ref=f3e216] [cursor=pointer]
        - button "关闭 C 合成轨道灯产品" [ref=f3e217] [cursor=pointer]: ×
        - button "C 合成轨道灯产品 标签操作" [ref=f3e218] [cursor=pointer]: ⋮
    - tabpanel "C 合成轨道灯产品" [ref=f3e220]:
      - generic [ref=f3e221]:
        - generic [ref=f3e222]:
          - generic [ref=f3e223]:
            - heading "产品管理" [level=2] [ref=f3e224]
            - paragraph [ref=f3e225]: 维护产品名称、分类和销售状态；SKU 编码请在“SKU 管理”中维护。
          - button "新建产品" [ref=f3e226] [cursor=pointer]
        - region "页面小计" [ref=f3e229]:
          - article [ref=f3e230]:
            - generic [ref=f3e231]: 产品总数
            - strong [ref=f3e232]: "1"
            - generic [ref=f3e233]: 当前筛选范围
          - article [ref=f3e237]:
            - generic [ref=f3e238]: 在售产品
            - strong [ref=f3e239]: "1"
            - generic [ref=f3e240]: 可继续添加 SKU
          - article [ref=f3e244]:
            - generic [ref=f3e245]: 开发中
            - strong [ref=f3e246]: "0"
            - generic [ref=f3e247]: 尚未正式销售
          - article [ref=f3e251]:
            - generic [ref=f3e252]: SKU 总数
            - strong [ref=f3e253]: "2"
            - generic [ref=f3e254]: 产品下的 SKU
        - generic [ref=f3e258]:
          - textbox "搜索产品" [ref=f3e263]:
            - /placeholder: 搜索产品编号或名称
          - combobox "产品分类筛选" [ref=f3e266] [cursor=pointer]:
            - option "全部分类" [selected]
          - combobox "产品排序" [ref=f3e267]:
            - option "产品编号顺序" [selected]
            - option "产品名称顺序"
            - option "SKU 数量最多"
          - button "查询" [ref=f3e268] [cursor=pointer]
          - button "重置" [ref=f3e269] [cursor=pointer]
          - button "刷新" [ref=f3e270] [cursor=pointer]
        - table [ref=f3e273]:
          - rowgroup [ref=f3e274]:
            - row [ref=f3e275]:
              - columnheader "产品编号" [ref=f3e276]
              - columnheader "产品名称" [ref=f3e277]
              - columnheader "销售型号前缀" [ref=f3e278]
              - columnheader "主分类" [ref=f3e279]
              - columnheader "状态" [ref=f3e280]
              - columnheader "SKU" [ref=f3e281]
              - columnheader "参数" [ref=f3e282]
              - columnheader "证书" [ref=f3e283]
              - columnheader [ref=f3e284]
          - rowgroup [ref=f3e285]:
            - row [ref=f3e286] [cursor=pointer]:
              - cell "C-P001" [ref=f3e287]
              - cell "C 合成轨道灯产品 未填写英文名称" [ref=f3e288]:
                - strong [ref=f3e289]: C 合成轨道灯产品
                - generic [ref=f3e290]: 未填写英文名称
              - cell "—" [ref=f3e291]
              - cell "未分类" [ref=f3e292]
              - cell "在售" [ref=f3e293]
              - cell "2" [ref=f3e295]
              - cell "0" [ref=f3e296]
              - cell "0" [ref=f3e297]
              - cell [ref=f3e298]:
                - generic [ref=f3e299]:
                  - button "编辑产品" [ref=f3e300]
                  - button "删除产品" [ref=f3e304]
        - article "关联详情" [ref=f3e309]:
          - generic [ref=f3e310]:
            - generic [ref=f3e311]:
              - generic [ref=f3e312]: 产品管理 / 产品详情
              - generic [ref=f3e314]:
                - link "查看经营分析" [ref=f3e315] [cursor=pointer]:
                  - /url: /reports?source=sales&group_by=product&filter_product=1&title=%E4%BA%A7%E5%93%81%E9%94%80%E5%94%AE%E5%88%86%E6%9E%90&returnTo=/products?detail=1%26tab=suppliers
                - button "编辑主档" [ref=f3e320] [cursor=pointer]
                - button "关闭详情" [ref=f3e324] [cursor=pointer]:
                  - generic [ref=f3e328]: 关闭
            - generic [ref=f3e329]:
              - generic [ref=f3e330]:
                - text: C-P001 · 未分类
                - heading "C 合成轨道灯产品" [level=2] [ref=f3e331]
              - generic [ref=f3e332]: 在售
            - generic [ref=f3e333]:
              - generic [ref=f3e334]:
                - generic [ref=f3e335]: SKU
                - strong [ref=f3e336]: "2"
              - generic [ref=f3e337]:
                - generic [ref=f3e338]: 供应商
                - strong [ref=f3e339]: "0"
              - generic [ref=f3e340]:
                - generic [ref=f3e341]: 当前库存
                - strong [ref=f3e342]: "0"
              - generic [ref=f3e343]:
                - generic [ref=f3e344]: 参数
                - strong [ref=f3e345]: "0"
          - generic [ref=f3e346]:
            - navigation "产品详情导航" [ref=f3e347]:
              - button "总览" [ref=f3e348] [cursor=pointer]
              - button "SKU 管理2" [ref=f3e349] [cursor=pointer]
              - button "供应能力规则0" [ref=f3e350] [cursor=pointer]
              - button "订单记录0" [ref=f3e351] [cursor=pointer]
              - button "销售统计" [ref=f3e352] [cursor=pointer]
              - button "出入库流水0" [ref=f3e353] [cursor=pointer]
              - button "产品参数0" [ref=f3e354] [cursor=pointer]
              - button "证书档案0" [ref=f3e355] [cursor=pointer]
              - button "销售规则" [ref=f3e356] [cursor=pointer]
              - button "操作日志" [ref=f3e357] [cursor=pointer]
            - main [ref=f3e358]:
              - region "SKU 参数与供应商管理" [ref=f3e359]:
                - generic [ref=f3e361]:
                  - heading "供应能力规则" [level=3] [ref=f3e362]
                  - paragraph [ref=f3e363]: 一份 SKU 清单管理规格与供货候选；实际采购供应商在销售订单或采购单中确认。
                - group [ref=f3e364]:
                  - generic "供应能力规则 · 1 条 批量匹配多个 SKU，不指定订单供应商" [ref=f3e365] [cursor=pointer]
                  - generic [ref=f3e366]:
                    - heading "供应能力规则" [level=4] [ref=f3e367]
                    - button "＋ 添加规则" [ref=f3e368] [cursor=pointer]
                  - paragraph [ref=f3e369]: 同一参数内任一取值匹配即可，不同参数须同时满足。留空表示不限。规则只推荐候选，实际供应商由采购单确定。
                  - generic [ref=f3e370]:
                    - generic [ref=f3e371]:
                      - strong [ref=f3e372]: 合成能力规则 1366
                      - text: · C 合成照明供应商 启用
                      - paragraph [ref=f3e373]: 本产品全部 SKU
                      - paragraph [ref=f3e374]: 包装：合成测试纸盒
                    - generic [ref=f3e375]:
                      - button "编辑" [ref=f3e376] [cursor=pointer]
                      - button "停用" [ref=f3e377] [cursor=pointer]
```

# Test source

```ts
  1   | import { execFileSync } from 'node:child_process'
  2   | import { fileURLToPath } from 'node:url'
  3   | import path from 'node:path'
  4   | import { expect, test } from '@playwright/test'
  5   | 
  6   | test('C editors, batch results and product logs retain real state', async ({ page }, info) => {
  7   |   test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)), 'Dedicated isolated Chrome profile only.')
  8   |   test.setTimeout(600000)
  9   |   page.setDefaultTimeout(15000)
  10  |   const repository = new URL('../../', import.meta.url)
  11  |   const seed = fileURLToPath(new URL('docs/uat-evidence/product-draft-protection-01/seed.py', repository))
  12  |   const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {cwd:fileURLToPath(new URL('backend/',repository)),encoding:'utf8'}).replace(/^\uFEFF/,''))
  13  |   const shot = name => page.screenshot({path:info.outputPath(`${name}.png`)})
  14  |   for (const width of [1366,1920,390]) {
  15  |     await page.setViewportSize({width,height:width===1366?768:width===1920?1080:844})
  16  |     await page.goto(`/products?detail=${fixture.product}&tab=suppliers`)
  17  |     await page.getByRole('button',{name:'＋ 添加规则',exact:true}).click()
  18  |     const name=page.getByLabel('规则名称',{exact:true})
  19  |     await name.fill(`合成能力规则 ${width}`)
  20  |     await page.locator('form.editor select').selectOption(String(fixture.supplier))
  21  |     await page.getByLabel('共同供货特点',{exact:true}).fill('包装：合成测试纸盒')
  22  |     await shot(`rule-filled-${width}`)
> 23  |     await page.getByRole('button',{name:'预览匹配',exact:true}).click()
      |                                                             ^ TimeoutError: locator.click: Timeout 15000ms exceeded.
  24  |     await expect(page.getByText('匹配 2 个现有 SKU：',{exact:false})).toBeVisible()
  25  |     await shot(`rule-preview-before-save-${width}`)
  26  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  27  |     await page.getByTestId('dialog-cancel').click()
  28  |     await expect(name).toHaveValue(`合成能力规则 ${width}`)
  29  |     await shot(`rule-retained-${width}`)
  30  |     // A rejected save must retain values and the dirty guard.
  31  |     await page.route('**/api/supplier-capabilities/', async route => route.request().method()==='POST' ? route.fulfill({status:400,json:{detail:'合成保存失败，请重试'}}) : route.continue())
  32  |     await page.getByRole('button',{name:'保存规则',exact:true}).click()
  33  |     await expect(name).toHaveValue(`合成能力规则 ${width}`)
  34  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  35  |     await page.getByTestId('dialog-cancel').click()
  36  |     await page.unroute('**/api/supplier-capabilities/')
  37  |     await page.getByRole('button',{name:'保存规则',exact:true}).click()
  38  |     await expect(name).toHaveCount(0)
  39  |     const rules=await (await page.request.get(`/api/supplier-capabilities/?product=${fixture.product}`)).json()
  40  |     expect((rules.results||rules).some(rule=>rule.name===`合成能力规则 ${width}` && rule.characteristics['包装']==='合成测试纸盒')).toBeTruthy()
  41  |     await shot(`rule-saved-${width}`)
  42  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  43  |     await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  44  |     await page.getByRole('button',{name:'操作日志',exact:true}).click()
  45  |     await expect(page).toHaveURL(/tab=operation_logs/)
  46  |     await page.reload()
  47  |     await expect(page.getByRole('button',{name:'操作日志',exact:true})).toHaveClass(/active/)
  48  |     await expect(page.locator('.operation-log-panel')).toBeVisible()
  49  |     await shot(`log-reopened-${width}`)
  50  |     await page.goto(`/products?detail=${fixture.product}&tab=skus`)
  51  |     await page.locator('.parameter-plan-panel summary').click()
  52  |     await page.getByRole('button',{name:/创建参数方案草稿|继续 V\d+ 草稿/}).click()
  53  |     if (await page.getByLabel('参数名称',{exact:true}).count()===0) await page.getByRole('button',{name:'＋ 新增参数',exact:true}).click()
  54  |     const parameter=page.getByLabel('参数名称',{exact:true}).first()
  55  |     await parameter.fill(`合成参数 ${width}`)
  56  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  57  |     await page.getByTestId('dialog-cancel').click()
  58  |     await expect(parameter).toHaveValue(`合成参数 ${width}`)
  59  |     await page.getByRole('button',{name:/继续 V\d+ 草稿/}).click()
  60  |     await page.getByTestId('dialog-cancel').click()
  61  |     await expect(parameter).toHaveValue(`合成参数 ${width}`)
  62  |     await shot(`plan-retained-${width}`)
  63  |     await page.getByRole('button',{name:'保存草稿并分析影响',exact:true}).click()
  64  |     await expect(page.getByRole('heading',{name:'发布前核对',exact:true})).toBeVisible()
  65  |     const plan=await (await page.request.get(`/api/products/${fixture.product}/sku-plan/`)).json()
  66  |     expect(plan.plans.find(p=>p.status==='draft').definitions[0].name).toBe(`合成参数 ${width}`)
  67  |     await shot(`plan-saved-readback-${width}`)
  68  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  69  |     await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  70  |   }
  71  |   await page.setViewportSize({width:1366,height:768})
  72  |   await page.goto(`/products?detail=${fixture.product}&tab=skus`)
  73  |   const rows=page.locator('.candidate-table tbody tr')
  74  |   await expect(rows).toHaveCount(2)
  75  |   await page.locator('.candidate-table thead input').check()
  76  |   // Inject exactly one rejection; the other PATCH and all readbacks use the real isolated API.
  77  |   const failed=`**/api/skus/${fixture.skus[1]}/`
  78  |   await page.route(failed,route=>route.request().method()==='PATCH'?route.fulfill({status:400,json:{detail:'合成停用失败'}}):route.continue())
  79  |   await page.getByRole('button',{name:'停用 2 项',exact:true}).click()
  80  |   await page.getByTestId('dialog-confirm').click()
  81  |   await expect(page.getByText(/成功 1 项，失败 1 项/)).toBeVisible()
  82  |   await expect(page.getByText('C-SKU-2：合成停用失败',{exact:true})).toBeVisible()
  83  |   await expect(rows.locator('input[type=checkbox]')).toBeChecked()
  84  |   expect((await (await page.request.get(`/api/skus/${fixture.skus[0]}/`)).json()).active).toBe(false)
  85  |   expect((await (await page.request.get(`/api/skus/${fixture.skus[1]}/`)).json()).active).toBe(true)
  86  |   await shot('batch-partial-real-readback')
  87  |   await page.getByRole('button',{name:'停用 1 项',exact:true}).click()
  88  |   await page.getByTestId('dialog-confirm').click()
  89  |   await expect(page.getByText(/成功 0 项，失败 1 项/)).toBeVisible()
  90  |   await shot('batch-total-failure-retained')
  91  |   await page.unroute(failed)
  92  |   await page.getByRole('button',{name:'停用 1 项',exact:true}).click()
  93  |   await page.getByTestId('dialog-confirm').click()
  94  |   await expect(page.getByText('已停用 1 项 SKU。',{exact:true})).toBeVisible()
  95  |   expect((await (await page.request.get(`/api/skus/${fixture.skus[1]}/`)).json()).active).toBe(false)
  96  |   await page.getByLabel('显示已停用',{exact:false}).check()
  97  |   await page.locator('.candidate-table thead input').check()
  98  |   await page.getByRole('button',{name:'重新启用 2 项',exact:true}).click()
  99  |   await page.getByTestId('dialog-confirm').click()
  100 |   await expect(page.getByText('已启用 2 项 SKU。',{exact:true})).toBeVisible()
  101 |   for (const id of fixture.skus) expect((await (await page.request.get(`/api/skus/${id}/`)).json()).active).toBe(true)
  102 |   await shot('batch-success-real-readback')
  103 | })
  104 | 
  105 | test.afterEach(async ({page}, info)=> { if(info.status!==info.expectedStatus) await page.screenshot({path:info.outputPath('failure.png')}) })
  106 | 
```