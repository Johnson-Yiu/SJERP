# R0-D4B2-B 采购共享权限

基线：073d3a6。复用服务端 development_superadmin_enabled、模块权限与客户 Data Scope，不更改开发身份配置。

| 业务 | 读取 | 写入 |
| --- | --- | --- |
| 供应商与供应商来源 | suppliers.view，共享 | suppliers 对应动作 |
| 采购单与采购 Context | purchases.view，共享 | purchases 对应动作 |
| 嵌套销售订单 | orders.view + 客户范围 | orders.view/update + 客户范围 |
| 到货 / 冲销 | purchases.view | purchases.update + inventory.create / update |
| 订单供应商分配 | orders.view + 客户范围 + suppliers.view | orders.update；全局推荐还需 suppliers.update |
| 生成采购草稿 | orders.view + 客户范围 | purchases.create + orders.update |
| 成本分配 | purchases.view；受限销售 ID、编号和名称脱敏 | purchases.update；旧、新全部销售归属须满足 orders.view/update + 客户范围 |
| 采购统计与导出 | reports 对应动作 + purchases.view | 不适用 |

采购订单搜索只检索有权查看的来源订单编号。采购审计原始快照仅向 all 范围且有 orders、finance、transactions 查看权限的人员展示；其余保留操作历史并隐藏原始载荷，不改写存储快照。供应商候选中的采购历史遵守 purchases.view。无销售权限仍可执行独立采购及库存成本归属。

## BLOCKED：跨范围委托成本重分摊

当前成本保存整单替换归属并重算所有公共费用，权限模型没有特定订单委托授权。包含无权修改订单时保留共享读取、隐藏受限销售身份，并拒绝整单预览及保存。需要业务确定委托权限或局部调整语义；本轮不新增授权模型。具备全部关联订单权限的部门、部门树或 all 授权人员可正常跨销售员分摊。共享到货及冲销产生的库存、预留派生计算保持原算法，不修改销售合同快照。

本轮不进入 B2-C。
