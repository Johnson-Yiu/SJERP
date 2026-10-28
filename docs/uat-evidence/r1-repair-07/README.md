# R1-REPAIR-07：订单列表 390px 布局验收

## 结论

已完成最小布局修复。订单列表在 390、700、1024、1440px 下均未产生页面级横向溢出；重置按钮保持单行；订单表格仍通过现有 `.table-wrap { overflow: auto; }` 横向查看完整列。

未修改业务规则、共享台账、财务逻辑，也未使用全局 `overflow-x: hidden`。

## 版本与环境

- 任务：`R1-REPAIR-07`
- 基线：`054bd82518039a5bc0e0c14234964a14d7fbbfd8`
- 分支：`codex/repair-orders-390-layout`
- 独立 worktree：`C:\Users\Johnson\.codex\worktrees\repair-orders-390-layout\森爵照明管理系统`
- 前端：Vite 8.3.5，Node `npm run` 脚本
- 浏览器：Playwright `PLAYWRIGHT_CHANNEL=chrome`，并用 Chrome 本地预览进行人工视觉检查

390/700/1024/1440px 的布局截图使用真实 Chrome 渲染，API 在测试内返回固定的两条订单数据，以便隔离布局变量；另用 Chrome 打开本地真实 API 预览确认订单管理页、筛选器和真实订单表格正常加载。

## 根因与修复

根因在订单工具栏沿用单行 flex 布局：搜索框、两个筛选框和重置按钮的最小内容宽度叠加，且订单筛选框有 `min-width: 120px`，重置按钮没有禁止换行。390px 下工具栏内容把文档宽度推到 393px，按钮文字因此被压缩为两行。

修复位于 [`frontend/src/views/DocumentPage.vue`](../../../frontend/src/views/DocumentPage.vue:550)：

- 仅对非报价工具栏（订单列表）改用四列 grid；
- 760px 以下改为两列，搜索框占满一行，重置按钮独占一行；
- 订单筛选框允许在网格中收缩，重置按钮使用 `white-space: nowrap`；
- 未修改 `.table-wrap` 或表格最小宽度，保留原有横向滚动行为。

## DOM 实测数据

数据文件：[`before-dom-390.json`](before-dom-390.json)、[`after-dom-390.json`](after-dom-390.json) 等同目录 JSON 文件。

| 视口 | 修复前文档 / body 宽度 | 修复后文档 / body 宽度 | 重置按钮 white-space（前 → 后） | 修复后表格容器 client / scroll 宽度 | 结论 |
|---:|---:|---:|---|---:|---|
| 390px | 393 / 393px | 390 / 390px | `normal` → `nowrap` | 364 / 1071px | 可滚动，最大横向偏移 707px |
| 700px | 700 / 700px | 700 / 700px | `normal` → `nowrap` | 662 / 1071px | 可滚动，最大横向偏移 409px |
| 1024px | 1024 / 1024px | 1024 / 1024px | `normal` → `nowrap` | 706 / 1071px | 侧栏占位下可滚动，最大横向偏移 365px |
| 1440px | 1440 / 1440px | 1440 / 1440px | `normal` → `nowrap` | 1122 / 1122px | 完整列在容器内显示，无需滚动 |

测试还将 390、700、1024px 的 `.table-wrap.scrollLeft` 从 0 设置到最大值并断言实际到达最大偏移；对应右侧列截图见下方。

## 截图证据

修复前：

- [390px](before-390.png) · [700px](before-700.png) · [1024px](before-1024.png) · [1440px](before-1440.png)

修复后：

- [390px](after-390.png) · [700px](after-700.png) · [1024px](after-1024.png) · [1440px](after-1440.png)
- 表格横向滚动到右侧：[390px](after-390-table-right.png) · [700px](after-700-table-right.png) · [1024px](after-1024-table-right.png)

## 验证结果

- 定向真实 Chrome 回归：`R1_REPAIR_07_PHASE=before/after npx playwright test browser-tests/orders-390-layout.spec.js --reporter=line`：修复前基线 4/4，修复后最终 4/4。
- 订单页面相关单元测试：`npm run test:unit -- src/views/DocumentPage.test.js`：17/17 通过。
- 生产构建：`npm run build`：通过；保留现有主 JS chunk 大于 500 kB 的 Vite 警告，本次布局修改未引入新的构建错误。
- Chrome 本地真实 API 预览：订单管理页、筛选器、表格和现有订单记录正常加载；未执行业务写入操作。

本任务未修改 `docs/PROJECT_ISSUES.md`、`docs/PROJECT_PHASES.md` 或其他共享台账，未合并 master，未关闭 Issue，未部署，提交使用 `[skip ci]` 以暂停 CI。
