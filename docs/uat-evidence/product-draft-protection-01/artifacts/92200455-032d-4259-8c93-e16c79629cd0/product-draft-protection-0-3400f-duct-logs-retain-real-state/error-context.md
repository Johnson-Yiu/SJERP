# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: product-draft-protection-01.spec.js >> C editors, batch results and product logs retain real state
- Location: browser-tests\product-draft-protection-01.spec.js:7:1

# Error details

```
Error: expect(locator).toBeChecked() failed

Locator: locator('.candidate-table tbody tr').locator('input[type=checkbox]')
Expected: checked
Error: strict mode violation: locator('.candidate-table tbody tr').locator('input[type=checkbox]') resolved to 2 elements:
    1) <input value="1" type="checkbox" data-v-e62e5d4d="" aria-label="选择 C-SKU-1"/> aka getByRole('checkbox', { name: '选择 C-SKU-1' })
    2) <input value="2" type="checkbox" data-v-e62e5d4d="" aria-label="选择 C-SKU-2"/> aka getByRole('checkbox', { name: '选择 C-SKU-2' })

Call log:
  - Expect "toBeChecked" locator('.candidate-table tbody tr').locator('input[type=checkbox]') with timeout 30000ms
  - waiting for locator('.candidate-table tbody tr').locator('input[type=checkbox]')

```

# Page snapshot

```yaml
- generic [ref=f14e3]:
  - complementary [ref=f14e4]:
    - generic [ref=f14e5]:
      - generic [ref=f14e6]: S
      - generic [ref=f14e7]:
        - strong [ref=f14e8]: 森爵照明管理系统
        - text: 客户 · 销售 · 产品
    - navigation [ref=f14e9]:
      - generic [ref=f14e10]: 经营
      - link "经营概览" [ref=f14e11] [cursor=pointer]:
        - /url: /
      - link "报表中心" [ref=f14e18] [cursor=pointer]:
        - /url: /reports
      - link "历史订单分析" [ref=f14e25] [cursor=pointer]:
        - /url: /historical-orders
      - generic [ref=f14e31]: 客户
      - link "客户管理" [ref=f14e32] [cursor=pointer]:
        - /url: /customers
      - link "联系人" [ref=f14e39] [cursor=pointer]:
        - /url: /contacts
      - link "跟进记录" [ref=f14e45] [cursor=pointer]:
        - /url: /follow-ups
      - generic [ref=f14e49]: 销售
      - link "报价管理" [ref=f14e50] [cursor=pointer]:
        - /url: /quotes
      - link "订单管理" [ref=f14e55] [cursor=pointer]:
        - /url: /orders
      - generic [ref=f14e61]: 采购与库存
      - link "供应商管理" [ref=f14e62] [cursor=pointer]:
        - /url: /suppliers
      - link "采购管理" [ref=f14e69] [cursor=pointer]:
        - /url: /purchase-orders
      - link "库存" [ref=f14e75] [cursor=pointer]:
        - /url: /inventory
      - link "库存流水" [ref=f14e80] [cursor=pointer]:
        - /url: /inventory-movements
      - generic [ref=f14e85]: 产品资料
      - link "产品管理" [ref=f14e86] [cursor=pointer]:
        - /url: /products
      - link "SKU 管理" [ref=f14e92] [cursor=pointer]:
        - /url: /skus
      - link "产品分类" [ref=f14e104] [cursor=pointer]:
        - /url: /categories
      - link "产品参数" [ref=f14e110] [cursor=pointer]:
        - /url: /product-parameters
      - link "包装管理" [ref=f14e113] [cursor=pointer]:
        - /url: /sku-packaging
      - link "交易单位" [ref=f14e119] [cursor=pointer]:
        - /url: /sku-trade-units
      - link "产品证书" [ref=f14e131] [cursor=pointer]:
        - /url: /product-certificates
      - link "HS 编码维护" [ref=f14e136] [cursor=pointer]:
        - /url: /hs-codes
      - generic [ref=f14e139]: 财务与工具
      - link "财务概览" [ref=f14e140] [cursor=pointer]:
        - /url: /finance
      - link "应收计划" [ref=f14e146] [cursor=pointer]:
        - /url: /receivables
      - link "应付计划" [ref=f14e152] [cursor=pointer]:
        - /url: /payables
      - link "财务流水" [ref=f14e158] [cursor=pointer]:
        - /url: /transactions
      - link "银行资金记录" [ref=f14e164] [cursor=pointer]:
        - /url: /rmb-cash-events
      - link "账户余额与对账" [ref=f14e170] [cursor=pointer]:
        - /url: /finance-ledger
      - link "数据导入" [ref=f14e176] [cursor=pointer]:
        - /url: /import
      - link "历史资料预检" [ref=f14e181] [cursor=pointer]:
        - /url: /history-preflight
      - link "历史资料承接" [ref=f14e187] [cursor=pointer]:
        - /url: /history-takeover
      - generic [ref=f14e193]: 组织与系统
      - link "组织与权限" [ref=f14e194] [cursor=pointer]:
        - /url: /organization
    - generic [ref=f14e199]:
      - generic [ref=f14e200]: C
      - generic [ref=f14e202]:
        - strong [ref=f14e203]: 当前账号：codex
        - generic [ref=f14e204]: 超级管理员 · 全部功能与数据权限
      - button "退出登录" [ref=f14e205] [cursor=pointer]
  - main [ref=f14e206]:
    - generic [ref=f14e207]:
      - generic [ref=f14e208]:
        - text: 产品资料
        - heading "产品管理" [level=1] [ref=f14e209]
      - generic [ref=f14e210]:
        - generic [ref=f14e211]: 11月14日周六
        - generic "codex" [ref=f14e212]: C
    - tablist "业务工作区" [ref=f14e214]:
      - generic [ref=f14e215]:
        - tab "C 合成轨道灯产品" [selected] [ref=f14e216] [cursor=pointer]
        - button "关闭 C 合成轨道灯产品" [ref=f14e217] [cursor=pointer]: ×
        - button "C 合成轨道灯产品 标签操作" [ref=f14e218] [cursor=pointer]: ⋮
    - tabpanel "C 合成轨道灯产品" [ref=f14e220]:
      - generic [ref=f14e221]:
        - generic [ref=f14e222]:
          - generic [ref=f14e223]:
            - heading "产品管理" [level=2] [ref=f14e224]
            - paragraph [ref=f14e225]: 维护产品名称、分类和销售状态；SKU 编码请在“SKU 管理”中维护。
          - button "新建产品" [ref=f14e226] [cursor=pointer]
        - region "页面小计" [ref=f14e229]:
          - article [ref=f14e230]:
            - generic [ref=f14e231]: 产品总数
            - strong [ref=f14e232]: "1"
            - generic [ref=f14e233]: 当前筛选范围
          - article [ref=f14e237]:
            - generic [ref=f14e238]: 在售产品
            - strong [ref=f14e239]: "1"
            - generic [ref=f14e240]: 可继续添加 SKU
          - article [ref=f14e244]:
            - generic [ref=f14e245]: 开发中
            - strong [ref=f14e246]: "0"
            - generic [ref=f14e247]: 尚未正式销售
          - article [ref=f14e251]:
            - generic [ref=f14e252]: SKU 总数
            - strong [ref=f14e253]: "2"
            - generic [ref=f14e254]: 产品下的 SKU
        - generic [ref=f14e258]:
          - textbox "搜索产品" [ref=f14e263]:
            - /placeholder: 搜索产品编号或名称
          - combobox "产品分类筛选" [ref=f14e266] [cursor=pointer]:
            - option "全部分类" [selected]
          - combobox "产品排序" [ref=f14e267]:
            - option "产品编号顺序" [selected]
            - option "产品名称顺序"
            - option "SKU 数量最多"
          - button "查询" [ref=f14e268] [cursor=pointer]
          - button "重置" [ref=f14e269] [cursor=pointer]
          - button "刷新" [ref=f14e270] [cursor=pointer]
        - table [ref=f14e273]:
          - rowgroup [ref=f14e274]:
            - row [ref=f14e275]:
              - columnheader "产品编号" [ref=f14e276]
              - columnheader "产品名称" [ref=f14e277]
              - columnheader "销售型号前缀" [ref=f14e278]
              - columnheader "主分类" [ref=f14e279]
              - columnheader "状态" [ref=f14e280]
              - columnheader "SKU" [ref=f14e281]
              - columnheader "参数" [ref=f14e282]
              - columnheader "证书" [ref=f14e283]
              - columnheader [ref=f14e284]
          - rowgroup [ref=f14e285]:
            - row [ref=f14e286] [cursor=pointer]:
              - cell "C-P001" [ref=f14e287]
              - cell "C 合成轨道灯产品 未填写英文名称" [ref=f14e288]:
                - strong [ref=f14e289]: C 合成轨道灯产品
                - generic [ref=f14e290]: 未填写英文名称
              - cell "—" [ref=f14e291]
              - cell "未分类" [ref=f14e292]
              - cell "在售" [ref=f14e293]
              - cell "2" [ref=f14e295]
              - cell "0" [ref=f14e296]
              - cell "0" [ref=f14e297]
              - cell [ref=f14e298]:
                - generic [ref=f14e299]:
                  - button "编辑产品" [ref=f14e300]
                  - button "删除产品" [ref=f14e304]
        - article "关联详情" [ref=f14e309]:
          - generic [ref=f14e310]:
            - generic [ref=f14e311]:
              - generic [ref=f14e312]: 产品管理 / 产品详情
              - generic [ref=f14e314]:
                - link "查看经营分析" [ref=f14e315] [cursor=pointer]:
                  - /url: /reports?source=sales&group_by=product&filter_product=1&title=%E4%BA%A7%E5%93%81%E9%94%80%E5%94%AE%E5%88%86%E6%9E%90&returnTo=/products?detail=1%26tab=skus
                - button "编辑主档" [ref=f14e320] [cursor=pointer]
                - button "关闭详情" [ref=f14e324] [cursor=pointer]:
                  - generic [ref=f14e328]: 关闭
            - generic [ref=f14e329]:
              - generic [ref=f14e330]:
                - text: C-P001 · 未分类
                - heading "C 合成轨道灯产品" [level=2] [ref=f14e331]
              - generic [ref=f14e332]: 在售
            - generic [ref=f14e333]:
              - generic [ref=f14e334]:
                - generic [ref=f14e335]: SKU
                - strong [ref=f14e336]: "2"
              - generic [ref=f14e337]:
                - generic [ref=f14e338]: 供应商
                - strong [ref=f14e339]: "0"
              - generic [ref=f14e340]:
                - generic [ref=f14e341]: 当前库存
                - strong [ref=f14e342]: "0"
              - generic [ref=f14e343]:
                - generic [ref=f14e344]: 参数
                - strong [ref=f14e345]: "0"
          - generic [ref=f14e346]:
            - navigation "产品详情导航" [ref=f14e347]:
              - button "总览" [ref=f14e348] [cursor=pointer]
              - button "SKU 管理2" [ref=f14e349] [cursor=pointer]
              - button "供应能力规则0" [ref=f14e350] [cursor=pointer]
              - button "订单记录0" [ref=f14e351] [cursor=pointer]
              - button "销售统计" [ref=f14e352] [cursor=pointer]
              - button "出入库流水0" [ref=f14e353] [cursor=pointer]
              - button "产品参数0" [ref=f14e354] [cursor=pointer]
              - button "证书档案0" [ref=f14e355] [cursor=pointer]
              - button "销售规则" [ref=f14e356] [cursor=pointer]
              - button "操作日志" [ref=f14e357] [cursor=pointer]
            - main [ref=f14e358]:
              - generic [ref=f14e359]:
                - generic [ref=f14e360]:
                  - heading "SKU 管理与批量维护" [level=3] [ref=f14e361]
                  - paragraph [ref=f14e372]: 新增组合在上方填写；下方统一维护已有 SKU、候选供应商及启停状态。
                - button "新增 SKU 组合" [ref=f14e373] [cursor=pointer]
              - region "SKU 参数与供应商管理" [ref=f14e375]:
                - generic [ref=f14e377]:
                  - heading "SKU 档案与供应商分配" [level=3] [ref=f14e378]
                  - paragraph [ref=f14e379]: 一份 SKU 清单管理规格与供货候选；实际采购供应商在销售订单或采购单中确认。
                - alert [ref=f14e380]:
                  - strong [ref=f14e381]: 停用结果：成功 1 项，失败 1 项
                  - list [ref=f14e382]:
                    - listitem [ref=f14e383]: C-SKU-2：合成停用失败
                - generic [ref=f14e384]:
                  - generic [ref=f14e385]:
                    - generic [ref=f14e386]:
                      - heading "已有 SKU · 1 条" [level=4] [ref=f14e387]
                      - paragraph [ref=f14e388]: 筛选参数并勾选 SKU，可批量绑定候选供应商；同一参数多选为任一匹配，不同参数同时满足。
                    - button "清空筛选" [ref=f14e390] [cursor=pointer]
                  - generic [ref=f14e391]:
                    - generic [ref=f14e392]:
                      - generic [ref=f14e393]: 启用 SKU 总数
                      - strong [ref=f14e394]: "1"
                    - generic [ref=f14e395]:
                      - generic [ref=f14e396]: 已有候选供应商
                      - strong [ref=f14e397]: "1"
                    - generic [ref=f14e398]:
                      - generic [ref=f14e399]: 覆盖率
                      - strong [ref=f14e400]: 100%
                  - generic [ref=f14e401]:
                    - textbox "搜索 SKU 编码、中文名称或 Sales Model" [ref=f14e402]
                    - combobox [ref=f14e403]:
                      - option "全部来源" [selected]
                      - option "按供货范围匹配"
                      - option "曾采购过"
                      - option "手动添加"
                      - option "已登记供货信息"
                  - generic [ref=f14e405]:
                    - generic [ref=f14e406]:
                      - checkbox "显示已停用 SKU" [ref=f14e407]
                      - text: 显示已停用 SKU
                    - generic [ref=f14e408]: 已选 1 项（仅当前筛选结果）
                    - button "批量绑定供应商" [ref=f14e409] [cursor=pointer]
                    - button "停用 1 项" [ref=f14e410] [cursor=pointer]
                    - button "取消选择" [ref=f14e411] [cursor=pointer]
                  - table [ref=f14e413]:
                    - rowgroup [ref=f14e414]:
                      - row [ref=f14e415]:
                        - columnheader [ref=f14e416]:
                          - checkbox "选择当前筛选的全部 SKU" [checked] [ref=f14e417]
                        - columnheader "SKU Code" [ref=f14e418]
                        - columnheader "中文名称 / Sales Model" [ref=f14e419]
                        - columnheader "规格" [ref=f14e420]
                        - columnheader "库存 / 单位" [ref=f14e421]
                        - columnheader "成本 / 售价" [ref=f14e422]
                        - columnheader "可选供应商" [ref=f14e423]
                        - columnheader "最近采购" [ref=f14e424]
                        - columnheader "状态" [ref=f14e425]
                        - columnheader "操作" [ref=f14e426]
                    - rowgroup [ref=f14e427]:
                      - row [ref=f14e428]:
                        - cell [ref=f14e429]:
                          - checkbox "选择 C-SKU-2" [checked] [ref=f14e430]
                        - cell [ref=f14e431]:
                          - button "C-SKU-2" [ref=f14e432] [cursor=pointer]
                        - cell "C 合成轨道灯产品 · C-SKU-2 未设置 Sales Model" [ref=f14e433]:
                          - strong [ref=f14e434]: C 合成轨道灯产品 · C-SKU-2
                          - generic [ref=f14e435]: 未设置 Sales Model
                        - cell "—" [ref=f14e436]
                        - cell "0.00 pcs" [ref=f14e437]:
                          - text: "0.00"
                          - generic [ref=f14e438]: pcs
                        - cell "0.0000 / 0.0000 USD" [ref=f14e439]:
                          - text: 0.0000 / 0.0000
                          - generic [ref=f14e440]: USD
                        - cell [ref=f14e441]:
                          - strong [ref=f14e442]: C 合成照明供应商
                        - cell "尚未采购" [ref=f14e443]
                        - cell "启用" [ref=f14e444]
                        - cell [ref=f14e445]:
                          - button "查看 SKU" [ref=f14e446] [cursor=pointer]
                - group [ref=f14e447]:
                  - generic "参数变更与历史方案 调整已有 SKU 时，先分析影响再确认发布" [ref=f14e448] [cursor=pointer]
```

# Test source

```ts
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
  137 |   await expect(page.getByText('C-SKU-2：合成停用失败',{exact:true})).toBeVisible()
> 138 |   await expect(rows.locator('input[type=checkbox]')).toBeChecked()
      |                                                      ^ Error: expect(locator).toBeChecked() failed
  139 |   expect((await (await page.request.get(`/api/skus/${fixture.skus[0]}/`)).json()).active).toBe(false)
  140 |   expect((await (await page.request.get(`/api/skus/${fixture.skus[1]}/`)).json()).active).toBe(true)
  141 |   await shot('batch-partial-real-readback')
  142 |   await page.getByRole('button',{name:'停用 1 项',exact:true}).click()
  143 |   await page.getByTestId('dialog-confirm').click()
  144 |   await expect(page.getByText(/成功 0 项，失败 1 项/)).toBeVisible()
  145 |   await shot('batch-total-failure-retained')
  146 |   await page.unroute(failed)
  147 |   await page.getByRole('button',{name:'停用 1 项',exact:true}).click()
  148 |   await page.getByTestId('dialog-confirm').click()
  149 |   await expect(page.getByText('已停用 1 项 SKU。',{exact:true})).toBeVisible()
  150 |   expect((await (await page.request.get(`/api/skus/${fixture.skus[1]}/`)).json()).active).toBe(false)
  151 |   await page.getByLabel('显示已停用',{exact:false}).check()
  152 |   await page.locator('.candidate-table thead input').check()
  153 |   await page.getByRole('button',{name:'重新启用 2 项',exact:true}).click()
  154 |   await page.getByTestId('dialog-confirm').click()
  155 |   await expect(page.getByText('已启用 2 项 SKU。',{exact:true})).toBeVisible()
  156 |   for (const id of fixture.skus) expect((await (await page.request.get(`/api/skus/${id}/`)).json()).active).toBe(true)
  157 |   await shot('batch-success-real-readback')
  158 |   await rows.first().locator('input[type=checkbox]').check()
  159 |   await page.getByRole('button',{name:'批量绑定供应商',exact:true}).click()
  160 |   const binding=page.getByRole('dialog',{name:'批量绑定供应商',exact:true})
  161 |   await binding.getByRole('switch').check()
  162 |   await binding.getByLabel('选择C 合成照明供应商',{exact:true}).check()
  163 |   await binding.getByRole('button',{name:'关闭',exact:true}).click()
  164 |   await page.getByTestId('dialog-cancel').click()
  165 |   await expect(binding.getByLabel('选择C 合成照明供应商',{exact:true})).toBeChecked()
  166 |   await expect(binding.getByRole('button',{name:'关闭',exact:true})).toBeFocused()
  167 |   await binding.getByRole('button',{name:'关闭',exact:true}).click()
  168 |   await page.getByTestId('dialog-confirm').click()
  169 |   await expect(binding).toHaveCount(0)
  170 |   await expect(page.getByRole('button',{name:'批量绑定供应商',exact:true})).toBeFocused()
  171 |   await page.getByRole('button',{name:'批量绑定供应商',exact:true}).click()
  172 |   await binding.getByRole('switch').check()
  173 |   await binding.getByLabel('选择C 合成照明供应商',{exact:true}).check()
  174 |   await binding.getByRole('button',{name:'保存候选供应商',exact:true}).click()
  175 |   await expect(binding).toHaveCount(0)
  176 |   const savedPool=await (await page.request.get(`/api/products/${fixture.product}/supplier-candidate-pool/`)).json()
  177 |   expect(savedPool.rows.find(row=>row.sku_id===fixture.skus[0]).candidate_source_types).toContain('manual')
  178 |   await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  179 |   await shot('binding-saved-real-readback')
  180 |   await page.getByRole('button',{name:'关闭 C 合成轨道灯产品',exact:true}).click()
  181 |   await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  182 |   await shot('binding-single-confirm-closed')
  183 | })
  184 | 
  185 | test.afterEach(async ({page}, info)=> { if(info.status!==info.expectedStatus) await page.screenshot({path:info.outputPath('failure.png')}) })
  186 | 
```