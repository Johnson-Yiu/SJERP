# 销售订单前端定向检查（2026-11-04）

基线：`4388947d70d26bca66ca0bfc76b2383a2fc0d404`；工作树：`.worktrees/core-workspace-ux-batch-20261104`；分支：`codex/core-workspace-ux-batch-20261104`。未提交。

已读取 AGENTS、PROJECT_ISSUES、PROJECT_PHASES、REVIEW_PROTOCOL、销售安全历史 `docs/R0-A-Sales-Safety-Reconciliation.md`，并检查 DocumentPage 最近修改历史。订单入口实际由 `frontend/src/views/DocumentPage.vue` 承载；未修改 ResourcePage、历史订单页、采购、库存或其他代理的文件。公共台账和最终集成由协调任务维护。

## 本轮确认及修复

| 本地标识（供协调登记） | 复现步骤与修复前表现 | 最小修复 | 状态 |
| --- | --- | --- | --- |
| SALES-ASYNC-01 | 在 `/orders` 快速依次筛选已确认、已完成；延迟第一个请求。旧请求最后成功时覆盖当前列表，旧请求失败时显示无关错误，并提前结束当前加载状态。空列表触发的“是否有订单”辅助请求也可迟到修改加载/空态。 | 为订单请求记录序号和资源上下文；主请求及辅助请求的结果、异常、finally 均检查有效性。卸载时失效。也防止共享页面从报价切到订单后接收旧订单/报价结果。报价独立请求原行为保留。 | FIXED_PENDING_REVIEW |
| SALES-SAVE-02 | 新建订单、载入有效报价、提交保存，在 POST 未完成时点击关闭或尝试导航。原表单可关闭，保存回调随后仍会导航至订单详情。 | 复用现有 unsaved guard 的 busy 入口，仅订单编辑器打开且 saving 时阻止关闭/离开；保存成功关闭编辑器后，既有内部导航继续执行；失败保留草稿并解除 busy。 | FIXED_PENDING_REVIEW |
| SALES-SOURCE-03 | 新建订单，选择来源报价，响应前关闭表单；随后报价请求失败，旧错误仍在列表页弹出。 | 错误提示同成功回填一样检查 sourceQuoteRequest；卸载也使来源请求失效。有效请求使用现有 apiErrorMessage 显示接口错误。 | FIXED_PENDING_REVIEW |

不改变业务校验、保存载荷、状态、快照、权限来源、开发超级管理员身份、API 或后端。页面文案人工核查：原销售订单文案和正式业务术语保留；未修改布局/样式、金额、财务展示条件或打印导出。

## 自动验证

独立回归文件：`frontend/tests/sales-orders-async.spec.js`，通过真实 Vue 挂载、内存路由和受控 Promise 验证；API 均为 mock，不代表真实后端验收。

- 修复前：将本任务独占的 DocumentPage 临时恢复为 HEAD 版本，运行最初 5 项测试，5 项全部按预期失败；finally 恢复修复代码。证据：[sales-orders-before.log](sales-orders-before.log)。日志落盘后控制台打印遇到 Windows GBK 无法编码 Vitest 符号，日志完整，源码已在 finally 恢复；不是测试环境失败。
- 首轮修复后：销售异步 5 项 + sales-safety + ux-copy-sales-purchase，合计 32/32 通过。
- 最终补充：增加旧空态辅助请求、当前错误重试和保存失败草稿保留，销售异步共 8 项；与 sales-safety、ux-copy-sales-purchase、route-lifecycle 组合共 4 文件、60/60 通过，见 [sales-orders-after.log](sales-orders-after.log)。
- `node --test frontend/src/views/DocumentPage.test.js`：17/17 通过。
- `git diff --check -- frontend/src/views/DocumentPage.vue frontend/tests/sales-orders-async.spec.js`：通过。

协调任务全量 Node 检查发现 `TaskK1Pagination.test.js` 仍要求旧语法 `rows.value = await listAll`，并直接插入 `props.type`。这是过时的源码形态断言：现在先捕获资源上下文，再获取全部分页结果、检查请求有效性、最后赋给 rows。仅替换该断言，检查资源捕获及 fetch → guard → assignment 顺序；所有其他分页加载器和选择器断言保留，不回退产品修复。补修仅运行该 Node 文件，未启动额外大型测试或干扰协调任务全量 Vitest。

补修验证：`node --test frontend/src/views/TaskK1Pagination.test.js` 1/1 通过；上述测试及本报告 `git diff --check` 通过。

最终定向命令（frontend 目录）：

```powershell
node node_modules/vitest/vitest.mjs run tests/sales-orders-async.spec.js tests/sales-safety.spec.js tests/ux-copy-sales-purchase.spec.js tests/route-lifecycle.spec.js
```

## 交协调任务验收

用户后续明确由协调任务负责真实后端及 IAB 全页验证，并要求本代理不启动本地 Chrome。因此本代理没有运行 Chrome/IAB、没有浏览器截图，也不宣称完成视觉或真实 API 验收。曾准备的独立浏览器测试文件已删除；本代理启动的临时 Vite 5279 已停止。另一次尝试 5207 被占用未启动，未停止其他服务。

建议使用合成订单和报价，在协调环境补验：

1. 桌面及窄屏订单列表快速切换状态/搜索，延迟或拒绝旧请求；当前筛选结果及加载状态不被旧响应覆盖；当前请求失败仍可重试。
2. 让筛选返回空结果，辅助请求迟到，再切另一筛选；辅助结果不结束最新加载。
3. 保存 POST 等待中尝试取消、关闭及导航；均不丢失当前表单。成功后按原规则进入返回 ID 的详情；失败保留输入并可继续编辑/关闭。
4. 来源报价请求等待时关闭表单；之后失败不弹旧错误；重新新建不回填旧报价。
5. 原客户/SKU 上下文、返回来源页、开发超级管理员动作入口、草稿编辑/删除限制按既有规则核验。受限权限和真实后端鉴权不在本代理证据内。

上述三项待独立复审；未新增/关闭公共 Issue，未改台账、后端、API、CI、依赖、采购/库存、打印或财务模块；未提交、推送、部署。生产构建和全量测试由协调任务统一执行。
