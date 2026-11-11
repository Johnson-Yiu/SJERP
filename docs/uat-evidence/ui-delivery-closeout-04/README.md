# UI-DELIVERY-CLOSEOUT-04

共同基线为 `f3b7242e77752b6cc5b72425bcc3df2fa938de61`。U3 的 `39a5c63f2991a775796c8829d293e6b38951e209` 和 `dbec86c9d620002157c0f18bfedb5251204dd3ea` 提供四个专项用例、合成种子和原始记录。当前 CI 的四个专项各有独立数据库和 Chrome 配置，默认遍历三种视口及两档原生缩放。基线的六项通过归原冻结源码，U3 的旧 CI 失败归旧提交。

销售草稿从订单详情打开时暂停该详情的交互，并保留订单和所选标签。关闭时恢复详情与焦点。SKU 上传或清除失败时在编辑器内保留业务提示，重试只发送尚未完成的图片请求。

- [销售草稿修复前截图](../ui-final-state-closeout-03/sales-draft-narrow/chrome-draft-recovery/sales-draft-save-obstructed-390-100.png)
- [SKU 修复前截图](../ui-final-state-closeout-03/sku-recovery-final/chrome-sku-recovery/sku-image-failed-390-125.png)
- [继承状态与原始失败](../ui-final-state-closeout-03/states.md)

完整打印及分页沿用原授权延期。正式部署环境、实际媒体权限、异地备份调度和真实历史资料仍需各自验收。
