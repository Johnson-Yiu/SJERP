# Task K1：正式测试前系统完整性收尾

本次收尾聚焦分页可见性、详情页健壮性、经营口径、不可操作入口与文档一致性，不改变已封板的订单、采购、库存、财务或客户业务规则。

## 列表与选择器

DRF 列表 API 默认分页大小为 50。ResourcePage、DocumentPage、ProductPage、PackagingPage、SKUPage 与 QuoteEditorModal 的管理列表和业务选择器使用前端 `listAll()` 汇总分页结果；搜索和现有筛选参数继续传给原 API。`listAll()` 同时兼容分页对象和 `categories/tree`、跟进方式、客户来源等数组型 action 返回值。

## Context 与金额口径

- 独立采购单允许没有销售订单；采购单 Context 在无关联订单时显示“—”，关联订单区块为空，其余供应商、采购明细和付款区块照常提供。
- 产品 Context 只统计 confirmed、production、shipped、completed 正式订单。销售统计按商品行金额乘订单汇率折成人民币；商品订单明细仍显示原币金额和币种。
- 供应商 Context 的正式采购统计只纳入 ordered、partial、completed 采购单。正式采购金额及已付采购款按各采购合同汇率折算人民币；已付金额使用 `PurchaseOrder.paid_amount`，遵循现有 supplier payment、预付款核销及 supplier refund 口径。
- 客户 Context 中列出客户订单商品的区块标为“订单商品记录”，避免与供应商采购混淆。

## 库存与跟进入口

- 自动库存流水只提供查看入口，不显示编辑和删除；详情页不显示通用“编辑主档”。手工库存流水保留列表编辑/删除，编辑类型与后端允许的手工类型一致。
- FollowUp 管理页卡片标记“计划日期已到记录”，提示其统计历史跟进记录；当前待跟进义务以经营概览中客户最新跟进投影为准。

## 导入与报价说明

正式订单 CSV 导入当前关闭。订单需经过报价、订单确认、库存预留、收款计划等正式流程。README 同步说明：保存订单草稿不会接受来源报价，确认订单时最终使用的 Quote / 最终修订版才标为 accepted；来源报价已拒绝或过期时，须创建新的报价修订版后再确认。

本次没有新增数据库字段或 migration。
