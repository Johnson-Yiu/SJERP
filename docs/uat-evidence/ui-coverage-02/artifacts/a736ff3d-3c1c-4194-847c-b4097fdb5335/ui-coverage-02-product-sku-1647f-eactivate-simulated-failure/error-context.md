# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui-coverage-02-product-sku-batch-failure.spec.js >> product SKU batch deactivate simulated failure
- Location: browser-tests\ui-coverage-02-product-sku-batch-failure.spec.js:6:1

# Error details

```
Test timeout of 90000ms exceeded.
```

```
Error: locator.scrollIntoViewIfNeeded: Test timeout of 90000ms exceeded.
Call log:
  - waiting for locator('.sku-management .error').filter({ hasText: '1 个操作失败' })

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
        - generic [ref=e211]: 11月10日周二
        - generic "codex" [ref=e212]: C
    - tablist "业务工作区" [ref=e214]:
      - generic [ref=e215]:
        - tab "产品管理" [ref=e216] [cursor=pointer]
        - button "关闭 产品管理" [ref=e217] [cursor=pointer]: ×
        - button "产品管理 标签操作" [ref=e218] [cursor=pointer]: ⋮
      - generic [ref=e219]:
        - tab "Workspace Light" [selected] [ref=e220] [cursor=pointer]
        - button "关闭 Workspace Light" [ref=e221] [cursor=pointer]: ×
        - button "Workspace Light 标签操作" [ref=e222] [cursor=pointer]: ⋮
    - tabpanel "Workspace Light" [ref=e224]:
      - generic [ref=e225]:
        - generic [ref=e226]:
          - generic [ref=e227]:
            - heading "产品管理" [level=2] [ref=e228]
            - paragraph [ref=e229]: 维护产品名称、分类和销售状态；SKU 编码请在“SKU 管理”中维护。
          - button "新建产品" [ref=e230] [cursor=pointer]
        - region "页面小计" [ref=e233]:
          - article [ref=e234]:
            - generic [ref=e235]: 产品总数
            - strong [ref=e236]: "1"
            - generic [ref=e237]: 当前筛选范围
          - article [ref=e241]:
            - generic [ref=e242]: 在售产品
            - strong [ref=e243]: "1"
            - generic [ref=e244]: 可继续添加 SKU
          - article [ref=e248]:
            - generic [ref=e249]: 开发中
            - strong [ref=e250]: "0"
            - generic [ref=e251]: 尚未正式销售
          - article [ref=e255]:
            - generic [ref=e256]: SKU 总数
            - strong [ref=e257]: "1"
            - generic [ref=e258]: 产品下的 SKU
        - generic [ref=e262]:
          - textbox "搜索产品" [ref=e267]:
            - /placeholder: 搜索产品编号或名称
          - combobox "产品分类筛选" [ref=e270] [cursor=pointer]:
            - option "全部分类" [selected]
            - option "Workspace Category"
          - combobox "产品排序" [ref=e271]:
            - option "产品编号顺序" [selected]
            - option "产品名称顺序"
            - option "SKU 数量最多"
          - button "查询" [ref=e272] [cursor=pointer]
          - button "重置" [ref=e273] [cursor=pointer]
          - button "刷新" [ref=e274] [cursor=pointer]
        - table [ref=e277]:
          - rowgroup [ref=e278]:
            - row [ref=e279]:
              - columnheader "产品编号" [ref=e280]
              - columnheader "产品名称" [ref=e281]
              - columnheader "销售型号前缀" [ref=e282]
              - columnheader "主分类" [ref=e283]
              - columnheader "状态" [ref=e284]
              - columnheader "SKU" [ref=e285]
              - columnheader "参数" [ref=e286]
              - columnheader "证书" [ref=e287]
              - columnheader [ref=e288]
          - rowgroup [ref=e289]:
            - row [ref=e290] [cursor=pointer]:
              - cell "WS-P001" [ref=e291]
              - cell "Workspace Light 未填写英文名称" [ref=e292]:
                - strong [ref=e293]: Workspace Light
                - generic [ref=e294]: 未填写英文名称
              - cell "—" [ref=e295]
              - cell "Workspace Category" [ref=e296]
              - cell "在售" [ref=e297]
              - cell "1" [ref=e299]
              - cell "0" [ref=e300]
              - cell "0" [ref=e301]
              - cell [ref=e302]:
                - generic [ref=e303]:
                  - button "编辑产品" [ref=e304]
                  - button "删除产品" [ref=e308]
        - article "关联详情" [ref=e313]:
          - generic [ref=e314]:
            - generic [ref=e315]:
              - generic [ref=e316]: 产品管理 / 产品详情
              - generic [ref=e318]:
                - link "查看经营分析" [ref=e319] [cursor=pointer]:
                  - /url: /reports?source=sales&group_by=product&filter_product=1&title=%E4%BA%A7%E5%93%81%E9%94%80%E5%94%AE%E5%88%86%E6%9E%90&returnTo=/products?detail=1%26tab=skus
                - button "编辑主档" [ref=e324] [cursor=pointer]
                - button "关闭详情" [ref=e328] [cursor=pointer]:
                  - generic [ref=e332]: 关闭
            - generic [ref=e333]:
              - generic [ref=e334]:
                - text: WS-P001 · Workspace Category
                - heading "Workspace Light" [level=2] [ref=e335]
              - generic [ref=e336]: 在售
            - generic [ref=e337]:
              - generic [ref=e338]:
                - generic [ref=e339]: SKU
                - strong [ref=e340]: "1"
              - generic [ref=e341]:
                - generic [ref=e342]: 供应商
                - strong [ref=e343]: "0"
              - generic [ref=e344]:
                - generic [ref=e345]: 当前库存
                - strong [ref=e346]: "0"
              - generic [ref=e347]:
                - generic [ref=e348]: 参数
                - strong [ref=e349]: "0"
          - generic [ref=e350]:
            - navigation "产品详情导航" [ref=e351]:
              - button "总览" [ref=e352] [cursor=pointer]
              - button "SKU 管理1" [ref=e353] [cursor=pointer]
              - button "供应能力规则0" [ref=e354] [cursor=pointer]
              - button "订单记录0" [ref=e355] [cursor=pointer]
              - button "销售统计" [ref=e356] [cursor=pointer]
              - button "出入库流水0" [ref=e357] [cursor=pointer]
              - button "产品参数0" [ref=e358] [cursor=pointer]
              - button "证书档案0" [ref=e359] [cursor=pointer]
              - button "销售规则" [ref=e360] [cursor=pointer]
              - button "操作日志" [ref=e361] [cursor=pointer]
            - main [ref=e362]:
              - generic [ref=e363]:
                - generic [ref=e364]:
                  - heading "SKU 管理与批量维护" [level=3] [ref=e365]
                  - paragraph [ref=e376]: 新增组合在上方填写；下方统一维护已有 SKU、候选供应商及启停状态。
                - button "新增 SKU 组合" [ref=e377] [cursor=pointer]
              - region "SKU 参数与供应商管理" [ref=e379]:
                - generic [ref=e381]:
                  - heading "SKU 档案与供应商分配" [level=3] [ref=e382]
                  - paragraph [ref=e383]: 一份 SKU 清单管理规格与供货候选；实际采购供应商在销售订单或采购单中确认。
                - status [ref=e384]: 成功停用 0 个 SKU。
                - generic [ref=e385]:
                  - generic [ref=e386]:
                    - generic [ref=e387]:
                      - heading "已有 SKU · 1 条" [level=4] [ref=e388]
                      - paragraph [ref=e389]: 筛选参数并勾选 SKU，可批量绑定候选供应商；同一参数多选为任一匹配，不同参数同时满足。
                    - button "清空筛选" [ref=e391] [cursor=pointer]
                  - generic [ref=e392]:
                    - generic [ref=e393]:
                      - generic [ref=e394]: 启用 SKU 总数
                      - strong [ref=e395]: "1"
                    - generic [ref=e396]:
                      - generic [ref=e397]: 已有候选供应商
                      - strong [ref=e398]: "0"
                    - generic [ref=e399]:
                      - generic [ref=e400]: 覆盖率
                      - strong [ref=e401]: 0%
                  - generic [ref=e402]:
                    - textbox "搜索 SKU 编码、中文名称或 Sales Model" [ref=e403]
                    - combobox [ref=e404]:
                      - option "全部来源" [selected]
                      - option "按供货范围匹配"
                      - option "曾采购过"
                      - option "手动添加"
                      - option "已登记供货信息"
                  - generic [ref=e406]:
                    - generic [ref=e407]:
                      - checkbox "显示已停用 SKU" [ref=e408]
                      - text: 显示已停用 SKU
                    - generic [ref=e409]: 已选 0 项（仅当前筛选结果）
                    - button "批量绑定供应商" [disabled] [ref=e410]
                  - table [ref=e412]:
                    - rowgroup [ref=e413]:
                      - row [ref=e414]:
                        - columnheader [ref=e415]:
                          - checkbox "选择当前筛选的全部 SKU" [ref=e416]
                        - columnheader "SKU Code" [ref=e417]
                        - columnheader "中文名称 / Sales Model" [ref=e418]
                        - columnheader "规格" [ref=e419]
                        - columnheader "库存 / 单位" [ref=e420]
                        - columnheader "成本 / 售价" [ref=e421]
                        - columnheader "可选供应商" [ref=e422]
                        - columnheader "最近采购" [ref=e423]
                        - columnheader "状态" [ref=e424]
                        - columnheader "操作" [ref=e425]
                    - rowgroup [ref=e426]:
                      - row [ref=e427]:
                        - cell [ref=e428]:
                          - checkbox "选择 WS-SKU001" [ref=e429]
                        - cell [ref=e430]:
                          - button "WS-SKU001" [ref=e431] [cursor=pointer]
                        - cell "Workspace Light 未设置 Sales Model" [ref=e432]:
                          - strong [ref=e433]: Workspace Light
                          - generic [ref=e434]: 未设置 Sales Model
                        - cell "—" [ref=e435]
                        - cell "0.00 pcs" [ref=e436]:
                          - text: "0.00"
                          - generic [ref=e437]: pcs
                        - cell "4.0000 / 10.0000 USD" [ref=e438]:
                          - text: 4.0000 / 10.0000
                          - generic [ref=e439]: USD
                        - cell "暂无可选供应商" [ref=e440]
                        - cell "尚未采购" [ref=e441]
                        - cell "启用" [ref=e442]
                        - cell [ref=e443]:
                          - button "查看 SKU" [ref=e444] [cursor=pointer]
                - group [ref=e445]:
                  - generic "参数变更与历史方案 调整已有 SKU 时，先分析影响再确认发布" [ref=e446] [cursor=pointer]
```

# Test source

```ts
  1  | import {test,expect} from '@playwright/test'
  2  | import {mkdir,writeFile} from 'node:fs/promises'
  3  | import {createHash} from 'node:crypto'
  4  | import path from 'node:path'
  5  | test.use({channel:'chrome',viewport:{width:1920,height:1080},deviceScaleFactor:1})
  6  | test('product SKU batch deactivate simulated failure',async({page,browser})=>{
  7  |  test.setTimeout(90000);const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true});let patches=0;await page.route('**/api/skus/**',async route=>{if(route.request().method()==='PATCH'){patches++;await route.fulfill({status:503,contentType:'application/json',body:'{"detail":"simulated"}'})}else await route.continue()});await page.goto('/products',{waitUntil:'networkidle'});await page.getByRole('row').filter({hasText:'WS-P001'}).click();const modal=page.locator('.product-detail-modal');await modal.locator('section').filter({hasText:'SKU 管理预览'}).getByRole('button',{name:'查看全部'}).click();await page.getByPlaceholder('搜索 SKU 编码、中文名称或 Sales Model').click();let reached=false;for(let i=0;i<30;i++){await page.keyboard.press('Tab');if(await page.evaluate(()=>document.activeElement?.getAttribute('aria-label')==='选择 WS-SKU001')){reached=true;break}}expect(reached).toBe(true);await page.keyboard.press('Space');await expect(page.getByLabel('选择 WS-SKU001')).toBeChecked();await page.getByRole('button',{name:'停用 1 项'}).click();await page.getByRole('dialog',{name:'确认停用 SKU'}).getByRole('button',{name:'确认停用'}).click();const error=page.locator('.sku-management .error').filter({hasText:'1 个操作失败'});await expect(error).toBeAttached();await expect.poll(()=>patches).toBe(1);await expect(page.getByLabel('选择 WS-SKU001')).not.toBeChecked();
  8  |  async function capture(id,steps){const state=await page.evaluate(()=>{const e=[...document.querySelectorAll('.sku-management .error')].find(x=>x.textContent.includes('1 个操作失败'));return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,error_rect:e?.getBoundingClientRect().toJSON(),visibleText:document.body.innerText.slice(0,5500)}}),n=id+'.png',b=await page.screenshot({path:path.join(root,'originals',n)});entries.push({evidence_id:id,surface_id:'P008',expanded_case_id:id,source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role:'authenticated codex test superuser',data:'isolated workspace fixture; WS-P001 active WS-SKU001',steps,patch_requests_intercepted:patches,simulated:true,capture_time_utc:new Date().toISOString(),file:`originals/${n}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)},review:'NOT_REVIEWED',limitation:'PATCH intercepted and fulfilled with simulated 503 before service; no SKU deactivated'});await writeFile(path.join(root,'product-sku-batch-failure-manifest.json'),JSON.stringify(entries,null,2));return state}
> 9  |  await capture('PRODUCT-SKU-BATCH-FAIL-B-1920',['open product SKU management','select SKU by keyboard','confirm deactivate','return simulated 503']);await error.scrollIntoViewIfNeeded();await capture('PRODUCT-SKU-BATCH-FAIL-SCROLLED-B-1920',['scroll error into view']);
     |                                                                                                                                                                  ^ Error: locator.scrollIntoViewIfNeeded: Test timeout of 90000ms exceeded.
  10 | })
  11 | 
```