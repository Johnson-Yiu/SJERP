# 文案补回后的扩展主体替换复验

2026-11-06：上轮 Chrome 测试 11:16 结束，本次 OrderDetailModal.vue 与 PurchaseDetailModal.vue 文案补回时间为 11:33，故旧运行没有跨越该次修改，旧证据完整保留在 `../browser-recheck-20261106-final/`，不能代表修改后的源码。

本轮基于修改后的工作树运行隔离 SQLite 和真实 Google Chrome，双合成账号，销售和采购桌面与 390px 扩展主体替换：1 项通过，[原始日志](run.log)。基础字段“真实原值 → 已留空”和“未记录 → 已留空”、扩展字段“未知 → 已留空”断言通过；审批后关联草稿保留税号明确空和电话未知。见[销售桌面](extended/order-review-desktop.png)、[销售390](extended/order-review-390.png)、[采购桌面](extended/purchase-review-desktop.png)、[采购390](extended/purchase-review-390.png)、[HTTP](extended/http-results.json)。人工查看采购390截图，差异可读。

含两笔确认收付款（客户和供应商各 USD 2）、一笔采购入库、一笔销售发货的合成原单：[前](extended/source-before.json)与[后](extended/source-after.json)逐项相同，另涵盖三个付款计划、发货明细、两条库存流水及原始资料。此结论限该样本与快照范围。测试前后七个选定业务文件和 spec 的哈希一致，见 `source-hashes-before.json` 与 `source-hashes-after.json`，不代表全仓源码哈希验证。未修改 backend/frontend、未触发 CI；不改变独立复审状态。
