# ISS-041-A API 请求记录

## 国家 + 客户

```text
GET /api/reports/data/?source=sales&group_by=country&group_by_2=customer&grain=month&date_field=order_date&metric=amount&view=bar&comparison=previous&date_from=2026-01-01&date_to=2026-10-22
```

响应：`api-country-customer.json`。合计 `33,200` 元、3 笔去重单据、`200 pcs / 10 box`；3 行均包含两个维度的 `groups`。

## 产品分类 + SKU

```text
GET /api/reports/data/?source=sales&group_by=category&group_by_2=sku&grain=month&date_field=order_date&metric=amount&view=bar&comparison=previous&date_from=2026-01-01&date_to=2026-10-22
```

响应：`api-category-sku.json`。金额、去重单据数和各单位数量与国家 + 客户查询的底层订单总计一致，但分组键和分组行不同。

## 自定义未来期间

```text
GET /api/reports/data/?source=sales&group_by=country&grain=month&date_field=order_date&metric=amount&view=bar&comparison=previous&date_from=2026-11-01&date_to=2026-11-30
```

响应：`api-future-custom.json`。返回 1 笔、`9,801` 元，保留自定义报表查询未来期间的能力。

## 最近 12 个自然月

```text
GET /api/reports/data/?source=sales&group_by=time&grain=month&date_field=order_date&metric=amount&view=bar&comparison=previous&date_from=2025-11-01&date_to=2026-10-22
```

响应：`api-time-12-months.json`，返回 2025-11 至 2026-10 共 12 个自然月。

## CSV

```text
GET /api/reports/data/?source=sales&group_by=country&group_by_2=customer&grain=month&date_field=order_date&metric=amount&view=bar&comparison=previous&date_from=2026-01-01&date_to=2026-10-22&export=csv
```

原始导出：`api-country-customer.csv`。CSV 使用现有安全转义，且查询范围、筛选和分组与页面一致。
