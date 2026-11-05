# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: access-readiness-highest-role-real.spec.js >> highest role reflects API effective permissions and is read-only (narrow)
- Location: browser-tests\access-readiness-highest-role-real.spec.js:7:3

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: expect(locator).toBeChecked() failed

Locator: getByRole('region', { name: '角色权限矩阵，可横向及纵向滚动' }).locator('tbody input[type=checkbox]').nth(129)
Expected: checked
Error: Test timeout of 30000ms exceeded.

Call log:
  - Expect "toBeChecked" getByRole('region', { name: '角色权限矩阵，可横向及纵向滚动' }).locator('tbody input[type=checkbox]').nth(129) with timeout 5000ms
  - waiting for getByRole('region', { name: '角色权限矩阵，可横向及纵向滚动' }).locator('tbody input[type=checkbox]').nth(129)
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
      - button [ref=e201] [cursor=pointer]
      - generic [ref=e203]:
        - text: Organization & access
        - heading "组织与权限" [level=1] [ref=e204]
      - generic "Johnson" [ref=e206]: J
    - generic [ref=e208]:
      - generic [ref=e209]:
        - generic [ref=e210]:
          - heading "组织与权限" [level=2] [ref=e211]
          - paragraph [ref=e212]: 查看组织架构，按角色维护功能权限。
        - button "刷新" [ref=e213] [cursor=pointer]
      - generic [ref=e218]:
        - strong [ref=e219]: 开发身份：全部功能与数据权限
        - paragraph [ref=e220]: 此页只维护已有角色模板，不改变当前访问模式。正式人员权限与数据范围仍需单独配置和验收。
      - generic [ref=e221]:
        - generic [ref=e222]:
          - generic [ref=e223]: 部门
          - strong [ref=e224]: "5"
        - generic [ref=e225]:
          - generic [ref=e226]: 岗位
          - strong [ref=e227]: "13"
        - generic [ref=e228]:
          - generic [ref=e229]: 角色模板
          - strong [ref=e230]: "15"
        - generic [ref=e231]:
          - generic [ref=e232]: 成员账号
          - strong [ref=e233]: "0"
      - group [ref=e234]:
        - generic "组织架构 部门与岗位" [ref=e235] [cursor=pointer]
      - generic [ref=e236]:
        - complementary [ref=e237]:
          - generic [ref=e239]:
            - heading "角色模板" [level=3] [ref=e240]
            - paragraph [ref=e241]: 共 15 个角色
          - textbox "搜索角色" [ref=e246]:
            - /placeholder: 搜索角色名称或代码
          - button "超级管理员 全部数据" [pressed] [ref=e247] [cursor=pointer]:
            - generic [ref=e248]:
              - strong [ref=e249]: 超级管理员
              - generic [ref=e250]: 全部数据
          - button "管理员 全部数据" [ref=e253] [cursor=pointer]:
            - generic [ref=e254]:
              - strong [ref=e255]: 管理员
              - generic [ref=e256]: 全部数据
          - button "销售主管 本部门及下级" [ref=e259] [cursor=pointer]:
            - generic [ref=e260]:
              - strong [ref=e261]: 销售主管
              - generic [ref=e262]: 本部门及下级
          - button "业务员 仅本人负责" [ref=e265] [cursor=pointer]:
            - generic [ref=e266]:
              - strong [ref=e267]: 业务员
              - generic [ref=e268]: 仅本人负责
          - button "跟单 仅本人负责" [ref=e271] [cursor=pointer]:
            - generic [ref=e272]:
              - strong [ref=e273]: 跟单
              - generic [ref=e274]: 仅本人负责
          - button "运营主管 本部门及下级" [ref=e277] [cursor=pointer]:
            - generic [ref=e278]:
              - strong [ref=e279]: 运营主管
              - generic [ref=e280]: 本部门及下级
          - button "网站运营 仅本人负责" [ref=e283] [cursor=pointer]:
            - generic [ref=e284]:
              - strong [ref=e285]: 网站运营
              - generic [ref=e286]: 仅本人负责
          - button "平台运营 仅本人负责" [ref=e289] [cursor=pointer]:
            - generic [ref=e290]:
              - strong [ref=e291]: 平台运营
              - generic [ref=e292]: 仅本人负责
          - button "仓库主管 本部门及下级" [ref=e295] [cursor=pointer]:
            - generic [ref=e296]:
              - strong [ref=e297]: 仓库主管
              - generic [ref=e298]: 本部门及下级
          - button "仓库员工 本部门" [ref=e301] [cursor=pointer]:
            - generic [ref=e302]:
              - strong [ref=e303]: 仓库员工
              - generic [ref=e304]: 本部门
          - button "财务主管 本部门及下级" [ref=e307] [cursor=pointer]:
            - generic [ref=e308]:
              - strong [ref=e309]: 财务主管
              - generic [ref=e310]: 本部门及下级
          - button "财务员工 本部门" [ref=e313] [cursor=pointer]:
            - generic [ref=e314]:
              - strong [ref=e315]: 财务员工
              - generic [ref=e316]: 本部门
          - button "人事行政主管 本部门及下级" [ref=e319] [cursor=pointer]:
            - generic [ref=e320]:
              - strong [ref=e321]: 人事行政主管
              - generic [ref=e322]: 本部门及下级
          - button "人事 本部门" [ref=e325] [cursor=pointer]:
            - generic [ref=e326]:
              - strong [ref=e327]: 人事
              - generic [ref=e328]: 本部门
          - button "行政 本部门" [ref=e331] [cursor=pointer]:
            - generic [ref=e332]:
              - strong [ref=e333]: 行政
              - generic [ref=e334]: 本部门
        - generic [ref=e337]:
          - generic [ref=e338]:
            - generic [ref=e339]:
              - text: superadmin
              - heading "超级管理员" [level=3] [ref=e340]
              - paragraph [ref=e341]: 系统最高权限，可管理所有业务、成员和权限。
            - generic [ref=e342]:
              - generic [ref=e343]: 默认数据范围（只读）
              - strong [ref=e344]: 全部数据
              - paragraph [ref=e345]: 数据范围当前首先用于客户/CRM/销售记录。产品、SKU、库存等共享主数据不按客户负责人切分。
          - generic [ref=e346]:
            - generic [ref=e347]:
              - text: 查找功能模块
              - textbox "查找功能模块" [ref=e348]:
                - /placeholder: 输入模块名称或代码
            - generic [ref=e349]: 24 / 24 个模块
            - generic [ref=e350]: 当前没有未保存修改
          - paragraph [ref=e351]: 勾选任一操作会同时勾选“查看”；取消“查看”会清除该模块的其他操作权限。筛选只影响显示，保存仍包含全部模块。
          - paragraph [ref=e352]: 包含全部ERP业务权限，不受普通勾选项限制。此最高角色不可修改；下方勾选反映实际生效权限。
          - region "角色权限矩阵，可横向及纵向滚动" [ref=e353]:
            - table [ref=e354]:
              - caption [ref=e355]: 超级管理员 · 功能权限
              - rowgroup [ref=e356]:
                - row [ref=e357]:
                  - columnheader "功能模块" [ref=e358]
                  - columnheader "查看" [ref=e359]
                  - columnheader "新建" [ref=e360]
                  - columnheader "修改" [ref=e361]
                  - columnheader "删除" [ref=e362]
                  - columnheader "导出" [ref=e363]
                  - columnheader "导入" [ref=e364]
              - rowgroup [ref=e365]:
                - row [ref=e366]:
                  - rowheader "经营概览" [ref=e367]
                  - cell [ref=e368]:
                    - checkbox "超级管理员 经营概览 查看" [checked] [disabled] [ref=e370]
                  - cell [ref=e374]:
                    - checkbox "超级管理员 经营概览 新建" [checked] [disabled] [ref=e376]
                  - cell [ref=e380]:
                    - checkbox "超级管理员 经营概览 修改" [checked] [disabled] [ref=e382]
                  - cell [ref=e386]:
                    - checkbox "超级管理员 经营概览 删除" [checked] [disabled] [ref=e388]
                  - cell [ref=e392]:
                    - checkbox "超级管理员 经营概览 导出" [checked] [disabled] [ref=e394]
                  - cell [ref=e398]:
                    - checkbox "超级管理员 经营概览 导入" [checked] [disabled] [ref=e400]
                - row [ref=e404]:
                  - rowheader "报表中心" [ref=e405]
                  - cell [ref=e406]:
                    - checkbox "超级管理员 报表中心 查看" [checked] [disabled] [ref=e408]
                  - cell [ref=e412]:
                    - checkbox "超级管理员 报表中心 新建" [checked] [disabled] [ref=e414]
                  - cell [ref=e418]:
                    - checkbox "超级管理员 报表中心 修改" [checked] [disabled] [ref=e420]
                  - cell [ref=e424]:
                    - checkbox "超级管理员 报表中心 删除" [checked] [disabled] [ref=e426]
                  - cell [ref=e430]:
                    - checkbox "超级管理员 报表中心 导出" [checked] [disabled] [ref=e432]
                  - cell [ref=e436]:
                    - checkbox "超级管理员 报表中心 导入" [checked] [disabled] [ref=e438]
                - row [ref=e442]:
                  - rowheader "客户管理" [ref=e443]
                  - cell [ref=e444]:
                    - checkbox "超级管理员 客户管理 查看" [checked] [disabled] [ref=e446]
                  - cell [ref=e450]:
                    - checkbox "超级管理员 客户管理 新建" [checked] [disabled] [ref=e452]
                  - cell [ref=e456]:
                    - checkbox "超级管理员 客户管理 修改" [checked] [disabled] [ref=e458]
                  - cell [ref=e462]:
                    - checkbox "超级管理员 客户管理 删除" [checked] [disabled] [ref=e464]
                  - cell [ref=e468]:
                    - checkbox "超级管理员 客户管理 导出" [checked] [disabled] [ref=e470]
                  - cell [ref=e474]:
                    - checkbox "超级管理员 客户管理 导入" [checked] [disabled] [ref=e476]
                - row [ref=e480]:
                  - rowheader "联系人" [ref=e481]
                  - cell [ref=e482]:
                    - checkbox "超级管理员 联系人 查看" [checked] [disabled] [ref=e484]
                  - cell [ref=e488]:
                    - checkbox "超级管理员 联系人 新建" [checked] [disabled] [ref=e490]
                  - cell [ref=e494]:
                    - checkbox "超级管理员 联系人 修改" [checked] [disabled] [ref=e496]
                  - cell [ref=e500]:
                    - checkbox "超级管理员 联系人 删除" [checked] [disabled] [ref=e502]
                  - cell [ref=e506]:
                    - checkbox "超级管理员 联系人 导出" [checked] [disabled] [ref=e508]
                  - cell [ref=e512]:
                    - checkbox "超级管理员 联系人 导入" [checked] [disabled] [ref=e514]
                - row [ref=e518]:
                  - rowheader "跟进记录" [ref=e519]
                  - cell [ref=e520]:
                    - checkbox "超级管理员 跟进记录 查看" [checked] [disabled] [ref=e522]
                  - cell [ref=e526]:
                    - checkbox "超级管理员 跟进记录 新建" [checked] [disabled] [ref=e528]
                  - cell [ref=e532]:
                    - checkbox "超级管理员 跟进记录 修改" [checked] [disabled] [ref=e534]
                  - cell [ref=e538]:
                    - checkbox "超级管理员 跟进记录 删除" [checked] [disabled] [ref=e540]
                  - cell [ref=e544]:
                    - checkbox "超级管理员 跟进记录 导出" [checked] [disabled] [ref=e546]
                  - cell [ref=e550]:
                    - checkbox "超级管理员 跟进记录 导入" [checked] [disabled] [ref=e552]
                - row [ref=e556]:
                  - rowheader "报价管理" [ref=e557]
                  - cell [ref=e558]:
                    - checkbox "超级管理员 报价管理 查看" [checked] [disabled] [ref=e560]
                  - cell [ref=e564]:
                    - checkbox "超级管理员 报价管理 新建" [checked] [disabled] [ref=e566]
                  - cell [ref=e570]:
                    - checkbox "超级管理员 报价管理 修改" [checked] [disabled] [ref=e572]
                  - cell [ref=e576]:
                    - checkbox "超级管理员 报价管理 删除" [checked] [disabled] [ref=e578]
                  - cell [ref=e582]:
                    - checkbox "超级管理员 报价管理 导出" [checked] [disabled] [ref=e584]
                  - cell [ref=e588]:
                    - checkbox "超级管理员 报价管理 导入" [checked] [disabled] [ref=e590]
                - row [ref=e594]:
                  - rowheader "订单管理" [ref=e595]
                  - cell [ref=e596]:
                    - checkbox "超级管理员 订单管理 查看" [checked] [disabled] [ref=e598]
                  - cell [ref=e602]:
                    - checkbox "超级管理员 订单管理 新建" [checked] [disabled] [ref=e604]
                  - cell [ref=e608]:
                    - checkbox "超级管理员 订单管理 修改" [checked] [disabled] [ref=e610]
                  - cell [ref=e614]:
                    - checkbox "超级管理员 订单管理 删除" [checked] [disabled] [ref=e616]
                  - cell [ref=e620]:
                    - checkbox "超级管理员 订单管理 导出" [checked] [disabled] [ref=e622]
                  - cell [ref=e626]:
                    - checkbox "超级管理员 订单管理 导入" [checked] [disabled] [ref=e628]
                - row [ref=e632]:
                  - rowheader "供应商管理" [ref=e633]
                  - cell [ref=e634]:
                    - checkbox "超级管理员 供应商管理 查看" [checked] [disabled] [ref=e636]
                  - cell [ref=e640]:
                    - checkbox "超级管理员 供应商管理 新建" [checked] [disabled] [ref=e642]
                  - cell [ref=e646]:
                    - checkbox "超级管理员 供应商管理 修改" [checked] [disabled] [ref=e648]
                  - cell [ref=e652]:
                    - checkbox "超级管理员 供应商管理 删除" [checked] [disabled] [ref=e654]
                  - cell [ref=e658]:
                    - checkbox "超级管理员 供应商管理 导出" [checked] [disabled] [ref=e660]
                  - cell [ref=e664]:
                    - checkbox "超级管理员 供应商管理 导入" [checked] [disabled] [ref=e666]
                - row [ref=e670]:
                  - rowheader "采购管理" [ref=e671]
                  - cell [ref=e672]:
                    - checkbox "超级管理员 采购管理 查看" [checked] [disabled] [ref=e674]
                  - cell [ref=e678]:
                    - checkbox "超级管理员 采购管理 新建" [checked] [disabled] [ref=e680]
                  - cell [ref=e684]:
                    - checkbox "超级管理员 采购管理 修改" [checked] [disabled] [ref=e686]
                  - cell [ref=e690]:
                    - checkbox "超级管理员 采购管理 删除" [checked] [disabled] [ref=e692]
                  - cell [ref=e696]:
                    - checkbox "超级管理员 采购管理 导出" [checked] [disabled] [ref=e698]
                  - cell [ref=e702]:
                    - checkbox "超级管理员 采购管理 导入" [checked] [disabled] [ref=e704]
                - row [ref=e708]:
                  - rowheader "库存" [ref=e709]
                  - cell [ref=e710]:
                    - checkbox "超级管理员 库存 查看" [checked] [disabled] [ref=e712]
                  - cell [ref=e716]:
                    - checkbox "超级管理员 库存 新建" [checked] [disabled] [ref=e718]
                  - cell [ref=e722]:
                    - checkbox "超级管理员 库存 修改" [checked] [disabled] [ref=e724]
                  - cell [ref=e728]:
                    - checkbox "超级管理员 库存 删除" [checked] [disabled] [ref=e730]
                  - cell [ref=e734]:
                    - checkbox "超级管理员 库存 导出" [checked] [disabled] [ref=e736]
                  - cell [ref=e740]:
                    - checkbox "超级管理员 库存 导入" [checked] [disabled] [ref=e742]
                - row [ref=e746]:
                  - rowheader "产品管理" [ref=e747]
                  - cell [ref=e748]:
                    - checkbox "超级管理员 产品管理 查看" [checked] [disabled] [ref=e750]
                  - cell [ref=e754]:
                    - checkbox "超级管理员 产品管理 新建" [checked] [disabled] [ref=e756]
                  - cell [ref=e760]:
                    - checkbox "超级管理员 产品管理 修改" [checked] [disabled] [ref=e762]
                  - cell [ref=e766]:
                    - checkbox "超级管理员 产品管理 删除" [checked] [disabled] [ref=e768]
                  - cell [ref=e772]:
                    - checkbox "超级管理员 产品管理 导出" [checked] [disabled] [ref=e774]
                  - cell [ref=e778]:
                    - checkbox "超级管理员 产品管理 导入" [checked] [disabled] [ref=e780]
                - row [ref=e784]:
                  - rowheader "SKU 管理" [ref=e785]
                  - cell [ref=e786]:
                    - checkbox "超级管理员 SKU 管理 查看" [checked] [disabled] [ref=e788]
                  - cell [ref=e792]:
                    - checkbox "超级管理员 SKU 管理 新建" [checked] [disabled] [ref=e794]
                  - cell [ref=e798]:
                    - checkbox "超级管理员 SKU 管理 修改" [checked] [disabled] [ref=e800]
                  - cell [ref=e804]:
                    - checkbox "超级管理员 SKU 管理 删除" [checked] [disabled] [ref=e806]
                  - cell [ref=e810]:
                    - checkbox "超级管理员 SKU 管理 导出" [checked] [disabled] [ref=e812]
                  - cell [ref=e816]:
                    - checkbox "超级管理员 SKU 管理 导入" [checked] [disabled] [ref=e818]
                - row [ref=e822]:
                  - rowheader "产品分类" [ref=e823]
                  - cell [ref=e824]:
                    - checkbox "超级管理员 产品分类 查看" [checked] [disabled] [ref=e826]
                  - cell [ref=e830]:
                    - checkbox "超级管理员 产品分类 新建" [checked] [disabled] [ref=e832]
                  - cell [ref=e836]:
                    - checkbox "超级管理员 产品分类 修改" [checked] [disabled] [ref=e838]
                  - cell [ref=e842]:
                    - checkbox "超级管理员 产品分类 删除" [checked] [disabled] [ref=e844]
                  - cell [ref=e848]:
                    - checkbox "超级管理员 产品分类 导出" [checked] [disabled] [ref=e850]
                  - cell [ref=e854]:
                    - checkbox "超级管理员 产品分类 导入" [checked] [disabled] [ref=e856]
                - row [ref=e860]:
                  - rowheader "产品参数" [ref=e861]
                  - cell [ref=e862]:
                    - checkbox "超级管理员 产品参数 查看" [checked] [disabled] [ref=e864]
                  - cell [ref=e868]:
                    - checkbox "超级管理员 产品参数 新建" [checked] [disabled] [ref=e870]
                  - cell [ref=e874]:
                    - checkbox "超级管理员 产品参数 修改" [checked] [disabled] [ref=e876]
                  - cell [ref=e880]:
                    - checkbox "超级管理员 产品参数 删除" [checked] [disabled] [ref=e882]
                  - cell [ref=e886]:
                    - checkbox "超级管理员 产品参数 导出" [checked] [disabled] [ref=e888]
                  - cell [ref=e892]:
                    - checkbox "超级管理员 产品参数 导入" [checked] [disabled] [ref=e894]
                - row [ref=e898]:
                  - rowheader "包装管理" [ref=e899]
                  - cell [ref=e900]:
                    - checkbox "超级管理员 包装管理 查看" [checked] [disabled] [ref=e902]
                  - cell [ref=e906]:
                    - checkbox "超级管理员 包装管理 新建" [checked] [disabled] [ref=e908]
                  - cell [ref=e912]:
                    - checkbox "超级管理员 包装管理 修改" [checked] [disabled] [ref=e914]
                  - cell [ref=e918]:
                    - checkbox "超级管理员 包装管理 删除" [checked] [disabled] [ref=e920]
                  - cell [ref=e924]:
                    - checkbox "超级管理员 包装管理 导出" [checked] [disabled] [ref=e926]
                  - cell [ref=e930]:
                    - checkbox "超级管理员 包装管理 导入" [checked] [disabled] [ref=e932]
                - row [ref=e936]:
                  - rowheader "交易单位" [ref=e937]
                  - cell [ref=e938]:
                    - checkbox "超级管理员 交易单位 查看" [checked] [disabled] [ref=e940]
                  - cell [ref=e944]:
                    - checkbox "超级管理员 交易单位 新建" [checked] [disabled] [ref=e946]
                  - cell [ref=e950]:
                    - checkbox "超级管理员 交易单位 修改" [checked] [disabled] [ref=e952]
                  - cell [ref=e956]:
                    - checkbox "超级管理员 交易单位 删除" [checked] [disabled] [ref=e958]
                  - cell [ref=e962]:
                    - checkbox "超级管理员 交易单位 导出" [checked] [disabled] [ref=e964]
                  - cell [ref=e968]:
                    - checkbox "超级管理员 交易单位 导入" [checked] [disabled] [ref=e970]
                - row [ref=e974]:
                  - rowheader "产品证书" [ref=e975]
                  - cell [ref=e976]:
                    - checkbox "超级管理员 产品证书 查看" [checked] [disabled] [ref=e978]
                  - cell [ref=e982]:
                    - checkbox "超级管理员 产品证书 新建" [checked] [disabled] [ref=e984]
                  - cell [ref=e988]:
                    - checkbox "超级管理员 产品证书 修改" [checked] [disabled] [ref=e990]
                  - cell [ref=e994]:
                    - checkbox "超级管理员 产品证书 删除" [checked] [disabled] [ref=e996]
                  - cell [ref=e1000]:
                    - checkbox "超级管理员 产品证书 导出" [checked] [disabled] [ref=e1002]
                  - cell [ref=e1006]:
                    - checkbox "超级管理员 产品证书 导入" [checked] [disabled] [ref=e1008]
                - row [ref=e1012]:
                  - rowheader "HS 编码" [ref=e1013]
                  - cell [ref=e1014]:
                    - checkbox "超级管理员 HS 编码 查看" [checked] [disabled] [ref=e1016]
                  - cell [ref=e1020]:
                    - checkbox "超级管理员 HS 编码 新建" [checked] [disabled] [ref=e1022]
                  - cell [ref=e1026]:
                    - checkbox "超级管理员 HS 编码 修改" [checked] [disabled] [ref=e1028]
                  - cell [ref=e1032]:
                    - checkbox "超级管理员 HS 编码 删除" [checked] [disabled] [ref=e1034]
                  - cell [ref=e1038]:
                    - checkbox "超级管理员 HS 编码 导出" [checked] [disabled] [ref=e1040]
                  - cell [ref=e1044]:
                    - checkbox "超级管理员 HS 编码 导入" [checked] [disabled] [ref=e1046]
                - row [ref=e1050]:
                  - rowheader "财务计划" [ref=e1051]
                  - cell [ref=e1052]:
                    - checkbox "超级管理员 财务计划 查看" [checked] [disabled] [ref=e1054]
                  - cell [ref=e1058]:
                    - checkbox "超级管理员 财务计划 新建" [checked] [disabled] [ref=e1060]
                  - cell [ref=e1064]:
                    - checkbox "超级管理员 财务计划 修改" [checked] [disabled] [ref=e1066]
                  - cell [ref=e1070]:
                    - checkbox "超级管理员 财务计划 删除" [checked] [disabled] [ref=e1072]
                  - cell [ref=e1076]:
                    - checkbox "超级管理员 财务计划 导出" [checked] [disabled] [ref=e1078]
                  - cell [ref=e1082]:
                    - checkbox "超级管理员 财务计划 导入" [checked] [disabled] [ref=e1084]
                - row [ref=e1088]:
                  - rowheader "财务流水" [ref=e1089]
                  - cell [ref=e1090]:
                    - checkbox "超级管理员 财务流水 查看" [checked] [disabled] [ref=e1092]
                  - cell [ref=e1096]:
                    - checkbox "超级管理员 财务流水 新建" [checked] [disabled] [ref=e1098]
                  - cell [ref=e1102]:
                    - checkbox "超级管理员 财务流水 修改" [checked] [disabled] [ref=e1104]
                  - cell [ref=e1108]:
                    - checkbox "超级管理员 财务流水 删除" [checked] [disabled] [ref=e1110]
                  - cell [ref=e1114]:
                    - checkbox "超级管理员 财务流水 导出" [checked] [disabled] [ref=e1116]
                  - cell [ref=e1120]:
                    - checkbox "超级管理员 财务流水 导入" [checked] [disabled] [ref=e1122]
                - row [ref=e1126]:
                  - rowheader "数据导入" [ref=e1127]
                  - cell [ref=e1128]:
                    - checkbox "超级管理员 数据导入 查看" [checked] [disabled] [ref=e1130]
                  - cell [ref=e1134]:
                    - checkbox "超级管理员 数据导入 新建" [checked] [disabled] [ref=e1136]
                  - cell [ref=e1140]:
                    - checkbox "超级管理员 数据导入 修改" [checked] [disabled] [ref=e1142]
                  - cell [ref=e1146]:
                    - checkbox "超级管理员 数据导入 删除" [checked] [disabled] [ref=e1148]
                  - cell [ref=e1152]:
                    - checkbox "超级管理员 数据导入 导出" [checked] [disabled] [ref=e1154]
                  - cell [ref=e1158]:
                    - checkbox "超级管理员 数据导入 导入" [checked] [disabled] [ref=e1160]
                - row [ref=e1164]:
                  - rowheader "组织架构" [ref=e1165]
                  - cell [ref=e1166]:
                    - checkbox "超级管理员 组织架构 查看" [checked] [disabled] [ref=e1168]
                  - cell [ref=e1172]:
                    - checkbox "超级管理员 组织架构 新建" [checked] [disabled] [ref=e1174]
                  - cell [ref=e1178]:
                    - checkbox "超级管理员 组织架构 修改" [checked] [disabled] [ref=e1180]
                  - cell [ref=e1184]:
                    - checkbox "超级管理员 组织架构 删除" [checked] [disabled] [ref=e1186]
                  - cell [ref=e1190]:
                    - checkbox "超级管理员 组织架构 导出" [checked] [disabled] [ref=e1192]
                  - cell [ref=e1196]:
                    - checkbox "超级管理员 组织架构 导入" [checked] [disabled] [ref=e1198]
                - row [ref=e1202]:
                  - rowheader "成员管理" [ref=e1203]
                  - cell [ref=e1204]:
                    - checkbox "超级管理员 成员管理 查看" [checked] [disabled] [ref=e1206]
                  - cell [ref=e1210]:
                    - checkbox "超级管理员 成员管理 新建" [checked] [disabled] [ref=e1212]
                  - cell [ref=e1216]:
                    - checkbox "超级管理员 成员管理 修改" [checked] [disabled] [ref=e1218]
                  - cell [ref=e1222]:
                    - checkbox "超级管理员 成员管理 删除" [checked] [disabled] [ref=e1224]
                  - cell [ref=e1228]:
                    - checkbox "超级管理员 成员管理 导出" [checked] [disabled] [ref=e1230]
                  - cell [ref=e1234]:
                    - checkbox "超级管理员 成员管理 导入" [checked] [disabled] [ref=e1236]
                - row [ref=e1240]:
                  - rowheader "权限配置" [ref=e1241]
                  - cell [ref=e1242]:
                    - checkbox "超级管理员 权限配置 查看" [checked] [disabled] [ref=e1244]
                  - cell [ref=e1248]:
                    - checkbox "超级管理员 权限配置 新建" [checked] [disabled] [ref=e1250]
                  - cell [ref=e1254]:
                    - checkbox "超级管理员 权限配置 修改" [checked] [disabled] [ref=e1256]
                  - cell [ref=e1260]:
                    - checkbox "超级管理员 权限配置 删除" [checked] [disabled] [ref=e1262]
                  - cell [ref=e1266]:
                    - checkbox "超级管理员 权限配置 导出" [checked] [disabled] [ref=e1268]
                  - cell [ref=e1272]:
                    - checkbox "超级管理员 权限配置 导入" [checked] [disabled] [ref=e1274]
          - generic [ref=e1278]: 只读配置
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
> 27 |       await expect(boxes.nth(index)).toBeChecked()
     |                                      ^ Error: expect(locator).toBeChecked() failed
  28 |       await expect(boxes.nth(index)).toBeDisabled()
  29 |     }
  30 |     await fs.mkdir(process.env.EVIDENCE_DIR, { recursive: true })
  31 |     await page.screenshot({ path: path.join(process.env.EVIDENCE_DIR, `highest-role-${name}.png`), fullPage: true })
  32 |     console.log(JSON.stringify({ viewport: name, modules: data.modules.length, checkedDisabled: await boxes.count(), matrixWrite: denied.status() }))
  33 |   })
  34 | }
  35 |
```
