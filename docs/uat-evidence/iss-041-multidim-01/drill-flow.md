# ISS-041-A 下钻记录

1. 初始查询：`国家/地区 + 客户`，日期 `2026-01-01 — 2026-10-22`。
2. 点击“国家/地区： 中国”：增加 `filter_country=中国`，第一维度切换为客户，第二维度清空；日期、来源和其他筛选保留。
3. 点击“客户”分组值：增加客户筛选，第一维度切换为国家/地区，第二维度清空；时间值仅展示，不生成 `filter_time`。
4. 点击“返回上次分析”：恢复原 `country + customer` 配置、原日期范围和 URL 查询条件。

自动化覆盖：`frontend/browser-tests/overview-reports.spec.js` 中的 `two-level groups show separate columns, drill either dimension and return the original query`，真实 Chrome 通过。

截图：

- 下钻后：`screenshots/reports-drill-1440.png`
- 返回后：`screenshots/reports-return-1440.png`
