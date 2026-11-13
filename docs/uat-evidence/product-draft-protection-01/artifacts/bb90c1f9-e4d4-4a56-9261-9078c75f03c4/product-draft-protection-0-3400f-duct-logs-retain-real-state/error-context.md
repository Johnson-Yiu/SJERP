# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: product-draft-protection-01.spec.js >> C editors, batch results and product logs retain real state
- Location: browser-tests\product-draft-protection-01.spec.js:7:1

# Error details

```
TimeoutError: locator.click: Timeout 60000ms exceeded.
Call log:
  - waiting for getByTestId('dialog-cancel')

```

# Page snapshot

```yaml
- generic [ref=f6e3]:
  - complementary [ref=f6e4]:
    - generic [ref=f6e5]:
      - generic [ref=f6e6]: S
      - generic [ref=f6e7]:
        - strong [ref=f6e8]: 森爵照明管理系统
        - text: 客户 · 销售 · 产品
    - navigation [ref=f6e9]:
      - generic [ref=f6e10]: 经营
      - link "经营概览" [ref=f6e11] [cursor=pointer]:
        - /url: /
      - link "报表中心" [ref=f6e18] [cursor=pointer]:
        - /url: /reports
      - link "历史订单分析" [ref=f6e25] [cursor=pointer]:
        - /url: /historical-orders
      - generic [ref=f6e31]: 客户
      - link "客户管理" [ref=f6e32] [cursor=pointer]:
        - /url: /customers
      - link "联系人" [ref=f6e39] [cursor=pointer]:
        - /url: /contacts
      - link "跟进记录" [ref=f6e45] [cursor=pointer]:
        - /url: /follow-ups
      - generic [ref=f6e49]: 销售
      - link "报价管理" [ref=f6e50] [cursor=pointer]:
        - /url: /quotes
      - link "订单管理" [ref=f6e55] [cursor=pointer]:
        - /url: /orders
      - generic [ref=f6e61]: 采购与库存
      - link "供应商管理" [ref=f6e62] [cursor=pointer]:
        - /url: /suppliers
      - link "采购管理" [ref=f6e69] [cursor=pointer]:
        - /url: /purchase-orders
      - link "库存" [ref=f6e75] [cursor=pointer]:
        - /url: /inventory
      - link "库存流水" [ref=f6e80] [cursor=pointer]:
        - /url: /inventory-movements
      - generic [ref=f6e85]: 产品资料
      - link "产品管理" [ref=f6e86] [cursor=pointer]:
        - /url: /products
      - link "SKU 管理" [ref=f6e92] [cursor=pointer]:
        - /url: /skus
      - link "产品分类" [ref=f6e104] [cursor=pointer]:
        - /url: /categories
      - link "产品参数" [ref=f6e110] [cursor=pointer]:
        - /url: /product-parameters
      - link "包装管理" [ref=f6e113] [cursor=pointer]:
        - /url: /sku-packaging
      - link "交易单位" [ref=f6e119] [cursor=pointer]:
        - /url: /sku-trade-units
      - link "产品证书" [ref=f6e131] [cursor=pointer]:
        - /url: /product-certificates
      - link "HS 编码维护" [ref=f6e136] [cursor=pointer]:
        - /url: /hs-codes
      - generic [ref=f6e139]: 财务与工具
      - link "财务概览" [ref=f6e140] [cursor=pointer]:
        - /url: /finance
      - link "应收计划" [ref=f6e146] [cursor=pointer]:
        - /url: /receivables
      - link "应付计划" [ref=f6e152] [cursor=pointer]:
        - /url: /payables
      - link "财务流水" [ref=f6e158] [cursor=pointer]:
        - /url: /transactions
      - link "银行资金记录" [ref=f6e164] [cursor=pointer]:
        - /url: /rmb-cash-events
      - link "账户余额与对账" [ref=f6e170] [cursor=pointer]:
        - /url: /finance-ledger
      - link "数据导入" [ref=f6e176] [cursor=pointer]:
        - /url: /import
      - link "历史资料预检" [ref=f6e181] [cursor=pointer]:
        - /url: /history-preflight
      - link "历史资料承接" [ref=f6e187] [cursor=pointer]:
        - /url: /history-takeover
      - generic [ref=f6e193]: 组织与系统
      - link "组织与权限" [ref=f6e194] [cursor=pointer]:
        - /url: /organization
    - generic [ref=f6e199]:
      - generic [ref=f6e200]: C
      - generic [ref=f6e202]:
        - strong [ref=f6e203]: 当前账号：codex
        - generic [ref=f6e204]: 超级管理员 · 全部功能与数据权限
      - button "退出登录" [ref=f6e205] [cursor=pointer]
  - main [ref=f6e206]:
    - generic [ref=f6e207]:
      - generic [ref=f6e208]:
        - text: 产品资料
        - heading "产品管理" [level=1] [ref=f6e209]
      - generic [ref=f6e210]:
        - generic [ref=f6e211]: 11月14日周六
        - generic "codex" [ref=f6e212]: C
    - tablist "业务工作区" [ref=f6e214]:
      - generic [ref=f6e215]:
        - tab "C 合成轨道灯产品未保存" [selected] [ref=f6e216] [cursor=pointer]: C 合成轨道灯产品 ●
        - button "关闭 C 合成轨道灯产品" [ref=f6e217] [cursor=pointer]: ×
        - button "C 合成轨道灯产品 标签操作" [ref=f6e218] [cursor=pointer]: ⋮
    - tabpanel "C 合成轨道灯产品" [ref=f6e220]:
      - generic [ref=f6e221]:
        - generic [ref=f6e222]:
          - generic [ref=f6e223]:
            - heading "产品管理" [level=2] [ref=f6e224]
            - paragraph [ref=f6e225]: 维护产品名称、分类和销售状态；SKU 编码请在“SKU 管理”中维护。
          - button "新建产品" [ref=f6e226] [cursor=pointer]
        - region "页面小计" [ref=f6e229]:
          - article [ref=f6e230]:
            - generic [ref=f6e231]: 产品总数
            - strong [ref=f6e232]: "1"
            - generic [ref=f6e233]: 当前筛选范围
          - article [ref=f6e237]:
            - generic [ref=f6e238]: 在售产品
            - strong [ref=f6e239]: "1"
            - generic [ref=f6e240]: 可继续添加 SKU
          - article [ref=f6e244]:
            - generic [ref=f6e245]: 开发中
            - strong [ref=f6e246]: "0"
            - generic [ref=f6e247]: 尚未正式销售
          - article [ref=f6e251]:
            - generic [ref=f6e252]: SKU 总数
            - strong [ref=f6e253]: "2"
            - generic [ref=f6e254]: 产品下的 SKU
        - generic [ref=f6e258]:
          - textbox "搜索产品" [ref=f6e263]:
            - /placeholder: 搜索产品编号或名称
          - combobox "产品分类筛选" [ref=f6e266] [cursor=pointer]:
            - option "全部分类" [selected]
          - combobox "产品排序" [ref=f6e267]:
            - option "产品编号顺序" [selected]
            - option "产品名称顺序"
            - option "SKU 数量最多"
          - button "查询" [ref=f6e268] [cursor=pointer]
          - button "重置" [ref=f6e269] [cursor=pointer]
          - button "刷新" [ref=f6e270] [cursor=pointer]
        - table [ref=f6e273]:
          - rowgroup [ref=f6e274]:
            - row [ref=f6e275]:
              - columnheader "产品编号" [ref=f6e276]
              - columnheader "产品名称" [ref=f6e277]
              - columnheader "销售型号前缀" [ref=f6e278]
              - columnheader "主分类" [ref=f6e279]
              - columnheader "状态" [ref=f6e280]
              - columnheader "SKU" [ref=f6e281]
              - columnheader "参数" [ref=f6e282]
              - columnheader "证书" [ref=f6e283]
              - columnheader [ref=f6e284]
          - rowgroup [ref=f6e285]:
            - row [ref=f6e286] [cursor=pointer]:
              - cell "C-P001" [ref=f6e287]
              - cell "C 合成轨道灯产品 未填写英文名称" [ref=f6e288]:
                - strong [ref=f6e289]: C 合成轨道灯产品
                - generic [ref=f6e290]: 未填写英文名称
              - cell "—" [ref=f6e291]
              - cell "未分类" [ref=f6e292]
              - cell "在售" [ref=f6e293]
              - cell "2" [ref=f6e295]
              - cell "0" [ref=f6e296]
              - cell "0" [ref=f6e297]
              - cell [ref=f6e298]:
                - generic [ref=f6e299]:
                  - button "编辑产品" [ref=f6e300]
                  - button "删除产品" [ref=f6e304]
        - article "关联详情" [ref=f6e309]:
          - generic [ref=f6e310]:
            - generic [ref=f6e311]:
              - generic [ref=f6e312]: 产品管理 / 产品详情
              - generic [ref=f6e314]:
                - link "查看经营分析" [ref=f6e315] [cursor=pointer]:
                  - /url: /reports?source=sales&group_by=product&filter_product=1&title=%E4%BA%A7%E5%93%81%E9%94%80%E5%94%AE%E5%88%86%E6%9E%90&returnTo=/products?detail=1%26tab=suppliers
                - button "编辑主档" [ref=f6e320] [cursor=pointer]
                - button "关闭详情" [ref=f6e324] [cursor=pointer]:
                  - generic [ref=f6e328]: 关闭
            - generic [ref=f6e329]:
              - generic [ref=f6e330]:
                - text: C-P001 · 未分类
                - heading "C 合成轨道灯产品" [level=2] [ref=f6e331]
              - generic [ref=f6e332]: 在售
            - generic [ref=f6e333]:
              - generic [ref=f6e334]:
                - generic [ref=f6e335]: SKU
                - strong [ref=f6e336]: "2"
              - generic [ref=f6e337]:
                - generic [ref=f6e338]: 供应商
                - strong [ref=f6e339]: "0"
              - generic [ref=f6e340]:
                - generic [ref=f6e341]: 当前库存
                - strong [ref=f6e342]: "0"
              - generic [ref=f6e343]:
                - generic [ref=f6e344]: 参数
                - strong [ref=f6e345]: "0"
          - generic [ref=f6e346]:
            - navigation "产品详情导航" [ref=f6e347]:
              - button "总览" [active] [ref=f6e348] [cursor=pointer]
              - button "SKU 管理2" [ref=f6e349] [cursor=pointer]
              - button "供应能力规则0" [ref=f6e350] [cursor=pointer]
              - button "订单记录0" [ref=f6e351] [cursor=pointer]
              - button "销售统计" [ref=f6e352] [cursor=pointer]
              - button "出入库流水0" [ref=f6e353] [cursor=pointer]
              - button "产品参数0" [ref=f6e354] [cursor=pointer]
              - button "证书档案0" [ref=f6e355] [cursor=pointer]
              - button "销售规则" [ref=f6e356] [cursor=pointer]
              - button "操作日志" [ref=f6e357] [cursor=pointer]
            - main [ref=f6e358]:
              - region "SKU 参数与供应商管理" [ref=f6e359]:
                - generic [ref=f6e361]:
                  - heading "供应能力规则" [level=3] [ref=f6e362]
                  - paragraph [ref=f6e363]: 一份 SKU 清单管理规格与供货候选；实际采购供应商在销售订单或采购单中确认。
                - group [ref=f6e364]:
                  - generic "供应能力规则 · 1 条 批量匹配多个 SKU，不指定订单供应商" [ref=f6e365] [cursor=pointer]
                  - generic [ref=f6e366]:
                    - heading "供应能力规则" [level=4] [ref=f6e367]
                    - button "＋ 添加规则" [ref=f6e368] [cursor=pointer]
                  - paragraph [ref=f6e369]: 同一参数内任一取值匹配即可，不同参数须同时满足。留空表示不限。规则只推荐候选，实际供应商由采购单确定。
                  - generic [ref=f6e370]:
                    - generic [ref=f6e371]:
                      - strong [ref=f6e372]: 合成能力规则 1366
                      - text: · C 合成照明供应商 启用
                      - paragraph [ref=f6e373]: 本产品全部 SKU
                      - paragraph [ref=f6e374]: 包装：合成测试纸盒
                    - generic [ref=f6e375]:
                      - button "编辑" [ref=f6e376] [cursor=pointer]
                      - button "停用" [ref=f6e377] [cursor=pointer]
                  - generic [ref=f6e378]:
                    - heading "新增供应能力" [level=4] [ref=f6e379]
                    - generic [ref=f6e380]:
                      - generic [ref=f6e381]:
                        - text: 规则名称
                        - textbox "规则名称" [ref=f6e382]:
                          - /placeholder: 例如：A厂常规灯带
                          - text: 合成能力规则 1920
                      - generic [ref=f6e383]:
                        - text: 供应商
                        - combobox "供应商" [ref=f6e384]:
                          - option "请选择"
                          - option "C 合成照明供应商" [selected]
                    - generic [ref=f6e385]:
                      - text: 共同供货特点
                      - textbox "共同供货特点" [ref=f6e386]:
                        - /placeholder: "PCB：白色\n背胶：3M\n包装：10米/卷"
                        - text: 包装：合成测试纸盒
                    - paragraph [ref=f6e387]: 共同特点作为供货档案初始值，已有档案和历史采购不会随规则更新。
                    - generic [ref=f6e388]:
                      - button "预览匹配" [ref=f6e389] [cursor=pointer]
                      - button "保存规则" [ref=f6e390] [cursor=pointer]
                      - button "取消" [ref=f6e391] [cursor=pointer]
                    - paragraph [ref=f6e392]: 匹配 2 个现有 SKU：C 合成轨道灯产品、C 合成轨道灯产品 · C-SKU-2
```

# Test source

```ts
  1   | import { execFileSync } from 'node:child_process'
  2   | import { fileURLToPath } from 'node:url'
  3   | import path from 'node:path'
  4   | import { expect as baseExpect, test } from '@playwright/test'
  5   | const expect=baseExpect.configure({timeout:30000})
  6   | 
  7   | test('C editors, batch results and product logs retain real state', async ({ page }, info) => {
  8   |   test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)), 'Dedicated isolated Chrome profile only.')
  9   |   test.setTimeout(600000)
  10  |   page.setDefaultTimeout(60000)
  11  |   const repository = new URL('../../', import.meta.url)
  12  |   const seed = fileURLToPath(new URL('docs/uat-evidence/product-draft-protection-01/seed.py', repository))
  13  |   const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {cwd:fileURLToPath(new URL('backend/',repository)),encoding:'utf8'}).replace(/^\uFEFF/,''))
  14  |   const shot = name => page.screenshot({path:info.outputPath(`${name}.png`)})
  15  |   if (process.env.AUDIT_LOG_ENABLED === '1') {
  16  |     await page.goto(`/products?detail=${fixture.product}&tab=operation_logs`)
  17  |     await expect(page.locator('.operation-log-panel').getByText('暂无操作日志。',{exact:true})).toBeVisible()
  18  |     await page.reload()
  19  |     await expect(page.locator('.operation-log-panel').getByText('暂无操作日志。',{exact:true})).toBeVisible()
  20  |     await shot('audit-enabled-empty-log-reloaded')
  21  |   }
  22  |   for (const width of [1366,1920,390]) {
  23  |     await page.setViewportSize({width,height:width===1366?768:width===1920?1080:844})
  24  |     await page.goto(`/products?detail=${fixture.product}&tab=suppliers`)
  25  |     await page.getByRole('button',{name:'＋ 添加规则',exact:true}).click()
  26  |     const name=page.getByLabel('规则名称',{exact:true})
  27  |     await name.fill(`合成能力规则 ${width}`)
  28  |     await page.locator('form.editor select').selectOption(String(fixture.supplier))
  29  |     await page.getByLabel('共同供货特点',{exact:true}).fill('包装：合成测试纸盒')
  30  |     await shot(`rule-filled-${width}`)
  31  |     await page.getByRole('button',{name:'预览匹配',exact:true}).click()
  32  |     await expect(page.getByText('匹配 2 个现有 SKU：',{exact:false})).toBeVisible()
  33  |     await shot(`rule-preview-before-save-${width}`)
  34  |     await page.getByRole('button',{name:'预览匹配',exact:true}).press('Enter')
  35  |     await page.getByRole('button',{name:'总览',exact:true}).click()
> 36  |     await page.getByTestId('dialog-cancel').click()
      |                                             ^ TimeoutError: locator.click: Timeout 60000ms exceeded.
  37  |     await expect(name).toHaveValue(`合成能力规则 ${width}`)
  38  |     await shot(`rule-retained-${width}`)
  39  |     if (width !== 390) {
  40  |       await page.getByRole('link',{name:'客户管理',exact:true}).click()
  41  |       await expect(page).toHaveURL(/customers/)
  42  |       await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  43  |       await page.getByRole('tab',{name:/C 合成轨道灯产品/}).click()
  44  |       await expect(name).toHaveValue(`合成能力规则 ${width}`)
  45  |       await page.getByRole('button',{name:'关闭 C 合成轨道灯产品',exact:true}).click()
  46  |       await page.getByTestId('dialog-cancel').click()
  47  |       await expect(name).toHaveValue(`合成能力规则 ${width}`)
  48  |       const dialogEvent=page.waitForEvent('dialog')
  49  |       const refresh=page.reload({timeout:5000}).catch(()=>{})
  50  |       const refreshDialog=await dialogEvent
  51  |       expect(refreshDialog.type()).toBe('beforeunload')
  52  |       await refreshDialog.dismiss(); await refresh
  53  |       await expect(name).toHaveValue(`合成能力规则 ${width}`)
  54  |     }
  55  |     // A rejected save must retain values and the dirty guard.
  56  |     await page.route('**/api/supplier-capabilities/', async route => route.request().method()==='POST' ? route.fulfill({status:400,json:{detail:'合成保存失败，请重试'}}) : route.continue())
  57  |     await page.getByRole('button',{name:'保存规则',exact:true}).click()
  58  |     await expect(name).toHaveValue(`合成能力规则 ${width}`)
  59  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  60  |     await page.getByTestId('dialog-cancel').click()
  61  |     await page.unroute('**/api/supplier-capabilities/')
  62  |     await page.getByRole('button',{name:'保存规则',exact:true}).click()
  63  |     await expect(name).toHaveCount(0)
  64  |     const rules=await (await page.request.get(`/api/supplier-capabilities/?product=${fixture.product}`)).json()
  65  |     expect((rules.results||rules).some(rule=>rule.name===`合成能力规则 ${width}` && rule.characteristics['包装']==='合成测试纸盒')).toBeTruthy()
  66  |     await shot(`rule-saved-${width}`)
  67  |     await page.getByRole('button',{name:'＋ 添加规则',exact:true}).click()
  68  |     await name.fill('明确放弃的合成规则')
  69  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  70  |     await page.getByTestId('dialog-confirm').click()
  71  |     await expect(name).toHaveCount(0)
  72  |     await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  73  |     await page.getByRole('button',{name:'操作日志',exact:true}).click()
  74  |     await expect(page).toHaveURL(/tab=operation_logs/)
  75  |     await page.reload()
  76  |     await expect(page.getByRole('button',{name:'操作日志',exact:true})).toHaveClass(/active/)
  77  |     await expect(page.locator('.operation-log-panel')).toBeVisible()
  78  |     await shot(`log-reopened-${width}`)
  79  |     await page.goto(`/products?detail=${fixture.product}&tab=skus`)
  80  |     await page.locator('.parameter-plan-panel summary').click()
  81  |     await page.getByRole('button',{name:/创建参数方案草稿|继续 V\d+ 草稿/}).click()
  82  |     await expect(page.locator('.parameter-plan-panel .editor')).toBeVisible()
  83  |     if (await page.getByLabel('参数名称',{exact:true}).count()===0) await page.getByRole('button',{name:'＋ 新增参数',exact:true}).click()
  84  |     const parameter=page.getByLabel('参数名称',{exact:true}).first()
  85  |     await parameter.fill(`合成参数 ${width}`)
  86  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  87  |     await page.getByTestId('dialog-cancel').click()
  88  |     await expect(parameter).toHaveValue(`合成参数 ${width}`)
  89  |     await page.getByRole('button',{name:/继续 V\d+ 草稿/}).click()
  90  |     await page.getByTestId('dialog-cancel').click()
  91  |     await expect(parameter).toHaveValue(`合成参数 ${width}`)
  92  |     await shot(`plan-retained-${width}`)
  93  |     if (width !== 390) {
  94  |       await page.getByRole('button',{name:'关闭 C 合成轨道灯产品',exact:true}).click()
  95  |       await page.getByTestId('dialog-cancel').click()
  96  |       await expect(parameter).toHaveValue(`合成参数 ${width}`)
  97  |     }
  98  |     await page.route(`**/api/products/${fixture.product}/sku-plan/`, route=>route.request().method()==='PATCH'?route.fulfill({status:400,json:{detail:'合成方案保存失败'}}):route.continue())
  99  |     await page.getByRole('button',{name:'保存草稿并分析影响',exact:true}).click()
  100 |     await expect(page.getByText('合成方案保存失败',{exact:true})).toBeVisible()
  101 |     await page.getByRole('button',{name:'总览',exact:true}).click()
  102 |     await page.getByTestId('dialog-cancel').click()
  103 |     await expect(parameter).toHaveValue(`合成参数 ${width}`)
  104 |     await page.unroute(`**/api/products/${fixture.product}/sku-plan/`)
  105 |     await page.getByRole('button',{name:'保存草稿并分析影响',exact:true}).click()
  106 |     await expect(page.getByRole('heading',{name:'发布前核对',exact:true})).toBeVisible()
  107 |     const plan=await (await page.request.get(`/api/products/${fixture.product}/sku-plan/`)).json()
  108 |     expect(plan.plans.find(p=>p.status==='draft').definitions[0].name).toBe(`合成参数 ${width}`)
  109 |     await shot(`plan-saved-readback-${width}`)
  110 |     await page.getByRole('button',{name:'总览',exact:true}).click()
  111 |     await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  112 |     await page.goto(`/products?detail=${fixture.product}&tab=skus`)
  113 |     await page.locator('.parameter-plan-panel summary').click()
  114 |     await page.getByRole('button',{name:/继续 V\d+ 草稿/}).click()
  115 |     await expect(parameter).toHaveValue(`合成参数 ${width}`)
  116 |     await parameter.fill('明确放弃的合成参数')
  117 |     await page.getByRole('button',{name:'总览',exact:true}).click()
  118 |     await page.getByTestId('dialog-confirm').click()
  119 |     await expect(parameter).toHaveCount(0)
  120 |     await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  121 |   }
  122 |   await page.setViewportSize({width:1366,height:768})
  123 |   await page.goto(`/products?detail=${fixture.product}&tab=skus`)
  124 |   const rows=page.locator('.candidate-table tbody tr')
  125 |   await expect(rows).toHaveCount(2)
  126 |   const checkbox=page.locator('.candidate-table thead input')
  127 |   await checkbox.scrollIntoViewIfNeeded()
  128 |   const box=await checkbox.boundingBox()
  129 |   await page.mouse.click(box.x+1,box.y+box.height/2)
  130 |   await expect(checkbox).toBeChecked()
  131 |   // Inject exactly one rejection; the other PATCH and all readbacks use the real isolated API.
  132 |   const failed=`**/api/skus/${fixture.skus[1]}/`
  133 |   await page.route(failed,route=>route.request().method()==='PATCH'?route.fulfill({status:400,json:{detail:'合成停用失败'}}):route.continue())
  134 |   await page.getByRole('button',{name:'停用 2 项',exact:true}).click()
  135 |   await page.getByTestId('dialog-confirm').click()
  136 |   await expect(page.getByText(/成功 1 项，失败 1 项/)).toBeVisible()
```