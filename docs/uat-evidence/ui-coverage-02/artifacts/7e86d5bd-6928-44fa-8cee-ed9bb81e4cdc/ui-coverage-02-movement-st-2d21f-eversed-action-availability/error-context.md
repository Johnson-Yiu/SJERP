# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui-coverage-02-movement-states.spec.js >> inventory manual automatic reversed action availability
- Location: browser-tests\ui-coverage-02-movement-states.spec.js:6:1

# Error details

```
Error: expect(locator).toHaveCount(expected) failed

Locator:  getByRole('row').filter({ hasText: 'WS-MOV-REVERSED' }).getByTitle('冲销')
Expected: 0
Received: 2
Timeout:  5000ms

Call log:
  - Expect "toHaveCount" getByRole('row').filter({ hasText: 'WS-MOV-REVERSED' }).getByTitle('冲销') with timeout 5000ms
  - waiting for getByRole('row').filter({ hasText: 'WS-MOV-REVERSED' }).getByTitle('冲销')
    13 × locator resolved to 2 elements
       - unexpected value "2"

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
        - text: Inventory ledger
        - heading "库存流水" [level=1] [ref=e209]
      - generic [ref=e210]:
        - generic [ref=e211]: 11月10日周二
        - generic "codex" [ref=e212]: C
    - tablist "业务工作区" [ref=e214]:
      - generic [ref=e215]:
        - tab "库存流水" [selected] [ref=e216] [cursor=pointer]
        - button "关闭 库存流水" [ref=e217] [cursor=pointer]: ×
        - button "库存流水 标签操作" [ref=e218] [cursor=pointer]: ⋮
    - tabpanel "库存流水" [ref=e220]:
      - generic [ref=e221]:
        - generic [ref=e222]:
          - paragraph [ref=e224]: 查看每次库存增减及其来源；库存缺口仅作核对参考，不会自动下采购单。
          - button "新建库存调整" [ref=e225] [cursor=pointer]
        - region "页面小计" [ref=e228]:
          - article [ref=e229]:
            - generic [ref=e230]: 流水记录
            - strong [ref=e231]: "4"
            - generic [ref=e232]: 当前筛选结果
          - article [ref=e236]:
            - generic [ref=e237]: 入库记录
            - strong [ref=e238]: "3"
            - generic [ref=e239]: 库存增加
          - article [ref=e243]:
            - generic [ref=e244]: 出库记录
            - strong [ref=e245]: "1"
            - generic [ref=e246]: 库存减少
          - article [ref=e250]:
            - generic [ref=e251]: 冲销记录
            - strong [ref=e252]: "1"
            - generic [ref=e253]: 冲销生成
        - generic "库存流水筛选" [ref=e257]:
          - generic [ref=e258]:
            - text: 搜索
            - textbox "搜索库存流水" [ref=e259]:
              - /placeholder: 流水号、SKU、产品、订单、仓库、参考号
          - generic [ref=e260]:
            - text: 类型
            - combobox "按流水类型筛选" [ref=e261]:
              - option "全部类型" [selected]
              - option "盘盈入库"
              - option "盘亏出库"
              - option "样品出库"
              - option "客户退回"
              - option "调拨入库"
              - option "调拨出库"
              - option "生产入库"
              - option "生产领料"
              - option "其他入库"
              - option "其他出库"
          - generic [ref=e262]:
            - text: 方向
            - combobox "按库存方向筛选" [ref=e263]:
              - option "全部方向" [selected]
              - option "入库"
              - option "出库"
          - generic [ref=e264]:
            - text: 来源
            - combobox "按流水来源筛选" [ref=e265]:
              - option "全部来源" [selected]
              - option "系统自动"
              - option "手工登记"
              - option "冲销"
          - button "重置" [ref=e266] [cursor=pointer]
        - paragraph [ref=e267]: 数量按 SKU 基础单位显示；自动流水不可手工修改。
        - table [ref=e270]:
          - rowgroup [ref=e271]:
            - row [ref=e272]:
              - columnheader "日期" [ref=e273]
              - columnheader "流水号" [ref=e274]
              - columnheader "SKU / 产品" [ref=e275]
              - columnheader "类型" [ref=e276]
              - columnheader "库存变动" [ref=e277]
              - columnheader "来源" [ref=e278]
              - columnheader "仓库" [ref=e279]
              - columnheader "关联单据" [ref=e280]
              - columnheader "冲销状态" [ref=e281]
              - columnheader "操作" [ref=e282]
          - rowgroup [ref=e283]:
            - row [ref=e284] [cursor=pointer]:
              - cell "2026-11-10" [ref=e285]
              - cell "WS-MOV-AUTO" [ref=e286]
              - cell "WS-SKU001 Workspace Light 基础单位：pcs" [ref=e287]:
                - strong [ref=e288]: WS-SKU001
                - generic [ref=e289]: Workspace Light
                - generic [ref=e290]: 基础单位：pcs
              - cell "盘盈入库" [ref=e291]
              - cell "+2 pcs" [ref=e293]
              - cell "系统自动" [ref=e294]
              - cell "隔离仓" [ref=e296]
              - cell "—" [ref=e297]
              - cell "正常" [ref=e298]
              - cell [ref=e299]:
                - button "查看详情" [ref=e301]
            - row [ref=e304] [cursor=pointer]:
              - cell "2026-11-10" [ref=e305]
              - cell "REV-F3E03E4FC047429C" [ref=e306]
              - cell "WS-SKU001 Workspace Light 基础单位：pcs" [ref=e307]:
                - strong [ref=e308]: WS-SKU001
                - generic [ref=e309]: Workspace Light
                - generic [ref=e310]: 基础单位：pcs
              - cell "盘亏出库" [ref=e311]
              - cell "-3 pcs" [ref=e313]
              - cell "冲销生成" [ref=e314]
              - cell "隔离仓" [ref=e316]
              - cell "WS-MOV-REVERSED" [ref=e317]
              - cell "冲销流水" [ref=e318]
              - cell [ref=e319]:
                - button "查看详情" [ref=e321]
            - row [ref=e324] [cursor=pointer]:
              - cell "2026-11-10" [ref=e325]
              - cell "WS-MOV-REVERSED" [ref=e326]
              - cell "WS-SKU001 Workspace Light 基础单位：pcs" [ref=e327]:
                - strong [ref=e328]: WS-SKU001
                - generic [ref=e329]: Workspace Light
                - generic [ref=e330]: 基础单位：pcs
              - cell "盘盈入库" [ref=e331]
              - cell "+3 pcs" [ref=e333]
              - cell "手工登记" [ref=e334]
              - cell "隔离仓" [ref=e336]
              - cell "—" [ref=e337]
              - cell "已冲销" [ref=e338]
              - cell [ref=e339]:
                - button "查看详情" [ref=e341]
            - row [ref=e344] [cursor=pointer]:
              - cell "2026-11-10" [ref=e345]
              - cell "WS-MOV001" [ref=e346]
              - cell "WS-SKU001 Workspace Light 基础单位：pcs" [ref=e347]:
                - strong [ref=e348]: WS-SKU001
                - generic [ref=e349]: Workspace Light
                - generic [ref=e350]: 基础单位：pcs
              - cell "盘盈入库" [ref=e351]
              - cell "+10 pcs" [ref=e353]
              - cell "手工登记" [ref=e354]
              - cell "隔离仓" [ref=e356]
              - cell "—" [ref=e357]
              - cell "正常" [ref=e358]
              - cell [ref=e359]:
                - generic [ref=e360]:
                  - button "查看详情" [ref=e361]
                  - button "编辑" [ref=e364]
                  - button "冲销" [ref=e368]
```

# Test source

```ts
  1 | import {test,expect} from '@playwright/test'
  2 | import {mkdir,writeFile} from 'node:fs/promises'
  3 | import {createHash} from 'node:crypto'
  4 | import path from 'node:path'
  5 | test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
  6 | test('inventory manual automatic reversed action availability',async({page,browser})=>{
> 7 |  test.setTimeout(90000);const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT;await mkdir(path.join(root,'originals'),{recursive:true});let writes=0;await page.route('**/api/inventory-movements/**',async r=>{if(!['GET','HEAD','OPTIONS'].includes(r.request().method())){writes++;await r.abort()}else await r.continue()});await page.goto('/inventory-movements',{waitUntil:'networkidle'});const manual=page.getByRole('row').filter({hasText:'WS-MOV001'}),reversed=page.getByRole('row').filter({hasText:'WS-MOV-REVERSED'}),auto=page.getByRole('row').filter({hasText:'WS-MOV-AUTO'});await expect(manual.getByTitle('冲销')).toHaveCount(1);await expect(reversed.getByTitle('冲销')).toHaveCount(0);await expect(auto.getByTitle('冲销')).toHaveCount(0);expect(writes).toBe(0);await reversed.scrollIntoViewIfNeeded();const id='MOVEMENT-STATES-ACTIONS-B-1366',n=id+'.png',b=await page.screenshot({path:path.join(root,'originals',n)}),state=await page.evaluate(()=>({route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,visibleText:document.body.innerText.slice(0,5000)}));await writeFile(path.join(root,'movement-states-manifest.json'),JSON.stringify([{evidence_id:id,surface_id:'G093',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role:'authenticated codex test superuser',data:'isolated synthetic manual, reversed manual, automatic movements',steps:['open inventory ledger','compare action buttons'],writes,simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${n}`,sha256:createHash('sha256').update(b).digest('hex'),review:'NOT_REVIEWED',limitation:'front-end action visibility only; automatic source synthetic; no backend authorization test'}],null,2))
    |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  ^ Error: expect(locator).toHaveCount(expected) failed
  8 | })
  9 | 
```