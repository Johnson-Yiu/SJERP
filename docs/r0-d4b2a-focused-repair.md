# R0-D4B2-A Focused Repair

基线：2a9d6cded67ffb4691f3741ea35ee712ce1f9d42。范围仅供应商 / 采购 Context 及相同嵌套身份遗漏；未开始 B2-B。

## 修复规则

| 数据 | 服务端规则 |
| --- | --- |
| 供应商详情中的共享采购合同 | purchases.view；不按销售员隔离采购合同金额和明细 |
| 嵌套收付款计划 | finance.view |
| 嵌套销售订单 ID、编号、关联分配订单 | orders.view + 客户 Data Scope |
| 已付、待付采购金额 | finance.view + transactions.view；供应商汇总还需 purchases.view |
| 采购记录数量、采购合同金额汇总 | purchases.view |
| 合作产品数量 | products.view |

供应商 Context 传入当前服务端用户；采购序列化同时支持真实 request 或显式服务端 user。缺少身份时仍复用 development_superadmin_enabled() 对应现有权限入口：开发身份保持完整权限，RBAC 环境默认隐藏受限关联和财务字段。未新增身份绕过或修改开发权限。

已排查所有 PurchaseOrderSerializer / SupplierSerializer 嵌套入口，修复订单履约返回、订单生成采购草稿返回、商品供应商关联及供应商候选返回的身份传递。采购 Context 的供应商嵌套也携带当前身份。受限字段在 API JSON 中过滤，不依赖前端隐藏；缺失财务金额在列表显示 —，工作台不显示付款信息，合法 0 金额仍正常显示。

## 回归

新增 11 项 Backend API JSON 测试：无 finance.view、无 orders.view、同部门其他销售员、跨部门客户订单、all 缺少 finance.view、完整授权正常查看、供应商无采购权限的汇总隐藏、缺省身份默认拒绝、显式 user 传递、履约混合关联采购和流水模块缺少权限。前端新增两项实际组件回归，验证受限金额不显示为零，以及合法零付款金额正常显示。

完整 Backend / PostgreSQL / Frontend 由最终 GitHub CI 及本地回归核验。供应商 / 采购真实 UI 截图位于 ux-review-evidence 的 ux-review/r0-d4b2a-finance-scope/focused-repair/。

## 剩余事项

本次 P1 身份及模块遗漏已修复。上一轮已记录的历史销售流水完全丢失客户 / 订单 / 计划归属，仍需业务核对；本轮未猜测或迁移历史归属，不修改记账、余额、分配记录或采购流程。
