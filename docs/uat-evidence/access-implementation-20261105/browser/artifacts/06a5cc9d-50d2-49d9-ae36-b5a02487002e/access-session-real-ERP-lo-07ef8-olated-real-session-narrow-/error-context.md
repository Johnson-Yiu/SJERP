# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: access-session-real.spec.js >> ERP login and logout use the isolated real session (narrow)
- Location: browser-tests\access-session-real.spec.js:6:3

# Error details

```
Test timeout of 30000ms exceeded.
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
      - generic [ref=e10]: 客户
      - link "客户管理" [ref=e11] [cursor=pointer]:
        - /url: /customers
    - generic [ref=e18]:
      - generic [ref=e19]: I
      - generic [ref=e21]:
        - strong [ref=e22]: 当前账号：ISS-055 隔离负责人
        - generic [ref=e23]: ISS-055 仅本人客户查看 · 按账号授权
      - button "退出登录" [ref=e24] [cursor=pointer]
  - main [ref=e25]:
    - generic [ref=e26]:
      - button [ref=e27] [cursor=pointer]
      - generic [ref=e29]:
        - text: 客户资料
        - heading "客户管理" [level=1] [ref=e30]
      - generic "ISS-055 隔离负责人" [ref=e32]: I
    - generic [ref=e34]:
      - paragraph [ref=e37]: 维护客户资料和负责人。客户阶段会随报价和订单自动更新。
      - region "页面小计" [ref=e39]:
        - article [ref=e40]:
          - generic [ref=e41]: 客户总数
          - strong [ref=e42]: "1"
          - generic [ref=e43]: 全部客户档案
        - article [ref=e47]:
          - generic [ref=e48]: 正式客户
          - strong [ref=e49]: "0"
          - generic [ref=e50]: 已有正式订单
        - article [ref=e54]:
          - generic [ref=e55]: 待开发
          - strong [ref=e56]: "1"
          - generic [ref=e57]: 尚未成交
        - article [ref=e61]:
          - generic [ref=e62]: 累计销售额
          - strong [ref=e63]: ¥ 0.00
          - generic [ref=e64]: 当前列表累计
      - generic "客户筛选" [ref=e68]:
        - generic [ref=e69]:
          - text: 搜索
          - textbox "搜索客户" [ref=e70]:
            - /placeholder: 名称、编号、国家/地区或负责人
        - generic [ref=e71]:
          - text: 负责人
          - combobox "按负责人筛选客户" [ref=e72]:
            - option "全部负责人" [selected]
            - option "ISS-055 隔离负责人 · ISS-055 隔离销售部"
        - generic [ref=e73]:
          - text: 国家/地区
          - combobox "按国家/地区筛选客户" [ref=e74]:
            - option "全部国家/地区" [selected]
            - option "中国"
        - generic [ref=e75]:
          - text: 状态
          - combobox "按客户状态筛选" [ref=e76]:
            - option "全部状态" [selected]
            - option "线索"
            - option "已联系"
            - option "商机"
            - option "正式客户"
            - option "返单客户"
        - button "重置" [ref=e77] [cursor=pointer]
        - button "刷新" [ref=e78] [cursor=pointer]
      - table [ref=e81]:
        - rowgroup [ref=e82]:
          - row [ref=e83]:
            - columnheader "客户名称" [ref=e84]
            - columnheader "客户编号" [ref=e85]
            - columnheader "状态" [ref=e86]
            - columnheader "国家/地区" [ref=e87]
            - columnheader "业务区域" [ref=e88]
            - columnheader "负责人" [ref=e89]
            - columnheader "下次跟进" [ref=e90]
            - columnheader "订单数" [ref=e91]
            - columnheader "累计销售额" [ref=e92]
            - columnheader "操作" [ref=e93]
        - rowgroup [ref=e94]:
          - row [ref=e95] [cursor=pointer]:
            - cell "ISS-055 有权客户" [ref=e96]
            - cell "ISS055-VISIBLE" [ref=e98]
            - cell "线索" [ref=e99]
            - cell "中国" [ref=e101]
            - cell "—" [ref=e102]
            - cell "ISS-055 隔离负责人" [ref=e103]
            - cell "—" [ref=e104]
            - cell "—" [ref=e105]
            - cell "—" [ref=e106]
            - cell [ref=e107]:
              - button "查看详情" [ref=e109]
```