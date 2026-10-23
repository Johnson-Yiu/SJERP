# R1-ISS-037-P1-FIX-01 历史商业单据展示补修证据

状态：`LOCAL PASS / CI PENDING / FIXED_PENDING_REVIEW`

基线：`98a8aa6075611a562a4b3967c6d253a19d1ae190`，在原分支 `codex/r1-iss-037-p1` 定向补修。没有新增数据库模型或迁移，没有修改历史业务数据、报价/订单/采购快照、金额、搜索或权限体系。

## 修复内容

1. 报价列表使用已保存的 `buyer_company_name`；为空时显示“历史主体未记录”，不再使用实时 `customer_name` 冒充历史买方。存在实时主档差异时单独标注“当前主档”。
2. 报价详情标题使用已保存的 `buyer_company_name`，并单独标注当前客户主档参考。
3. 销售订单“采购与发货”关联采购卡片：草稿使用当前供应商名称；正式采购单使用 `supplier_name_snapshot`；历史快照为空时显示“历史主体未记录”，差异只显示为“当前主档参考”。
4. 保留报价修订链、报价编号、编辑限制、客户关联、采购单链接、状态、金额和履约统计。PI 数据接口和 Excel 导出未改写。

## 自动化测试

以下命令均在本 worktree 执行并退出码为 `0`：

| 命令 | 结果 |
| --- | --- |
| `python manage.py test crm.tests.test_formal_party_snapshots crm.tests.test_contract_lifecycle crm.tests.test_quotes crm.tests.test_procurement crm.tests.test_purchase_order_related_orders --verbosity 1` | 103/103 通过 |
| `python manage.py test`（临时可写 `MEDIA_ROOT`） | SQLite 773 项，跳过13项，`OK` |
| `npm run test:unit` | 140/140 通过 |
| `npm run build` | Vite 生产构建通过；仅有既有 chunk 体积提示 |

全量后端输出中的 Bad Request、Forbidden 和故意注入的 Internal Server Error 是既有负向及事务回滚测试的预期日志；最终汇总为 `Ran 773 tests ... OK (skipped=13)`。

本机无 PostgreSQL 5432 监听，因此未宣称 PostgreSQL 通过；GitHub Actions 继续按额度策略保持 `CI PENDING`。

## 真实 Chrome 验收

使用隔离数据库和真实 Chrome 完成：

- 客户主档为“浏览器客户·原始主体”、报价历史买方为“报价主体原始名称”时，报价列表显示后者，并标注“当前主档：浏览器客户·原始主体”。
- 打开报价详情，标题显示“报价主体原始名称”，PI Excel 导出仍读取报价保存的主体信息。
- 供应商主档为“供应商原始名称”、正式采购快照为“供应商主体原始名称”时，销售订单“采购与发货”卡片显示快照，并标注“当前主档参考：供应商原始名称”。点击采购单后，采购详情仍显示快照。
- 另一条历史采购记录没有供应商快照时，关联采购卡片显示“历史主体未记录”，没有用当前供应商名称填充。

证据文件：

- [报价列表：历史买方主体](quote-list-live.png)
- [报价详情：历史买方主体](quote-detail-live.png)
- [关联采购卡片：历史供应商主体](order-associated-purchase-live.png)
- [采购详情：历史供应商主体](purchase-detail-history-live.png)
- [缺失历史快照：不冒用当前主档](missing-history-live.png)
- [实际 PI Excel 导出](SJ20261021DE998-browser-export.xlsx)

PI Excel 用 `openpyxl` 实际读取，工作表为 `PI`；Buyer Name、Recipient、Address、Email、Tel 均分别为报价保存的历史值，校验输出为 `PI_EXPORT_SNAPSHOT_PASS`。

## 尚未解决事项

- PostgreSQL 和 GitHub CI 未在本轮重复触发/执行；需环境可用或额度恢复后补跑。
- 正式员工 RBAC 仍按上一轮边界，不在本定向 UI 补修中扩大。
- ISS-037 保持 `FIXED_PENDING_REVIEW`，等待 ChatGPT 独立复审，不标记 `CLOSED`。
