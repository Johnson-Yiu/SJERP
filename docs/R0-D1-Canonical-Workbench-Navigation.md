# R0-D1 — Canonical Workbench Navigation

基线：`6528ae29be808cdef0e8b7322c68f590d6fa9838`。

正式报价、订单和采购单关系行直接打开对应工作台。明细关系进入 `items`，来源关系进入 `overview`。统一导航 helper 支持 `id / tab / returnTo`，兼容原单参数调用；关闭时恢复合法站内来源的详情、标签、筛选及上下文，外部地址回退到本模块列表。跨工作台跳转保留完整来源链。

关联新增按关系角色明确允许；单据明细和纯来源关系不提供新增 SKU 或单据。采购通用详情备用标签顺序为明细、供应商、订单、付款。通用详情指标桌面自适应，窄屏两列或一列。未修改业务规则、权限或其他工作区。

## 验证

- 前端单元测试：115 PASS；Vitest：46 文件、452 测试 PASS；独立排版测试：1 PASS。
- 后端完整测试：614，OK（10 skipped）；采购上下文顺序追加断言单独通过。
- 生产构建 PASS；`makemigrations --check`：No changes detected。
- 新增 focused tests 覆盖正式单据入口、来源恢复、非法来源、关系新增允许列表及单据明细禁止新增；现有跨工作台测试通过实际关闭按钮验证恢复来源。

## 页面验收

Chrome Use 重连失败；根据用户明确授权，使用内置浏览器完成真实页面验收。没有通过 API 或数据库替代界面操作，没有修改业务数据。

- 客户报价记录直接进入报价明细；关闭后恢复客户报价标签。
- 供应商采购记录直接进入采购明细。
- 采购关联订单进入订单概览；关闭后恢复采购关联订单标签，再关闭恢复供应商采购标签。
- 桌面供应商五项指标均匀填充；触及文案人工检查完成。

截图仅存于 `ux-review-evidence` 分支的 `ux-review/r0-d1-canonical-workbench/`：

1. `R0D1_01_customer_quote_workbench.png`
2. `R0D1_02_customer_return.png`
3. `R0D1_03_supplier_purchase_workbench.png`
4. `R0D1_04_cross_workbench_return.png`

最终 production SHA、对应 exact-head CI 与 evidence SHA 以交付报告为准。完成后停止，等待独立审查。
