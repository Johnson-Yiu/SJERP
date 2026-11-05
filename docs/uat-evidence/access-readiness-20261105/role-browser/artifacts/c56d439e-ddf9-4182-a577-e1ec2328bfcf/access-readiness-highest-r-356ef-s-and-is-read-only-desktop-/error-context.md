# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: access-readiness-highest-role-real.spec.js >> highest role reflects API effective permissions and is read-only (desktop)
- Location: browser-tests\access-readiness-highest-role-real.spec.js:7:3

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: expect(locator).toBeDisabled() failed

Locator: getByRole('region', { name: '角色权限矩阵，可横向及纵向滚动' }).locator('tbody input[type=checkbox]').nth(107)
Expected: disabled
Error: Test timeout of 30000ms exceeded.

Call log:
  - Expect "toBeDisabled" getByRole('region', { name: '角色权限矩阵，可横向及纵向滚动' }).locator('tbody input[type=checkbox]').nth(107) with timeout 5000ms
  - waiting for getByRole('region', { name: '角色权限矩阵，可横向及纵向滚动' }).locator('tbody input[type=checkbox]').nth(107)
  - Test timeout of 30000ms exceeded.

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
      - generic [ref=e201]:
        - text: Organization & access
        - heading "组织与权限" [level=1] [ref=e202]
      - generic [ref=e203]:
        - generic [ref=e204]: 11月5日周四
        - generic "Johnson" [ref=e205]: J
    - generic [ref=e207]:
      - generic [ref=e208]:
        - generic [ref=e209]:
          - heading "组织与权限" [level=2] [ref=e210]
          - paragraph [ref=e211]: 查看组织架构，按角色维护功能权限。
        - button "刷新" [ref=e212] [cursor=pointer]
      - generic [ref=e217]:
        - strong [ref=e218]: 开发身份：全部功能与数据权限
        - paragraph [ref=e219]: 此页只维护已有角色模板，不改变当前访问模式。正式人员权限与数据范围仍需单独配置和验收。
      - generic [ref=e220]:
        - generic [ref=e221]:
          - generic [ref=e222]: 部门
          - strong [ref=e223]: "5"
        - generic [ref=e224]:
          - generic [ref=e225]: 岗位
          - strong [ref=e226]: "13"
        - generic [ref=e227]:
          - generic [ref=e228]: 角色模板
          - strong [ref=e229]: "15"
        - generic [ref=e230]:
          - generic [ref=e231]: 成员账号
          - strong [ref=e232]: "0"
      - group [ref=e233]:
        - generic "组织架构 部门与岗位" [ref=e234] [cursor=pointer]
      - generic [ref=e235]:
        - complementary [ref=e236]:
          - generic [ref=e238]:
            - heading "角色模板" [level=3] [ref=e239]
            - paragraph [ref=e240]: 共 15 个角色
          - textbox "搜索角色" [ref=e245]:
            - /placeholder: 搜索角色名称或代码
          - button "超级管理员 全部数据" [pressed] [ref=e246] [cursor=pointer]:
            - generic [ref=e247]:
              - strong [ref=e248]: 超级管理员
              - generic [ref=e249]: 全部数据
          - button "管理员 全部数据" [ref=e252] [cursor=pointer]:
            - generic [ref=e253]:
              - strong [ref=e254]: 管理员
              - generic [ref=e255]: 全部数据
          - button "销售主管 本部门及下级" [ref=e258] [cursor=pointer]:
            - generic [ref=e259]:
              - strong [ref=e260]: 销售主管
              - generic [ref=e261]: 本部门及下级
          - button "业务员 仅本人负责" [ref=e264] [cursor=pointer]:
            - generic [ref=e265]:
              - strong [ref=e266]: 业务员
              - generic [ref=e267]: 仅本人负责
          - button "跟单 仅本人负责" [ref=e270] [cursor=pointer]:
            - generic [ref=e271]:
              - strong [ref=e272]: 跟单
              - generic [ref=e273]: 仅本人负责
          - button "运营主管 本部门及下级" [ref=e276] [cursor=pointer]:
            - generic [ref=e277]:
              - strong [ref=e278]: 运营主管
              - generic [ref=e279]: 本部门及下级
          - button "网站运营 仅本人负责" [ref=e282] [cursor=pointer]:
            - generic [ref=e283]:
              - strong [ref=e284]: 网站运营
              - generic [ref=e285]: 仅本人负责
          - button "平台运营 仅本人负责" [ref=e288] [cursor=pointer]:
            - generic [ref=e289]:
              - strong [ref=e290]: 平台运营
              - generic [ref=e291]: 仅本人负责
          - button "仓库主管 本部门及下级" [ref=e294] [cursor=pointer]:
            - generic [ref=e295]:
              - strong [ref=e296]: 仓库主管
              - generic [ref=e297]: 本部门及下级
          - button "仓库员工 本部门" [ref=e300] [cursor=pointer]:
            - generic [ref=e301]:
              - strong [ref=e302]: 仓库员工
              - generic [ref=e303]: 本部门
          - button "财务主管 本部门及下级" [ref=e306] [cursor=pointer]:
            - generic [ref=e307]:
              - strong [ref=e308]: 财务主管
              - generic [ref=e309]: 本部门及下级
          - button "财务员工 本部门" [ref=e312] [cursor=pointer]:
            - generic [ref=e313]:
              - strong [ref=e314]: 财务员工
              - generic [ref=e315]: 本部门
          - button "人事行政主管 本部门及下级" [ref=e318] [cursor=pointer]:
            - generic [ref=e319]:
              - strong [ref=e320]: 人事行政主管
              - generic [ref=e321]: 本部门及下级
          - button "人事 本部门" [ref=e324] [cursor=pointer]:
            - generic [ref=e325]:
              - strong [ref=e326]: 人事
              - generic [ref=e327]: 本部门
          - button "行政 本部门" [ref=e330] [cursor=pointer]:
            - generic [ref=e331]:
              - strong [ref=e332]: 行政
              - generic [ref=e333]: 本部门
        - generic [ref=e336]:
          - generic [ref=e337]:
            - generic [ref=e338]:
              - text: superadmin
              - heading "超级管理员" [level=3] [ref=e339]
              - paragraph [ref=e340]: 系统最高权限，可管理所有业务、成员和权限。
            - generic [ref=e341]:
              - generic [ref=e342]: 默认数据范围（只读）
              - strong [ref=e343]: 全部数据
              - paragraph [ref=e344]: 数据范围当前首先用于客户/CRM/销售记录。产品、SKU、库存等共享主数据不按客户负责人切分。
          - generic [ref=e345]:
            - generic [ref=e346]:
              - text: 查找功能模块
              - textbox "查找功能模块" [ref=e347]:
                - /placeholder: 输入模块名称或代码
            - generic [ref=e348]: 24 / 24 个模块
            - generic [ref=e349]: 当前没有未保存修改
          - paragraph [ref=e350]: 勾选任一操作会同时勾选“查看”；取消“查看”会清除该模块的其他操作权限。筛选只影响显示，保存仍包含全部模块。
          - paragraph [ref=e351]: 包含全部ERP业务权限，不受普通勾选项限制。此最高角色不可修改；下方勾选反映实际生效权限。
          - region "角色权限矩阵，可横向及纵向滚动" [ref=e352]:
            - table [ref=e353]:
              - caption [ref=e354]: 超级管理员 · 功能权限
              - rowgroup [ref=e355]:
                - row [ref=e356]:
                  - columnheader "功能模块" [ref=e357]
                  - columnheader "查看" [ref=e358]
                  - columnheader "新建" [ref=e359]
                  - columnheader "修改" [ref=e360]
                  - columnheader "删除" [ref=e361]
                  - columnheader "导出" [ref=e362]
                  - columnheader "导入" [ref=e363]
              - rowgroup [ref=e364]:
                - row [ref=e365]:
                  - rowheader "经营概览" [ref=e366]
                  - cell [ref=e367]:
                    - checkbox "超级管理员 经营概览 查看" [checked] [disabled] [ref=e369]
                  - cell [ref=e373]:
                    - checkbox "超级管理员 经营概览 新建" [checked] [disabled] [ref=e375]
                  - cell [ref=e379]:
                    - checkbox "超级管理员 经营概览 修改" [checked] [disabled] [ref=e381]
                  - cell [ref=e385]:
                    - checkbox "超级管理员 经营概览 删除" [checked] [disabled] [ref=e387]
                  - cell [ref=e391]:
                    - checkbox "超级管理员 经营概览 导出" [checked] [disabled] [ref=e393]
                  - cell [ref=e397]:
                    - checkbox "超级管理员 经营概览 导入" [checked] [disabled] [ref=e399]
                - row [ref=e403]:
                  - rowheader "报表中心" [ref=e404]
                  - cell [ref=e405]:
                    - checkbox "超级管理员 报表中心 查看" [checked] [disabled] [ref=e407]
                  - cell [ref=e411]:
                    - checkbox "超级管理员 报表中心 新建" [checked] [disabled] [ref=e413]
                  - cell [ref=e417]:
                    - checkbox "超级管理员 报表中心 修改" [checked] [disabled] [ref=e419]
                  - cell [ref=e423]:
                    - checkbox "超级管理员 报表中心 删除" [checked] [disabled] [ref=e425]
                  - cell [ref=e429]:
                    - checkbox "超级管理员 报表中心 导出" [checked] [disabled] [ref=e431]
                  - cell [ref=e435]:
                    - checkbox "超级管理员 报表中心 导入" [checked] [disabled] [ref=e437]
                - row [ref=e441]:
                  - rowheader "客户管理" [ref=e442]
                  - cell [ref=e443]:
                    - checkbox "超级管理员 客户管理 查看" [checked] [disabled] [ref=e445]
                  - cell [ref=e449]:
                    - checkbox "超级管理员 客户管理 新建" [checked] [disabled] [ref=e451]
                  - cell [ref=e455]:
                    - checkbox "超级管理员 客户管理 修改" [checked] [disabled] [ref=e457]
                  - cell [ref=e461]:
                    - checkbox "超级管理员 客户管理 删除" [checked] [disabled] [ref=e463]
                  - cell [ref=e467]:
                    - checkbox "超级管理员 客户管理 导出" [checked] [disabled] [ref=e469]
                  - cell [ref=e473]:
                    - checkbox "超级管理员 客户管理 导入" [checked] [disabled] [ref=e475]
                - row [ref=e479]:
                  - rowheader "联系人" [ref=e480]
                  - cell [ref=e481]:
                    - checkbox "超级管理员 联系人 查看" [checked] [disabled] [ref=e483]
                  - cell [ref=e487]:
                    - checkbox "超级管理员 联系人 新建" [checked] [disabled] [ref=e489]
                  - cell [ref=e493]:
                    - checkbox "超级管理员 联系人 修改" [checked] [disabled] [ref=e495]
                  - cell [ref=e499]:
                    - checkbox "超级管理员 联系人 删除" [checked] [disabled] [ref=e501]
                  - cell [ref=e505]:
                    - checkbox "超级管理员 联系人 导出" [checked] [disabled] [ref=e507]
                  - cell [ref=e511]:
                    - checkbox "超级管理员 联系人 导入" [checked] [disabled] [ref=e513]
                - row [ref=e517]:
                  - rowheader "跟进记录" [ref=e518]
                  - cell [ref=e519]:
                    - checkbox "超级管理员 跟进记录 查看" [checked] [disabled] [ref=e521]
                  - cell [ref=e525]:
                    - checkbox "超级管理员 跟进记录 新建" [checked] [disabled] [ref=e527]
                  - cell [ref=e531]:
                    - checkbox "超级管理员 跟进记录 修改" [checked] [disabled] [ref=e533]
                  - cell [ref=e537]:
                    - checkbox "超级管理员 跟进记录 删除" [checked] [disabled] [ref=e539]
                  - cell [ref=e543]:
                    - checkbox "超级管理员 跟进记录 导出" [checked] [disabled] [ref=e545]
                  - cell [ref=e549]:
                    - checkbox "超级管理员 跟进记录 导入" [checked] [disabled] [ref=e551]
                - row [ref=e555]:
                  - rowheader "报价管理" [ref=e556]
                  - cell [ref=e557]:
                    - checkbox "超级管理员 报价管理 查看" [checked] [disabled] [ref=e559]
                  - cell [ref=e563]:
                    - checkbox "超级管理员 报价管理 新建" [checked] [disabled] [ref=e565]
                  - cell [ref=e569]:
                    - checkbox "超级管理员 报价管理 修改" [checked] [disabled] [ref=e571]
                  - cell [ref=e575]:
                    - checkbox "超级管理员 报价管理 删除" [checked] [disabled] [ref=e577]
                  - cell [ref=e581]:
                    - checkbox "超级管理员 报价管理 导出" [checked] [disabled] [ref=e583]
                  - cell [ref=e587]:
                    - checkbox "超级管理员 报价管理 导入" [checked] [disabled] [ref=e589]
                - row [ref=e593]:
                  - rowheader "订单管理" [ref=e594]
                  - cell [ref=e595]:
                    - checkbox "超级管理员 订单管理 查看" [checked] [disabled] [ref=e597]
                  - cell [ref=e601]:
                    - checkbox "超级管理员 订单管理 新建" [checked] [disabled] [ref=e603]
                  - cell [ref=e607]:
                    - checkbox "超级管理员 订单管理 修改" [checked] [disabled] [ref=e609]
                  - cell [ref=e613]:
                    - checkbox "超级管理员 订单管理 删除" [checked] [disabled] [ref=e615]
                  - cell [ref=e619]:
                    - checkbox "超级管理员 订单管理 导出" [checked] [disabled] [ref=e621]
                  - cell [ref=e625]:
                    - checkbox "超级管理员 订单管理 导入" [checked] [disabled] [ref=e627]
                - row [ref=e631]:
                  - rowheader "供应商管理" [ref=e632]
                  - cell [ref=e633]:
                    - checkbox "超级管理员 供应商管理 查看" [checked] [disabled] [ref=e635]
                  - cell [ref=e639]:
                    - checkbox "超级管理员 供应商管理 新建" [checked] [disabled] [ref=e641]
                  - cell [ref=e645]:
                    - checkbox "超级管理员 供应商管理 修改" [checked] [disabled] [ref=e647]
                  - cell [ref=e651]:
                    - checkbox "超级管理员 供应商管理 删除" [checked] [disabled] [ref=e653]
                  - cell [ref=e657]:
                    - checkbox "超级管理员 供应商管理 导出" [checked] [disabled] [ref=e659]
                  - cell [ref=e663]:
                    - checkbox "超级管理员 供应商管理 导入" [checked] [disabled] [ref=e665]
                - row [ref=e669]:
                  - rowheader "采购管理" [ref=e670]
                  - cell [ref=e671]:
                    - checkbox "超级管理员 采购管理 查看" [checked] [disabled] [ref=e673]
                  - cell [ref=e677]:
                    - checkbox "超级管理员 采购管理 新建" [checked] [disabled] [ref=e679]
                  - cell [ref=e683]:
                    - checkbox "超级管理员 采购管理 修改" [checked] [disabled] [ref=e685]
                  - cell [ref=e689]:
                    - checkbox "超级管理员 采购管理 删除" [checked] [disabled] [ref=e691]
                  - cell [ref=e695]:
                    - checkbox "超级管理员 采购管理 导出" [checked] [disabled] [ref=e697]
                  - cell [ref=e701]:
                    - checkbox "超级管理员 采购管理 导入" [checked] [disabled] [ref=e703]
                - row [ref=e707]:
                  - rowheader "库存" [ref=e708]
                  - cell [ref=e709]:
                    - checkbox "超级管理员 库存 查看" [checked] [disabled] [ref=e711]
                  - cell [ref=e715]:
                    - checkbox "超级管理员 库存 新建" [checked] [disabled] [ref=e717]
                  - cell [ref=e721]:
                    - checkbox "超级管理员 库存 修改" [checked] [disabled] [ref=e723]
                  - cell [ref=e727]:
                    - checkbox "超级管理员 库存 删除" [checked] [disabled] [ref=e729]
                  - cell [ref=e733]:
                    - checkbox "超级管理员 库存 导出" [checked] [disabled] [ref=e735]
                  - cell [ref=e739]:
                    - checkbox "超级管理员 库存 导入" [checked] [disabled] [ref=e741]
                - row [ref=e745]:
                  - rowheader "产品管理" [ref=e746]
                  - cell [ref=e747]:
                    - checkbox "超级管理员 产品管理 查看" [checked] [disabled] [ref=e749]
                  - cell [ref=e753]:
                    - checkbox "超级管理员 产品管理 新建" [checked] [disabled] [ref=e755]
                  - cell [ref=e759]:
                    - checkbox "超级管理员 产品管理 修改" [checked] [disabled] [ref=e761]
                  - cell [ref=e765]:
                    - checkbox "超级管理员 产品管理 删除" [checked] [disabled] [ref=e767]
                  - cell [ref=e771]:
                    - checkbox "超级管理员 产品管理 导出" [checked] [disabled] [ref=e773]
                  - cell [ref=e777]:
                    - checkbox "超级管理员 产品管理 导入" [checked] [disabled] [ref=e779]
                - row [ref=e783]:
                  - rowheader "SKU 管理" [ref=e784]
                  - cell [ref=e785]:
                    - checkbox "超级管理员 SKU 管理 查看" [checked] [disabled] [ref=e787]
                  - cell [ref=e791]:
                    - checkbox "超级管理员 SKU 管理 新建" [checked] [disabled] [ref=e793]
                  - cell [ref=e797]:
                    - checkbox "超级管理员 SKU 管理 修改" [checked] [disabled] [ref=e799]
                  - cell [ref=e803]:
                    - checkbox "超级管理员 SKU 管理 删除" [checked] [disabled] [ref=e805]
                  - cell [ref=e809]:
                    - checkbox "超级管理员 SKU 管理 导出" [checked] [disabled] [ref=e811]
                  - cell [ref=e815]:
                    - checkbox "超级管理员 SKU 管理 导入" [checked] [disabled] [ref=e817]
                - row [ref=e821]:
                  - rowheader "产品分类" [ref=e822]
                  - cell [ref=e823]:
                    - checkbox "超级管理员 产品分类 查看" [checked] [disabled] [ref=e825]
                  - cell [ref=e829]:
                    - checkbox "超级管理员 产品分类 新建" [checked] [disabled] [ref=e831]
                  - cell [ref=e835]:
                    - checkbox "超级管理员 产品分类 修改" [checked] [disabled] [ref=e837]
                  - cell [ref=e841]:
                    - checkbox "超级管理员 产品分类 删除" [checked] [disabled] [ref=e843]
                  - cell [ref=e847]:
                    - checkbox "超级管理员 产品分类 导出" [checked] [disabled] [ref=e849]
                  - cell [ref=e853]:
                    - checkbox "超级管理员 产品分类 导入" [checked] [disabled] [ref=e855]
                - row [ref=e859]:
                  - rowheader "产品参数" [ref=e860]
                  - cell [ref=e861]:
                    - checkbox "超级管理员 产品参数 查看" [checked] [disabled] [ref=e863]
                  - cell [ref=e867]:
                    - checkbox "超级管理员 产品参数 新建" [checked] [disabled] [ref=e869]
                  - cell [ref=e873]:
                    - checkbox "超级管理员 产品参数 修改" [checked] [disabled] [ref=e875]
                  - cell [ref=e879]:
                    - checkbox "超级管理员 产品参数 删除" [checked] [disabled] [ref=e881]
                  - cell [ref=e885]:
                    - checkbox "超级管理员 产品参数 导出" [checked] [disabled] [ref=e887]
                  - cell [ref=e891]:
                    - checkbox "超级管理员 产品参数 导入" [checked] [disabled] [ref=e893]
                - row [ref=e897]:
                  - rowheader "包装管理" [ref=e898]
                  - cell [ref=e899]:
                    - checkbox "超级管理员 包装管理 查看" [checked] [disabled] [ref=e901]
                  - cell [ref=e905]:
                    - checkbox "超级管理员 包装管理 新建" [checked] [disabled] [ref=e907]
                  - cell [ref=e911]:
                    - checkbox "超级管理员 包装管理 修改" [checked] [disabled] [ref=e913]
                  - cell [ref=e917]:
                    - checkbox "超级管理员 包装管理 删除" [checked] [disabled] [ref=e919]
                  - cell [ref=e923]:
                    - checkbox "超级管理员 包装管理 导出" [checked] [disabled] [ref=e925]
                  - cell [ref=e929]:
                    - checkbox "超级管理员 包装管理 导入" [checked] [disabled] [ref=e931]
                - row [ref=e935]:
                  - rowheader "交易单位" [ref=e936]
                  - cell [ref=e937]:
                    - checkbox "超级管理员 交易单位 查看" [checked] [disabled] [ref=e939]
                  - cell [ref=e943]:
                    - checkbox "超级管理员 交易单位 新建" [checked] [disabled] [ref=e945]
                  - cell [ref=e949]:
                    - checkbox "超级管理员 交易单位 修改" [checked] [disabled] [ref=e951]
                  - cell [ref=e955]:
                    - checkbox "超级管理员 交易单位 删除" [checked] [disabled] [ref=e957]
                  - cell [ref=e961]:
                    - checkbox "超级管理员 交易单位 导出" [checked] [disabled] [ref=e963]
                  - cell [ref=e967]:
                    - checkbox "超级管理员 交易单位 导入" [checked] [disabled] [ref=e969]
                - row [ref=e973]:
                  - rowheader "产品证书" [ref=e974]
                  - cell [ref=e975]:
                    - checkbox "超级管理员 产品证书 查看" [checked] [disabled] [ref=e977]
                  - cell [ref=e981]:
                    - checkbox "超级管理员 产品证书 新建" [checked] [disabled] [ref=e983]
                  - cell [ref=e987]:
                    - checkbox "超级管理员 产品证书 修改" [checked] [disabled] [ref=e989]
                  - cell [ref=e993]:
                    - checkbox "超级管理员 产品证书 删除" [checked] [disabled] [ref=e995]
                  - cell [ref=e999]:
                    - checkbox "超级管理员 产品证书 导出" [checked] [disabled] [ref=e1001]
                  - cell [ref=e1005]:
                    - checkbox "超级管理员 产品证书 导入" [checked] [disabled] [ref=e1007]
                - row [ref=e1011]:
                  - rowheader "HS 编码" [ref=e1012]
                  - cell [ref=e1013]:
                    - checkbox "超级管理员 HS 编码 查看" [checked] [disabled] [ref=e1015]
                  - cell [ref=e1019]:
                    - checkbox "超级管理员 HS 编码 新建" [checked] [disabled] [ref=e1021]
                  - cell [ref=e1025]:
                    - checkbox "超级管理员 HS 编码 修改" [checked] [disabled] [ref=e1027]
                  - cell [ref=e1031]:
                    - checkbox "超级管理员 HS 编码 删除" [checked] [disabled] [ref=e1033]
                  - cell [ref=e1037]:
                    - checkbox "超级管理员 HS 编码 导出" [checked] [disabled] [ref=e1039]
                  - cell [ref=e1043]:
                    - checkbox "超级管理员 HS 编码 导入" [checked] [disabled] [ref=e1045]
                - row [ref=e1049]:
                  - rowheader "财务计划" [ref=e1050]
                  - cell [ref=e1051]:
                    - checkbox "超级管理员 财务计划 查看" [checked] [disabled] [ref=e1053]
                  - cell [ref=e1057]:
                    - checkbox "超级管理员 财务计划 新建" [checked] [disabled] [ref=e1059]
                  - cell [ref=e1063]:
                    - checkbox "超级管理员 财务计划 修改" [checked] [disabled] [ref=e1065]
                  - cell [ref=e1069]:
                    - checkbox "超级管理员 财务计划 删除" [checked] [disabled] [ref=e1071]
                  - cell [ref=e1075]:
                    - checkbox "超级管理员 财务计划 导出" [checked] [disabled] [ref=e1077]
                  - cell [ref=e1081]:
                    - checkbox "超级管理员 财务计划 导入" [checked] [disabled] [ref=e1083]
                - row [ref=e1087]:
                  - rowheader "财务流水" [ref=e1088]
                  - cell [ref=e1089]:
                    - checkbox "超级管理员 财务流水 查看" [checked] [disabled] [ref=e1091]
                  - cell [ref=e1095]:
                    - checkbox "超级管理员 财务流水 新建" [checked] [disabled] [ref=e1097]
                  - cell [ref=e1101]:
                    - checkbox "超级管理员 财务流水 修改" [checked] [disabled] [ref=e1103]
                  - cell [ref=e1107]:
                    - checkbox "超级管理员 财务流水 删除" [checked] [disabled] [ref=e1109]
                  - cell [ref=e1113]:
                    - checkbox "超级管理员 财务流水 导出" [checked] [disabled] [ref=e1115]
                  - cell [ref=e1119]:
                    - checkbox "超级管理员 财务流水 导入" [checked] [disabled] [ref=e1121]
                - row [ref=e1125]:
                  - rowheader "数据导入" [ref=e1126]
                  - cell [ref=e1127]:
                    - checkbox "超级管理员 数据导入 查看" [checked] [disabled] [ref=e1129]
                  - cell [ref=e1133]:
                    - checkbox "超级管理员 数据导入 新建" [checked] [disabled] [ref=e1135]
                  - cell [ref=e1139]:
                    - checkbox "超级管理员 数据导入 修改" [checked] [disabled] [ref=e1141]
                  - cell [ref=e1145]:
                    - checkbox "超级管理员 数据导入 删除" [checked] [disabled] [ref=e1147]
                  - cell [ref=e1151]:
                    - checkbox "超级管理员 数据导入 导出" [checked] [disabled] [ref=e1153]
                  - cell [ref=e1157]:
                    - checkbox "超级管理员 数据导入 导入" [checked] [disabled] [ref=e1159]
                - row [ref=e1163]:
                  - rowheader "组织架构" [ref=e1164]
                  - cell [ref=e1165]:
                    - checkbox "超级管理员 组织架构 查看" [checked] [disabled] [ref=e1167]
                  - cell [ref=e1171]:
                    - checkbox "超级管理员 组织架构 新建" [checked] [disabled] [ref=e1173]
                  - cell [ref=e1177]:
                    - checkbox "超级管理员 组织架构 修改" [checked] [disabled] [ref=e1179]
                  - cell [ref=e1183]:
                    - checkbox "超级管理员 组织架构 删除" [checked] [disabled] [ref=e1185]
                  - cell [ref=e1189]:
                    - checkbox "超级管理员 组织架构 导出" [checked] [disabled] [ref=e1191]
                  - cell [ref=e1195]:
                    - checkbox "超级管理员 组织架构 导入" [checked] [disabled] [ref=e1197]
                - row [ref=e1201]:
                  - rowheader "成员管理" [ref=e1202]
                  - cell [ref=e1203]:
                    - checkbox "超级管理员 成员管理 查看" [checked] [disabled] [ref=e1205]
                  - cell [ref=e1209]:
                    - checkbox "超级管理员 成员管理 新建" [checked] [disabled] [ref=e1211]
                  - cell [ref=e1215]:
                    - checkbox "超级管理员 成员管理 修改" [checked] [disabled] [ref=e1217]
                  - cell [ref=e1221]:
                    - checkbox "超级管理员 成员管理 删除" [checked] [disabled] [ref=e1223]
                  - cell [ref=e1227]:
                    - checkbox "超级管理员 成员管理 导出" [checked] [disabled] [ref=e1229]
                  - cell [ref=e1233]:
                    - checkbox "超级管理员 成员管理 导入" [checked] [disabled] [ref=e1235]
                - row [ref=e1239]:
                  - rowheader "权限配置" [ref=e1240]
                  - cell [ref=e1241]:
                    - checkbox "超级管理员 权限配置 查看" [checked] [disabled] [ref=e1243]
                  - cell [ref=e1247]:
                    - checkbox "超级管理员 权限配置 新建" [checked] [disabled] [ref=e1249]
                  - cell [ref=e1253]:
                    - checkbox "超级管理员 权限配置 修改" [checked] [disabled] [ref=e1255]
                  - cell [ref=e1259]:
                    - checkbox "超级管理员 权限配置 删除" [checked] [disabled] [ref=e1261]
                  - cell [ref=e1265]:
                    - checkbox "超级管理员 权限配置 导出" [checked] [disabled] [ref=e1267]
                  - cell [ref=e1271]:
                    - checkbox "超级管理员 权限配置 导入" [checked] [disabled] [ref=e1273]
          - generic [ref=e1277]: 只读配置
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | import fs from 'node:fs/promises'
  3  | import path from 'node:path'
  4  |
  5  | // Uses the existing isolated runner and actual Django/Vite services, no API mocks.
  6  | for (const [name, viewport] of [['desktop', { width: 1440, height: 900 }], ['narrow', { width: 390, height: 844 }]]) {
  7  |   test(`highest role reflects API effective permissions and is read-only (${name})`, async ({ page }) => {
  8  |     await page.setViewportSize(viewport)
  9  |     const response = await page.request.get('/api/organization/overview/')
  10 |     expect(response.status()).toBe(200)
  11 |     const data = await response.json()
  12 |     const role = data.roles.find(item => item.code === 'superadmin')
  13 |     expect(role?.has_all_permissions).toBe(true)
  14 |     expect(role.effective_permissions).toHaveLength(data.modules.length)
  15 |     for (const row of role.effective_permissions) {
  16 |       for (const key of ['can_view', 'can_create', 'can_update', 'can_delete', 'can_export', 'can_import']) expect(row[key]).toBe(true)
  17 |     }
  18 |     const denied = await page.request.post(`/api/access-roles/${role.id}/permission-matrix/`, { data: { permissions: [] } })
  19 |     expect(denied.status()).toBe(400)
  20 |     await page.goto('/organization')
  21 |     const matrix = page.getByRole('region', { name: '角色权限矩阵，可横向及纵向滚动' })
  22 |     await expect(matrix).toBeVisible()
  23 |     await expect(page.getByText('此最高角色不可修改', { exact: false })).toBeVisible()
  24 |     const boxes = matrix.locator('tbody input[type=checkbox]')
  25 |     await expect(boxes).toHaveCount(data.modules.length * 6)
  26 |     for (let index = 0; index < await boxes.count(); index++) {
  27 |       await expect(boxes.nth(index)).toBeChecked()
> 28 |       await expect(boxes.nth(index)).toBeDisabled()
     |                                      ^ Error: expect(locator).toBeDisabled() failed
  29 |     }
  30 |     await fs.mkdir(process.env.EVIDENCE_DIR, { recursive: true })
  31 |     await page.screenshot({ path: path.join(process.env.EVIDENCE_DIR, `highest-role-${name}.png`), fullPage: true })
  32 |     console.log(JSON.stringify({ viewport: name, modules: data.modules.length, checkedDisabled: await boxes.count(), matrixWrite: denied.status() }))
  33 |   })
  34 | }
  35 |
```
