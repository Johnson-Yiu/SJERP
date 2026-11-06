# 扩展主体替换 Chrome 复验（2026-11-06）

结果：通过。基线 HEAD `506b14f293fe8fcb989eeaf1c5d35866624553ad`，使用当时工作树的未提交修改；本次运行前后所列 7 个相关源码和 spec 的 SHA-256 一致，见 `source-hashes-before.json` 和 `source-hashes-after.json`，不能据此推断全部工作树文件均未变化。隔离 SQLite 和媒体、两个合成认证账号、真实 Google Chrome，开发超级管理员模式；不代表自然人独立或正式 RBAC 验收。

`party-replacement-extended-20261106.spec.js` 1 项通过，覆盖销售订单及采购订单：桌面申请，桌面和 390px 审批差异，独立账号审批并创建关联草稿。[实际运行日志](run.log)、[HTTP及申请快照](extended/http-results.json)。对基础字段逐项断言真实原值 → 已留空；采购联系人断言未记录 → 已留空；扩展税号断言未知 → 已留空。人工查看[销售桌面](extended/order-review-desktop.png)与[采购390](extended/purchase-review-390.png)；另存[销售390](extended/order-review-390.png)、[采购桌面](extended/purchase-review-desktop.png)。

新草稿资料接口确认税号为空字符串、电话为 null、账单地址为新值，见[销售](extended/order-result-details.json)和[采购](extended/purchase-result-details.json)。原单合成样本包含确认客户收款 USD 2、确认供应商付款 USD 2、采购入库 1、销售发货 1；[前](extended/source-before.json)与[后](extended/source-after.json)逐项相同，覆盖两张原单、两笔流水、三个付款计划、一笔入库、一笔发货及明细、两条库存流水和原始扩展资料。结果仅证明该合成样本和快照范围。

此前基础主体差异显示缺陷在本次覆盖的销售和采购场景未再复现；不自行关闭等待独立复审的问题。控制台仍记录既有 Vue Transition 警告，本次没有判断其业务影响。未修改业务代码，未触发 CI；测试和报告完成后停止修改。
