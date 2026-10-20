# 真实 Chrome 联合流程记录

## 执行方式

工作目录：临时集成 worktree 的 `frontend/`。

实际命令：

```powershell
$env:PLAYWRIGHT_CHANNEL='chrome'; npx playwright test --config=playwright.joint.config.js --reporter=line; $code = $LASTEXITCODE; Write-Output "EXIT_CODE=$code"; exit $code
```

结果：`Running 1 test using 1 worker`，`1 passed (11.1s)`，`EXIT_CODE=0`。测试使用 Playwright 的 Chrome channel，非模拟图片或静态 DOM 文本检查。

## 已完成的联合操作

在采购编辑弹窗中：

1. 选择供应商并打开 SKU 选择器。
2. 在 1440px 和 700px 视口搜索并选择 SKU A。
3. 查看库存参考：实际库存 100、已预留 30、可用库存 70、在途采购 40。
4. 输入采购数量 12，确认 MOQ 提醒显示实际数量 12、MOQ 100、差额 88。
5. 打开库存记录与差异，检查当前供应来源、历史采购快照标签及仓库信息。
6. 切换到 SKU B，确认库存参考随 SKU 更新。
7. 取消选择 SKU B，确认原 SKU A 的采购数量 12 未被库存参考改写。
8. 检查页面无水平溢出；700px 下 SKU 列表可见、可勾选、可取消。

## 截图

- [1440px 联合流程](joint-moq-inventory-1440.png)：库存参考、MOQ 实际数量/MOQ/差额以及采购编辑布局。
- [700px 联合流程](joint-moq-inventory-700.png)：窄屏 SKU 列表、选择状态和库存参考区域。

截图由真实 Chrome 流程写入本目录。由于本轮是证据补齐，截图中的业务数据为隔离浏览器测试夹具；不代表生产数据。

## 未覆盖项

本次联合流程未替代完整生产验收；尤其未在本轮执行 PostgreSQL，也未在正式分支提交临时 Playwright 测试脚本。相关限制已在 `execution-log.md` 记录。
