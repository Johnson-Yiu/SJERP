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
    - locator resolved to <button type="button" class="btn btn-secondary" data-testid="dialog-cancel">继续编辑</button>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <article class="chosen" data-v-b3925ba4="">…</article> from <div data-v-b3925ba4="" class="binding-backdrop">…</div> subtree intercepts pointer events
    - retrying click action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <article class="chosen" data-v-b3925ba4="">…</article> from <div data-v-b3925ba4="" class="binding-backdrop">…</div> subtree intercepts pointer events
    - retrying click action
      - waiting 100ms
    112 × waiting for element to be visible, enabled and stable
        - element is visible, enabled and stable
        - scrolling into view if needed
        - done scrolling
        - <article class="chosen" data-v-b3925ba4="">…</article> from <div data-v-b3925ba4="" class="binding-backdrop">…</div> subtree intercepts pointer events
      - retrying click action
        - waiting 500ms

```

# Page snapshot

```yaml
- generic [ref=f12e1]:
  - generic [ref=f12e3]:
    - complementary [ref=f12e4]:
      - generic [ref=f12e5]:
        - generic [ref=f12e6]: S
        - generic [ref=f12e7]:
          - strong [ref=f12e8]: 森爵照明管理系统
          - text: 客户 · 销售 · 产品
      - navigation [ref=f12e9]:
        - generic [ref=f12e10]: 经营
        - link "经营概览" [ref=f12e11] [cursor=pointer]:
          - /url: /
        - link "报表中心" [ref=f12e18] [cursor=pointer]:
          - /url: /reports
        - link "历史订单分析" [ref=f12e25] [cursor=pointer]:
          - /url: /historical-orders
        - generic [ref=f12e31]: 客户
        - link "客户管理" [ref=f12e32] [cursor=pointer]:
          - /url: /customers
        - link "联系人" [ref=f12e39] [cursor=pointer]:
          - /url: /contacts
        - link "跟进记录" [ref=f12e45] [cursor=pointer]:
          - /url: /follow-ups
        - generic [ref=f12e49]: 销售
        - link "报价管理" [ref=f12e50] [cursor=pointer]:
          - /url: /quotes
        - link "订单管理" [ref=f12e55] [cursor=pointer]:
          - /url: /orders
        - generic [ref=f12e61]: 采购与库存
        - link "供应商管理" [ref=f12e62] [cursor=pointer]:
          - /url: /suppliers
        - link "采购管理" [ref=f12e69] [cursor=pointer]:
          - /url: /purchase-orders
        - link "库存" [ref=f12e75] [cursor=pointer]:
          - /url: /inventory
        - link "库存流水" [ref=f12e80] [cursor=pointer]:
          - /url: /inventory-movements
        - generic [ref=f12e85]: 产品资料
        - link "产品管理" [ref=f12e86] [cursor=pointer]:
          - /url: /products
        - link "SKU 管理" [ref=f12e92] [cursor=pointer]:
          - /url: /skus
        - link "产品分类" [ref=f12e104] [cursor=pointer]:
          - /url: /categories
        - link "产品参数" [ref=f12e110] [cursor=pointer]:
          - /url: /product-parameters
        - link "包装管理" [ref=f12e113] [cursor=pointer]:
          - /url: /sku-packaging
        - link "交易单位" [ref=f12e119] [cursor=pointer]:
          - /url: /sku-trade-units
        - link "产品证书" [ref=f12e131] [cursor=pointer]:
          - /url: /product-certificates
        - link "HS 编码维护" [ref=f12e136] [cursor=pointer]:
          - /url: /hs-codes
        - generic [ref=f12e139]: 财务与工具
        - link "财务概览" [ref=f12e140] [cursor=pointer]:
          - /url: /finance
        - link "应收计划" [ref=f12e146] [cursor=pointer]:
          - /url: /receivables
        - link "应付计划" [ref=f12e152] [cursor=pointer]:
          - /url: /payables
        - link "财务流水" [ref=f12e158] [cursor=pointer]:
          - /url: /transactions
        - link "银行资金记录" [ref=f12e164] [cursor=pointer]:
          - /url: /rmb-cash-events
        - link "账户余额与对账" [ref=f12e170] [cursor=pointer]:
          - /url: /finance-ledger
        - link "数据导入" [ref=f12e176] [cursor=pointer]:
          - /url: /import
        - link "历史资料预检" [ref=f12e181] [cursor=pointer]:
          - /url: /history-preflight
        - link "历史资料承接" [ref=f12e187] [cursor=pointer]:
          - /url: /history-takeover
        - generic [ref=f12e193]: 组织与系统
        - link "组织与权限" [ref=f12e194] [cursor=pointer]:
          - /url: /organization
      - generic [ref=f12e199]:
        - generic [ref=f12e200]: C
        - generic [ref=f12e202]:
          - strong [ref=f12e203]: 当前账号：codex
          - generic [ref=f12e204]: 超级管理员 · 全部功能与数据权限
        - button "退出登录" [ref=f12e205] [cursor=pointer]
    - main [ref=f12e206]:
      - generic [ref=f12e207]:
        - generic [ref=f12e208]:
          - text: 产品资料
          - heading "产品管理" [level=1] [ref=f12e209]
        - generic [ref=f12e210]:
          - generic [ref=f12e211]: 11月14日周六
          - generic "codex" [ref=f12e212]: C
      - tablist "业务工作区" [ref=f12e214]:
        - generic [ref=f12e215]:
          - tab "C 合成轨道灯产品未保存" [selected] [ref=f12e216] [cursor=pointer]: C 合成轨道灯产品 ●
          - button "关闭 C 合成轨道灯产品" [ref=f12e217] [cursor=pointer]: ×
          - button "C 合成轨道灯产品 标签操作" [ref=f12e218] [cursor=pointer]: ⋮
      - tabpanel "C 合成轨道灯产品" [ref=f12e220]:
        - generic [ref=f12e221]:
          - generic [ref=f12e222]:
            - generic [ref=f12e223]:
              - heading "产品管理" [level=2] [ref=f12e224]
              - paragraph [ref=f12e225]: 维护产品名称、分类和销售状态；SKU 编码请在“SKU 管理”中维护。
            - button "新建产品" [ref=f12e226] [cursor=pointer]
          - region "页面小计" [ref=f12e229]:
            - article [ref=f12e230]:
              - generic [ref=f12e231]: 产品总数
              - strong [ref=f12e232]: "1"
              - generic [ref=f12e233]: 当前筛选范围
            - article [ref=f12e237]:
              - generic [ref=f12e238]: 在售产品
              - strong [ref=f12e239]: "1"
              - generic [ref=f12e240]: 可继续添加 SKU
            - article [ref=f12e244]:
              - generic [ref=f12e245]: 开发中
              - strong [ref=f12e246]: "0"
              - generic [ref=f12e247]: 尚未正式销售
            - article [ref=f12e251]:
              - generic [ref=f12e252]: SKU 总数
              - strong [ref=f12e253]: "2"
              - generic [ref=f12e254]: 产品下的 SKU
          - generic [ref=f12e258]:
            - textbox "搜索产品" [ref=f12e263]:
              - /placeholder: 搜索产品编号或名称
            - combobox "产品分类筛选" [ref=f12e266] [cursor=pointer]:
              - option "全部分类" [selected]
            - combobox "产品排序" [ref=f12e267]:
              - option "产品编号顺序" [selected]
              - option "产品名称顺序"
              - option "SKU 数量最多"
            - button "查询" [ref=f12e268] [cursor=pointer]
            - button "重置" [ref=f12e269] [cursor=pointer]
            - button "刷新" [ref=f12e270] [cursor=pointer]
          - table [ref=f12e273]:
            - rowgroup [ref=f12e274]:
              - row [ref=f12e275]:
                - columnheader "产品编号" [ref=f12e276]
                - columnheader "产品名称" [ref=f12e277]
                - columnheader "销售型号前缀" [ref=f12e278]
                - columnheader "主分类" [ref=f12e279]
                - columnheader "状态" [ref=f12e280]
                - columnheader "SKU" [ref=f12e281]
                - columnheader "参数" [ref=f12e282]
                - columnheader "证书" [ref=f12e283]
                - columnheader [ref=f12e284]
            - rowgroup [ref=f12e285]:
              - row [ref=f12e286] [cursor=pointer]:
                - cell "C-P001" [ref=f12e287]
                - cell "C 合成轨道灯产品 未填写英文名称" [ref=f12e288]:
                  - strong [ref=f12e289]: C 合成轨道灯产品
                  - generic [ref=f12e290]: 未填写英文名称
                - cell "—" [ref=f12e291]
                - cell "未分类" [ref=f12e292]
                - cell "在售" [ref=f12e293]
                - cell "2" [ref=f12e295]
                - cell "0" [ref=f12e296]
                - cell "0" [ref=f12e297]
                - cell [ref=f12e298]:
                  - generic [ref=f12e299]:
                    - button "编辑产品" [ref=f12e300]
                    - button "删除产品" [ref=f12e304]
          - article "关联详情" [ref=f12e309]:
            - generic [ref=f12e310]:
              - generic [ref=f12e311]:
                - generic [ref=f12e312]: 产品管理 / 产品详情
                - generic [ref=f12e314]:
                  - link "查看经营分析" [ref=f12e315] [cursor=pointer]:
                    - /url: /reports?source=sales&group_by=product&filter_product=1&title=%E4%BA%A7%E5%93%81%E9%94%80%E5%94%AE%E5%88%86%E6%9E%90&returnTo=/products?detail=1%26tab=skus
                  - button "编辑主档" [ref=f12e320] [cursor=pointer]
                  - button "关闭详情" [ref=f12e324] [cursor=pointer]:
                    - generic [ref=f12e328]: 关闭
              - generic [ref=f12e329]:
                - generic [ref=f12e330]:
                  - text: C-P001 · 未分类
                  - heading "C 合成轨道灯产品" [level=2] [ref=f12e331]
                - generic [ref=f12e332]: 在售
              - generic [ref=f12e333]:
                - generic [ref=f12e334]:
                  - generic [ref=f12e335]: SKU
                  - strong [ref=f12e336]: "2"
                - generic [ref=f12e337]:
                  - generic [ref=f12e338]: 供应商
                  - strong [ref=f12e339]: "0"
                - generic [ref=f12e340]:
                  - generic [ref=f12e341]: 当前库存
                  - strong [ref=f12e342]: "0"
                - generic [ref=f12e343]:
                  - generic [ref=f12e344]: 参数
                  - strong [ref=f12e345]: "0"
            - generic [ref=f12e346]:
              - navigation "产品详情导航" [ref=f12e347]:
                - button "总览" [ref=f12e348] [cursor=pointer]
                - button "SKU 管理2" [ref=f12e349] [cursor=pointer]
                - button "供应能力规则0" [ref=f12e350] [cursor=pointer]
                - button "订单记录0" [ref=f12e351] [cursor=pointer]
                - button "销售统计" [ref=f12e352] [cursor=pointer]
                - button "出入库流水0" [ref=f12e353] [cursor=pointer]
                - button "产品参数0" [ref=f12e354] [cursor=pointer]
                - button "证书档案0" [ref=f12e355] [cursor=pointer]
                - button "销售规则" [ref=f12e356] [cursor=pointer]
                - button "操作日志" [ref=f12e357] [cursor=pointer]
              - main [ref=f12e358]:
                - generic [ref=f12e359]:
                  - generic [ref=f12e360]:
                    - heading "SKU 管理与批量维护" [level=3] [ref=f12e361]
                    - paragraph [ref=f12e372]: 新增组合在上方填写；下方统一维护已有 SKU、候选供应商及启停状态。
                  - button "新增 SKU 组合" [ref=f12e373] [cursor=pointer]
                - region "SKU 参数与供应商管理" [ref=f12e375]:
                  - generic [ref=f12e377]:
                    - heading "SKU 档案与供应商分配" [level=3] [ref=f12e378]
                    - paragraph [ref=f12e379]: 一份 SKU 清单管理规格与供货候选；实际采购供应商在销售订单或采购单中确认。
                  - status [ref=f12e380]: 已启用 2 项 SKU。
                  - generic [ref=f12e381]:
                    - generic [ref=f12e382]:
                      - generic [ref=f12e383]:
                        - heading "已有 SKU · 2 条" [level=4] [ref=f12e384]
                        - paragraph [ref=f12e385]: 筛选参数并勾选 SKU，可批量绑定候选供应商；同一参数多选为任一匹配，不同参数同时满足。
                      - button "清空筛选" [ref=f12e387] [cursor=pointer]
                    - generic [ref=f12e388]:
                      - generic [ref=f12e389]:
                        - generic [ref=f12e390]: 启用 SKU 总数
                        - strong [ref=f12e391]: "2"
                      - generic [ref=f12e392]:
                        - generic [ref=f12e393]: 已有候选供应商
                        - strong [ref=f12e394]: "2"
                      - generic [ref=f12e395]:
                        - generic [ref=f12e396]: 覆盖率
                        - strong [ref=f12e397]: 100%
                    - generic [ref=f12e398]:
                      - textbox "搜索 SKU 编码、中文名称或 Sales Model" [ref=f12e399]
                      - combobox [ref=f12e400]:
                        - option "全部来源" [selected]
                        - option "按供货范围匹配"
                        - option "曾采购过"
                        - option "手动添加"
                        - option "已登记供货信息"
                    - generic [ref=f12e402]:
                      - generic [ref=f12e403]:
                        - checkbox "显示已停用 SKU" [checked] [ref=f12e404]
                        - text: 显示已停用 SKU
                      - generic [ref=f12e405]: 已选 1 项（仅当前筛选结果）
                      - button "批量绑定供应商" [ref=f12e406] [cursor=pointer]
                      - button "停用 1 项" [ref=f12e407] [cursor=pointer]
                      - button "取消选择" [ref=f12e408] [cursor=pointer]
                    - table [ref=f12e410]:
                      - rowgroup [ref=f12e411]:
                        - row [ref=f12e412]:
                          - columnheader [ref=f12e413]:
                            - checkbox "选择当前筛选的全部 SKU" [ref=f12e414]
                          - columnheader "SKU Code" [ref=f12e415]
                          - columnheader "中文名称 / Sales Model" [ref=f12e416]
                          - columnheader "规格" [ref=f12e417]
                          - columnheader "库存 / 单位" [ref=f12e418]
                          - columnheader "成本 / 售价" [ref=f12e419]
                          - columnheader "可选供应商" [ref=f12e420]
                          - columnheader "最近采购" [ref=f12e421]
                          - columnheader "状态" [ref=f12e422]
                          - columnheader "操作" [ref=f12e423]
                      - rowgroup [ref=f12e424]:
                        - row [ref=f12e425]:
                          - cell [ref=f12e426]:
                            - checkbox "选择 C-SKU-1" [checked] [ref=f12e427]
                          - cell [ref=f12e428]:
                            - button "C-SKU-1" [ref=f12e429] [cursor=pointer]
                          - cell "C 合成轨道灯产品 未设置 Sales Model" [ref=f12e430]:
                            - strong [ref=f12e431]: C 合成轨道灯产品
                            - generic [ref=f12e432]: 未设置 Sales Model
                          - cell "—" [ref=f12e433]
                          - cell "0.00 pcs" [ref=f12e434]:
                            - text: "0.00"
                            - generic [ref=f12e435]: pcs
                          - cell "0.0000 / 0.0000 USD" [ref=f12e436]:
                            - text: 0.0000 / 0.0000
                            - generic [ref=f12e437]: USD
                          - cell [ref=f12e438]:
                            - strong [ref=f12e439]: C 合成照明供应商
                          - cell "尚未采购" [ref=f12e440]
                          - cell "启用" [ref=f12e441]
                          - cell [ref=f12e442]:
                            - button "查看 SKU" [ref=f12e443] [cursor=pointer]
                        - row [ref=f12e444]:
                          - cell [ref=f12e445]:
                            - checkbox "选择 C-SKU-2" [ref=f12e446]
                          - cell [ref=f12e447]:
                            - button "C-SKU-2" [ref=f12e448] [cursor=pointer]
                          - cell "C 合成轨道灯产品 · C-SKU-2 未设置 Sales Model" [ref=f12e449]:
                            - strong [ref=f12e450]: C 合成轨道灯产品 · C-SKU-2
                            - generic [ref=f12e451]: 未设置 Sales Model
                          - cell "—" [ref=f12e452]
                          - cell "0.00 pcs" [ref=f12e453]:
                            - text: "0.00"
                            - generic [ref=f12e454]: pcs
                          - cell "0.0000 / 0.0000 USD" [ref=f12e455]:
                            - text: 0.0000 / 0.0000
                            - generic [ref=f12e456]: USD
                          - cell [ref=f12e457]:
                            - strong [ref=f12e458]: C 合成照明供应商
                          - cell "尚未采购" [ref=f12e459]
                          - cell "启用" [ref=f12e460]
                          - cell [ref=f12e461]:
                            - button "查看 SKU" [ref=f12e462] [cursor=pointer]
                  - group [ref=f12e463]:
                    - generic "参数变更与历史方案 调整已有 SKU 时，先分析影响再确认发布" [ref=f12e464] [cursor=pointer]
  - dialog [ref=f12e466]:
    - banner [ref=f12e467]:
      - heading "未保存修改" [level=2] [ref=f12e468]
    - paragraph [ref=f12e470]: 当前修改尚未保存，离开后将丢失。是否继续？
    - contentinfo [ref=f12e471]:
      - button "继续编辑" [active] [ref=f12e472] [cursor=pointer]
      - button "放弃修改" [ref=f12e473] [cursor=pointer]
  - dialog "批量绑定供应商" [ref=f12e475]:
    - banner [ref=f12e476]:
      - generic [ref=f12e477]:
        - heading "批量绑定供应商" [level=3] [ref=f12e478]
        - paragraph [ref=f12e479]: 为 1 个 SKU 添加候选供应商。采购时仍需选择实际供应来源。
      - button "关闭" [ref=f12e480] [cursor=pointer]
    - generic [ref=f12e481]:
      - paragraph [ref=f12e482]: 优先展示分类匹配的供应商，也可打开开关从全部供应商中选择。切换筛选不会清除已选供应商。
      - generic [ref=f12e483]:
        - textbox "搜索供应商" [ref=f12e484]:
          - /placeholder: 搜索名称、代码或可供分类
        - generic [ref=f12e485]:
          - switch "显示全部供应商" [checked] [ref=f12e486]
          - text: 显示全部供应商
      - table [ref=f12e488]:
        - rowgroup [ref=f12e489]:
          - row [ref=f12e490]:
            - columnheader [ref=f12e491]:
              - checkbox "全选当前筛选供应商" [checked] [ref=f12e492]
            - columnheader "供应商 / 代码" [ref=f12e493]
            - columnheader "可供分类" [ref=f12e494]
            - columnheader "匹配情况" [ref=f12e495]
        - rowgroup [ref=f12e496]:
          - row [ref=f12e497]:
            - cell [ref=f12e498]:
              - checkbox "选择C 合成照明供应商" [checked] [ref=f12e499]
            - cell "C 合成照明供应商 CC" [ref=f12e500]:
              - strong [ref=f12e501]: C 合成照明供应商
              - generic [ref=f12e502]: CC
            - cell "未设置分类" [ref=f12e503]
            - cell "其他供应商" [ref=f12e504]
      - generic [ref=f12e505]:
        - generic [ref=f12e506]: 当前显示 1 家 · 已选 1 家
        - button "清空已选" [ref=f12e507] [cursor=pointer]
      - heading "已选供应商 · 供货差异" [level=4] [ref=f12e508]
      - article [ref=f12e509]:
        - generic [ref=f12e510]:
          - strong [ref=f12e511]: C 合成照明供应商
          - generic [ref=f12e512]: CC
          - button "移除" [ref=f12e513] [cursor=pointer]
        - generic [ref=f12e514]:
          - generic [ref=f12e515]:
            - text: 推荐优先级
            - combobox "推荐优先级" [ref=f12e516]:
              - option "高"
              - option "中" [selected]
              - option "低"
          - generic [ref=f12e517]:
            - text: 质量等级
            - combobox "质量等级" [ref=f12e518]:
              - option "A+"
              - option "A"
              - option "B" [selected]
              - option "C"
          - generic [ref=f12e519]:
            - text: 供货稳定度
            - combobox "供货稳定度" [ref=f12e520]:
              - option "高"
              - option "中" [selected]
              - option "低"
          - generic [ref=f12e521]:
            - text: 交货期
            - combobox "交货期" [ref=f12e522]:
              - option "快"
              - option "标准" [selected]
              - option "慢"
          - generic [ref=f12e523]:
            - text: 其他备注
            - textbox "其他备注" [ref=f12e524]
    - contentinfo [ref=f12e525]:
      - generic [ref=f12e526]: 已选 1 家供应商
      - button "保存候选供应商" [ref=f12e527] [cursor=pointer]
```

# Test source

```ts
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
  138 |   await expect(rows.locator('input[type=checkbox]')).toBeChecked()
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
> 157 |   await shot('batch-success-real-readback')
      |                                           ^ TimeoutError: locator.click: Timeout 60000ms exceeded.
  158 |   await rows.first().locator('input[type=checkbox]').check()
  159 |   await page.getByRole('button',{name:'批量绑定供应商',exact:true}).click()
  160 |   const binding=page.getByRole('dialog',{name:'批量绑定供应商',exact:true})
  161 |   await binding.getByRole('switch').check()
  162 |   await binding.getByLabel('选择C 合成照明供应商',{exact:true}).check()
  163 |   await binding.getByRole('button',{name:'关闭',exact:true}).click()
  164 |   await page.getByTestId('dialog-cancel').click()
  165 |   await expect(binding.getByLabel('选择C 合成照明供应商',{exact:true})).toBeChecked()
  166 |   await page.getByRole('button',{name:'关闭 C 合成轨道灯产品',exact:true}).click()
  167 |   await page.getByTestId('dialog-confirm').click()
  168 |   await expect(binding).toHaveCount(0)
  169 |   await expect(page.getByTestId('dialog-confirm')).toHaveCount(0)
  170 |   await shot('binding-single-confirm-closed')
  171 | })
  172 | 
  173 | test.afterEach(async ({page}, info)=> { if(info.status!==info.expectedStatus) await page.screenshot({path:info.outputPath('failure.png')}) })
  174 | 
```