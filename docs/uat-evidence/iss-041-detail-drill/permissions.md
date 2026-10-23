# ISS-041-B 权限与数据范围证据

明细接口 `/api/reports/details/` 在返回任何原始行前执行：

- 报表查看权限；
- 销售来源的订单、客户、产品、SKU查看权限；
- 采购来源的采购单、供应商、产品、SKU查看权限；
- 当前报表维度和附加筛选维度的查看权限；
- 销售订单既有客户数据范围过滤；
- 正式单据状态和 `historical_only=False` 过滤。

自动化覆盖：

- `test_second_dimension_requires_its_own_view_permission`：第二维度客户无查看权限时，交叉汇总返回 403。
- `test_raw_details_require_original_record_permission`：订单原始权限关闭时，明细接口返回 403。
- `test_details_reject_invalid_selection_and_keep_historical_order_out`：时间不能作为普通筛选值；历史订单不进入正式明细。
- 前端 `restricted UI hides sources, export and navigation` 保持旧 URL/保存配置也不能绕过来源权限；服务器权限仍是最终边界。

客户、产品、SKU详情弹窗的“查看经营分析”入口要求 `reports.view` 和对应主数据模块 `view`，并通过内部路径校验保留原详情返回地址。入口只生成 `/reports` 查询，不直接泄露原始业务记录。
