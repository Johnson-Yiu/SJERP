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
R1_MOQ_02_REAL_UAT=1 VITE_API_PROXY_PORT=8101 PLAYWRIGHT_CHANNEL=chrome npx playwright test browser-tests/r1-moq-02-real.spec.js --config=playwright.config.js --workers=1 --reporter=line --output=test-results-r1-moq-02-fix01
```

结果：`1 passed (13.9s)`。

覆盖内容：

1. 创建数量等于 MOQ 的采购草稿并确认下单。
2. 在草稿编辑页将同一 SupplierSKU 分成两行，每行 3 箱，实时显示合计 60 pcs、MOQ 100 pcs 和差额 40 pcs。
3. 验证交易单位按 1 箱 = 10 pcs 换算，且实时提醒不阻止保存草稿。
4. 取消例外确认，采购单仍保持草稿。
5. 填写例外原因后确认下单。
6. 关闭并重新打开采购单，核对 MOQ 例外原因、格式化后的本地时间、人员和明细。
7. 700px 窄屏检查无水平溢出。

响应日志还记录了低于 MOQ 时第一次确认返回 400、填写原因重试返回 200，以及正常下单返回 200。

## 文件

- `01-normal-draft-list.png`：正常采购草稿
- `02-normal-placed.png`：正常确认下单
- `03-editor-moq-warning.png`：编辑页实时 MOQ 提醒、两行合计和交易单位换算
- `04-low-moq-confirmation.png`：正式确认时的 MOQ 例外提示
- `05-cancel-keeps-draft.png`：取消后仍为草稿
- `06-moq-exception-record.png`：下单后例外记录及本地日期时间
- `07-reopen-exception.png`：重新打开后的历史记录
- `08-narrow-workbench.png`：窄屏工作台
- `browser-log.json`：真实浏览器 API 响应日志
- `migration-compatibility.md`：R1-SKU-01 与本分支 0078 migration 图冲突及安全整合顺序

截图均由真实 Chrome 在上述隔离数据库上生成，未使用模拟图片。
