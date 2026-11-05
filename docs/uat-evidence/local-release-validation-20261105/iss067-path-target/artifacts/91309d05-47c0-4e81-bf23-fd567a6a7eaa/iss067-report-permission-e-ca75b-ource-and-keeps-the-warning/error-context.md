# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: iss067-report-permission.spec.js >> employee opening an old unauthorized report URL gets a valid source and keeps the warning
- Location: browser-tests\iss067-report-permission.spec.js:6:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByRole('link', { name: '经营概览', exact: true })
    - locator resolved to <a href="/" class="nav-item">…</a>
  - attempting click action
    - waiting for element to be visible, enabled and stable

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
      - generic [ref=e25]: 客户
      - link "客户管理" [ref=e26] [cursor=pointer]:
        - /url: /customers
    - generic [ref=e33]:
      - generic [ref=e34]: —
      - generic [ref=e36]:
        - strong [ref=e37]: 当前账号：
        - generic [ref=e38]: · 按账号授权
  - main [ref=e39]:
    - generic [ref=e40]:
      - generic [ref=e41]:
        - text: Reports & analytics
        - heading "报表中心" [level=1] [ref=e42]
      - generic [ref=e43]:
        - generic [ref=e44]: 11月5日周四
        - generic [ref=e45]: —
    - generic [ref=e47]:
      - paragraph [ref=e49]: 选择报表、日期口径和日期范围；查询后可继续筛选、下钻或保存图表。
      - form "报表查询" [ref=e50]:
        - group "1. 选择报表与指标" [ref=e51]:
          - generic [ref=e53]:
            - generic [ref=e54]:
              - text: 报表预设
              - combobox "报表预设" [ref=e55]:
                - option "自定义查询" [selected]
                - option "客户增长趋势"
                - option "客户来源分布"
            - paragraph [ref=e56]: 选择预设后可调整条件；点击“查询报表”后，表格中的分组可继续下钻。
          - generic [ref=e57]:
            - generic [ref=e58]:
              - text: 数据来源
              - combobox "数据来源" [ref=e59]:
                - option "客户增长" [selected]
            - generic [ref=e60]:
              - text: 统计维度
              - combobox "统计维度" [ref=e61]:
                - option "时间" [selected]
                - option "来源"
            - generic [ref=e62]:
              - text: 第二统计维度（可选）
              - combobox "第二统计维度（可选）" [ref=e63]:
                - option "不设置" [selected]
                - option "来源"
            - generic [ref=e64]:
              - text: 图表指标
              - combobox "图表指标" [ref=e65]:
                - option "去重单据 / 档案数" [selected]
            - generic [ref=e66]:
              - text: 图表类型
              - combobox "图表类型" [ref=e67]:
                - option "折线图" [selected]
                - option "条形图"
                - option "环形图"
                - option "数据表"
        - group "2. 日期口径与比较" [ref=e68]:
          - generic "日期快捷选择" [ref=e70]:
            - button "近30天" [ref=e71] [cursor=pointer]
            - button "近90天" [ref=e72] [cursor=pointer]
            - button "今天" [ref=e73] [cursor=pointer]
            - button "本周至今" [ref=e74] [cursor=pointer]
            - button "本月至今" [ref=e75] [cursor=pointer]
            - button "本季度至今" [ref=e76] [cursor=pointer]
            - button "本年至今" [ref=e77] [cursor=pointer]
            - button "上月" [ref=e78] [cursor=pointer]
            - button "去年" [ref=e79] [cursor=pointer]
          - generic [ref=e80]:
            - generic [ref=e81]:
              - text: 日期口径
              - combobox "日期口径" [ref=e82]:
                - option "创建时间" [selected]
            - generic [ref=e83]:
              - text: 开始日期
              - textbox "开始日期" [ref=e84]: 2026-01-01
            - generic [ref=e85]:
              - text: 结束日期（含当天）
              - textbox "结束日期（含当天）" [ref=e86]: 2026-11-05
            - generic [ref=e87]:
              - text: 比较方式
              - combobox "比较方式" [ref=e88]:
                - option "上一等长期间" [selected]
                - option "去年同期"
            - generic [ref=e89]:
              - text: 时间粒度
              - combobox "时间粒度" [ref=e90]:
                - option "日"
                - option "月" [selected]
                - option "年"
          - paragraph [ref=e91]: 按档案创建时间统计。
          - paragraph [ref=e92]: 日期口径决定按哪一天统计：销售 / 采购通常按订单日期，账面收支按流水发生日期，银行实际人民币资金按银行实际日期；当前余额只在财务概览余额区使用。
        - group "3. 附加筛选" [ref=e93]:
          - generic [ref=e95]:
            - generic [ref=e96]:
              - text: 筛选维度
              - combobox "筛选维度" [ref=e97]:
                - option "选择维度" [selected]
                - option "来源"
            - generic [ref=e98]:
              - text: 可用值
              - combobox "可用值" [disabled] [ref=e99]:
                - option "请选择" [selected]
            - button "刷新选项" [disabled] [ref=e100]
            - button "添加筛选" [disabled] [ref=e101]
        - generic [ref=e102]:
          - generic [ref=e103]:
            - text: 图表名称
            - textbox "图表名称" [ref=e104]: 客户增长
          - button "查询报表" [ref=e105] [cursor=pointer]
          - button "保存为图表块" [disabled] [ref=e106]
          - generic [ref=e107]: 最多 30 块，仅当前浏览器可用。
        - alert [ref=e108]: 地址中的报表来源当前不可查看，请重新选择查询。
      - region "团队共享模板" [ref=e109]:
        - generic [ref=e110]:
          - generic [ref=e111]:
            - heading "团队共享模板" [level=2] [ref=e112]
            - paragraph [ref=e113]: 模板只保存报表条件；每次使用仍按当前账号的数据权限重新查询。
          - button "刷新" [ref=e115] [cursor=pointer]
        - paragraph [ref=e116]: 当前没有可用的已发布模板。
      - generic [ref=e117]:
        - heading "我的图表块 0 / 30" [level=2] [ref=e118]
        - paragraph [ref=e119]: 保存来源、维度、指标和筛选；日期跟随本页已查询条件。设置仅在当前浏览器保存。
      - paragraph [ref=e120]: 查询后点击“保存为图表块”，下次打开可继续使用。
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | import { mockApi } from './reporting-fixtures.js'
  3  |
  4  | const oldSalesUrl = '/reports?source=sales&group_by=customer&grain=month&date_field=order_date&metric=amount&view=bar&comparison=previous&date_from=2026-09-01&date_to=2026-10-23&filter_country=China'
  5  |
  6  | test('employee opening an old unauthorized report URL gets a valid source and keeps the warning', async ({ page }) => {
  7  |   const state = await mockApi(page, { restricted: true })
  8  |   await page.goto(oldSalesUrl)
  9  |
  10 |   const source = page.getByRole('combobox', { name: '数据来源', exact: true })
  11 |   await expect(source).toHaveValue('customers')
  12 |   await expect(source.locator('option')).toHaveCount(1)
  13 |   await expect(page.getByRole('alert')).toContainText('地址中的报表来源当前不可查看')
  14 |   await expect(page.locator('.report-block')).toHaveCount(0)
  15 |   expect(state.reportRequests).toHaveLength(0)
  16 |   await page.screenshot({ path: test.info().outputPath('employee-old-url-1440.png'), fullPage: true })
  17 |
> 18 |   await page.getByRole('link', { name: '经营概览', exact: true }).click()
     |                                                               ^ Error: locator.click: Test timeout of 30000ms exceeded.
  19 |   await page.goBack()
  20 |   await expect(page).toHaveURL(/source=sales/)
  21 |   await expect(page.getByRole('combobox', { name: '数据来源', exact: true })).toHaveValue('customers')
  22 |   await expect(page.getByRole('alert')).toContainText('地址中的报表来源当前不可查看')
  23 |
  24 |   await page.getByRole('button', { name: '查询报表', exact: true }).click()
  25 |   await expect(page).toHaveURL(/source=customers/)
  26 |   await expect(page).not.toHaveURL(/source=sales/)
  27 |   await expect(page.locator('.reports-page > .report-block .block-kpis')).toBeVisible()
  28 |   expect(state.reportRequests.at(-1).get('source')).toBe('customers')
  29 |
  30 |   await page.getByRole('button', { name: '保存为图表块', exact: true }).click()
  31 |   await expect(page.locator('.saved-block')).toHaveCount(1)
  32 |   await page.reload()
  33 |   await expect(source).toHaveValue('customers')
  34 |   await expect(page.locator('.reports-page > .report-block .block-kpis')).toBeVisible()
  35 |   await expect(page.locator('.saved-block')).toHaveCount(1)
  36 |   await page.screenshot({ path: test.info().outputPath('employee-authorized-source-1440.png'), fullPage: true })
  37 |
  38 |   await page.setViewportSize({ width: 700, height: 1000 })
  39 |   await page.goto(oldSalesUrl)
  40 |   await expect(page.getByRole('combobox', { name: '数据来源', exact: true })).toHaveValue('customers')
  41 |   await expect(page.getByRole('alert')).toContainText('地址中的报表来源当前不可查看')
  42 |   await page.screenshot({ path: test.info().outputPath('employee-old-url-700.png'), fullPage: true })
  43 | })
  44 |
  45 | test('shared template path remains available to an employee with the source permission', async ({ page }) => {
  46 |   const state = { templates: [{ id: 1, name: '团队销售模板', description: '', config: { source: 'sales', group_by: 'country', group_by_2: '', date_field: 'order_date', grain: 'month', metric: 'amount', view: 'bar', comparison: 'previous', title: '团队销售模板', filters: {} }, published: true, published_at: '2026-10-23T09:00:00Z', config_version: 2, can_use: true, can_manage: false }], nextId: 2 }
  47 |   await page.route('**/api/**', async route => {
  48 |     const url = new URL(route.request().url())
  49 |     if (url.pathname.includes('current-operator')) return route.fulfill({ json: { authenticated: true, development_superadmin: false, has_all_permissions: false, rbac_enforcement: true, permissions: { reports: { view: true }, orders: { view: true }, customers: { view: true }, products: { view: true }, skus: { view: true }, categories: { view: true } } } })
  50 |     if (url.pathname === '/api/reports/catalog/') return route.fulfill({ json: { sources: { sales: { label: '销售报表', dimensions: ['time', 'customer', 'country'], dates: { order_date: '订单日期' }, note: '有效销售合同金额。' } }, dimensions: { time: '时间', customer: '客户', country: '国家/地区' }, grains: { month: '月' } } })
  51 |     if (url.pathname === '/api/reports/templates/' && route.request().method() === 'GET') return route.fulfill({ json: { count: state.templates.length, next: null, previous: null, results: state.templates } })
  52 |     if (url.pathname === '/api/reports/data/') return route.fulfill({ json: { source: 'sales', group_by: 'country', date_field: 'order_date', period: { date_from: '2026-01-01', date_to: '2026-10-23' }, comparison_period: { date_from: '2025-01-01', date_to: '2025-10-23' }, comparison: 'previous', totals: { amount: '100', count: 1, quantities: {} }, changes: { amount: 0, count: 0 }, rows: [{ key: 'CN', label: '中国', amount: '100', count: 1, quantities: {} }], filters: {}, filter_summary: [], note: '共享模板测试数据。' } })
  53 |     return route.fulfill({ json: [] })
  54 |   })
  55 |   await page.goto('/reports?shared_template=1&source=sales&group_by=country&date_field=order_date&grain=month&metric=amount&view=bar&comparison=previous&date_from=2026-01-01&date_to=2026-10-23')
  56 |   await expect(page.locator('.active-template-note')).toContainText('团队销售模板')
  57 |   await expect(page.locator('.reports-page > .report-block .block-kpis')).toBeVisible()
  58 | })
  59 |
```
