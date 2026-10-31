# ISS-041-B 真实 Chrome 证据

测试命令：

```text
cd frontend
$env:PLAYWRIGHT_CHANNEL='chrome'
node node_modules/@playwright/test/cli.js test browser-tests/iss041b-evidence.spec.js --config=playwright.config.js
```

结果：**2 passed**，真实 Chrome 截图均在等待 700px 侧栏收起动画后保存。

- [1440px 报表明细截图](reports-detail-1440.png)
- [700px 报表明细截图](reports-detail-700.png)

覆盖内容：销售报表国家 + 客户交叉分组、原始明细面板、历史商品名称、明细金额摘要、操作列、原始订单详情链接，以及窄桌面侧栏收起后的无遮挡布局。
