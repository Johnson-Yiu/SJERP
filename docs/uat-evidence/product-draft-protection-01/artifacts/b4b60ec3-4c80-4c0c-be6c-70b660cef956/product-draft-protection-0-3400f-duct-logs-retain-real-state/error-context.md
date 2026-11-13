# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: product-draft-protection-01.spec.js >> C editors, batch results and product logs retain real state
- Location: browser-tests\product-draft-protection-01.spec.js:6:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: '发布前核对', exact: true })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('heading', { name: '发布前核对', exact: true }) with timeout 5000ms
  - waiting for getByRole('heading', { name: '发布前核对', exact: true })

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
  - text: 产品资料
  - heading "产品管理" [level=1]
  - text: 11月14日周六 C
  - tablist "业务工作区":
    - tab "C 合成轨道灯产品未保存" [selected]: C 合成轨道灯产品 ●
    - button "关闭 C 合成轨道灯产品": ×
    - button "C 合成轨道灯产品 标签操作": ⋮
  - tabpanel "C 合成轨道灯产品":
    - heading "产品管理" [level=2]
    - paragraph: 维护产品名称、分类和销售状态；SKU 编码请在“SKU 管理”中维护。
    - button "新建产品"
    - region "页面小计":
      - article:
        - text: 产品总数
        - strong: "1"
        - text: 当前筛选范围
      - article:
        - text: 在售产品
        - strong: "1"
        - text: 可继续添加 SKU
      - article:
        - text: 开发中
        - strong: "0"
        - text: 尚未正式销售
      - article:
        - text: SKU 总数
        - strong: "2"
        - text: 产品下的 SKU
    - textbox "搜索产品":
      - /placeholder: 搜索产品编号或名称
    - combobox "产品分类筛选":
      - option "全部分类" [selected]
    - combobox "产品排序":
      - option "产品编号顺序" [selected]
      - option "产品名称顺序"
      - option "SKU 数量最多"
    - button "查询"
    - button "重置"
    - button "刷新"
    - table:
      - rowgroup:
        - row "产品编号 产品名称 销售型号前缀 主分类 状态 SKU 参数 证书":
          - columnheader "产品编号"
          - columnheader "产品名称"
          - columnheader "销售型号前缀"
          - columnheader "主分类"
          - columnheader "状态"
          - columnheader "SKU"
          - columnheader "参数"
          - columnheader "证书"
          - columnheader
      - rowgroup:
        - row "C-P001 C 合成轨道灯产品 未填写英文名称 — 未分类 在售 2 0 0":
          - cell "C-P001"
          - cell "C 合成轨道灯产品 未填写英文名称":
            - strong: C 合成轨道灯产品
            - text: 未填写英文名称
          - cell "—"
          - cell "未分类"
          - cell "在售"
          - cell "2"
          - cell "0"
          - cell "0"
          - cell:
            - button "编辑产品"
            - button "删除产品"
    - article "关联详情":
      - text: 产品管理 / 产品详情
      - link "查看经营分析":
        - /url: /reports?source=sales&group_by=product&filter_product=1&title=%E4%BA%A7%E5%93%81%E9%94%80%E5%94%AE%E5%88%86%E6%9E%90&returnTo=/products?detail=1%26tab=skus
      - button "编辑主档"
      - button "关闭详情": 关闭
      - text: C-P001 · 未分类
      - heading "C 合成轨道灯产品" [level=2]
      - text: 在售 SKU
      - strong: "2"
      - text: 供应商
      - strong: "0"
      - text: 当前库存
      - strong: "0"
      - text: 参数
      - strong: "0"
      - navigation "产品详情导航":
        - button "总览"
        - button "SKU 管理2"
        - button "供应能力规则0"
        - button "订单记录0"
        - button "销售统计"
        - button "出入库流水0"
        - button "产品参数0"
        - button "证书档案0"
        - button "销售规则"
        - button "操作日志"
      - main:
        - heading "SKU 管理与批量维护" [level=3]
        - paragraph: 新增组合在上方填写；下方统一维护已有 SKU、候选供应商及启停状态。
        - button "新增 SKU 组合"
        - region "SKU 参数与供应商管理":
          - heading "SKU 档案与供应商分配" [level=3]
          - paragraph: 一份 SKU 清单管理规格与供货候选；实际采购供应商在销售订单或采购单中确认。
          - alert: 每个参数必须有名称和稳定标识。
          - heading "已有 SKU · 2 条" [level=4]
          - paragraph: 筛选参数并勾选 SKU，可批量绑定候选供应商；同一参数多选为任一匹配，不同参数同时满足。
          - button "清空筛选"
          - text: 启用 SKU 总数
          - strong: "2"
          - text: 已有候选供应商
          - strong: "2"
          - text: 覆盖率
          - strong: 100%
          - textbox "搜索 SKU 编码、中文名称或 Sales Model"
          - combobox:
            - option "全部来源" [selected]
            - option "按供货范围匹配"
            - option "曾采购过"
            - option "手动添加"
            - option "已登记供货信息"
          - checkbox "显示已停用 SKU"
          - text: 显示已停用 SKU 已选 0 项（仅当前筛选结果）
          - button "批量绑定供应商" [disabled]
          - table:
            - rowgroup:
              - row "选择当前筛选的全部 SKU SKU Code 中文名称 / Sales Model 规格 库存 / 单位 成本 / 售价 可选供应商 最近采购 状态 操作":
                - columnheader "选择当前筛选的全部 SKU":
                  - checkbox "选择当前筛选的全部 SKU"
                - columnheader "SKU Code"
                - columnheader "中文名称 / Sales Model"
                - columnheader "规格"
                - columnheader "库存 / 单位"
                - columnheader "成本 / 售价"
                - columnheader "可选供应商"
                - columnheader "最近采购"
                - columnheader "状态"
                - columnheader "操作"
            - rowgroup:
              - row "选择 C-SKU-1 C-SKU-1 C 合成轨道灯产品 未设置 Sales Model — 0.00 pcs 0.0000 / 0.0000 USD C 合成照明供应商 尚未采购 启用 查看 SKU":
                - cell "选择 C-SKU-1":
                  - checkbox "选择 C-SKU-1"
                - cell "C-SKU-1":
                  - button "C-SKU-1"
                - cell "C 合成轨道灯产品 未设置 Sales Model":
                  - strong: C 合成轨道灯产品
                  - text: 未设置 Sales Model
                - cell "—"
                - cell "0.00 pcs"
                - cell "0.0000 / 0.0000 USD"
                - cell "C 合成照明供应商":
                  - strong: C 合成照明供应商
                - cell "尚未采购"
                - cell "启用"
                - cell "查看 SKU":
                  - button "查看 SKU"
              - row "选择 C-SKU-2 C-SKU-2 C 合成轨道灯产品 · C-SKU-2 未设置 Sales Model — 0.00 pcs 0.0000 / 0.0000 USD C 合成照明供应商 尚未采购 启用 查看 SKU":
                - cell "选择 C-SKU-2":
                  - checkbox "选择 C-SKU-2"
                - cell "C-SKU-2":
                  - button "C-SKU-2"
                - cell "C 合成轨道灯产品 · C-SKU-2 未设置 Sales Model":
                  - strong: C 合成轨道灯产品 · C-SKU-2
                  - text: 未设置 Sales Model
                - cell "—"
                - cell "0.00 pcs"
                - cell "0.0000 / 0.0000 USD"
                - cell "C 合成照明供应商":
                  - strong: C 合成照明供应商
                - cell "尚未采购"
                - cell "启用"
                - cell "查看 SKU":
                  - button "查看 SKU"
          - group:
            - text: 参数变更与历史方案 调整已有 SKU 时，先分析影响再确认发布
            - paragraph: 新增参数先补值；不再区分商品的参数改为普通属性。需要拆分时只添加实际组合；出现相同组合时合并为新 SKU。旧单据、库存及供货档案保留在原 SKU。
            - button "继续 V1 草稿"
            - text: 已发布：尚无
            - heading "V1 草稿" [level=4]
            - button "＋ 新增参数"
            - table:
              - rowgroup:
                - row "参数名称 单位 补充默认值 区分 SKU 参与型号 必填":
                  - columnheader "参数名称"
                  - columnheader "单位"
                  - columnheader "补充默认值"
                  - columnheader "区分 SKU"
                  - columnheader "参与型号"
                  - columnheader "必填"
              - rowgroup:
                - row "合成参数 1920":
                  - cell "合成参数 1920":
                    - textbox "参数名称": 合成参数 1920
                  - cell:
                    - textbox "单位"
                  - cell:
                    - textbox "仅补充空值"
                  - cell:
                    - checkbox [checked]
                  - cell:
                    - checkbox
                  - cell:
                    - checkbox
                - row:
                  - cell:
                    - textbox "参数名称"
                  - cell:
                    - textbox "单位"
                  - cell:
                    - textbox "仅补充空值"
                  - cell:
                    - checkbox [checked]
                  - cell:
                    - checkbox
                  - cell:
                    - checkbox
            - paragraph: 取消“区分 SKU”和“参与型号”即可降为普通属性，原取值仍保留。默认值只用于空缺参数，已有值不会被覆盖。
            - heading "现有 SKU 补值 / 拆分" [level=4]
            - textbox "搜索 SKU 编码或名称"
            - strong: C 合成轨道灯产品 · C-SKU-1
            - button "＋ 拆分一个实际组合"
            - text: 合成参数 1920
            - textbox "合成参数 1920":
              - /placeholder: 待补值
            - textbox:
              - /placeholder: 待补值
            - strong: C 合成轨道灯产品 · C-SKU-2 · C-SKU-2
            - button "＋ 拆分一个实际组合"
            - text: 合成参数 1920
            - textbox "合成参数 1920":
              - /placeholder: 待补值
            - textbox:
              - /placeholder: 待补值
            - button "保存草稿并分析影响"
            - button "丢弃草稿"
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
  23  |     await page.getByRole('button',{name:'预览匹配',exact:true}).click()
  24  |     await expect(page.getByText('匹配 2 个现有 SKU：',{exact:false})).toBeVisible()
  25  |     await shot(`rule-preview-before-save-${width}`)
  26  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  27  |     await page.getByTestId('dialog-cancel').click()
  28  |     await expect(name).toHaveValue(`合成能力规则 ${width}`)
  29  |     await shot(`rule-retained-${width}`)
  30  |     if (width !== 390) {
  31  |       await page.getByRole('link',{name:'客户管理',exact:true}).click()
  32  |       await expect(page).toHaveURL(/customers/)
  33  |       await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  34  |       await page.getByRole('tab',{name:/C 合成轨道灯产品/}).click()
  35  |       await expect(name).toHaveValue(`合成能力规则 ${width}`)
  36  |       await page.getByRole('button',{name:'关闭 C 合成轨道灯产品',exact:true}).click()
  37  |       await page.getByTestId('dialog-cancel').click()
  38  |       await expect(name).toHaveValue(`合成能力规则 ${width}`)
  39  |       const dialogEvent=page.waitForEvent('dialog')
  40  |       const refresh=page.reload().catch(()=>{})
  41  |       const refreshDialog=await dialogEvent
  42  |       expect(refreshDialog.type()).toBe('beforeunload')
  43  |       await refreshDialog.dismiss(); await refresh
  44  |       await expect(name).toHaveValue(`合成能力规则 ${width}`)
  45  |     }
  46  |     // A rejected save must retain values and the dirty guard.
  47  |     await page.route('**/api/supplier-capabilities/', async route => route.request().method()==='POST' ? route.fulfill({status:400,json:{detail:'合成保存失败，请重试'}}) : route.continue())
  48  |     await page.getByRole('button',{name:'保存规则',exact:true}).click()
  49  |     await expect(name).toHaveValue(`合成能力规则 ${width}`)
  50  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  51  |     await page.getByTestId('dialog-cancel').click()
  52  |     await page.unroute('**/api/supplier-capabilities/')
  53  |     await page.getByRole('button',{name:'保存规则',exact:true}).click()
  54  |     await expect(name).toHaveCount(0)
  55  |     const rules=await (await page.request.get(`/api/supplier-capabilities/?product=${fixture.product}`)).json()
  56  |     expect((rules.results||rules).some(rule=>rule.name===`合成能力规则 ${width}` && rule.characteristics['包装']==='合成测试纸盒')).toBeTruthy()
  57  |     await shot(`rule-saved-${width}`)
  58  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  59  |     await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  60  |     await page.getByRole('button',{name:'操作日志',exact:true}).click()
  61  |     await expect(page).toHaveURL(/tab=operation_logs/)
  62  |     await page.reload()
  63  |     await expect(page.getByRole('button',{name:'操作日志',exact:true})).toHaveClass(/active/)
  64  |     await expect(page.locator('.operation-log-panel')).toBeVisible()
  65  |     await shot(`log-reopened-${width}`)
  66  |     await page.goto(`/products?detail=${fixture.product}&tab=skus`)
  67  |     await page.locator('.parameter-plan-panel summary').click()
  68  |     await page.getByRole('button',{name:/创建参数方案草稿|继续 V\d+ 草稿/}).click()
  69  |     if (await page.getByLabel('参数名称',{exact:true}).count()===0) await page.getByRole('button',{name:'＋ 新增参数',exact:true}).click()
  70  |     const parameter=page.getByLabel('参数名称',{exact:true}).first()
  71  |     await parameter.fill(`合成参数 ${width}`)
  72  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  73  |     await page.getByTestId('dialog-cancel').click()
  74  |     await expect(parameter).toHaveValue(`合成参数 ${width}`)
  75  |     await page.getByRole('button',{name:/继续 V\d+ 草稿/}).click()
  76  |     await page.getByTestId('dialog-cancel').click()
  77  |     await expect(parameter).toHaveValue(`合成参数 ${width}`)
  78  |     await shot(`plan-retained-${width}`)
  79  |     await page.route(`**/api/products/${fixture.product}/sku-plan/`, route=>route.request().method()==='PATCH'?route.fulfill({status:400,json:{detail:'合成方案保存失败'}}):route.continue())
  80  |     await page.getByRole('button',{name:'保存草稿并分析影响',exact:true}).click()
  81  |     await expect(page.getByText('合成方案保存失败',{exact:true})).toBeVisible()
  82  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  83  |     await page.getByTestId('dialog-cancel').click()
  84  |     await expect(parameter).toHaveValue(`合成参数 ${width}`)
  85  |     await page.unroute(`**/api/products/${fixture.product}/sku-plan/`)
  86  |     await page.getByRole('button',{name:'保存草稿并分析影响',exact:true}).click()
> 87  |     await expect(page.getByRole('heading',{name:'发布前核对',exact:true})).toBeVisible()
      |                                                                       ^ Error: expect(locator).toBeVisible() failed
  88  |     const plan=await (await page.request.get(`/api/products/${fixture.product}/sku-plan/`)).json()
  89  |     expect(plan.plans.find(p=>p.status==='draft').definitions[0].name).toBe(`合成参数 ${width}`)
  90  |     await shot(`plan-saved-readback-${width}`)
  91  |     await page.getByRole('button',{name:'总览',exact:true}).click()
  92  |     await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  93  |   }
  94  |   await page.setViewportSize({width:1366,height:768})
  95  |   await page.goto(`/products?detail=${fixture.product}&tab=skus`)
  96  |   const rows=page.locator('.candidate-table tbody tr')
  97  |   await expect(rows).toHaveCount(2)
  98  |   const checkbox=page.locator('.candidate-table thead input')
  99  |   await checkbox.scrollIntoViewIfNeeded()
  100 |   const box=await checkbox.boundingBox()
  101 |   await page.mouse.click(box.x+1,box.y+box.height/2)
  102 |   await expect(checkbox).toBeChecked()
  103 |   // Inject exactly one rejection; the other PATCH and all readbacks use the real isolated API.
  104 |   const failed=`**/api/skus/${fixture.skus[1]}/`
  105 |   await page.route(failed,route=>route.request().method()==='PATCH'?route.fulfill({status:400,json:{detail:'合成停用失败'}}):route.continue())
  106 |   await page.getByRole('button',{name:'停用 2 项',exact:true}).click()
  107 |   await page.getByTestId('dialog-confirm').click()
  108 |   await expect(page.getByText(/成功 1 项，失败 1 项/)).toBeVisible()
  109 |   await expect(page.getByText('C-SKU-2：合成停用失败',{exact:true})).toBeVisible()
  110 |   await expect(rows.locator('input[type=checkbox]')).toBeChecked()
  111 |   expect((await (await page.request.get(`/api/skus/${fixture.skus[0]}/`)).json()).active).toBe(false)
  112 |   expect((await (await page.request.get(`/api/skus/${fixture.skus[1]}/`)).json()).active).toBe(true)
  113 |   await shot('batch-partial-real-readback')
  114 |   await page.getByRole('button',{name:'停用 1 项',exact:true}).click()
  115 |   await page.getByTestId('dialog-confirm').click()
  116 |   await expect(page.getByText(/成功 0 项，失败 1 项/)).toBeVisible()
  117 |   await shot('batch-total-failure-retained')
  118 |   await page.unroute(failed)
  119 |   await page.getByRole('button',{name:'停用 1 项',exact:true}).click()
  120 |   await page.getByTestId('dialog-confirm').click()
  121 |   await expect(page.getByText('已停用 1 项 SKU。',{exact:true})).toBeVisible()
  122 |   expect((await (await page.request.get(`/api/skus/${fixture.skus[1]}/`)).json()).active).toBe(false)
  123 |   await page.getByLabel('显示已停用',{exact:false}).check()
  124 |   await page.locator('.candidate-table thead input').check()
  125 |   await page.getByRole('button',{name:'重新启用 2 项',exact:true}).click()
  126 |   await page.getByTestId('dialog-confirm').click()
  127 |   await expect(page.getByText('已启用 2 项 SKU。',{exact:true})).toBeVisible()
  128 |   for (const id of fixture.skus) expect((await (await page.request.get(`/api/skus/${id}/`)).json()).active).toBe(true)
  129 |   await shot('batch-success-real-readback')
  130 |   await rows.first().locator('input[type=checkbox]').check()
  131 |   await page.getByRole('button',{name:'批量绑定供应商',exact:true}).click()
  132 |   const binding=page.getByRole('dialog',{name:'批量绑定供应商',exact:true})
  133 |   await binding.getByRole('switch').check()
  134 |   await binding.getByLabel('选择C 合成照明供应商',{exact:true}).check()
  135 |   await binding.getByRole('button',{name:'关闭',exact:true}).click()
  136 |   await page.getByTestId('dialog-cancel').click()
  137 |   await expect(binding.getByLabel('选择C 合成照明供应商',{exact:true})).toBeChecked()
  138 |   await page.getByRole('button',{name:'关闭 C 合成轨道灯产品',exact:true}).click()
  139 |   await page.getByTestId('dialog-confirm').click()
  140 |   await expect(binding).toHaveCount(0)
  141 |   await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  142 |   await shot('binding-single-confirm-closed')
  143 | })
  144 | 
  145 | test.afterEach(async ({page}, info)=> { if(info.status!==info.expectedStatus) await page.screenshot({path:info.outputPath('failure.png')}) })
  146 | 
```