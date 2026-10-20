# R1-MOQ-02 真实浏览器验收证据

## 环境

- 日期：2026-10-20
- 浏览器：Google Chrome（Playwright `channel=chrome`，真实浏览器进程）
- 视口：常规桌面 1440×1000；窄屏 700×900
- 后端：独立本机 Django 服务 `127.0.0.1:8101`
- 数据库：独立 SQLite `backend/r1-moq-02-uat.sqlite3`，不使用共享开发数据库
- 验收数据：`UAT-MOQ-SKU` / `UAT-MOQ-SOURCE`，MOQ 100 pcs

## 已执行流程

最终运行命令：

```text
VITE_API_PROXY_PORT=8101 PLAYWRIGHT_CHANNEL=chrome npx playwright test browser-tests/r1-moq-02-real.spec.js --config=playwright.config.js --workers=1 --reporter=line --output=test-results-r1-moq-02g
```

结果：`1 passed (7.3s)`。

覆盖内容：

1. 创建数量等于 MOQ 的采购草稿并确认下单。
2. 创建数量低于 MOQ 的采购草稿，查看实际数量、MOQ 和差额。
3. 取消例外确认，采购单仍保持草稿。
4. 填写例外原因后确认下单。
5. 关闭并重新打开采购单，核对 MOQ 例外原因、时间、人员和明细。
6. 700px 窄屏检查无水平溢出。

响应日志还记录了低于 MOQ 时第一次确认返回 400、填写原因重试返回 200，以及正常下单返回 200。

## 文件

- `01-normal-draft-list.png`：正常采购草稿
- `02-normal-placed.png`：正常确认下单
- `03-low-moq-warning.png`：MOQ 异常与例外原因输入
- `04-cancel-keeps-draft.png`：取消后仍为草稿
- `05-moq-exception-record.png`：下单后例外记录
- `06-reopen-exception.png`：重新打开后的历史记录
- `07-narrow-workbench.png`：窄屏工作台
- `browser-log.json`：真实浏览器 API 响应日志

截图均由真实 Chrome 在上述隔离数据库上生成，未使用模拟图片。
