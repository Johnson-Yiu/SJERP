# R0-B2 — Supplier Payment Terms → Purchase Payable Plan

2026-10-10。基线 master：a6014b9f66ee6d956a68ce0e406d54772329e73a。

## 实现

- Supplier.payment_terms 保留原文字，仅作为说明/备注，不解析比例或日期。新增 payment_terms_config；空列表表示使用系统默认预付款30%、尾款70%。
- PurchaseOrder 新增 payment_terms_snapshot。新采购复制供应商规则或系统默认；保存后不受供应商后续修改影响。采购草稿可单独调整，正式采购快照纳入敏感字段保护。
- 共用付款阶段编辑器：1至5阶段、名称必填、正比例且严格合计100%、合法日期依据及非负整数天数。合计不符时明确提示并禁止保存。供应商空配置编辑时呈现系统默认，删除全部阶段不能保存为空自定义规则。
- changeSupplier 保留 R0-B1 供货档案、价格和交易单位保护。人工改过本次计划时同一确认框追加付款计划替换提醒；取消完全保留，继续才加载新供应商规则。
- 采购确认下单读取快照生成应付，旧空快照回退30/70。日期依据支持下单日、预计到货日和暂不设日期；预计到货缺失时为null。最后一期吸收四位金额精度的Decimal尾差，合计等于合同金额；极小金额舍入为0的阶段不创建零金额计划，保留既有正金额约束。合同总金额为0仍不生成计划。
- 已有PaymentPlan时不重复生成或改写。采购工作台付款页签只读展示预计日期、阶段、应付、已付、待付、状态。销售计划分支逻辑未改动。

## 迁移与自动验证

迁移：backend/crm/migrations/0072_supplier_payment_terms.py，仅新增两个JSONField，default=list；不回填猜测历史条款，不改写历史计划或付款。

- migration apply PASS；Django check PASS；makemigrations --check --dry-run PASS。
- 后端完整581项PASS（SQLite跳过10项PostgreSQL专用测试）；新增5个测试方法覆盖A至N及非法阶段字段、极小金额尾差。
- 前端完整41文件432项PASS，包含R0-A和R0-B1回归；新增规则编辑器精确比例校验、复制隔离、采购继承/覆盖/切供应商取消/继续、非法计划阻止POST。
- Node完整111项PASS；独立详情排版1项PASS；production build PASS（已有chunk体积提示）。
- 最终提交exact-head CI三个作业与Actions链接在交付回复记录。

## 真实Chrome UAT

使用项目开发环境localhost:5191，Chrome正常视口及缩放；仅通过界面操作专用UAT数据。

1. 已有UAT供应商C（UC）设置50/50，备注文字仍为原30/70。保存后重开仍50/50，证明系统未解析文字。
2. 新采购选择C自动继承50/50；修改首期20%时合计70%，保存按钮禁用且提示合计必须100%。
3. 尾期修改80%，人工付款计划切供应商A出现原自定义确认并追加“更换供应商还将替换本次采购的付款计划。”；取消后C及20/80保留。
4. 专用UI采购PO-2026-00022：USD1000，合同汇率7，下单2026-10-10，预计到货2026-10-30，SKU-000001数量1基础单位，价格1000。保存并重新编辑仍20/80。
5. 确认下单后付款页显示预付款USD200、尾款USD800；日期分别2026-10-10、2026-10-30。两期已付0，待付200/800，待结清。页面无横向溢出，金额和表头完整可读。
6. 回查供应商C仍50/50；未修改其他供应商，未收货、未登记付款，保留PO22供独立审查。

## 截图与范围

仅ux-review-evidence分支：ux-review/r0-b2-payment-terms/

- R0B2_01_supplier_terms.png
- R0B2_02_purchase_terms_inherited.png
- R0B2_03_purchase_terms_override.png（已保存采购重开）
- R0B2_04_generated_payables.png

全部完成，无缺失。原始Chrome截图仅转换JPG→PNG，不裁剪或重绘；图片不进master。

未修改客户条款、Quote/Order、Finance整体UX、成本币种语义、SupplierSKU、库存、RBAC或Dashboard。不建立模板管理中心；不进入R0-C。完成后停止，等待独立ChatGPT审查。
