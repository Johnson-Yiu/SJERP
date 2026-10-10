# R0-B1 — Purchase Safety Reconciliation

2026-10-10。修改前master：66b5744eb7cc5969dbd8887b35a8bc6c8cc5d5e7。

## 实现范围

1. 供应商下拉和“查找其他供应商”共用changeSupplier；有供应商来源、已填采购价格（含0）、交易单位任一内容时弹既有自定义确认。取消不改供应商或商品行、不重新加载档案；继续才resetSupplierLine并加载目标供应商档案。匹配面板在确认期间收起，取消后恢复，避免遮挡确认框。确认期间禁止保存。
2. 采购币种变更有已填价格（含0）时确认。取消保留币种、汇率及全部行；继续清除价格，CNY=1、外币汇率留空。仅同币种SupplierSKU参考价可按既有交易换算初始化，不自动换汇。
3. PurchaseOrder serializer 校验当前/本次汇率必须大于0，CNY严格等于1。新采购API必须显式提供汇率，外币不猜测；编辑未提交汇率沿用原合同汇率。原采购来源回归测试补齐显式汇率1以保留其既有测试语义；不是修改业务数据。
4. PurchasePaymentModal 新增“本次实际汇率”：外币默认合同汇率可修改，CNY只读1，提交正数。本次值提交/pay/并使用既有财务服务写Transaction，不修改采购合同汇率；与PaymentPlan入口既有正数/CNY=1服务规则一致。
5. 下单自定义确认框附上0单价条数及赠品/样品提醒。零价采购仍可保存和下单。

未修改Supplier付款条款、30/70计划算法、PaymentPlan架构、OrderItem成本语义、Finance整体UX、Quote/Order、SKU主页面、Dashboard或RBAC。无迁移；不进入R0-B2。

## 改动文件

生产：frontend/src/views/PurchaseOrderPage.vue、frontend/src/components/PurchasePaymentModal.vue、backend/crm/serializers.py。
测试：frontend/tests/purchase-safety.spec.js（新）、purchase-payment.spec.js、purchase-editor-receipt.spec.js、frontend/src/views/PurchaseOrderPage.test.js；backend/crm/tests/test_purchase_safety.py（新）及test_supplier_sku.py、test_sku_plans_candidates.py、test_supplier_allocation.py、test_supplier_batch_binding.py、test_trade_finance_upgrade.py、test_trade_units.py（仅采购API测试显式汇率）。另为本验收文档。

## 自动验证

新增前端13项、后端3个方法（含多币种子用例）：供应商取消/继续及匹配面板确认、币种取消/继续与同币种参考价、实际付款汇率/CNY只读/非正数、Transaction汇率且合同不变、0价提醒和合法下单。

- Frontend完整Vitest：40文件/428项PASS（包含原R0-A测试）。
- Node：111项PASS；独立详情排版1项PASS。
- Backend完整：576项PASS，SQLite跳过10项PostgreSQL专用测试。
- Production build PASS，既有chunk体积提示。
- Django check / makemigrations --check --dry-run PASS，无迁移。
- 最终exact-head三个CI作业及Actions链接在交付回复报告，不以旧提交结果替代。
- 首次PostgreSQL CI发现新增测试供应商编码超出模型两位限制；已将隔离测试夹具改为RB，未修改模型或业务数据，重新执行最终提交CI。

## 真实Chrome UAT

100%缩放，原始截图仅JPG转换PNG，无裁剪/重绘。使用已有UAT供应商及SKU，不写数据库或调用API代替用户页面。

- 选供应商A、SKU-000001，已有供货档案和箱规格、人工价格12.00，切供应商B出现确认。取消供应商仍A、价格12.00、档案和箱规格保持。
- USD/7/12.00切EUR出现确认，取消全保留；继续价格及汇率留空；切CNY不带USD参考价，汇率按规则1。
- “查找其他供应商”选择B亦出现相同确认。取消保留原供应商/行；确认后旧规格清空，载入B的档案及同币种参考价。
- 专用UI新建PO-2026-00021：USD合同汇率7，同SKU两个行，数量各1、单价10及0，总额10。下单弹出1条零价商品提醒，确认后正常已下单。
- 该专用采购登记1 USD测试付款，本次实际汇率7.45，备注明确UAT非真实付款。保存成功，已付1/未付9；重新打开付款默认仍为合同汇率7.000000，合同未改为7.45。
- 仅打开已有CNY采购PO-2026-00001的付款弹窗检查，只读汇率1，关闭未提交。

保留专用采购及测试流水供独立审查；未收货、未修改/删除历史采购或历史流水。Transaction实际汇率字段另由隔离后端测试核实。

## 证据

仅ux-review-evidence分支，目录ux-review/r0-b1-purchase-safety/：

- R0B1_01_supplier_change_confirm.png 完成
- R0B1_02_currency_change_confirm.png 完成
- R0B1_03_actual_payment_rate.png 完成
- R0B1_04_zero_price_warning.png 完成
- R0B1_05_payment_saved.png 补充：保存成功后的采购付款余额

必需4张无缺失。本轮无BLOCKED项。停止，等待独立ChatGPT审查；Supplier付款条款到自动应付计划留给R0-B2，不在本轮处理。
