# UI-DELIVERY-CLOSEOUT-04

共同基线为 `f3b7242e77752b6cc5b72425bcc3df2fa938de61`。U3 的 `39a5c63f2991a775796c8829d293e6b38951e209` 和 `dbec86c9d620002157c0f18bfedb5251204dd3ea` 提供四个专项用例、合成种子和原始记录。当前 CI 的四个专项各有独立数据库和 Chrome 配置，默认遍历三种视口及两档原生缩放。基线的六项通过归原冻结源码，U3 的旧 CI 失败归旧提交。

销售草稿从订单详情打开时暂停该详情的交互，并保留订单和所选标签。关闭时恢复详情与焦点。SKU 上传或清除失败时在编辑器内保留业务提示，重试只发送尚未完成的图片请求。

- [销售草稿修复前截图](../ui-final-state-closeout-03/sales-draft-narrow/chrome-draft-recovery/sales-draft-save-obstructed-390-100.png)
- [SKU 修复前截图](../ui-final-state-closeout-03/sku-recovery-final/chrome-sku-recovery/sku-image-failed-390-125.png)
- [继承状态与原始失败](../ui-final-state-closeout-03/states.md)

完整打印及分页沿用原授权延期。正式部署环境、实际媒体权限、异地备份调度和真实历史资料仍需各自验收。

本轮订单、采购、客户和报价的首轮通过证据来自 `6d63aeca2ebe825c3811cf736b4a3e0cef09346e`。其后的产品差异仅涉及 SKU 提示位置。订单草稿六组在原详情的「订单明细」标签启动，验证编辑器焦点、详情暂停、挂起、受控 400、实际 PUT 200、单次写入、原标签及焦点、继续编辑、放弃修改和重开读回。采购草稿六组验证挂起、受控 400、真实保存及重开。报价修订六组实际生成并打开修订版。

- [订单及采购运行记录](candidate/draft-recovery/chrome-draft-recovery/run.json)
- [报价修订运行记录](candidate/revision-recovery/chrome-revision-recovery/run.json)
- [首次标签回退失败](draft-recovery/chrome-draft-recovery/run.json)
- [逐项状态及剩余清单](remaining.md)

并行包提交 `0bc7ad307c50ebae1c54269348bd941705d136ff` 的 17 个证据文件已接入。38 项结论保留，账户对账通过只覆盖其原视口。银行资金记录与财务流水在 1440×900、390×844 原生 125% 补验通过，实际尾列详情按钮可点击，文档无横向溢出。首跑缺少资金来源关联导致合成事件不可见，补齐真实来源快照后重跑。银行入口保持「银行资金记录」，未执行可选改名。[分支核销报告](../branch-coverage-closeout-01/README.md)

先行候选 `6d63aeca2ebe825c3811cf736b4a3e0cef09346e` 的三个 Linux 专项通过，主 CI 的前端单测阶段失败。调整旧的表单与提示断言后，本地 Node 全量 197 项通过。后续 CI 以新候选自己的运行记录为准。[先行主 CI](https://github.com/Johnson-Yiu/SJERP/actions/runs/43005568492) · [先行 Linux 专项](https://github.com/Johnson-Yiu/SJERP/actions/runs/43005568481)

客户负责人候选加载在六组受控失败后从同一表单真实重试，随后验证负责人选择、创建内嵌联系人、保存失败恢复和从详情单独新增联系人。[客户及联系人运行记录](final/customer-contact/chrome-customer-contact/run.json)

SKU 图片上传及清除错误六组均通过。在提示仍位于视口时可点击重试，上传、清除重试各只发图片请求，重开核对图片。批量部分失败的 Vitest 断言确认成功项不重传，SKU 批量创建只写入一次。最终 SKU 视觉复验绑定产品源码 `f4531b883163db8fff26d67212e37e33792ae991`。[SKU 运行记录](final/sku-recovery/chrome-sku-recovery/run.json) · [390／125% 修复后](final/sku-recovery/chrome-sku-recovery/sku-image-failed-390-125.png)

本地按 CI 命令执行的 Vitest 为 91 文件、841 项通过；Node 全量 197 项、抽屉排版 1 项、生产构建均通过。首次误以默认 Vitest 参数运行的结果不用于认证，随后按工作流配置复跑。


并行补测见 [财务布局](final/finance-retest/chrome-finance-layout/run.json) 和 [首跑记录](final/finance-layout/chrome-finance-layout/run.json)。另在同一产品源码上运行现有工作区集成专项，4 项通过，包括独立草稿、会话状态及客户上下文。最终候选 Actions 见[分支运行列表](https://github.com/Johnson-Yiu/SJERP/actions?query=branch%3Acodex%2Fui-delivery-closeout-04)。


[浏览器 CI 失败归因及原始证据](ci-43007744664/README.md)。浏览器 CI 的客户故障注入修复限于测试和证据。采购草稿状态续验发现单独的初始化时序缺陷。账户对账 390×844 原生 125% 通过真实隔离后台的账户建立、凭证上传、记账、余额与事实查看、凭证入口、展开详情和 CSV。保留原标准两组并加入独立原生缩放模式。[账户详情截图](ci-repair/account-viewport/account-native/account-detail-390-125.png) · [仍待核销状态](remaining.md)

采购草稿原失败证据见 [U3 未保存尝试](../ui-final-state-closeout-03/draft-recovery-retest/chrome-draft-recovery/run.json)。供货选项异步加载完成时建立初始基线，旧顺序在编辑器已经可用时才建立基线。新顺序先完成选项加载、确认当前仍是同一草稿及详情，再建立基线并打开编辑器。回归用例延迟供货选项响应，确认初始化期间编辑器未开放，再验证继续编辑、放弃与重开读回。


在固定产品源码 `d22a30954bf2d69fa9f45b875dddad594d8df8bf` 上，订单及采购草稿的六组均通过。采购未保存确认和数量读回已核销。最终证据提交与该产品树一致。[修后运行](ci-repair/draft-final/chrome-draft-recovery/run.json)
