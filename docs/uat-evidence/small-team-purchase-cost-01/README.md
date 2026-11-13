# SMALL-TEAM-PURCHASE-COST-01

基线：30b3579a579174de5f3e4336619dcdb4c8502470，已核对 SJERP 的 codex/ui-delivery-closeout-04。
状态：待独立复审。关联 ISS-039，沿用原有台账及延期边界。

- 修复前 SQLite 回归：采购合同批准调减后有效金额 90，成本归属 API 返回 100。
- SQLite 定向 87 项通过。标签：test_purchase_costs、test_iss039_shared_purchase_costs、test_reporting、test_finance_drill、test_finance_data_scope，均位于 crm.tests。DATABASE_URL=sqlite:///:memory:。
- 临时 PostgreSQL 17 集群的上述标签首轮 86 项通过。复用 history-product-sku-linking-01/run-postgres.py，以 --test-label 逐一指定。首次在 Windows 沙箱启动失败，使用批准后的沙箱外运行。
- 前端 node --test 的 OrderDetailModal.test.js 和 PurchaseOrderPage.test.js 共 20 项通过，npm run build 通过。
- Chrome 真实前后端，独立 SQLite、合成采购与订单，沿用服务端开发超级管理员。批准 HTTP 201，商品成本 100，合同调整 −10，归属成本 90，订单预计毛利 110。截图依次为 01-approved.png、02-cost.png、03-profit.png。
- 已批准的净合同调整按原归属商品金额计算，稳定排序处理尾差。调整有分以下精度时保留四位。零权重、缺失归属、负有效成本返回明确错误。
- 历史文件、SKU 独立成本、供应商参考价、正式权限及上线验收保留原有边界。未进行受限身份的 Chrome 操作，权限由项目 API 回归覆盖。
