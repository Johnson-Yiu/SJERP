# R1-INV-03-FIX-01 浏览器测试日志

```text
2026-10-20 真实 Chrome / Playwright channel=chrome
route: /purchase-orders?create=1
viewports: 1440x900, 1024x900, 700x900

[PASS] 1440px: SKU列表可见，勾选 A/B，库存参考显示 B 的 20 box / 20 box / 0 box / 5 box，查看差异成功。
[PASS] 1024px: SKU列表可见，勾选 A/B，库存参考显示 B 的 20 box / 20 box / 0 box / 5 box，查看差异成功。
[PASS] 700px: SKU列表可见且可滚动，勾选 A/B，库存参考显示 B 的 20 box / 20 box / 0 box / 5 box，查看差异成功。
[PASS] 取消 B 后只保留 A，A 的采购数量输入 12 未改变，当前库存参考回到 A。
[PASS] 快速切换：A 的库存响应延迟 320ms，B 先返回；等待迟到响应后当前仍为 B，B 的库存 20 未被 A 的 100 覆盖。
[PASS] 差异记录显示：北区成品仓、PO-FIX-001、防潮袋、客户 LOGO 待确认。
[PASS] 1440/1024/700 页面 document.scrollWidth <= innerWidth。

[REAL CHROME] 可见 Chrome 实际操作：选择 INV3-STOCKED-001 后显示 100/30/70/40 pcs；点击“查看库存记录与差异”展开流水；切换 INV3-EMPTY-002 显示 0/0/0/0 box；填写采购数量 12，取消无库存 SKU 后回到有库存 SKU，数量仍为 12。
```

首次运行曾因受管 worktree 无法创建 Playwright `test-results` 目录而在测试步骤前失败；授权运行后按同一提交重新执行并通过，未因此修改业务代码。
