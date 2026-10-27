# 120 秒超时调查记录

## 初始现象

ISS-022 和 ISS-075 的真实浏览器场景均在 120 秒附近超时。直接检查专用本地端口后发现，端口上存在前序任务遗留的多个 Django 监听器；同时旧的 Vite 进程会被 Playwright 复用。ISS-022 的混合运行日志出现 `/api/purchase-orders/` 返回 `count:4`，与刚迁移且尚未 seed 采购单的新 SQLite 不符。

这说明初始失败不能直接归因到 MOQ 或付款计划业务。没有通过提高 timeout 掩盖问题。

## 隔离步骤

1. 只清理本轮专用端口 `54127`、`54174` 上的旧进程树。
2. 分别创建并迁移独立 SQLite：`backend/browser-run/iss022/iss022.sqlite3`、`backend/browser-run/iss075/iss075.sqlite3`。
3. 每个端口只启动一个当前 worktree 的 Django 服务。
4. 重新 seed 本轮 fixture，并用 Chrome channel 执行原测试文件。
5. 另行以 `CI=1` 禁止复用旧 Vite 服务，重跑 supplier-ux。

## 隔离后结果

- ISS-022：1 passed，15.3 s；API 日志包含预期的成功请求、MOQ 拒绝请求和带理由的例外提交，最终状态筛选成功。
- ISS-075：1 passed，18.6 s；供应商、采购单、历史付款计划和窄屏布局请求均完成。
- supplier-ux：8 passed，51.0 s；使用新 Vite 进程，不再依赖旧端口状态。

## 结论

本轮没有证据表明 120 秒超时由产品代码、数据库迁移或采购业务流程导致。根因是本地浏览器回归运行环境的进程和数据库未隔离；该环境可靠性改进已在主验收报告中记录为后续事项，但不改变业务代码和正式规则。
