# ISS-042-FIX-01 共享模板并发版本与删除审计补修

日期：2026-10-23

分支：`codex/iss-042-shared-reports`

基线：`6d5ce10a2ce8a432b427371542eac7378daca655`

## 修复结果

1. 发布和取消发布现在都在 `select_for_update()` 原子事务中校验提交版本、递增 `config_version` 并写入新版本审计。
2. 重复发布或重复取消发布返回 409，不修改状态、不递增版本、不生成虚假审计。
3. 删除后模板不恢复；管理人员可通过原路径 `/api/reports/templates/{id}/history/` 按固定实体和原 ID 读取完整历史。
4. 通用 `/api/operation-logs/` 对 `reports.update` 管理员保留已删除共享模板日志；普通员工只看到当前仍可用模板，不能读取已删除模板历史。
5. 前端已保留并验证 409 刷新提示，不静默覆盖另一名管理员的操作。

## 权限与数据边界

删除后历史查询只允许 `reports.update`。普通 `reports.view` 员工对删除模板的专用历史接口返回 403，对通用操作日志返回空结果；查询只使用 `entity=crm.sharedreporttemplate`，不会混入订单、资金或其他业务审计。

此前已完成的同模板实时数据范围、采购/银行模板来源权限、个人 localStorage 图表和报表核心查询继续通过回归。本轮没有改动报表引擎、数据库模型、实际人民币资金口径或前端布局。

## 浏览器验收边界

真实 Chrome/Playwright 的共享模板测试使用独立 manager/employee browser context 和 mock API，覆盖管理者状态操作、409 提示、跨会话刷新、个人图表保留及 1440/1024/700px 截图。这是前端交互验收，不冒充真实 Django 后端跨账号浏览器集成。

真实 Django 权限、并发、审计和数据范围由后端 SQLite `APIClient` 测试覆盖。当前环境未建立可供 Playwright 登录的 Django 测试服务账号，因此真实后端跨账号浏览器集成保留为后续待办。

## 证据

- 请求/响应及版本序列：`concurrency-and-audit.md`
- 测试命令和原始输出：`test-results.md` 及同目录 `.log`
- Chrome 截图：`manager-1440px.png`、`manager-1024px.png`、`employee-700px.png`、`employee-700px-after-delete.png`

PostgreSQL 和 GitHub CI 继续 PENDING；未创建 PR，不合并 master。
