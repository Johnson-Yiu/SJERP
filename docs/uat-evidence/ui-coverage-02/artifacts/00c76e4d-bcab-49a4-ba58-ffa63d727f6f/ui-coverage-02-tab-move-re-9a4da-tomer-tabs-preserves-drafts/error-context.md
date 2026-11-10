# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui-coverage-02-tab-move.spec.js >> reorder dirty customer tabs preserves drafts
- Location: browser-tests\ui-coverage-02-tab-move.spec.js:6:1

# Error details

```
Test timeout of 90000ms exceeded.
```

```
Error: locator.click: Test timeout of 90000ms exceeded.
Call log:
  - waiting for getByRole('button', { name: '向右移动', exact: true })

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
        - text: 客户资料
        - heading "客户管理" [level=1] [ref=e209]
      - generic [ref=e210]:
        - generic [ref=e211]: 11月10日周二
        - generic "codex" [ref=e212]: C
    - tablist "业务工作区" [ref=e214]:
      - generic [ref=e215]:
        - tab "客户管理" [ref=e216] [cursor=pointer]
        - button "关闭 客户管理" [ref=e217] [cursor=pointer]: ×
        - button "客户管理 标签操作" [ref=e218] [cursor=pointer]: ⋮
      - generic [ref=e219]:
        - tab "客户管理 · 新建 2未保存" [selected] [ref=e220] [cursor=pointer]: 客户管理 · 新建 2 ●
        - button "关闭 客户管理 · 新建 2" [ref=e221] [cursor=pointer]: ×
        - button "客户管理 · 新建 2 标签操作" [active] [ref=e222] [cursor=pointer]: ⋮
      - generic [ref=e223]:
        - tab "客户管理 · 新建 1未保存" [ref=e224] [cursor=pointer]: 客户管理 · 新建 1 ●
        - button "关闭 客户管理 · 新建 1" [ref=e225] [cursor=pointer]: ×
        - button "客户管理 · 新建 1 标签操作" [ref=e226] [cursor=pointer]: ⋮
    - tabpanel "客户管理 · 新建 2" [ref=e228]:
      - generic [ref=e229]:
        - generic [ref=e230]:
          - paragraph [ref=e232]: 维护客户资料和负责人。客户阶段会随报价和订单自动更新。
          - button "新建客户" [ref=e233] [cursor=pointer]
        - region "页面小计" [ref=e236]:
          - article [ref=e237]:
            - generic [ref=e238]: 客户总数
            - strong [ref=e239]: "2"
            - generic [ref=e240]: 全部客户档案
          - article [ref=e244]:
            - generic [ref=e245]: 正式客户
            - strong [ref=e246]: "0"
            - generic [ref=e247]: 已有正式订单
          - article [ref=e251]:
            - generic [ref=e252]: 待开发
            - strong [ref=e253]: "2"
            - generic [ref=e254]: 尚未成交
          - article [ref=e258]:
            - generic [ref=e259]: 累计销售额
            - strong [ref=e260]: ¥ 0.00
            - generic [ref=e261]: 当前列表累计
        - link "新品提醒" [ref=e265] [cursor=pointer]:
          - /url: /new-product-reminders?tag=%E6%96%B0%E5%93%81%E6%8F%90%E9%86%92
        - generic "客户筛选" [ref=e266]:
          - generic [ref=e267]:
            - text: 搜索
            - textbox "搜索客户" [ref=e268]:
              - /placeholder: 名称、编号、国家/地区或负责人
          - generic [ref=e269]:
            - text: 负责人
            - combobox "按负责人筛选客户" [ref=e270]:
              - option "全部负责人" [selected]
          - generic [ref=e271]:
            - text: 国家/地区
            - combobox "按国家/地区筛选客户" [ref=e272]:
              - option "全部国家/地区" [selected]
              - option "United Kingdom / GB"
              - option "United States / US"
          - generic [ref=e273]:
            - text: 状态
            - combobox "按客户状态筛选" [ref=e274]:
              - option "全部状态" [selected]
              - option "线索"
              - option "已联系"
              - option "商机"
              - option "正式客户"
              - option "返单客户"
          - button "重置" [ref=e275] [cursor=pointer]
          - button "刷新" [ref=e276] [cursor=pointer]
        - table [ref=e279]:
          - rowgroup [ref=e280]:
            - row [ref=e281]:
              - columnheader "客户名称" [ref=e282]
              - columnheader "客户编号" [ref=e283]
              - columnheader "状态" [ref=e284]
              - columnheader "国家/地区" [ref=e285]
              - columnheader "业务区域" [ref=e286]
              - columnheader "负责人" [ref=e287]
              - columnheader "下次跟进" [ref=e288]
              - columnheader "订单数" [ref=e289]
              - columnheader "累计销售额" [ref=e290]
              - columnheader "操作" [ref=e291]
          - rowgroup [ref=e292]:
            - row [ref=e293] [cursor=pointer]:
              - cell "Workspace Beta" [ref=e294]
              - cell "WS-C002" [ref=e296]
              - cell "线索" [ref=e297]
              - cell "United Kingdom / GB" [ref=e299]
              - cell "—" [ref=e300]
              - cell "—" [ref=e301]
              - cell "—" [ref=e302]
              - cell "0" [ref=e303]
              - cell "¥ 0.00" [ref=e304]
              - cell [ref=e305]:
                - generic [ref=e306]:
                  - link "新品提醒" [ref=e307]:
                    - /url: /new-product-reminders?customer=2
                  - button "查看详情" [ref=e308]
                  - button "编辑" [ref=e311]
                  - button "删除" [ref=e315]
            - row [ref=e319] [cursor=pointer]:
              - cell "Workspace Alpha" [ref=e320]
              - cell "WS-C001" [ref=e322]
              - cell "线索" [ref=e323]
              - cell "United States / US" [ref=e325]
              - cell "—" [ref=e326]
              - cell "—" [ref=e327]
              - cell "—" [ref=e328]
              - cell "0" [ref=e329]
              - cell "¥ 0.00" [ref=e330]
              - cell [ref=e331]:
                - generic [ref=e332]:
                  - link "新品提醒" [ref=e333]:
                    - /url: /new-product-reminders?customer=1
                  - button "查看详情" [ref=e334]
                  - button "编辑" [ref=e337]
                  - button "删除" [ref=e341]
        - generic [ref=e346]:
          - generic [ref=e347]:
            - heading "新建客户" [level=3] [ref=e348]
            - button [ref=e349] [cursor=pointer]
          - generic [ref=e353]:
            - generic [ref=e354]:
              - generic [ref=e355]:
                - generic [ref=e356]:
                  - text: 客户名称
                  - emphasis [ref=e357]: "*"
                - textbox "输入客户名称" [ref=e358]: Synthetic Draft B
              - generic [ref=e359]:
                - generic [ref=e360]:
                  - text: 客户编号
                  - emphasis [ref=e361]: "*"
                - textbox [ref=e362]: "202611100000"
              - generic [ref=e363]:
                - generic [ref=e364]: 国家/地区
                - textbox "国家/地区" [ref=e367]:
                  - /placeholder: 搜索名称、中文或代码后选择
                - paragraph [ref=e368]: 请选择标准英文名称 / 两位代码；历史文本需人工确认。
              - generic [ref=e369]:
                - generic [ref=e370]: 业务区域
                - textbox [ref=e371]
              - generic [ref=e372]:
                - generic [ref=e373]: 负责人
                - combobox [ref=e374]:
                  - option "请选择" [selected]
              - generic [ref=e375]:
                - generic [ref=e376]: 客户来源
                - textbox "选择或输入" [ref=e379]
            - generic [ref=e380]:
              - generic [ref=e381]:
                - generic [ref=e382]:
                  - text: 联系人信息
                  - paragraph [ref=e383]: 至少登记一位联系人，可指定默认联系人。
                - generic [ref=e384]: 1 位
              - generic [ref=e385]:
                - generic [ref=e386]:
                  - strong [ref=e387]: 联系人 1
                  - generic [ref=e389] [cursor=pointer]:
                    - checkbox "默认联系人" [checked]
                    - generic [ref=e392]: 默认联系人
                - generic [ref=e393]:
                  - generic [ref=e394]:
                    - generic [ref=e395]:
                      - text: 姓名
                      - emphasis [ref=e396]: "*"
                    - textbox [ref=e397]
                  - generic [ref=e398]:
                    - generic [ref=e399]: 职位
                    - textbox [ref=e400]
                  - generic [ref=e401]:
                    - generic [ref=e402]: 邮箱
                    - textbox [ref=e403]
                  - generic [ref=e404]:
                    - generic [ref=e405]: 电话
                    - textbox [ref=e406]
                  - generic [ref=e407]:
                    - generic [ref=e408]: WhatsApp
                    - textbox [ref=e409]
                  - generic [ref=e410]:
                    - generic [ref=e411]: 备注
                    - textbox [ref=e412]
              - button "新增联系人" [ref=e413] [cursor=pointer]
            - heading "补充信息" [level=4] [ref=e417]
            - generic [ref=e418]:
              - generic [ref=e419]:
                - generic [ref=e420]: 网站
                - textbox [ref=e421]
              - generic [ref=e422]:
                - generic [ref=e423]: 地址
                - textbox [ref=e424]
              - generic [ref=e425]:
                - generic [ref=e426]: 备注
                - textbox [ref=e427]
          - generic [ref=e428]:
            - button "取消" [ref=e429] [cursor=pointer]
            - button "保存客户" [ref=e430] [cursor=pointer]
```

# Test source

```ts
  1  | import {test,expect} from '@playwright/test'
  2  | import {mkdir,writeFile} from 'node:fs/promises'
  3  | import {createHash} from 'node:crypto'
  4  | import path from 'node:path'
  5  | test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
  6  | test('reorder dirty customer tabs preserves drafts',async({page,browser})=>{
  7  |  test.setTimeout(90000);const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true});const active=()=>page.locator('.workspace-pane[aria-hidden="false"]'),name=()=>active().locator('.customer-editor .field').filter({hasText:'客户名称'}).locator('input').first()
  8  |  async function capture(id,steps){const state=await page.evaluate(()=>({route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,tabOrder:[...document.querySelectorAll('.workspace-tab [role=tab]')].map(e=>e.innerText)}));const n=id+'.png',b=await page.screenshot({path:path.join(root,'originals',n)});entries.push({evidence_id:id,surface_id:'G003',expanded_case_id:id,source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role:'authenticated codex test superuser',data:'isolated workspace fixture; two unsaved synthetic customer drafts',steps,simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${n}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)},review:'NOT_REVIEWED'});await writeFile(path.join(root,'tab-move-manifest.json'),JSON.stringify(entries,null,2))}
> 9  |  await page.goto('/customers',{waitUntil:'networkidle'});await active().getByRole('button',{name:/新建客户/}).click();await name().fill('Synthetic Draft A');await page.getByRole('tab',{name:'客户管理',exact:true}).click();await active().getByRole('button',{name:/新建客户/}).click();await name().fill('Synthetic Draft B');await capture('TAB-MOVE-BEFORE-B-1366',['create two dirty customer drafts']);await page.getByRole('button',{name:/客户管理.*新建 2.*标签操作/}).click();await page.getByRole('button',{name:'向左移动',exact:true}).click();await expect(page.getByRole('tab').nth(1)).toHaveText(/新建 2/);await expect(name()).toHaveValue('Synthetic Draft B');await capture('TAB-MOVE-LEFT-B-1366',['open second tab actions','move left','verify B remains']);await page.getByRole('button',{name:/客户管理.*新建 2.*标签操作/}).click();await page.getByRole('button',{name:'向右移动',exact:true}).click();await expect(page.getByRole('tab').nth(2)).toHaveText(/新建 2/);await page.getByRole('tab',{name:/新建 1/}).click();await expect(name()).toHaveValue('Synthetic Draft A');await capture('TAB-MOVE-RIGHT-B-1366',['move second tab right','switch to first','verify A remains'])
     |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   ^ Error: locator.click: Test timeout of 90000ms exceeded.
  10 | })
  11 | 
```