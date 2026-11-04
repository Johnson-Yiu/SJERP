# InventoryPage 异步与导航回归（2026-11-04）

最终CI补验优先说明：阶段66869e0的inventory-ux HTTP500场景证实直接读取response.detail破坏统一错误策略。已改用现有apiErrorMessage，保留403具体原因和500统一提示；未改浏览器断言或timeout。normalized403夹具及新增500/重试组件回归合跑30/30通过，构建通过。下方29项及“优先detail”描述为早先阶段历史，不作为最终错误实现说明。原始失败与补修日志见主README。

状态：代码修复与组件回归完成，等待协调任务 IAB 视觉验证和独立复审；未提交。

## 范围与依据

- 工作树：`.worktrees/core-workspace-ux-batch-20261104`；读取时 HEAD：`4388947d70d26bca66ca0bfc76b2383a2fc0d404`。
- 已读 AGENTS.md、PROJECT_ISSUES.md、PROJECT_PHASES.md、REVIEW_PROTOCOL.md、InventoryPage 历史提交、R1-REPAIR-04 证据和既有库存工作台回归。历史 ISS-006/013/014/068/069/070 不由本轮自行关闭。
- 所有权：仅 `frontend/src/views/InventoryPage.vue`、新增独立 `frontend/tests/inventory-async-ux.spec.js` 和本文。未修改其他视图、后端、API、业务计算、权限机制、全局配置、CI、依赖或公共台账。协调任务负责公共台账及最终集成。

## 当前代码确认的问题与修复

1. 详情 A 请求未完成时刷新列表，再切到 B 或关闭详情：原 watcher 在 loading=true 时跳过 loadDetail，也没有递增请求序号，A 的成功/失败仍可回填。现在列表刷新及 detail URL 改变立即使旧请求失效，并清除旧详情身份/内容/错误；列表结束后只加载当前 SKU。页面卸载及离页同样使旧任务失效。
2. 搜索防抖与已序列化的 updateQuery 缺少页面生命周期边界：离开库存页时仅 clearTimeout 无法撤销已排入 Promise 队列的路由更新。现在离页守卫、路径变化和卸载更新导航序号，队列执行前检查页面与序号，避免陈旧搜索把用户带回库存页。现有筛选与详情 URL 语义保持。
3. 列表加载异常只读取 Error.message，Axios 403 会显示通用状态码而忽略服务端原因。现在优先显示 response.data.detail，失败仍走 PageLoadState，保留错误/刷新失败/真正空数据的现有区分。列表异步提交增加最新请求及卸载失效检查。

可见文案人工检查：未改正式字段、状态值或业务术语；服务端错误按原文显示，已有“刷新失败，当前显示上一次成功加载的数据”和“请先在 SKU 管理中添加 SKU。”分别用于失败及空结果。

## 自动验证

命令（frontend 目录）：

```text
npx vitest run tests/inventory-async-ux.spec.js tests/inventory-workbench.spec.js --environment jsdom
PASS：2 files，29 tests（独立新增 7 + 既有 22）
```

独立测试使用真实 Vue 挂载、内存 Router、可控 Promise 与 fake timers，不连接业务后端：

- 刷新中切 SKU：旧详情成功和失败分别晚到，只显示最新 SKU 与最新内容。
- 刷新中关闭详情：晚到结果不重开抽屉，重开新 SKU 身份正确。
- 搜索 300ms 防抖触发与离页交错：最终停留订单页。
- 403：展示服务端权限原因，无空库存提示，重试成功。
- 刷新失败：保留上次成功记录；后续成功空数组：显示真正空结果，无残留错误。
- 受限权限：隐藏订单/采购入口与页签，不请求可选 SKU 操作日志。

首次写入测试使用了重复 frontend 前缀，文件创建失败；改为工作目录相对 tests 路径后完成，未改依赖或降低断言。

## IAB 接力与未覆盖

按用户分工未运行本地 Chrome、Playwright 或其他浏览器。以上为组件证据，不能代替视觉验收。协调任务请在 IAB 核验：库存列表搜索后立即跳订单页；打开 SKU 后刷新并切换/关闭详情；网络失败重试；403 与空库存分别显示；桌面详情头部与加载态无旧 SKU 残留。无正式账号/RBAC 启用、业务写入、生产或 CI 验证。旧业务冲销/并发验收不在本轮范围。

最终复跑：同一组件命令再次 PASS，2 files / 29 tests，52.27s（2026-11-04 本机）。`node --test src/views/InventoryPage.test.js` PASS 2/2；`git diff --check` PASS。既有工作台回归含 URL 搜索/排序、详情导航及上下文保留。共享工作树存在其他任务的修改，已核对并未触及或清理。
